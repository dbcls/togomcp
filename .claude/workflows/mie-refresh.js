export const meta = {
  name: 'mie-refresh',
  description: 'Batch-build/revise MIE files (one mie-builder agent per database), then independently re-validate each against the live endpoint',
  whenToUse: 'Quarterly refresh of many MIE files, or onboarding several new RDF databases at once. For a single user-steered file, run the mie-generator skill in the main thread instead.',
  phases: [
    { title: 'Build', detail: 'one mie-builder agent per database — runs the full mie-generator procedure' },
    { title: 'Re-validate', detail: 'independent agent re-runs every query + sample ASK from the written file; does NOT trust the builder' },
  ],
}

// args: an array of db keys  ["glycosmos","bgee"]  OR  { databases:[...], server:"togomcp-dev" }
const input = args || {}
const databases = Array.isArray(input) ? input : (input.databases || [])
const server = (Array.isArray(input) ? null : input.server) || 'togomcp-dev'

if (!databases.length) {
  log('mie-refresh: no databases provided. Pass args as ["glycosmos", ...] or {databases:[...]}.')
  return { error: 'no databases provided', databases: [] }
}
log(`mie-refresh: ${databases.length} database(s) → server ${server}`)

const BUILD_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    database: { type: 'string' },
    file_path: { type: 'string' },
    mode: { type: 'string', enum: ['created', 'revised'] },
    validation_summary: { type: 'string', description: 'Phase 6 declaration block verbatim' },
    unverifiable: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['database', 'file_path', 'mode', 'validation_summary'],
}

const VALIDATE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    database: { type: 'string' },
    yaml_parses: { type: 'boolean' },
    queries_total: { type: 'integer' },
    queries_passed: { type: 'integer' },
    queries_failed: { type: 'integer' },
    sample_entries_total: { type: 'integer' },
    sample_entries_passed: { type: 'integer' },
    failures: { type: 'array', items: { type: 'string' }, description: 'one line per failing query/entry: what it was + the error or 0-row symptom' },
    verdict: { type: 'string', enum: ['PASS', 'FAIL'] },
  },
  required: ['database', 'verdict', 'queries_total', 'queries_passed', 'queries_failed'],
}

const buildPrompt = (db) => `Generate or revise the MIE file for database "${db}".
Use the togomcp server "${server}". Follow .claude/skills/mie-generator/SKILL.md end to end,
including all of Phase 5 validation. Target file: togo_mcp/data/mie/${db}.yaml.
Return your machine-readable report per your output contract.`

const validatePrompt = (db) => `INDEPENDENT re-validation of an MIE file. Trust NOTHING from any prior report.

Target file: togo_mcp/data/mie/${db}.yaml  (database key: "${db}")

Steps:
1. Read the file. Confirm it parses as YAML:
   Bash: python3 -c "import yaml; yaml.safe_load(open('togo_mcp/data/mie/${db}.yaml'))"
2. Load the SPARQL tool: ToolSearch "select:mcp__${server.replace(/-/g, '_')}__run_sparql"
   (if that exact name is unavailable, ToolSearch "run_sparql ${server}" and pick the matching tool).
3. Extract and RE-RUN every SPARQL block against database "${db}":
   - each sparql_query_examples[].sparql
   - each anti_patterns[].correct_sparql
   - each cross_database_queries[].examples[].sparql (if any)
   A query PASSES if it executes with no SPARQL error. Treat a 0-row result as a FAILURE only when
   the query's stated question clearly expects rows (note these in failures with the symptom).
4. For each of the 3 sample_rdf_entries: turn its triples into an ASK query (shared rdf_prefixes +
   the entry's triples) and run it. It PASSES only if ASK returns true.
5. Report exact counts, every failure (one line each: the title + the error/symptom), and a verdict.
   verdict = PASS only if yaml_parses AND queries_failed == 0 AND sample_entries_passed == sample_entries_total.

Do not edit the file. Do not invent results. Return the structured verdict.`

const results = await pipeline(
  databases,
  (db) => agent(buildPrompt(db), { agentType: 'mie-builder', label: `build:${db}`, phase: 'Build', schema: BUILD_SCHEMA }),
  (buildResult, db) =>
    agent(validatePrompt(db), { agentType: 'Explore', label: `revalidate:${db}`, phase: 'Re-validate', schema: VALIDATE_SCHEMA })
      .then((v) => ({ database: db, build: buildResult, validation: v }))
)

const rows = results.filter(Boolean)
const passed = rows.filter((r) => r.validation && r.validation.verdict === 'PASS').map((r) => r.database)
const failed = rows.filter((r) => !r.validation || r.validation.verdict !== 'PASS')

log(`mie-refresh done: ${passed.length}/${databases.length} PASS independent re-validation`)
if (failed.length) log(`NEEDS ATTENTION: ${failed.map((r) => r.database).join(', ')}`)

return {
  server,
  total: databases.length,
  passed,
  failed: failed.map((r) => ({
    database: r.database,
    verdict: r.validation ? r.validation.verdict : 'NO_VERDICT',
    failures: r.validation ? r.validation.failures : ['validation agent returned nothing'],
  })),
  details: rows,
}

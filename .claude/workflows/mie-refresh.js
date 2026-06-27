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

// NOTE: the build stage uses the DEFAULT workflow agent with a self-contained prompt rather than a
// custom agentType. Custom .claude/agents/*.md (e.g. mie-builder) only register at session start, so
// depending on agentType:'mie-builder' here fails in a fresh process. The prompt below carries the
// same hard rules + output contract, so it works regardless. mie-builder.md remains usable for direct
// Agent() calls once the session has loaded it.
const buildPrompt = (db) => `You build/revise exactly ONE MIE file: togo_mcp/data/mie/${db}.yaml (database "${db}").

Read .claude/skills/mie-generator/SKILL.md in full (plus its references/ files), then follow it end to
end — every phase 0-6, including all of Phase 5 validation. Use the togomcp server "${server}" (load
run_sparql etc. via ToolSearch, keyword "run_sparql ${server}"). The existing MIE is a HINT to verify,
never a source of truth — Phase 2a get_graph_list is mandatory. Write the file directly with Write/Edit.

TWO HARD RULES (you will be independently re-validated):
- No blind retry loops: if a query fails twice, diagnose (wrong predicate/graph/IRI/literal-typing)
  before retrying.
- Nothing invented: every sample_rdf_entries triple, every sparql_query_examples / anti_patterns
  correct_sparql query, and every data_statistics number must be retrieved live before writing. A
  false "validated" claim is a hard failure.

Return ONLY a compact report: database, file_path, mode (created|revised), validation_summary (the
Phase 6 declaration verbatim), unverifiable (or "none"), notes (<=3 lines).`

const validatePrompt = (db) => `INDEPENDENT re-validation of an MIE file. Trust NOTHING from any prior report.
You MUST actually EXECUTE the queries. A verdict produced from static inspection alone is itself a FAIL.
The run_sparql tool is a read-only SELECT/ASK tool — you ARE permitted to call it, and you must.

Target file: togo_mcp/data/mie/${db}.yaml  (database key: "${db}")

Steps:
1. Read the file. Confirm it parses as YAML:
   Bash: python3 -c "import yaml; yaml.safe_load(open('togo_mcp/data/mie/${db}.yaml'))"
2. Load the SPARQL tool via ToolSearch with the keyword query "run_sparql ${server}", then pick the
   run_sparql tool for that server (its exact name looks like mcp__${server}__run_sparql, hyphens kept).
3. RUN each RUNNABLE query against database "${db}" and record pass/fail:
   - every sparql_query_examples[].sparql  (all expect to execute without error)
   - every anti_patterns[].correct_sparql THAT IS A COMPLETE QUERY (contains SELECT/ASK + WHERE). Some
     anti-pattern correct_sparql values are deliberate TRIPLE-PATTERN FRAGMENTS for illustration only
     (no SELECT/WHERE) — SKIP those; they are not meant to run and are NOT failures.
   - every cross_database_queries[].examples[].sparql (if any)
   A query PASSES if it executes with no SPARQL error. Count a 0-row result as a FAILURE only when the
   query's stated question clearly expects rows (note the symptom in failures).
4. For each of the 3 sample_rdf_entries: build an ASK from (shared rdf_prefixes + that entry's triples)
   and run it. It PASSES only if ASK returns true.
5. Report exact counts, every failure (one line each: the title + the error/symptom), and a verdict.
   verdict = PASS only if yaml_parses AND queries_failed == 0 AND sample_entries_passed == sample_entries_total.

Do not edit the file. Do not invent results. Return the structured verdict.`

const results = await pipeline(
  databases,
  (db) => agent(buildPrompt(db), { label: `build:${db}`, phase: 'Build', schema: BUILD_SCHEMA }),
  // Validator uses general-purpose, NOT Explore: Explore reliably declines to call the run_sparql MCP
  // tool and "validates" statically, which defeats the entire purpose. general-purpose executes the
  // queries. It has Write/Edit, but the prompt forbids edits and the task never needs them.
  (buildResult, db) =>
    agent(validatePrompt(db), { agentType: 'general-purpose', label: `revalidate:${db}`, phase: 'Re-validate', schema: VALIDATE_SCHEMA })
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

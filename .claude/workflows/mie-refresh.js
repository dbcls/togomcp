export const meta = {
  name: 'mie-refresh',
  description: 'Batch-build/revise MIE files (one mie-builder agent per database), then independently re-validate each against the live endpoint',
  whenToUse: 'Quarterly refresh of many MIE files, or onboarding several new RDF databases at once. For a single user-steered file, run the mie-generator skill in the main thread instead.',
  phases: [
    { title: 'Build', detail: 'one mie-builder agent per database — runs the full mie-generator procedure' },
    { title: 'Re-validate', detail: 'independent agent re-runs every example query from the written file; does NOT trust the builder' },
    { title: 'Catalog', detail: 'regenerate the Usage-Guide database catalog ONCE after the whole batch (builders may run in parallel/worktrees — a per-agent regen would race on a partial corpus)' },
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

Format is v3 — the authorable contract is togo_mcp/data/docs/MIE_v3_spec.md. Read
.claude/skills/mie-generator/SKILL.md in full (plus its references/ files), then follow it end to
end — every phase 0-6, including all of Phase 5 validation. Use the togomcp server "${server}" (load
run_sparql etc. via ToolSearch, keyword "run_sparql ${server}"). The discovery trio
(find_databases/list_databases/list_categories) is retired — do not call it. The existing MIE is a
HINT to verify, never a source of truth, and may still be a v2 file — you are authoring v3. Phase 2a
get_graph_list is mandatory. Write the file directly with Write/Edit.

TWO HARD RULES (you will be independently re-validated):
- No blind retry loops: if a query fails twice, diagnose (wrong predicate/graph/IRI/literal-typing)
  before retrying.
- Nothing invented: every examples[].sparql (incl. the elevated aggregation + cross_db ones) and
  every entity_counts number must be retrieved live before writing, with the result recorded in the
  example's verified: block plus a date: key (never on:, which YAML parses as boolean true). A false
  "validated" claim is a hard failure.

Return ONLY a compact report: database, file_path, mode (created|revised), validation_summary (the
Phase 6 declaration verbatim), unverifiable (or "none"), notes (<=3 lines).`

const validatePrompt = (db) => `INDEPENDENT re-validation of a v3 MIE file. Trust NOTHING from any prior report.
You MUST actually EXECUTE the queries. A verdict produced from static inspection alone is itself a FAIL.
The run_sparql tool is a read-only SELECT/ASK tool — you ARE permitted to call it, and you must.

Target file: togo_mcp/data/mie/${db}.yaml  (database key: "${db}") — v3 format (contract:
togo_mcp/data/docs/MIE_v3_spec.md). Top-level keys: database, discovery, endpoint, graphs, examples,
schema_delta (optional), id_join_map.

Steps:
1. Read the file. Confirm it parses as YAML AND has the required keys:
   Bash: python3 -c "import yaml,sys; d=yaml.safe_load(open('togo_mcp/data/mie/${db}.yaml')); req={'database','discovery','endpoint','graphs','examples','id_join_map'}; m=req-set(d); sys.exit(f'MISSING {m}') if m else print('keys OK')"
   Also grep for the YAML date trap — this must print nothing:
   Bash: grep -nE '^[[:space:]]+on:' togo_mcp/data/mie/${db}.yaml   (an 'on:' key means a mis-typed date)
2. Load the SPARQL tool via ToolSearch with the keyword query "run_sparql ${server}", then pick the
   run_sparql tool for that server (its exact name looks like mcp__${server}__run_sparql, hyphens kept).
3. RUN every examples[].sparql against database "${db}" and record pass/fail. A query PASSES if it
   executes with no SPARQL error. Count a 0-row result as a FAILURE unless the example carries
   expect_empty: true (then 0 rows is expected). Note the symptom in failures.
4. For every example, confirm it has a verified: block with a date: field (not on:). An example
   missing verified:/date: is a FAILURE (record it). If a verified: block states a scalar result
   (e.g. n: 108) and re-running the query now yields a different number, record it as a drift failure.
5. Report exact counts (queries_total/passed/failed; treat "examples with a valid verified:+date:" as
   sample_entries_passed/total), every failure (one line each: example id + the error/symptom), and a
   verdict. verdict = PASS only if keys OK AND no 'on:' key AND queries_failed == 0 AND every example
   has verified: with a date:.

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

// Regenerate the Usage-Guide database catalog ONCE, after every builder has finished writing.
// Any builder that changed a `discovery:` block leaves the static catalog stale; the
// tests/test_catalog_in_sync.py drift guard fails until it is regenerated. This MUST run after the
// whole batch, never per-builder — builders may run in parallel/worktrees and a per-agent regen
// would bake a partial corpus. The generator is format-agnostic (reads discovery OR schema_info)
// and idempotent, so running it once when nothing changed is harmless.
phase('Catalog')
const CATALOG_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    regenerated: { type: 'boolean' },
    in_sync: { type: 'boolean', description: 'true if generate_usage_guide_catalog.py --check passes after regen' },
    note: { type: 'string' },
  },
  required: ['regenerated', 'in_sync'],
}
const catalog = await agent(
  `Regenerate the TogoMCP Usage-Guide database catalog once, now that all MIE files in this batch are written.
Run, from the repo root:
  Bash: uv run python scripts/generate_usage_guide_catalog.py
then confirm it is in sync:
  Bash: uv run python scripts/generate_usage_guide_catalog.py --check   (exit 0 == in sync)
Report regenerated=true, in_sync=(the --check exit was 0), and a one-line note naming the catalog part
file if it changed (togo_mcp/data/resources/usage_guide_v6/02b_database_catalog.md). Do not edit MIE files.`,
  { label: 'catalog-regen', phase: 'Catalog', schema: CATALOG_SCHEMA }
)
if (catalog && !catalog.in_sync) log('WARNING: catalog drift guard still failing after regen — inspect 02b_database_catalog.md')

return {
  server,
  total: databases.length,
  passed,
  failed: failed.map((r) => ({
    database: r.database,
    verdict: r.validation ? r.validation.verdict : 'NO_VERDICT',
    failures: r.validation ? r.validation.failures : ['validation agent returned nothing'],
  })),
  catalog,
  details: rows,
}

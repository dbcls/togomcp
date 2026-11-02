# Query ledger format (`ledger.yaml`, version 1)

The ledger is the one machine-readable output of this workflow. It is read by the
re-run script (`references/reproduce.md`), which **refuses a `ledger_version` it does
not know** — so keep `ledger_version: 1` and do not add structure beyond what is
specified here. Unknown extra keys are ignored by the script, but they are also not
checked.

## Complete example

The numbers and query below illustrate the SHAPE only; they are not verified facts.
For a real, re-run ledger see `references/worked-example.md`.

```yaml
ledger_version: 1
mode: prospective            # prospective | retrospective
created: 2026-11-02          # date the ledger was started; full timestamp only if known
togomcp:
  server_url: https://togomcp.rdfportal.org/mcp   # the connector URL; "local" for a stdio server
  server_version: null       # ALWAYS null in a session — not visible to you
calls:
  - id: q01
    role: evidence           # evidence | lookup | diagnostic
    purpose: "Number of reviewed human proteins annotated with GO:0006869 (lipid transport)"
    tool: run_sparql
    args:                    # the argument object exactly as passed to the tool
      database: uniprot
      sparql_query: |-
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
        PREFIX obo: <http://purl.obolibrary.org/obo/>
        SELECT (COUNT(DISTINCT ?protein) AS ?n)
        FROM <http://sparql.uniprot.org/uniprot>
        WHERE {
          ?protein a up:Protein ; up:reviewed true ; up:organism taxon:9606 ;
                   up:classifiedWith obo:GO_0006869 .
        }
    executed_at: 2026-11-02
    endpoint_url: https://rdfportal.org/sib/sparql    # run_sparql only; from get_sparql_endpoints
    graphs: [http://sparql.uniprot.org/uniprot]        # FROM / FROM NAMED / GRAPH IRIs in the query
    observed:
      n_rows: 1
      value: 214
    verification:
      checked_on: 2026-11-02
      status: match           # match | mismatch | unchecked | error
      category: null          # for mismatch/error: data_changed | ledger_error | endpoint_error
      note: null

  - id: q02
    role: lookup
    purpose: "Confirm the UniProt accession of human APOE"
    tool: search_uniprot_entity
    args:
      query: APOE human
    executed_at: 2026-11-02
    observed:
      key_values: [P02649]
    verification:
      checked_on: 2026-11-02
      status: match

  - id: q03
    role: diagnostic
    purpose: "Same count without the graph pin: inflated by co-hosted graphs; kept to show why q01 pins its graph"
    tool: run_sparql
    args:
      database: uniprot
      sparql_query: |-
        ...
    executed_at: 2026-11-02
    endpoint_url: https://rdfportal.org/sib/sparql
    graphs: []
    observed:
      value: 611

claims:
  - text: "214 reviewed human proteins are annotated to lipid transport (GO:0006869)."
    supported_by: [q01]
```

## Top level

| Key | Required | Meaning |
|---|---|---|
| `ledger_version` | yes | `1`. The script stops on anything else. |
| `mode` | yes | `prospective` (recorded as the work happened) or `retrospective` (rebuilt afterwards). |
| `created` | yes | Date (`YYYY-MM-DD`), or a timestamp only if you actually know the time. |
| `togomcp.server_url` | yes | The TogoMCP URL the session used (the public server is `https://togomcp.rdfportal.org/mcp`); `local` for a stdio server. The script replays non-SPARQL calls here (a `local` ledger is replayed against the public server). |
| `togomcp.server_version` | yes | `null` in a session. |
| `calls` | yes | Non-empty list of call entries. |
| `claims` | yes | The claims of the write-up and the calls that support them. |

## Call entries

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Unique within the ledger: `q01`, `q02`, … in the order the calls were made. |
| `role` | yes | `evidence` (supports a claim; re-run, mismatch fails), `lookup` (intermediate; re-run, mismatch warns), `diagnostic` (explains the path; not re-run). |
| `purpose` | yes | One sentence: what this call establishes. Written for a reader of the paper. |
| `tool` | yes | The tool name as called, without any client prefix (`run_sparql`, not `mcp__togomcp__run_sparql`). |
| `args` | yes* | The argument object exactly as passed: same keys (aliases included), same text. Write a multi-line query as a `|-` block: plain `|` appends a newline the original did not have. *Omitted only for an `unrecoverable` entry. |
| `executed_at` | yes | Date, or timestamp if known. |
| `endpoint_url` | `run_sparql` | From `get_sparql_endpoints` → `databases[<database>].url`, unless the call passed `endpoint_name` (use `endpoints[<name>].url`) or `endpoint_url` (use it). The script POSTs the query **directly** to this URL, bypassing TogoMCP. |
| `graphs` | `run_sparql` | IRIs from `FROM`, `FROM NAMED` and `GRAPH <…>` in the query; `[]` if it pins none. |
| `observed` | evidence, lookup | What the call returned that the claim relies on (below). |
| `verification` | after step 3 | The result of re-running (below). |
| `unrecoverable` | retrospective only | `true` when the call's exact text is no longer visible. Such an entry has `role: diagnostic`, no `args` (or only the parts still visible, under `partial_args`), and a `purpose` saying what it was for. If its result is needed, make a fresh call and record that as a new entry. |

### `observed`

Record only what you can read off the result; leave a field out rather than guess.

| Key | Meaning | Compared as |
|---|---|---|
| `n_rows` | Data rows in the result. For `run_sparql`: CSV rows after the header, with leading `#` note lines dropped. For list tools: the length of the returned JSON array (or of `results` in a `{total_count, has_more, results}` envelope). | equal |
| `value` | The single value of a one-row, one-column result — typically a `COUNT`. | equal as text, or numerically equal |
| `key_values` | Values the claim relies on: accessions, IDs, labels. Each must be a string that appears literally in the result (`P02649` matches inside `http://purl.uniprot.org/uniprot/P02649`). | each must appear |
| `result_sha256` | **Always `null` in a session.** The script computes it (over the result with line endings normalized, trailing whitespace stripped and the `#` note removed) and can write it into a copy of the ledger (`--write-ledger`). | equal (script only) |

Choose fields by tool:

- **`run_sparql` count** → `n_rows: 1` and `value`.
- **`run_sparql` list** → `n_rows`, plus `key_values` for the members the claim names. Add `ORDER BY` if the query has a `LIMIT`.
- **`search_*`, `togoid_*`, `togovar_*`** → `key_values` (ranking can change between releases; a count of search hits is rarely a claim).
- **`ncbi_*`** → `key_values` only (free text; no row count).

### `verification`

| Key | Meaning |
|---|---|
| `checked_on` | Date of the re-run. |
| `status` | `match`, `mismatch`, `unchecked` (nothing recorded to compare), or `error` (could not run). |
| `category` | For `mismatch`/`error`: `data_changed`, `ledger_error` or `endpoint_error`. |
| `note` | For a mismatch: both values, and why you classified it as you did. |

`diagnostic` entries have no `verification`.

## Claims

```yaml
claims:
  - text: "<the claim, as worded in the write-up>"
    supported_by: [q01, q04]
```

Every id in `supported_by` must be a call in `calls` with `role: evidence` or
`lookup`, and every claim needs at least one `evidence` call.

## Outputs

### `PROVENANCE.md`

```markdown
# Provenance: <investigation title>

<!-- retrospective only: -->
> Reconstructed after the fact; calls lost to context compaction may be missing.

- Recorded: <created> (<mode>)
- TogoMCP: <server_url> (version: <server_version, or "not recorded in-session; reported by the re-run script">)
- Verified: <date of step 3> — <n> of <m> evidence calls match

## Claims

### 1. <claim text>

Supported by **q01** — <purpose>

- Tool: `run_sparql` (database `uniprot`, endpoint `https://rdfportal.org/sib/sparql`)
- Graphs: `http://sparql.uniprot.org/uniprot`
- Observed: 214 (re-run <date>: match)

```sparql
<query text, exactly as in the ledger>
```

(For a non-SPARQL tool: the tool name and its arguments as a JSON object.)

## Path notes

<diagnostic entries: what was tried, why it was set aside>

## Re-running

<script URL and command from references/reproduce.md>

## Limitations

<the four limitations from SKILL.md, adapted to this investigation>
```

### `METHODS.md`

The filled template from `references/methods-template.md`.

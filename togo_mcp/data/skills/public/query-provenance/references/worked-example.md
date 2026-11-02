# Worked example: lipid-transport proteins in human

A small investigation run end to end on 2026-11-03 against the public TogoMCP server
(`https://togomcp.rdfportal.org/mcp`), in prospective mode. Every query, value and
output below is real; nothing was edited after the run except trimming.

**Question:** How many reviewed human UniProt entries are annotated to GO:0006869
(lipid transport), and what is the NCBI Gene ID of one of them?

## 1. Record (as the work happened)

| Call | What happened | Ledger role |
|---|---|---|
| `get_MIE_file(database="uniprot")` | Read first. It gives the graph pin (`FROM <http://sparql.uniprot.org/uniprot>`) and the GO annotation pattern (`up:classifiedWith obo:GO_*`). | not recorded (reading documentation, not evidence) |
| `run_sparql` count | `60` | **q01** evidence |
| `run_sparql` APOE (P02649) check | **0 rows**. APOE is not *directly* annotated to GO:0006869. | **q02** diagnostic: it shows the count is direct-annotation only |
| `togoid_convertId` P02649 | `348`. This lookup was for APOE, which turned out not to be in the set. | not recorded (supports no claim) |
| `run_sparql` first five by mnemonic | ABCA2, ABCA3, **ABCA4 (P78363)**, ABCA5, ABCA6 | **q03** evidence |
| `togoid_convertId` P78363 | `[["P78363", "24"]]` | **q04** lookup |
| `get_sparql_endpoints` | `databases.uniprot.url` = `https://rdfportal.org/sib/sparql` | gives `endpoint_url`; not itself recorded |

The surprise (q02) changed the claim. "Lipid-transport proteins" would have
suggested APOE was counted. The claim now says *directly annotated*, and q02 stays in
the ledger to show why.

## 2. The ledger (after step 3)

```yaml
ledger_version: 1
mode: prospective
created: 2026-11-03
togomcp:
  server_url: https://togomcp.rdfportal.org/mcp
  server_version: null
calls:
  - id: q01
    role: evidence
    purpose: "Number of reviewed human proteins directly annotated to GO:0006869 (lipid transport)"
    tool: run_sparql
    args:
      database: uniprot
      sparql_query: |-
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX obo: <http://purl.obolibrary.org/obo/>
        PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
        SELECT (COUNT(DISTINCT ?protein) AS ?n)
        FROM <http://sparql.uniprot.org/uniprot>
        WHERE {
          ?protein a up:Protein ; up:reviewed true ;
                   up:organism taxon:9606 ;
                   up:classifiedWith obo:GO_0006869 .
        }
    executed_at: 2026-11-03
    endpoint_url: https://rdfportal.org/sib/sparql
    graphs: [http://sparql.uniprot.org/uniprot]
    observed:
      n_rows: 1
      value: 60
    verification:
      checked_on: 2026-11-03
      status: match

  - id: q02
    role: diagnostic
    purpose: "APOE (P02649) is NOT directly annotated to GO:0006869 (0 rows): the q01 count covers direct annotations only, not descendant terms"
    tool: run_sparql
    args:
      database: uniprot
      sparql_query: |-
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX obo: <http://purl.obolibrary.org/obo/>
        PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
        SELECT ?mnemonic
        FROM <http://sparql.uniprot.org/uniprot>
        WHERE {
          uniprot:P02649 up:reviewed true ;
                         up:classifiedWith obo:GO_0006869 ;
                         up:mnemonic ?mnemonic .
        }
    executed_at: 2026-11-03
    endpoint_url: https://rdfportal.org/sib/sparql
    graphs: [http://sparql.uniprot.org/uniprot]
    observed:
      n_rows: 0

  - id: q03
    role: evidence
    purpose: "The first five of those proteins by UniProt mnemonic; ABCA4 (P78363) is among them"
    tool: run_sparql
    args:
      database: uniprot
      sparql_query: |-
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX obo: <http://purl.obolibrary.org/obo/>
        PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
        SELECT ?protein ?mnemonic
        FROM <http://sparql.uniprot.org/uniprot>
        WHERE {
          ?protein a up:Protein ; up:reviewed true ;
                   up:organism taxon:9606 ;
                   up:classifiedWith obo:GO_0006869 ;
                   up:mnemonic ?mnemonic .
        }
        ORDER BY ?mnemonic
        LIMIT 5
    executed_at: 2026-11-03
    endpoint_url: https://rdfportal.org/sib/sparql
    graphs: [http://sparql.uniprot.org/uniprot]
    observed:
      n_rows: 5
      key_values: [P78363, ABCA4_HUMAN]
    verification:
      checked_on: 2026-11-03
      status: match

  - id: q04
    role: lookup
    purpose: "NCBI Gene ID of ABCA4 (UniProt P78363)"
    tool: togoid_convertId
    args:
      ids: P78363
      route: uniprot,ncbigene
    executed_at: 2026-11-03
    observed:
      n_rows: 1
      key_values: ["24"]
    verification:
      checked_on: 2026-11-03
      status: match

claims:
  - text: "60 reviewed human UniProt entries are directly annotated to GO:0006869 (lipid transport); proteins annotated only to its descendant terms, such as APOE, are not included."
    supported_by: [q01]
  - text: "ABCA4 (UniProt P78363; NCBI Gene 24) is one of them."
    supported_by: [q03, q04]
```

Points to notice:

- **q01 is a COUNT.** The claim is a number, so the evidence is the `COUNT`, compared
  by `value`. Nobody counted rows by eye.
- **q03 has `ORDER BY` with its `LIMIT`.** Without it the "first five" could differ
  between runs. Its `key_values` name only what the claim uses.
- **q04 records the ID as a string (`"24"`).** `key_values` are matched as text.
- **Queries are `|-` blocks**, so the stored text equals what was sent: no trailing
  newline was added.
- **`server_version: null` and no `result_sha256`.** Neither can be observed in a
  session.

## 3. Re-run and compare (in the session, no code)

q01, q03 and q04 were called again with arguments copied **from the ledger**:

| Call | Recorded | Re-run | Status |
|---|---|---|---|
| q01 | value 60 | `"n"\n60` | match |
| q03 | 5 rows; P78363, ABCA4_HUMAN | the same 5 rows | match |
| q04 | 1 pair; "24" | `[["P78363", "24"]]` | match |

q02 is `diagnostic` and is not re-run.

## 4. What the reader's script reports

The same ledger, re-run later with `references/reproduce.md`'s script (outside the
session):

```
$ uv run togomcp_reproduce.py ledger.yaml --write-ledger ledger.hashed.yaml
togomcp_reproduce 1.0.0
MCP server: https://togomcp.rdfportal.org/mcp (serverInfo.version: 2.28.1)

id         role       route   status     detail
q01        evidence   sparql  match      n_rows ok; value ok
q02        diagnostic skipped skipped
q03        evidence   sparql  match      n_rows ok; key_values ok
q04        lookup     mcp     match      n_rows ok; key_values ok
```

Exit code 0. The SPARQL calls went directly to `https://rdfportal.org/sib/sparql`; q04
was replayed over MCP, which is where the server version came from. With one recorded
number altered (q03 `n_rows: 6`), the script reports
`q03 … mismatch  n_rows expected 6 got 5` and exits 1. `ledger.hashed.yaml` carries
`result_sha256` for the three matching calls, so a later re-run also checks the exact
content.

## 5. PROVENANCE.md (abridged)

````markdown
# Provenance: lipid-transport proteins in human

- Recorded: 2026-11-03 (prospective)
- TogoMCP: https://togomcp.rdfportal.org/mcp (version: not recorded in-session; reported by the re-run script)
- Verified: 2026-11-03 — 2 of 2 evidence calls match (1 lookup also matches)

## Claims

### 1. 60 reviewed human UniProt entries are directly annotated to GO:0006869 (lipid transport); proteins annotated only to its descendant terms, such as APOE, are not included.

Supported by **q01**: number of reviewed human proteins directly annotated to GO:0006869.

- Tool: `run_sparql` (database `uniprot`, endpoint `https://rdfportal.org/sib/sparql`)
- Graphs: `http://sparql.uniprot.org/uniprot`
- Observed: 60 (re-run 2026-11-03: match)

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
…
```

### 2. ABCA4 (UniProt P78363; NCBI Gene 24) is one of them.

Supported by **q03** (first five by mnemonic, includes P78363) and **q04**
(`togoid_convertId` `{"ids": "P78363", "route": "uniprot,ncbigene"}` → 24).

## Path notes

q02: APOE (P02649) returned 0 rows for a direct GO:0006869 annotation, so the claim
is worded "directly annotated".

## Re-running

uv run https://raw.githubusercontent.com/dbcls/togomcp/v2.29.0/scripts/togomcp_reproduce.py ledger.yaml

## Limitations

…the four from SKILL.md. Here: no UniProt release number is exposed, so the date and
graph IRI stand in for it.
````

## 6. METHODS.md

> **Data retrieval.** Database queries were performed with TogoMCP (Kinjo et al.,
> 2026), a Model Context Protocol server that gives a large language model access to
> the RDF Portal knowledge graphs and selected REST APIs, version 2.28.1
> (https://togomcp.rdfportal.org/mcp). [ASSISTANT — fill in] issued the queries. The
> three queries supporting the results reported here were run on 3 November 2026
> against UniProt (graph `http://sparql.uniprot.org/uniprot`, endpoint
> https://rdfportal.org/sib/sparql). The identifier conversion used TogoID.
>
> **Reproducibility.** Every query, with its exact text and the result it returned,
> is provided in Supplementary File [n] (`ledger.yaml`; human-readable version
> `PROVENANCE.md`). All queries were re-executed on 3 November 2026, and 2 of 2
> evidence queries (and the identifier lookup) reproduced the recorded results
> exactly. The ledger can be re-executed with the script `togomcp_reproduce.py`
> (https://github.com/dbcls/togomcp/blob/v2.29.0/scripts/togomcp_reproduce.py). It
> sends SPARQL queries directly to the endpoints, independently of TogoMCP.

The version (2.28.1) is filled in here because the script reported it. In a session
without the script, it stays `[VERSION — fill in]`.

> Usage Guide reference file — fetched on demand with `get_workflow(name="usage-guide", path="references/endpoints.md")`. The always-loaded core is `TogoMCP_Usage_Guide()`.

## 🔌 ENDPOINTS — DETAIL

The endpoint table (which `database` keys share which endpoint) is in the core guide.
This file holds what the table cannot: graph multiplicity, drift, `SERVICE` federation,
and non-RDF-Portal infrastructure.

> **One database ≠ one graph.** GlyCosmos (~150 graphs), PubChem (69), PDB (46), DDBJ
> (43), IDSM (39), MarpolBase (7) and TogoVar (16) serve many graphs from their *own* endpoint —
> TogoVar keeps a variant's coordinates and its annotation in two graphs (and until its 2026-10
> reload re-typed 2.9M variant IRIs in a third, now removed), MarpolBase re-declares gene
> identifiers and symbols across two of its own (×2.00 on the plain gene lookup), and IDSM re-hosts nine chemical
> datasets under their original IRIs with a union default graph. Co-tenancy is a property
> of **graphs**, not of this table. Only SuperCon (2) and SwissLipids (3, of which just one
> holds data — the other two are `.well-known/void` and `.well-known/sparql-examples`) are
> near-single-graph — and LIPID MAPS declares **no named graphs at all**, so every
> `GRAPH`/`FROM` pin returns 0 rows there.

Copied from `endpoints.csv` and it **drifts**: a database mounted beside yours silently
rewrites what your unpinned query means (OMA landed on `sib` 2026-04-28 and changed
answers written months earlier). `get_sparql_endpoints()` is authoritative.

Same endpoint → single SPARQL. Different endpoints → `togoid_convertId` or NCBI
cross-reference. Call `get_sparql_endpoints()` when planning a bridge, or when a
count looks inflated (it hurt scores when called routinely: 16.73 vs. 17.59 without).

**Third route, from a few verified callers only: `SERVICE` federation.** Some endpoints
can send part of a query to another endpoint in a `SERVICE <url> { … }` block — verified
2026-09-15: WikiPathways → UniProt on SIB, IDSM → Rhea, SwissLipids → Rhea, and RDF
Portal's `ebi` → LIPID MAPS; 2026-09-17: `microbes` → UniProt on SIB. Run the query on the
**calling** endpoint (`database=wikipathways` / `idsm` / `swisslipids` / `bh26microbes`; for the LIPID MAPS join,
`database=lipidmaps` with `endpoint_name=ebi`), not the one inside
`SERVICE`: routed to the remote endpoint instead it fails or returns 0 rows. The direction
matters, and it is NOT a property of the domain: `swisslipids` calls out to Rhea in ~3 s,
while `lipidmaps` — the other lipid database — cannot call out at all, every `SERVICE`
from it returning HTTP 502 after ~60 s. `marpolbase` refuses `SERVICE` by permission
(verified 2026-09-18: HTTP 500, `SQ070:SECURITY: Must have select privileges on view
DB.DBA.SPARQL_SINV_2`, in 0.1 s) — a deterministic refusal, not an outage, so its
cross-DB work is always two separate calls. Do not carry one lipid DB's answer over to the
other. Copy the MIE's `cross_db` example rather than writing one; each carries its own
limits (bind the join key locally first, cap the bindings before crossing). Other RDF
Portal endpoints have not been verified as callers — do not assume it works there.

**Endpoints outside RDF Portal carry their own infrastructure, and it can reject valid
SPARQL before the engine ever sees it.** Verified 2026-09-16: a Cloudflare WAF rejects `substr(`,
`concat(` and `char(` on `lipidmaps` with **HTTP 403 and an HTML body**. The rule matches the
**raw request body**, not the parsed query — a bare string literal `"SUBSTR("` inside a `BIND`
is blocked too, which is the proof it never reaches SPARQL. It is deterministic, so retrying
does not help, and because the reply is not SPARQL it reads as an endpoint outage rather than a
rejected query. The fix is one character: **put a space before the paren** — `SUBSTR (?s, 33, 2)`
and `CONCAT (?a, ?b)` are valid SPARQL and clear the rule. `GROUP_CONCAT(` already passes (the
preceding `_` defeats the word boundary), as do `REPLACE`, `STRBEFORE`, `STRAFTER`, `REGEX`,
`STRLEN`, `UCASE`, `CONTAINS` and `STRSTARTS`. Slicing an accession is the obvious thing to reach
for, so this bites on a first attempt. Two more non-SPARQL bodies from the same host: a ~30 s
timeout answers `HTTP 503 Query timed out`, and rapid sequential querying draws transient 403s
that clear on retry. Expect the same class of thing on the next non-RDF-Portal endpoint added.

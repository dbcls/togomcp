---
name: mie-generator
description: Generate or update MIE (Metadata Interoperability Exchange) YAML files that describe RDF databases for TogoMCP. Use this skill whenever the user asks to create, write, regenerate, update, or improve an MIE file for any RDF database (UniProt, ChEMBL, Reactome, Rhea, PubChem, MeSH, PDB, or any new bio/chem database being added to TogoMCP), or mentions anything about the `togo_mcp/data/mie/` directory, MIE schema documentation, database onboarding for TogoMCP, or describing an RDF endpoint's schema/ShEx/SPARQL examples for LLM consumption. Trigger even if the user says things like "document this database", "add Reactome to our MIE collection", "the ChEMBL metadata file is out of date", or "I need to describe this SPARQL endpoint for Claude" — as long as the context is TogoMCP or an RDF database being described in YAML.
---

# MIE File Generator

An MIE file is a compact YAML document that describes an RDF database well enough for an LLM to write correct, efficient SPARQL against it on the first try. Good MIE files are the difference between "Claude writes a working query" and "Claude times out the endpoint with a `FILTER(CONTAINS())` over 244M triples".

**Format: v3.** The authorable contract is `togo_mcp/data/docs/MIE_v3_spec.md` — read it before writing. v3 is organized by **agent need × recoverability** with the **verified, executable worked example as the atomic unit**: five need-based parts (`database`, `discovery`, the header, `examples`, `schema_delta`, `id_join_map`), where each example simultaneously **is** the schema shape, the sample triple, and (via `traps_avoided`) the warning it would otherwise be written as three or four times. The worked reference is the hand-authored pilot `togo_mcp/data/mie/uniprot.yaml`. Carry only what the model **cannot recover** on its own (spec §4.3); where this skill and the spec disagree, the spec wins.

This skill lives in a Claude Code environment with filesystem access and SPARQL execution tools (from the `togomcp_local` MCP server). Use filesystem tools freely — that is the normal mode of operation here.

## The Two Hard Rules

**1. No blind SPARQL retry loops.** Schema discovery legitimately requires many queries, but if a query fails twice in a row, stop and diagnose — wrong predicate, wrong graph, wrong IRI pattern — before retrying. More retries without diagnosis do not fix a structurally wrong query.

**2. Nothing in the MIE file is invented — and "it ran" is not "it's right."** Every `examples` entry must be executed against the real endpoint before the file is written, its live result recorded in the `verified:` block **with a `date:`**, and that result **confirmed correct**, not merely error-free:

- **SPARQL** (every `examples[].sparql`, including the `aggregation` and `cross_db` ones): must run AND return the right thing. A query that succeeds but returns a union-inflated COUNT is a *failed* test, not a passing one — scope the graph and verify the figure (Phase 2g / 5c). The `verified:` block records the actual figure you saw, so a later re-run that disagrees is a drift signal, not silent rot.
- **Search-wrapper claims**: any assertion the file makes about a `search_*` / `ncbi_esearch` / `OLS4:searchClasses` tool's behavior (e.g. "use `search_chembl_target` for targets, EGFR → CHEMBL203") must be run through the actual tool and the claimed hit confirmed to appear at a *usable* rank/limit — not buried at rank 5 behind unrelated hits, and present at the limit the claim implies (Phase 5e).

Fake or unverified examples are worse than missing ones: they train the downstream LLM to write queries *and tool-calls* that look right but fail silently.

## File locations in this environment

| Asset                      | Path                                       | Tool to use            |
|----------------------------|--------------------------------------------|------------------------|
| Existing MIE files         | `./togo_mcp/data/mie/<db>.yaml`            | Read / Write / Edit    |
| Endpoint registry          | `./togo_mcp/data/resources/endpoints.csv`  | Read / Edit            |

Phase 2 (live discovery) is the canonical source of truth for the schema and example queries — never let prior assumptions override what the endpoint actually exposes.

The MCP tools `get_MIE_file` and `save_MIE_file` are **not** used in this environment — read and write MIE files directly. The remaining TogoMCP tools (`run_sparql`, `get_sparql_endpoints`, `get_graph_list`, the search APIs) ARE used; they hit live endpoints and cannot be replaced by filesystem access. `WebFetch` is used in Phase 0 to look up unregistered endpoints on rdfportal.org. **The discovery trio (`find_databases` / `list_databases` / `list_categories`) is retired — do not call it.** The database catalog it served is now a static, generated Usage-Guide section (`togo_mcp/data/resources/usage_guide_v6/02b_database_catalog.md`), built from every MIE's `discovery:` block; when this skill changes a MIE's `discovery` block, regenerate that catalog (Phase 6).

## Workflow

### Phase 0 — Register the endpoint (skip if already in `endpoints.csv`)

Before discovery, the target database must exist as a row in `./togo_mcp/data/resources/endpoints.csv`. The columns are `database,endpoint_url,endpoint_name,keyword_search_api`. If the user supplies only a dataset name, derive the rest from rdfportal.org.

1. **Check the registry first.** Read `./togo_mcp/data/resources/endpoints.csv`. If `<db>` is already a row, skip Phase 0 entirely — registration is done.

2. **Look up the dataset on rdfportal.org.** Call `WebFetch` on `https://rdfportal.org/access_methods/sparql_endpoints/` with a prompt asking which endpoint provider lists `<db>` and what its canonical slug is. The page is nested bullet lists grouped by provider; canonical dataset slugs match the names already used in the CSV (e.g. `uniprot`, `chembl`, `pdb`).

3. **Derive the row:**
   - `database` — canonical slug from the page (lowercase; strip spaces, dots, dashes).
   - `endpoint_url` — the parent provider's SPARQL URL (e.g. anything under "EBI" gets `https://rdfportal.org/ebi/sparql`).
   - `endpoint_name` — the URL path component (e.g. `https://rdfportal.org/ebi/sparql` → `ebi`).
   - `keyword_search_api` — **default to `sparql`**. Other valid values: a dedicated tool like `search_uniprot_entity`, an OLS4 path like `OLS4:searchClasses`, or `ncbi_esearch`. This requires human knowledge of which client tool fits — *tell the user the default and offer to override*. If unsure, leave as `sparql`; the user can edit later.

4. **Append** the row to `endpoints.csv` with `Edit` (preserve trailing newline; do not reorder existing rows).

5. **If the dataset isn't on the rdfportal.org page**, do **not** invent values. Tell the user, ask them for the SPARQL endpoint URL directly, then return to step 3 with their input.

After registration, proceed to Phase 1.

### Phase 1 — Orient (1–2 minutes)

Before touching the endpoint:

1. `Read ./togo_mcp/data/mie/<db>.yaml` — is there an existing MIE? If yes, this is an update, not a fresh build. It may be a v2 file (the pre-redesign format) — you are rewriting it to v3, so treat its structure as legacy, not a template. **Treat every claim in the existing file as a hint to verify, not a source of truth — including its graph list. Graphs get added upstream all the time, and a previously-correct graph list can be incomplete by the next snapshot.** Phase 2a is mandatory whether you're authoring or revising.
2. Call `get_sparql_endpoints()` — confirm the endpoint URL is what you expect (it should already be in `endpoints.csv` after Phase 0).

That's it. Phase 2 is where the real work happens. Local prior art — **the existing MIE under revision** — is optional context; **do not let it shape the MIE without re-verification against the live endpoint**.

### Phase 2 — Discover (10–20 minutes)

Goal: extract the named graph(s), classes, typed predicates, IRI patterns, and representative entities you'll need so that the `examples` can prefer structured lookups over text search. This is the canonical source of truth — every fact in the MIE comes from queries you ran here.

#### 2a. Identify the data graph(s) — mandatory, including for revisions

Endpoints often host multiple databases (SIB hosts UniProt + Rhea + Bgee + OMA; the primary endpoint hosts ~30 ontologies and datasets). Picking the right graph(s) is step zero.

**This step is mandatory whether you're authoring a new MIE or revising an existing one.** The most common revision failure is trusting the existing graph list as authoritative — graphs get added upstream between snapshots, and a stale list silently caps every downstream query. A real instance: an Ensembl revision missed `ensembl-glossary`, `ensembl_ontology`, and `ensembl_taxonomy` because the existing graphs list was treated as ground truth. If `get_graph_list` wasn't called this turn, you don't know what graphs exist.

```python
get_graph_list("<db>")
```

`get_graph_list` filters out Virtuoso/OpenLink internal graphs and **ranks graphs whose URI contains the database slug at the top** — so `get_graph_list("bgee")` puts `<http://bgee.org>` first; `get_graph_list("supercon")` puts `<http://rdfportal.org/dataset/supercon>` first. Common URI conventions in RDF Portal: `http://<db>.org` (Bgee, Rhea, JCM), `http://rdfportal.org/dataset/<db>` (OMA, BRENDA, ChEBI, Reactome), `http://sparql.<db>.org/<db>` (UniProt). Browse the ranked list, pick the graph(s). For a revision, diff what you find against the existing file's graph list — additions and removals both matter.

**Multi-graph databases** (UniProt, Bgee with subgraphs, etc.): if several graphs share the same prefix (e.g. `sparql.uniprot.org/{core,taxonomy,go,keywords,…}`), the database spans all of them. In v3 this becomes `graphs.primary` (the DB's own default-pin graph) plus `graphs.supporting` (the same-DB sibling graph localnames); document any non-obvious per-graph role in `schema_delta`.

**No name match**: if no graph URI contains the slug, the data graph URI is unconventional. Fall back to running quick `COUNT(*)` queries on candidate graphs to find the largest data-bearing one, or inspect the dataset's documentation. This is rare on RDF Portal.

#### 2b. Enumerate classes and predicates

Once you know the graph(s), scope every discovery query with `GRAPH <…>`:

```sparql
# Classes and instance counts
SELECT ?class (COUNT(?s) AS ?n)
WHERE { GRAPH <http://example.org/dataset> { ?s a ?class } }
GROUP BY ?class ORDER BY DESC(?n) LIMIT 50

# Predicate usage (anchor on a major class to keep cardinality bounded)
SELECT ?p (COUNT(*) AS ?n)
WHERE { GRAPH <http://example.org/dataset> { ?s a <MajorClass> ; ?p ?o } }
GROUP BY ?p ORDER BY DESC(?n) LIMIT 50
```

Counts give you a feel for which classes are central (top 5 typically carry 90%+ of the data) and which predicates form the backbone of the schema. Skip BFO / CDAO / framework upper-types — pick the canonical class.

**Run a dedicated predicate survey for every class an example will query** — not only the top-level anchor class. Annotation classes, measurement classes, and cross-reference classes are just as likely to have missing or misnamed predicates as the central entity class. The rule is simple: if a predicate appears in an `examples[].sparql` or a `schema_delta` entry, its survey must have been run first. A predicate you use that is absent from the survey has no business in the file; a surveyed predicate with COUNT > 0 that a query would plausibly need is either shown in an example or noted in `schema_delta`.

While running predicate surveys, note any predicate whose COUNT distribution is surprising as a **trap candidate** (a `global_gotchas` entry if it bites any query, or a `traps_avoided` line on the specific example it affects):

- COUNT equals class instance count but the predicate name looks like it might have an alias or alternate namespace form — confirm only one form is queryable.
- COUNT is much lower than the class instance count for a predicate that looks mandatory — document as a caveat on cardinality, or as a trap if omitting it causes a silent wrong result rather than just an empty one.
- COUNT is greater than the class instance count for a predicate that looks singular — document the multi-valued behaviour.
- Two predicates return overlapping results for what appears to be the same concept — document which form is the correct join key.

Caveat: this predicate survey is GRAPH-scoped, so it CANNOT see cross-graph re-declaration —
a predicate duplicated in ANOTHER graph (a sibling dataset's, or another of this database's own)
reads as COUNT = 1 here and looks perfectly singular. Never conclude "singular, therefore safe"
from a scoped COUNT on any endpoint holding more than one graph. That trap is found only by the
2g union-inflation probe.

Write these candidates down immediately. `global_gotchas` and the examples' `traps_avoided` lines are assembled in Phase 4 from this list — not reconstructed from memory.

**Check object polymorphism for every linking predicate.** For each predicate whose object is an IRI (not a literal or bnode), GROUP BY the object's type or namespace. A predicate whose object spans **more than one class/namespace is a denormalized, polymorphic link** — and that is simultaneously a design signal and a silent-failure trap, because any downstream query that assumes a single object type will quietly drop the other kinds.

```sparql
# Object-type spread of a linking predicate (by namespace prefix; cheap and endpoint-agnostic)
SELECT ?ns (COUNT(*) AS ?n) WHERE {
  GRAPH <…> {
    ?s <predicate> ?o .
    BIND(REPLACE(STR(?o), "^(.*/)[^/]+$", "$1") AS ?ns)
  }
} GROUP BY ?ns ORDER BY DESC(?n)
# (or GROUP BY the object's rdf:type via  ?o a ?ns  when objects are typed)
```

Run this on every predicate you plan to traverse in an example. If the object set is heterogeneous: enumerate **all** object kinds with their counts (in a `schema_delta` line or an inline query comment, and a `global_gotchas`/`traps_avoided` entry), and show the disambiguating filter (e.g. `FILTER(CONTAINS(STR(?o), "/protein/"))`) in the example query. Real case: PubChem's `obo:RO_0000057` (MeasureGroup → target) resolves to protein **and** taxonomy, gene, cell, and anatomy IRIs — five object kinds under one predicate; a query filtering to only one silently loses the rest, and the first revision documented only three of the five until this GROUP BY was run.

**Probe the literal form for every literal you'll match exactly — EMPIRICALLY, by matching it.** Whenever a predicate's object is a literal that a downstream query will match in a `VALUES` block, a `FILTER(?x = …)`, or a triple-pattern object, the *stored* term must match the *query* term exactly — including datatype and language tag. A query term of the wrong form returns 0 rows with no error.

> **`DATATYPE()` CANNOT ANSWER THIS QUESTION — DO NOT BUILD THE MATCH FORM FROM IT.** On Virtuoso (and any RDF-1.1 store), a *plain* literal and an *`xsd:string`-typed* literal BOTH report `DATATYPE() = xsd:string`, because RDF 1.1 defines them as the same value. But Virtuoso matches **terms, not values**: the two forms do NOT unify in a triple pattern *or* in `FILTER(?x = …)`. So `DATATYPE()` reports identically for two graphs whose required match form is **opposite**, and a probe-driven guess is right half the time and silently wrong the other half.
>
> Verified 2026-07-16 on the RDF Portal primary endpoint, both reporting `DATATYPE() = xsd:string`:
> - `<ontology/hp>` — `HP_0001250 rdfs:label "Seizure"^^xsd:string` MATCHES; plain `"Seizure"` → 0 rows.
> - `<ontology/efo>` — `EFO_0000305 rdfs:label "obsolete_breast carcinoma"` MATCHES; the `^^xsd:string` form → 0 rows.
>
> This is exactly how a previous `ontology.yaml` shipped the false lead warning "every literal here is xsd:string" — true for hp/go, inverted for uberon/cl/efo/edam.

`DATATYPE()`/`LANG()` remain useful for what they *can* see — a language tag, and genuine non-string types (`xsd:integer`, `xsd:boolean`, `xsd:date`) — so still run the survey to spot those and any mixed typing:

```sparql
SELECT ?dt ?lang (COUNT(*) AS ?n) WHERE {
  GRAPH <…> { ?s <predicate> ?o . BIND(DATATYPE(?o) AS ?dt) BIND(LANG(?o) AS ?lang) }
} GROUP BY ?dt ?lang ORDER BY DESC(?n)
```

> **THERE IS NO CLOSED LIST OF STRING-LIKE FORMS. ASK FOR WHATEVER DATATYPE THE SURVEY ACTUALLY REPORTS.** Do not memorise "plain / `xsd:string` / `@en`" as the options — a value that *reads* as text can carry any datatype, and only that exact datatype matches. Two verified culprits, and the list is open:
> - **`xsd:anyURI`** — an `xsd:` type, so a "watch out for non-`xsd:` datatypes" rule misses it. `<ontology/go>`'s `obo:IAO_0000233` is 20,249 values, ALL `^^xsd:anyURI`: `"…/issues/29194"^^xsd:anyURI` matches, while **both** the plain form and `^^xsd:string` return 0 rows.
> - **`rr:Literal`** (`<http://www.w3.org/ns/r2rml#Literal>`) — stamped by an R2RML relational-to-RDF mapping. `bacdive`'s 18,215 `schema:hasGramStain` values are all `^^rr:Literal`, so `hasGramStain "positive"` returns 0 rows silently.
>
> Expect others (`xsd:token`, `xsd:normalizedString`, `xsd:NCName`, `xsd:language`, custom datatypes) and treat each as its own term form. `FILTER(STR(?x) = …)` matches every one of them — verified for `xsd:anyURI` and `rr:Literal` as well as plain/typed/`@en`.

> **AN EMPTY `DATATYPE()` MAY MEAN "NOT A LITERAL", NOT "odd string type".** `DATATYPE()` is unbound on an IRI, so an empty column can be a non-literal object rather than a lang-tagged one. Check `isLiteral()` / `isIRI()` before concluding anything. Verified 2026-07-16: `<ontology/hp>`'s `obo:IAO_0000233` reports an empty datatype because all 1,461 objects are **IRIs** — while the same predicate in `<ontology/go>` is 20,249 `xsd:anyURI` **literals**, in `<ontology/cl>` `xsd:string` literals, and in `mondo`/`uberon` a *mix* of `xsd:anyURI` literals and a handful of IRIs. One predicate, IRI-or-literal and three datatypes, decided by the graph. `ontology.yaml` shipped this annotated `xsd:anyURI ?` with the comment "(a LITERAL, not IRI)" — exactly backwards for the graph its own counts came from.

But when the survey says "string-ish" (`xsd:string` with no lang), you have learned nothing about the match form. **Settle it by trying each candidate form against a known term** — one ASK per form, cheap and decisive:

```sparql
ASK { GRAPH <…> { <known-subject> <predicate> "known value" } }                    # plain
ASK { GRAPH <…> { <known-subject> <predicate> "known value"^^xsd:string } }        # typed
ASK { GRAPH <…> { <known-subject> <predicate> "known value"@en } }                 # lang-tagged
ASK { GRAPH <…> { <known-subject> <predicate> "known value"^^<dt-from-survey> } }  # EVERY datatype
                                                                                   # the survey
                                                                                   # reported — incl.
                                                                                   # xsd: ones like
                                                                                   # xsd:anyURI
```

Map the result to the exact-match rule, and record it (a `global_gotchas` entry if it is database-wide, otherwise a `traps_avoided` line on the affected example) whenever a query would break by getting it wrong:

| Established by ASK | Exact-match query term must be |
|---|---|
| only the typed ASK is true | `"value"^^xsd:string` — a plain `"value"` joins to nothing |
| only the plain ASK is true | `"value"` — adding `^^xsd:string` joins to nothing |
| only the `@en` ASK is true | `"value"@en` — both bare forms join to nothing |
| the survey reported ANY other datatype (`xsd:anyURI`, `rr:Literal`, `xsd:token`, …) | `"value"^^<that-exact-datatype>` — plain AND `^^xsd:string` both join to nothing |
| `xsd:integer` / `xsd:decimal` / `xsd:double` | the matching numeric type — `"2"^^xsd:integer` ≠ `"2"^^xsd:decimal` ≠ `2.0`. (Numerics DO coerce in Virtuoso where strings do not: on an `xsd:boolean`, both `= 1` and `= true` match.) |
| no ASK is true, and `isIRI()` is true | it is **not a literal** — do not annotate it as one |

Two rules that follow, both verified:

- **`FILTER(?x = "value")` is NOT a workaround.** It is term-based on Virtuoso and fails identically to the triple pattern (`FILTER(?l = "Seizure")` on hp → false; `FILTER(?l = "Seizure"^^xsd:string)` → true). Only **`FILTER(STR(?x) = "value")`** unifies every form — verified matching in go (typed), uberon + edam (plain), fma + sio (`@en`) and bacdive (`rr:Literal`) alike. Prefer `STR()` in any example query that spans graphs or whose form you have not established by ASK; use the bare typed/plain form only where you have (it is faster and index-friendly).
- **The form can vary BY GRAPH inside ONE endpoint, by predicate inside one graph, and even across predicates on the SAME SUBJECT.** Never generalize from one probe to "this database stores X". Two verified cases: `<ontology/fma>` stores `rdfs:label` as `@en` (104,919 of 104,936) while its sibling `fma:preferred_name` / `fma:definition` on the very same subject are `xsd:string`. And a `bacdive` GramStain node carries `rdfs:label` as `xsd:string` but `hasGramStain` + `hasPhenotypeInformation` as `rr:Literal` — while `hasOxygenTolerance`, the same modelling family, is plain `xsd:string`. Probe per graph, and per predicate you will match.

The nastiest variant is **inconsistent typing within one predicate** (some values `xsd:string`, some plain, or mixed numeric types): the GROUP BY shows two or more rows for the same predicate. Then no single exact-match form catches everything — document it and use `STR()`-based comparison (or a `VALUES` block listing every form) in the example query. Real case: Reactome stores `bp:db` / `bp:id` / `bp:name` / `bp:eCNumber` / `bp:controlType` as `xsd:string`, so every `VALUES`/`FILTER =`/object literal needs `^^xsd:string` — its single most common silent-failure mode, now the file's lead `critical_warning`. `VALUES` is the highest-miss spot because the typing requirement isn't visually cued there the way it is in a triple object.

#### 2c. DESCRIBE 3–5 representative entities

Pick entities that span the taxonomy of the database — a "central" entity (most-frequent class), a "linker" entity (something that joins multiple classes), and a "leaf" entity (terminal annotation):

```sparql
SELECT ?p ?o WHERE { GRAPH <…> { <iri-of-entity> ?p ?o } } LIMIT 200
```

(Plain `DESCRIBE` works on most endpoints but truncates unpredictably; the SELECT form above is more reliable.)

Use these inspections to nail down: IRI patterns (`http://<base>/<class>/<id>`), denormalized predicates (one predicate that serves multiple roles — e.g. Bgee's `genex:isExpressedIn` mixing anatomy IRIs and condition IRIs), measurement scaffolds (bnode chains for typed-value triples), and parallel namespace traps (the same NCBI taxon ID minted under two different IRI schemes — Bgee, see its `global_gotchas`).

**Trace every blank node chain.** For each predicate in your DESCRIBE output whose object is a blank node, retrieve the bnode's full predicate set by walking from the parent entity in a single query:

```sparql
SELECT DISTINCT ?bPred ?bObj WHERE {
  GRAPH <…> {
    ?parent a <ParentClass> ; <bnodePredicate> ?bnode .
    ?bnode ?bPred ?bObj .
  }
} LIMIT 50
```

Do this for every distinct bnode-valued predicate you encounter — typed-value scaffolds, position nodes, sequence nodes, evidence nodes, and any other bnode-valued property. An undiscovered bnode schema means an incomplete shape and a missing shape definition for the referenced `@<ShapeName>`.

Note also that bnode shapes reached via different parent classes may differ in structure even when they share the same predicate name — the same property can resolve to an `ExactPosition` bnode (carrying an integer + a back-reference IRI) on one parent class and to a `Region` bnode (carrying `begin` and `end` sub-bnodes) on another. Never assume two bnode chains with the same predicate name have the same internal structure; verify each one independently via a parent-anchored query.

#### 2d. Anchor IRIs via search tools — and resolve opaque IRIs back to labels

If the database has a dedicated search tool (`search_uniprot_entity`, `search_chembl_molecule`, `search_chembl_target`, `search_pdb_entity`, `search_reactome_entity`, `search_rhea_entity`, `search_mesh_descriptor`, `OLS4:searchClasses`, `ncbi_esearch`), use it to turn human-readable terms ("TP53", "tumor protein p53", "kinase activity") into specific IRIs. Then DESCRIBE those IRIs to learn the canonical predicate names. This is the fastest path from "I know what concept I'm looking for" to "I have a structured-IRI query that works."

If no search tool exists (BRENDA, BacDive, MediaDive, SuperCon, Glycosmos, NIMS): generate a short `bif:contains` (Virtuoso) probe to find one example, DESCRIBE it, and pivot to typed-predicate queries from there. If a text-search example survives into the file at all, state in its `teaches` line (in one sentence) why no structured alternative existed.

**The inverse direction — an opaque IRI whose meaning you don't know.** 2b/2c routinely surface bare numeric OBO IRIs (`SO_0000704`, `RO_0002211`, `BFO_0000050`, `ECO_0000269`) as predicates or objects. **Never guess one from its shape, and never gloss one in a comment you didn't resolve** — a wrong gloss in an example comment or a `schema_delta` line is invisible to Phase 5 (the query still runs) and ships as fact.

The primary endpoint carries ~40 ontology graphs under `http://rdfportal.org/ontology/` (`go`, `hp`, `so`, `uberon`, `cl`, `clo`, `eco`, `efo`, `mondo`, `pro`, `fma`, `edam`, `sio`, `po`, `xco`, `cmo`, `meo`, `mmo`, `uo`, plus the `glycordf`/`orth`/`piero` schema vocabularies). Batch-resolve against them in **one** query — this works from any endpoint's survey, resolves many IRIs at once, and covers **object properties as well as classes**:

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?iri ?g ?label WHERE {
  VALUES ?iri { <http://purl.obolibrary.org/obo/SO_0000704>
                <http://purl.obolibrary.org/obo/RO_0002211> }
  GRAPH ?g { ?iri rdfs:label ?label }
  FILTER(LANG(?label) IN ("", "en"))
}
```
(`database=go`, `endpoint_name=primary` — any registered member DB works as the routing hint.)

Three verified traps, all of which produce a confidently wrong answer rather than an empty one:

- **Never `FILTER(LANG(?label) = "en")` — and never `= ""` either.** The authoritative labels in `ontology/go`, `ontology/hp`, and `ontology/so` carry **no language tag at all**; only the copies re-imported by other ontologies are tagged `en`. Filtering on `"en"` silently drops the owning ontology's label and leaves you quoting a second-hand one. But the rule **inverts** for the non-OBO graphs: in `ontology/fma`, `ontology/sio` and `ontology/meo` the ontology's OWN label IS `@en` (verified 2026-07-16: 104,919 of FMA's 104,936 labels are `@en`; only 17 are `xsd:string`), so `= ""` drops ~99.98% of them. Always `IN ("", "en")` — the only form correct on both halves of the endpoint. It also excludes the Japanese labels (e.g. PubCaseFinder's 発作 for `HP_0001250`).
- **The same IRI gets conflicting labels from different graphs — take the owner's, not the first row.** Map the IRI prefix to its home graph (`SO_`→`ontology/so`, `HP_`→`ontology/hp`, `GO_`→`ontology/go`, `UBERON_`→`ontology/uberon`, `CL_`→`ontology/cl`, `ECO_`→`ontology/eco`, `EFO_`→`ontology/efo`). Real case: `RO_0002211` is "regulates" in `go`/`cl`/`clo`/`po`/`uberon` but **"has_component" in `ontology/xco`** — flatly wrong. Row order is arbitrary without an `ORDER BY`, so "the first row" is not a deterministic pick, let alone a correct one: bind the owning graph, or read all rows and take the majority.
- **Shared-prefix predicates (`RO_`, `BFO_`, `IAO_`) have no home graph — and `ontology/go` is NOT a reliable fallback.** There is no `ontology/ro`. They resolve only where an importing ontology's closure embeds them, so every hit is second-hand *and coverage is per-term*: a graph carries only the RO_/BFO_ terms it actually uses. Verified 2026-07-16 — a go-pinned lookup returns **0 rows** for `RO_0002206` "expressed in" (cl/clo/pro/uberon), `RO_0002162` "in taxon" (cl/clo/efo/po/uberon) and `BFO_0000001` "entity" (clo/uberon), while GO *does* carry the ones it uses (`RO_0002211`, `BFO_0000050`, `IAO_0000115`). So do **not** pin one graph: bind `?g` over a `VALUES` set and read all rows (`ontology/uberon` and `ontology/clo` were the broadest carriers tested). Take the majority label, expect harmless variants (`part of` / `part_of`; `regulates` / `regulates (processual)`), and treat a lone dissenter as noise.

Use **OLS4** (`OLS4:searchClasses`, `fetch`, `getAncestors`/`getDescendants`) instead when the term's ontology isn't on the primary endpoint, or when you need the *definition*, synonyms, or hierarchy rather than a label. OLS4 is per-ontology authoritative, so it sidesteps the cross-graph collision above entirely — but it's one term per call and can't join to data. Rule of thumb: **many IRIs → the batch SPARQL above; one IRI you need to genuinely understand → OLS4.**

#### 2e. Verify predicate cardinality for every predicate an example uses

For each class–predicate pair an example will traverse, determine the actual multiplicity with a cardinality distribution query. v3 has no ShEx shapes, but cardinality still decides **two concrete authoring choices**: whether a predicate must be wrapped in `OPTIONAL` in the example (some subjects have 0 values), and whether a naive join fan-outs (some subjects have >1 value → the row count multiplies, so the `verified:` block needs a note or the query needs `DISTINCT`).

```sparql
SELECT ?nValues (COUNT(?s) AS ?nSubjects) WHERE {
  GRAPH <…> {
    { SELECT ?s (COUNT(?o) AS ?nValues) WHERE {
        ?s a <TargetClass> ; <TargetPredicate> ?o .
      } GROUP BY ?s }
  }
}
GROUP BY ?nValues ORDER BY ?nValues
```

Map the result to the authoring choice:

| Observed pattern | v3 consequence |
|---|---|
| All subjects, exactly 1 value | required — use it as a plain triple; a coverage figure of 100% |
| Some subjects have 0, none have > 1 | wrap in `OPTIONAL` in any example that selects it; record the coverage % (in `entity_counts` or a `schema_delta` line) |
| Some subjects have > 1 | the join fans out — the example needs `DISTINCT` or a `verified:` note explaining the row multiplier |

**Never assume optionality or multiplicity by intuition.** Every "this is OPTIONAL" / "this can repeat" decision in an example must be justified by a cardinality query result. This step is cheap (one query per predicate) and catches a large class of silent errors — a missing `OPTIONAL` drops rows, a missing `DISTINCT` inflates a count.

#### 2f. Probe design boundaries with a ground-truth asymmetry test

Counts and DESCRIBEs tell you what the schema *contains*; this step tells you where the schema's worldview *diverges from yours* — which is exactly what `global_gotchas` and the examples' `traps_avoided` lines exist to capture. A query that simply succeeds teaches you nothing about the design (you can't see why it worked). The strongest signal is a **controlled asymmetry**: two facts you are confident are biologically true and structurally equivalent, where the obvious query answers one and silently misses the other.

The method:

1. **Anchor on ground truth.** Pick 2–3 facts you *know* are true from domain knowledge — "ROCK2 participates in RHO signaling", "aspirin inhibits COX", "this drug hits this target". Don't pick obscure cases; pick textbook ones, so a zero/partial result can only mean *your query model is wrong*, never *the fact is absent*.
2. **Write the obvious query** — the one a competent but schema-naïve user would write — and run it for all anchors at once.
3. **Read the divergence, not the success.** If every anchor returns, you've confirmed the happy path but learned little. If some return and some don't (the productive case), the difference is localized to the few variables that differ between them — follow that difference down (`SELECT ?p ?o WHERE { <missing-entity> ?p ?o }`, reverse lookups `?s ?p <entity>`, type checks) until you find the predicate/entity-type/grouping the design uses that your query didn't.

Why asymmetry beats a bare zero-result: a single empty result has too many possible causes (typo, wrong graph, nonexistent entity, wrong predicate). A *differential* — "ROCK1 is found, ROCK2 is not, via an identical query" — pins the cause to whatever differs between the two, turning an open-ended debug into a one-variable diff.

Real case (Reactome): the obvious query `?reaction (bp:left|bp:right) ?protein` returned ROCK1 but **not** ROCK2, despite both being textbook RHO effectors. Chasing only that asymmetry surfaced the EntitySet / `bp:memberPhysicalEntity` grouping pattern — a silent trap affecting 45,785 groups that no amount of happy-path querying would have revealed. The discovery became the file's central `critical_warning`.

Distinguish design from accident as you go: some divergences are principled modeling (Reactome EntitySets express "any family member fills this role"); others are export artifacts or curation drift (a predicate sometimes attached directly, sometimes via an intermediate; `UniProt` vs `UniProt Isoform` db split; a misspelled predicate). For the MIE it does not matter which it is — **document the observable behavior and its operational consequence either way.** Understanding the *why* improves your ability to predict sibling traps (if `EntitySet` exists, look for `CandidateSet`/`DefinedSet`); the warning itself records the *what*.

#### 2g. Cross-graph redeclaration / union-inflation probe — MANDATORY on any multi-GRAPH endpoint

Steps 2a–2f are deliberately GRAPH-scoped, which is exactly why they are BLIND to a whole
class of downstream trap. Any graph on this endpoint — a sibling database, or another graph
belonging to this same database — can re-declare the SAME predicate on the SAME shared IRI.
A downstream query with database=<db> defaults to the UNION of all graphs, so an unscoped
triple pattern matches once per graph and inflates rows/COUNTs — silently. A scoped Phase-2b
survey shows the predicate as singular (COUNT = 1 in your graph) and never flags it, so this
probe is the ONLY place the trap is visible.

**Trigger: run 2g whenever `get_graph_list()` returns MORE THAN ONE graph.** Do NOT gate this
on the number of DATABASES on the endpoint — that is the wrong question, and it was the actual
bug in this skill until 2026-07-17:

> `togovar` has an endpoint entirely to itself. Under the old "co-hosts >1 database" rule it
> skipped 2g. It needed the probe anyway: `togovar.org/variant/annotation/clinvar` re-types the
> same variant IRIs that `togovar.org/variant` declares — ×2 across 2,944,525 variants. The
> re-declaring graph belonged to the SAME database. Likewise `glycosmos` sits alone on its
> endpoint and hosts ~150 graphs; `pdb`, `ddbj` and `pubchem` are each "single-database" yet
> carry 43–68 graphs (the full `rdfportal.org/ontology/*` suite plus `mesh` and `goa`).

Conversely, sharing an endpoint does NOT imply a trap — `rhea` shares SIB with UniProt/Bgee/OMA
and probes genuinely clean: no co-tenant touches an `rdf.rhea-db.org` IRI at all. **The entry must
come from the probe, in both directions.**

**Classify into THREE kinds. Zero IRI overlap does NOT mean safe** — this skill said it did until
2026-07-17, and two independent probes disproved it:
  1. **Same IRI, same predicate → ROW DUPLICATION.** EFO re-declares 16,423 MONDO classes → ×4 on
     `?c a owl:Class ; rdfs:label ?l`. DISTINCT masks it; the pin fixes it.
  2. **Same IRI, CONFLICTING value → WRONG ANSWER.** DISTINCT cannot help. `microbedbjp` names taxid
     1224 "Proteobacteria" vs the authoritative "Pseudomonadota"; DDBJ labels taxon 9606 `"9606"`
     while `ontology/taxonomy` labels it `"Homo sapiens"`.
  3. **Same CLASS, DISJOINT IRIs → SCOPE BLEED.** Nothing is duplicated; foreign ENTITIES are added.
     Every row unique and well-formed, so **DISTINCT is useless and only the pin helps**. Measured:
     `?e a dsmz:Enzyme` = 627,832 unpinned, only 8.7% BRENDA's (×11.47); MediaDive's culture media
     ×15.5; `?t a taxo:Taxon` 3,764,445 vs 2,840,372 pinned (×1.33, surplus = gtdb + microbedbjp).
     A ×2 duplicate is conspicuous; a ×15 union of plausible foreign rows is not.
So the overlap probe CLASSIFIES a trap; it never dismisses one. Zero overlap rules out kind 1 only.

Probe two kinds of node, reusing entities already found in 2c/2d:
  (a) a representative entity of THIS database — catches a sibling RE-TYPING it (e.g. OMA
      asserting `<uniprot-protein> a up:Protein` on SIB), which double-counts a bare COUNT;
  (b) each shared reference / hub IRI it points to — taxa, ChEBI, GO, MeSH … the join keys —
      taken from the 2c DESCRIBE object values. **Follow the hub even if the hub is not your
      database**: NBRC's `mccv:MCCV_000065` lands on `identifiers.org/taxonomy/<taxid>`, which
      microbedbjp re-declares — so "pin the NBRC graph" was NOT enough; the trap was on the
      NAME leg, ×1.94, in a graph the reader never asked for.

  SELECT ?g ?p (COUNT(*) AS ?n) WHERE {
    VALUES ?node { <representative-entity> <hub-iri-1> <hub-iri-2> }
    GRAPH ?g { ?node ?p ?o . }
  } GROUP BY ?g ?p ORDER BY ?p ?g

**Keep `?p` unbound. Do NOT lead with `?s a <YourClass>`.** This query is deliberately a REVERSE
probe — every predicate, no type filter — because that is the only shape that sees all three
failure modes at once. A type-first probe produces FALSE CLEANS, twice observed:
  - `ensembl_grch37` types genes as `obo:SO_0001217`, NOT `terms:EnsemblGene` — invisible to a
    type probe — while re-declaring `rdfs:label` on the SAME gene IRIs. Real multiplier ×3. The
    agent that hit this said: "My first two probes came back 'clean' for that reason."
  - `glycovid_pubchem` declares MeSH *descriptor* IRIs as `meshv:Concept`: same-class overlap 0
    (looks clean), cross-class overlap 768, and its label is the bare accession ("D000163").
**Inflation is a PRODUCT of legs**: a graph carrying only the type still multiplies against a graph
carrying only the label (chebi water = 4 type-graphs × 3 label-graphs = ×12). So a per-leg count is
not the answer — after the reverse probe, run the realistic join pinned vs unpinned and report THAT.

Then compare VALUES, not just row counts. Two graphs supplying the same predicate with DIFFERENT
values is worse than a duplicate, because DISTINCT cannot mask it and the result still looks well
formed (EFO drops MONDO's "obsolete " prefix; DDBJ labels taxon 9606 `"9606"` where
ontology/taxonomy says `"Homo sapiens"`).

Read the result against THIS database's own graphs (`graphs.primary` + `graphs.supporting` from 2a). For any
predicate appearing in a graph OUTSIDE that list, the union multiplier for that predicate =
the number of graphs it appears in. Joining k re-declared predicates multiplies as the
PRODUCT (scientificName x3 × rank x3 = x9 rows). Record, per re-declared predicate: the
sibling graph(s), the multiplier, and whether it is a reference-node LABEL or a RE-TYPING of
this DB's own entity. This list is the source for the `graphs.co_hosted` map and a
`global_gotchas` entry in Phase 4 — write it down now, do not reconstruct from memory.

**Record the outcome either way — a clean probe is a RESULT, not a skip.** If 2g finds no
re-declaration, say so AND say what you probed: which legs (type, label/identifier, cross-class,
hub) and the figure behind the verdict. A bare "no re-declaration found" is not enough — a narrow
probe and a thorough one leave identical notes, and the narrow one is how false cleans survive.
Good: *"PROBED CLEAN — ALL LEGS (2026-07-17): reverse probe on 18 IRIs → all 54,242 triples in the
DB's own graph; label leg 0 in every co-tenant."* An omitted field and a probed-clean field look
identical in the finished MIE, and only one is trustworthy; absence on a multi-graph endpoint is a
Phase-5 review failure.

The ONLY exemption is an endpoint where `get_graph_list()` returns exactly one graph (across the
current 36 databases, only `supercon` qualifies — it returns its own graph plus `owl#`). Say so
in the field rather than omitting it.

Do not assume a same-database sibling graph is safe: the "internal split" case cross-inflates
whenever the two graphs share IRIs (togovar above). It is benign only where they do not (e.g.
UniProt's citationmapping graph) — which is something you establish with the probe, not by
assumption. Keep entity counts on COUNT(DISTINCT ?entity) regardless.

### Phase 3 — Design the example set

The `examples` are the load-bearing content: each one **is** the schema shape, the sample, and (via `traps_avoided`) the warning. There is **no fixed count** — author the set the DB's questions actually need. Cover, at minimum:

- **The primary lookup routes** — the 3–6 questions a user most often asks this DB (an entity's core attributes, its key relationships). `complexity: basic`/`intermediate`/`advanced`.
- **Every set-level enumeration route the DB supports** (spec §4.4). For each "**all** entities with property/feature/class X" question, a first-class `enum_*` example showing the controlled-vocabulary / typed-predicate route — never only a text match, never buried as a caveat. Check this DB's row in `benchmark/redesign/enumeration_audit.md`: **Tier A** = the route is buried in v2, so add a *new* standalone `enum_*` example; **Tier B/C** = keep the worked query and its load-bearing caveat together.
- **At least one `aggregation` example** where the DB supports counting — it ships its verified total and demonstrates `COUNT(DISTINCT)` + graph-scoping (the union-inflation-safe recipe).
- **At least one `cross_db` example** where a co-hosted join or a documented xref exists — the least-recoverable, highest-failure class. Set `endpoint_name` on it.

Strategy priorities across the set (unchanged from v2 — the format changed, the query craft did not):

- Prefer specific IRIs / `VALUES` with IRIs, then typed predicates / graph navigation (`rdfs:subClassOf+`, `skos:broader+`).
- Text search is a last resort: at most one example, and only if the Gate Check in `references/query-strategy.md` passes. If you reach for `bif:contains` / `FILTER(CONTAINS(...))` more than once, stop and re-read that file — almost every "free text" field is backed by a controlled vocabulary or IRI somewhere.

**No test leakage (spec §4.6):** as you pick the subject for each example (keyword phrase, class IRI, gold gene/compound/accession), keep it clear of the benchmark. You will grep it against `benchmark/questions/*.yaml` in Phase 5; it is cheaper to pick a neutral member of the same class now.

Read `references/query-strategy.md` now if you haven't — it contains the decision tree, the circular-reasoning trap, and the Virtuoso-specific `bif:contains` pitfalls (especially around property paths).

### Phase 4 — Write the file

Use `references/template.yaml` as your scaffold. Copy it to the target path, then fill it in. Top-level keys, **in order** (spec §2):

1. **`database`** — the DB key (== filename stem).
2. **`discovery`** — `title`, `description` (ONE sentence), `keywords` (lowercase domain terms), `categories`.
   - **Verify each category token is an exact match** — same case, same underscores — against the categories already in the corpus. Print the canonical set with `uv run python scripts/generate_usage_guide_catalog.py --list-categories` (this replaces the retired `list_categories()` tool). An off-spec token fragments the catalog into a single-DB bucket. Do not proceed until every token matches or is a deliberate new category.
3. **The header** — `endpoint`, optional `base_uri`, `graphs`, optional `entity_counts`, `global_gotchas`.
   - **`graphs.co_hosted` is REQUIRED whenever `get_graph_list()` returned >1 graph.** If 2g found re-declaration: one `{name: note}` entry per sibling graph, naming the re-declared predicate(s), the multiplier, the trap kind (reference-label inflation / entity re-typing / empty stub / join target) and the fix. If 2g found nothing, record it explicitly (`probed_clean: "2g probe run YYYY-MM-DD — no re-declaration found"`) — do NOT omit the field; a silent omission is indistinguishable from never having probed. Copy the shape from `uniprot.yaml`; do not invent a new one.
   - **`entity_counts`** — every value `COUNT(DISTINCT)` + graph-pinned, each with a `date:`. Record the inflated unpinned `COUNT(*)` with a "never report" note where union inflation exists.
   - **`global_gotchas`** — the 2–5 database-wide traps, each `{id, say}`. If 2g fired, one of them is `union_inflation`: the per-predicate multipliers; that joining several re-declared predicates multiplies as the PRODUCT; that `a <OwnEntityClass>` may be re-typed by a sibling graph so a bare COUNT double-counts; and the SAFE PATTERN — pin this DB's own graph(s) with GRAPH/FROM (or use `COUNT(DISTINCT ?entity)`). Note that `SELECT DISTINCT` only MASKS the symptom and can collapse genuine multi-valued predicates.
4. **`examples`** — the core. Each entry: `id`, `intent`, `question`, `complexity`, `sparql`, `verified:` (the live result **+ `date:`**), `teaches`, optional `traps_avoided`; `endpoint_name` on `cross_db` examples only. Include the enumeration route(s), one `aggregation`, and one `cross_db` where the DB supports them (Phase 3). A query-specific trap goes here as a `traps_avoided` line, never in `global_gotchas`.
5. **`schema_delta`** (optional) — ONLY non-obvious predicates/idioms **no example demonstrates**. If a predicate appears in an example, it does NOT go here. Not a schema dump.
6. **`id_join_map`** — `stable_anchor`, optional `same_endpoint_joins` (co-hosted direct GRAPH joins — point each at its `cross_db` example), optional `xrefs` (mechanism-agnostic, with coverage), optional `bridged_via_togoid`.

**The `verified:`/`date:` YAML trap (spec §4.1):** use `date:`, **never `on:`** — YAML 1.1 parses the bare word `on` (also `off`/`yes`/`no`) as boolean `true`, so `on: 2026-07-21` becomes the key `true` and a validator looking for `on` silently finds nothing. Quote the date value too.

**One fact, one place (spec §4.2):** do not restate a fact across sections. A predicate shown in an example is not repeated in `schema_delta`. A warning is database-wide (`global_gotchas`) OR query-specific (`traps_avoided`) — never both.

Byte budget: there is no line ceiling, but a v3 file should be **clearly smaller** than the v2 file it replaces (the pilot came in ~55–74% smaller). Record the byte count of both (Phase 5). If it isn't smaller, you are probably restating a fact the examples already carry — the example IS the shape and the sample; don't write them again.

`references/mie-structure.md` has the detailed requirements per key, and `references/template.yaml` is the fillable v3 skeleton. `togo_mcp/data/mie/uniprot.yaml` is the worked reference.

### Phase 5 — Validate (this is the non-negotiable part)

This phase is where most MIE files go wrong, and it's where this skill diverges most from a casual "just generate the YAML" approach. The checklist mirrors spec §5.

**5a. YAML parses; required keys present.** Load the file and confirm it parses, then confirm the required top-level keys exist (`database`, `discovery`, `endpoint`, `graphs`, `examples`, `id_join_map`):

```bash
python3 -c "import yaml,sys; d=yaml.safe_load(open('./togo_mcp/data/mie/<db>.yaml')); \
  req={'database','discovery','endpoint','graphs','examples','id_join_map'}; \
  missing=req-set(d); sys.exit(f'MISSING KEYS: {missing}') if missing else print('keys OK')"
```

Also confirm `discovery` has all four fields and its `description` is one sentence.

**5b. Every example is verified, dated, and actually re-run this pass.** For **every** entry in `examples`:

1. Run its `sparql` against the endpoint. It must execute with no error AND return the right thing — a query that succeeds but returns a union-inflated COUNT is a *failed* test (5d). Record the live result in `verified:` and stamp `date:` with today's date.
2. **The `verified:` value must match what you just saw.** A `verified: {n: 108}` whose query now returns 112 is a drift you must resolve (fix the query or update the figure), not paper over.
3. **Check the `date:` key is literally `date:`, not `on:`** (spec §4.1 YAML trap — `on:` parses as boolean `true`). Grep the file: `grep -nE '^\s+on:' <file>` must return nothing.

Automate the zero-row/error half: `uv run python scripts/check_mie_examples.py <db>` runs every `examples[].sparql` against the live endpoint and flags ZERO-row and ERROR results (it harvests the file's PREFIXes; treats a lone `COUNT`→0 as zero-row; reports 5xx as net-fail, not a defect). **Require a clean run — 0 zero-row, 0 error — before shipping.** A genuinely-empty example (rare) must carry a sibling `expect_empty: true`. The tool does NOT catch a query that returns the WRONG rows (a union-inflated COUNT, a mis-scoped join that still yields plausible rows) — that is 5d, by hand.

For each `cross_db` example that returns results, spot-check join validity: take one join value from the result and `ASK`/`SELECT` against the second graph to confirm it resolves to a real entity there. A `cross_db` query returning 3 rows when thousands are expected is a join failure (the linking IRI form probably differs between the two DBs), not a passing test.

**5c. Elevated coverage: at least one `aggregation` and one `cross_db`** where the DB supports them, and **every set-level enumeration route has its own example** (spec §4.4). Check this DB's row in `benchmark/redesign/enumeration_audit.md`: a **Tier A** DB must add a standalone `enum_*` example; **Tier B/C** must keep the worked query + its load-bearing caveat together. Do not compress a positive route down to a `traps_avoided` caveat.

**5d. Cross-graph inflation (any multi-GRAPH endpoint).** If Phase 2g recorded re-declaration: re-run the 2g probe to confirm each documented multiplier, and confirm the SAFE PATTERN collapses it — the graph-pinned form must return the non-inflated figure the union form inflates. Then confirm every `aggregation`/count example is graph-scoped (or `COUNT(DISTINCT)`) so it reports the un-inflated figure. A `graphs.co_hosted` entry whose multiplier no longer reproduces is stale — fix or remove it.

**A MISSING `graphs.co_hosted` ON A MULTI-GRAPH ENDPOINT IS A REVIEW FAILURE — fail the file.** The gate is `get_graph_list()` returning >1 graph, NOT `get_sparql_endpoints()` showing >1 database (that older wording exempted `togovar`, `glycosmos`, `pdb`, `ddbj`, `pubchem`, all multi-graph on an endpoint of their own). Accept exactly three states:
  - probe-confirmed entries, each naming graph + predicate + multiplier + trap kind + fix;
  - an explicit `probed_clean: "2g probe run YYYY-MM-DD — no re-declaration found"`;
  - a single-graph endpoint, stated as such (only `supercon` qualifies today).
Silence is not one of them.

**5e. Verify every `global_gotchas` / `traps_avoided` cited predicate and IRI exists.** For every predicate name and IRI string cited in a `global_gotchas` `say` or a `traps_avoided` line, run a minimal query confirming it exists on the endpoint:

```sparql
SELECT ?s WHERE { GRAPH <…> { ?s <cited-predicate> ?o } } LIMIT 1
```

Zero rows → the cited predicate/IRI is wrong; fix it. A warning about a non-existent predicate is worse than no warning. Also confirm each trap is still accurate against the current snapshot — one documented in a previous version may have been corrected upstream.

**5f. Verify `id_join_map` and `entity_counts`.** Mint each xref IRI form by DESCRIBEing a real entity and reading the actual object value (do not trust documentation); if two forms exist, name which is the join key. Every `entity_counts` value is `COUNT(DISTINCT)` + graph-pinned, re-run this pass, with its `date:`. A coverage percentage must equal `(subset count)/(class count)` to within rounding — document ~65.9%, not a loose "~70%".

**5g. Verify every search-wrapper claim.** Rule 2 covers tool-behavior claims, not just SPARQL. For each assertion the file makes about a `search_*` / `ncbi_esearch` / `OLS4:searchClasses` tool (scan `teaches`/`traps_avoided`/`id_join_map`), call the tool exactly as the claim implies and confirm the result. "Tool X maps term T to ID I" passes ONLY if the tool returns I *usably*: at the top, or within a limit a caller would plausibly use — not at rank 5 behind unrelated hits, and present at the limit the claim states. If the tool doesn't satisfy the claim, rewrite it to what the tool actually does (with the rank/limit caveat) or drop it. (Real regression: the ChEMBL MIE claimed `search_chembl_target("EGFR") → CHEMBL203`; the tool returned CHEMBL203 at rank 5, and not at all at `limit=3`.)

**5h. No test leakage (spec §4.6).** For every example, check its subject (keyword phrase, class IRI, gold gene/compound/accession) against `benchmark/questions/*.yaml` — grep the `inspiration_keyword` and `exact_answer` fields. If a subject collides with a question that uses **this DB**, swap it for a neutral member of the same class and re-verify. Canonical non-benchmark subjects (ATP, TP53, BRCA1) are fine.

**5i. Record the byte count** of the v3 file and the v2 file it replaces (the deterministic half of the win — spec §5 item 7). It should be clearly smaller; if not, hunt for a fact restated across sections (§4.2) and cut it.

### Phase 6 — Regenerate the catalog, then declare

**If you added, removed, or changed the MIE's discovery block** (`discovery:` in v3 / `schema_info:` in v2 — its title, description, keywords, or categories), regenerate the static database catalog so the served Usage Guide stays in sync:

```bash
uv run python scripts/generate_usage_guide_catalog.py   # rewrites usage_guide_v6/02b_database_catalog.md
```

The `tests/test_catalog_in_sync.py` drift guard fails if you skip this. A pure examples/schema edit that left the discovery block untouched produces no diff — running it is still safe (idempotent). Include the regenerated `02b_database_catalog.md` in your changes.

Only after Phases 1–5 (and the regeneration above) are complete, report to the user:

```
✓ MIE file (v3) written to ./togo_mcp/data/mie/<db>.yaml
  - YAML parses; required keys present (database, discovery, endpoint, graphs, examples, id_join_map)
  - discovery: 4 fields present, description one sentence; category tokens exact-matched (list_categories() retired)
  - examples: N/N executed live; every one carries verified: with a date: (no `on:` key); check_mie_examples.py <db> → 0 zero-row / 0 error
  - elevated classes: ≥1 aggregation + ≥1 cross_db present (or "DB supports neither: <why>");
    every set-level enumeration route is a first-class example (enumeration_audit tier: [A/B/C/OK])
  - cross-graph inflation: co-hosted endpoint probed (2g), multipliers + safe pattern validated
    and recorded in graphs.co_hosted/global_gotchas — or "single-graph endpoint, N/A"
  - global_gotchas/traps_avoided: all cited predicate names and IRIs confirmed against endpoint
  - id_join_map/entity_counts verified: xref IRI forms confirmed by DESCRIBE, counts COUNT(DISTINCT)+pinned+dated
  - search-wrapper claims verified: every search_*/ncbi/OLS4 tool-behavior claim run through
    the tool and confirmed to return the stated result usably (5g) — or "no tool-behavior claims"
  - no test leakage: no example subject collides with benchmark/questions/*.yaml for this DB (5h)
  - database catalog regenerated: generate_usage_guide_catalog.py run if discovery changed; 02b in the changeset (test_catalog_in_sync passes)
  - Bytes: [v3 count] (was [v2 count], −[pct]%)
```

If any bullet can't be checked off honestly, say so and explain what's left.

## Quality bar

A complete v3 MIE file satisfies:

- Required keys present and in order (spec §2); YAML parses.
- Clearly smaller than the v2 file it replaces (the pilot: −55–74%). No fact restated across sections (§4.2): a predicate in an example is not repeated in `schema_delta`; a warning is `global_gotchas` OR `traps_avoided`, never both.
- **Every** `examples[].sparql` re-run live, with a `verified:` block carrying the real result + a `date:` (never `on:`). `check_mie_examples.py <db>` clean.
- Query craft: prioritise specific IRIs / typed predicates over text search; `bif:contains` over `FILTER(CONTAINS())` on Virtuoso, property paths split before it; no circular reasoning (never `VALUES ?x { <search-api results> }` inside a COUNT).
- At least one `aggregation` and one `cross_db` example where the DB supports them; every set-level enumeration route is a first-class `example` (not a caveat) — spec §4.4.
- `global_gotchas` documents every database-wide silent-failure trap (mandatory filters, IRI namespace mismatches, absent labels, verbatim typos, union inflation); every cited predicate/IRI confirmed live.
- On a multi-graph endpoint, cross-graph re-declaration probed (2g); any union-inflation trap recorded in `graphs.co_hosted` + `global_gotchas` with the graph-pinned safe pattern (or `probed_clean`).
- Every search-wrapper behavior claim run through the tool and confirmed at a usable rank/limit — not just that the tool ran (5g).
- No example subject drawn from the benchmark for this DB (spec §4.6).

## Reference files

- `references/query-strategy.md` — query design hierarchy, circular-reasoning trap, text-search Gate Check, Virtuoso pitfalls. **Read this before designing the example set.**
- `references/mie-structure.md` — the v3 per-key requirements, what goes where, what v3 dropped.
- `references/template.yaml` — the fillable v3 YAML skeleton with inline comments.
- `references/anti-patterns.md` — where trap knowledge lives in v3 (`global_gotchas` vs inline `traps_avoided`), and the enumeration-route rule.
- `togo_mcp/data/docs/MIE_v3_spec.md` — **the authorable contract.** Read it; it wins over this skill on any disagreement.
- `togo_mcp/data/mie/uniprot.yaml` — the worked v3 reference.

## One more thing about text search

Text search (`bif:contains`, `FILTER(CONTAINS())`) is seductive because it always "works" in the sense of not erroring out. It is almost never the right choice. Before using it in an example, confirm:

- You have inspected the live schema (Phase 2 surveys) and checked for specific IRIs
- You have checked for typed predicates with controlled vocabularies
- You have checked for hierarchical relationships (`rdfs:subClassOf`, `skos:broader`)
- You have used any available search API to find and DESCRIBE example entities
- You can write a sentence (put it in the example's `teaches`) explaining why no structured alternative exists

If you cannot write that sentence, the structured alternative exists — keep looking.

Good luck. These files are a lot of work to get right, but a well-made MIE turns an unfamiliar RDF database into something the next LLM can actually query.

---
name: mie-generator
description: Generate or update MIE (Metadata Interoperability Exchange) YAML files that describe RDF databases for TogoMCP. Use this skill whenever the user asks to create, write, regenerate, update, or improve an MIE file for any RDF database (UniProt, ChEMBL, Reactome, Rhea, PubChem, MeSH, PDB, or any new bio/chem database being added to TogoMCP), or mentions anything about the `togo_mcp/data/mie/` directory, MIE schema documentation, database onboarding for TogoMCP, or describing an RDF endpoint's schema/ShEx/SPARQL examples for LLM consumption. Trigger even if the user says things like "document this database", "add Reactome to our MIE collection", "the ChEMBL metadata file is out of date", or "I need to describe this SPARQL endpoint for Claude" — as long as the context is TogoMCP or an RDF database being described in YAML.
---

# MIE File Generator

An MIE file is a compact YAML document that describes an RDF database well enough for an LLM to write correct, efficient SPARQL against it on the first try. Good MIE files are the difference between "Claude writes a working query" and "Claude times out the endpoint with a `FILTER(CONTAINS())` over 244M triples".

This skill lives in a Claude Code environment with filesystem access and SPARQL execution tools (from the `togomcp_local` MCP server). Use filesystem tools freely — that is the normal mode of operation here.

## The Two Hard Rules

**1. No blind SPARQL retry loops.** Schema discovery legitimately requires many queries, but if a query fails twice in a row, stop and diagnose — wrong predicate, wrong graph, wrong IRI pattern — before retrying. More retries without diagnosis do not fix a structurally wrong query.

**2. Nothing in the MIE file is invented — and "it ran" is not "it's right."** Every RDF triple in `sample_rdf_entries` must be retrievable, and every *executable claim* in the file must be executed against the real endpoint before the file is written **and its result confirmed correct**, not merely error-free:

- **SPARQL** (`sparql_query_examples`, `cross_database_queries`, `anti_patterns.correct_sparql`, embedded `cross_references`): must run AND return the right thing. A query that succeeds but returns a union-inflated COUNT is a *failed* test, not a passing one — scope the graph and verify the figure (Phase 2g / 5i).
- **Search-wrapper claims**: any assertion the file makes about a `search_*` / `ncbi_esearch` / `OLS4:searchClasses` tool's behavior (e.g. `architectural_notes.query_strategy`'s "use `search_chembl_target` for targets, EGFR → CHEMBL203") must be run through the actual tool and the claimed hit confirmed to appear at a *usable* rank/limit — not buried at rank 5 behind unrelated hits, and present at the limit the claim implies (Phase 5j).

Fake or unverified examples are worse than missing ones: they train the downstream LLM to write queries *and tool-calls* that look right but fail silently.

## File locations in this environment

| Asset                      | Path                                       | Tool to use            |
|----------------------------|--------------------------------------------|------------------------|
| Existing MIE files         | `./togo_mcp/data/mie/<db>.yaml`            | Read / Write / Edit    |
| Endpoint registry          | `./togo_mcp/data/resources/endpoints.csv`  | Read / Edit            |

Phase 2 (live discovery) is the canonical source of truth for the schema and example queries — never let prior assumptions override what the endpoint actually exposes.

The MCP tools `get_MIE_file` and `save_MIE_file` are **not** used in this environment — read and write MIE files directly. The remaining TogoMCP tools (`run_sparql`, `find_databases`, `list_databases`, `get_sparql_endpoints`, `get_graph_list`, the search APIs) ARE used; they hit live endpoints and cannot be replaced by filesystem access. `WebFetch` is used in Phase 0 to look up unregistered endpoints on rdfportal.org.

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

1. `Read ./togo_mcp/data/mie/<db>.yaml` — is there an existing MIE? If yes, this is an update, not a fresh build. Note which sections are weak. **Treat every claim in the existing file as a hint to verify, not a source of truth — including `schema_info.graphs`. Graphs get added upstream all the time, and a previously-correct graph list can be incomplete by the next snapshot.** Phase 2a is mandatory whether you're authoring or revising.
2. Call `get_sparql_endpoints()` — confirm the endpoint URL is what you expect (it should already be in `endpoints.csv` after Phase 0).

That's it. Phase 2 is where the real work happens. Local prior art — **the existing MIE under revision** — is optional context; **do not let it shape the MIE without re-verification against the live endpoint**.

### Phase 2 — Discover (10–20 minutes)

Goal: extract the named graph(s), classes, typed predicates, IRI patterns, and representative entities you'll need so that `sparql_query_examples` can prefer structured lookups over text search. This is the canonical source of truth — every fact in the MIE comes from queries you ran here.

#### 2a. Identify the data graph(s) — mandatory, including for revisions

Endpoints often host multiple databases (SIB hosts UniProt + Rhea + Bgee + OMA; the primary endpoint hosts ~30 ontologies and datasets). Picking the right graph(s) is step zero.

**This step is mandatory whether you're authoring a new MIE or revising an existing one.** The most common revision failure is trusting the existing `schema_info.graphs` as authoritative — graphs get added upstream between snapshots, and a stale list silently caps every downstream query. A real instance: an Ensembl revision missed `ensembl-glossary`, `ensembl_ontology`, and `ensembl_taxonomy` because the existing graphs list was treated as ground truth. If `get_graph_list` wasn't called this turn, you don't know what graphs exist.

```python
get_graph_list("<db>")
```

`get_graph_list` filters out Virtuoso/OpenLink internal graphs and **ranks graphs whose URI contains the database slug at the top** — so `get_graph_list("bgee")` puts `<http://bgee.org>` first; `get_graph_list("supercon")` puts `<http://rdfportal.org/dataset/supercon>` first. Common URI conventions in RDF Portal: `http://<db>.org` (Bgee, Rhea, JCM), `http://rdfportal.org/dataset/<db>` (OMA, BRENDA, ChEBI, Reactome), `http://sparql.<db>.org/<db>` (UniProt). Browse the ranked list, pick the graph(s). For a revision, diff what you find against `schema_info.graphs` in the existing file — additions and removals both matter.

**Multi-graph databases** (UniProt, Bgee with subgraphs, etc.): if several graphs share the same prefix (e.g. `sparql.uniprot.org/{core,taxonomy,go,keywords,…}`), the database spans all of them — list them all in `schema_info.graphs` and document the role of each in `architectural_notes.schema_design`.

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

Counts give you a feel for which classes are central (top 5 typically carry 90%+ of the data) and which predicates form the backbone of the schema. Skip BFO / CDAO / framework upper-types when documenting in `shape_expressions` — pick the canonical class.

**Run a dedicated predicate survey for every class you plan to document in `shape_expressions`** — not only the top-level anchor class. Annotation classes, measurement classes, and cross-reference classes are just as likely to have missing or misnamed predicates as the central entity class. The rule is simple: if a class will appear in `shape_expressions`, its predicate survey must have been run before you write that shape. A predicate absent from the survey has no business in the shape; a predicate present in the survey with COUNT > 0 must be either documented or explicitly excluded with a note.

While running predicate surveys, note any predicate whose COUNT distribution is surprising as a `critical_warnings` candidate:

- COUNT equals class instance count but the predicate name looks like it might have an alias or alternate namespace form — confirm only one form is queryable.
- COUNT is much lower than the class instance count for a predicate that looks mandatory — document as a caveat on cardinality, or as a trap if omitting it causes a silent wrong result rather than just an empty one.
- COUNT is greater than the class instance count for a predicate that looks singular — document the multi-valued behaviour.
- Two predicates return overlapping results for what appears to be the same concept — document which form is the correct join key.

Caveat: this predicate survey is GRAPH-scoped, so it CANNOT see cross-graph re-declaration —
a predicate duplicated in ANOTHER graph (a sibling dataset's, or another of this database's own)
reads as COUNT = 1 here and looks perfectly singular. Never conclude "singular, therefore safe"
from a scoped COUNT on any endpoint holding more than one graph. That trap is found only by the
2g union-inflation probe.

Write these candidates down immediately. `critical_warnings` is assembled in Phase 4 from this list — not reconstructed from memory.

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

Run this on every predicate you plan to traverse in `sparql_query_examples`. If the object set is heterogeneous: enumerate **all** object kinds with their counts in the shape comment and `critical_warnings`, and show the disambiguating filter (e.g. `FILTER(CONTAINS(STR(?o), "/protein/"))`) in the example query. Real case: PubChem's `obo:RO_0000057` (MeasureGroup → target) resolves to protein **and** taxonomy, gene, cell, and anatomy IRIs — five object kinds under one predicate; a query filtering to only one silently loses the rest, and the first revision documented only three of the five until this GROUP BY was run.

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

Map the result to the exact-match rule, and record it in `critical_warnings` whenever a query would break by getting it wrong:

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

Use these inspections to nail down: IRI patterns (`http://<base>/<class>/<id>`), denormalized predicates (one predicate that serves multiple roles — e.g. Bgee's `genex:isExpressedIn` mixing anatomy IRIs and condition IRIs), measurement scaffolds (bnode chains for typed-value triples), and parallel namespace traps (the same NCBI taxon ID minted under two different IRI schemes — Bgee, see its critical_warnings).

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

If no search tool exists (BRENDA, BacDive, MediaDive, SuperCon, Glycosmos, NIMS): generate a short `bif:contains` (Virtuoso) probe to find one example, DESCRIBE it, and pivot to typed-predicate queries from there. Document this as the only legitimate text-search use, and note in `architectural_notes.text_search_justification` why no structured alternative existed.

**The inverse direction — an opaque IRI whose meaning you don't know.** 2b/2c routinely surface bare numeric OBO IRIs (`SO_0000704`, `RO_0002211`, `BFO_0000050`, `ECO_0000269`) as predicates or objects. **Never guess one from its shape, and never gloss one in a comment you didn't resolve** — a wrong gloss in `shape_expressions` is invisible to Phase 5 (the query still runs) and ships as fact.

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

#### 2e. Verify predicate cardinality for every shape

For each class–predicate pair you intend to document in `shape_expressions`, determine the actual multiplicity with a cardinality distribution query:

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

Map the result to the correct ShEx cardinality modifier:

| Observed pattern | ShEx notation |
|---|---|
| All subjects, exactly 1 value | `IRI` (no modifier — required) |
| Some subjects have 0, none have > 1 | `IRI ?` |
| Some subjects have > 1 | `IRI *` (if 0 is possible) or `IRI +` |

**Never assign `?`, `+`, or `*` based on intuition.** Every modifier must be justified by a cardinality query result. This step is cheap (one query per predicate) and catches a large class of silent errors in the finished MIE.

#### 2f. Probe design boundaries with a ground-truth asymmetry test

Counts and DESCRIBEs tell you what the schema *contains*; this step tells you where the schema's worldview *diverges from yours* — which is exactly what `critical_warnings` exists to capture. A query that simply succeeds teaches you nothing about the design (you can't see why it worked). The strongest signal is a **controlled asymmetry**: two facts you are confident are biologically true and structurally equivalent, where the obvious query answers one and silently misses the other.

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
and probes clean, and `dataset/gtdb` co-habits with NCBI Taxonomy but uses entirely its own IRIs
(zero overlap), so it cannot inflate a taxon join. **The entry must come from the probe, in both
directions.** Probe two kinds of node, reusing entities already found in 2c/2d:
  (a) a representative entity of THIS database — catches a sibling RE-TYPING it (e.g. OMA
      asserting `<uniprot-protein> a up:Protein` on SIB), which double-counts a bare COUNT;
  (b) each shared reference / hub IRI it points to — taxa, ChEBI, GO, MeSH … the join keys —
      taken from the 2c DESCRIBE object values.

  SELECT ?g ?p (COUNT(*) AS ?n) WHERE {
    VALUES ?node { <representative-entity> <hub-iri-1> <hub-iri-2> }
    GRAPH ?g { ?node ?p ?o . }
  } GROUP BY ?g ?p ORDER BY ?p ?g

Read the result against THIS database's own graphs (schema_info.graphs from 2a). For any
predicate appearing in a graph OUTSIDE that list, the union multiplier for that predicate =
the number of graphs it appears in. Joining k re-declared predicates multiplies as the
PRODUCT (scientificName x3 × rank x3 = x9 rows). Record, per re-declared predicate: the
sibling graph(s), the multiplier, and whether it is a reference-node LABEL or a RE-TYPING of
this DB's own entity. This list is the source for the `co_hosted_graphs` field and a
`critical_warnings` entry in Phase 4 — write it down now, do not reconstruct from memory.

**Record the outcome either way — a clean probe is a RESULT, not a skip.** If 2g finds no
re-declaration, write `co_hosted_graphs: ["2g probe run YYYY-MM-DD — no re-declaration found"]`.
An omitted field and a probed-clean field look identical in the finished MIE, and only one of
them is trustworthy; absence on a multi-graph endpoint is a Phase-5 review failure.

The ONLY exemption is an endpoint where `get_graph_list()` returns exactly one graph (across the
current 36 databases, only `supercon` qualifies — it returns its own graph plus `owl#`). Say so
in the field rather than omitting it.

Do not assume a same-database sibling graph is safe: the "internal split" case cross-inflates
whenever the two graphs share IRIs (togovar above). It is benign only where they do not (e.g.
UniProt's citationmapping graph) — which is something you establish with the probe, not by
assumption. Keep entity counts on COUNT(DISTINCT ?entity) regardless.

### Phase 3 — Design the query set

You are going to write **exactly 7 SPARQL examples**: 2 basic, 3 intermediate, 2 advanced. The distribution across strategies should look like:

- ≥ 2 queries use specific IRIs or `VALUES` with IRIs
- ≥ 2 queries use typed predicates or graph navigation (`rdfs:subClassOf+`, `skos:broader+`)
- ≤ 1 query uses text search, and only if the Gate Check in `references/query-strategy.md` passes

If you find yourself reaching for `bif:contains` or `FILTER(CONTAINS(...))` more than once, stop and re-read `references/query-strategy.md`. Almost every field that looks "free text" in an RDF database is actually backed by a controlled vocabulary or IRI somewhere.

Read `references/query-strategy.md` now if you haven't — it contains the decision tree, the circular-reasoning trap, and the Virtuoso-specific `bif:contains` pitfalls (especially around property paths).

### Phase 4 — Write the file

Use `references/template.yaml` as your scaffold. Copy it to the target path, then fill it in. Required sections, in order:

1. `schema_info`
   - **After filling in `schema_info.categories`, call `list_categories()` and verify each token you wrote is an exact match — same case, same underscores — against the returned list. Do not proceed to the next section if any token is off-spec; fix it first.** An off-spec token silently excludes the database from `find_databases(category=…)` results.
   - **`co_hosted_graphs` is REQUIRED whenever `get_graph_list()` returned >1 graph** (the field
     already exists in the schema). If 2g found re-declaration: one entry per sibling graph,
     naming the re-declared predicate(s), the multiplier, the trap kind (reference-label
     inflation / entity re-typing / empty stub / older nomenclature vintage) and the fix. If 2g
     found nothing, write the explicit `"2g probe run YYYY-MM-DD — no re-declaration found"` —
     do NOT leave the field out; a silent omission is indistinguishable from never having probed.
     Copy the shape from `togovar.yaml` or `uniprot.yaml`; do not invent a new one.
   - `data_version`: a date you verified this session, or an endpoint-derived release citing its
     source. Never carry the old value forward unchecked (see 5i-2).
2. `critical_warnings` (use `[]` only if there are genuinely none — most real databases have at least one silent-failure trap)
   - If 2g fired, add a UNION-INFLATION warning: the per-predicate multipliers; that joining
     several re-declared predicates multiplies as the PRODUCT; that `a <OwnEntityClass>` may be
     re-typed by a sibling graph so a bare COUNT over it double-counts; and the SAFE PATTERN —
     pin this DB's own graph(s) with GRAPH/FROM (or use COUNT(DISTINCT ?entity)). Note that
     SELECT DISTINCT only MASKS the symptom and can collapse genuine multi-valued predicates.
3. `shape_expressions`
4. `sample_rdf_entries` — exactly 3, shared prefix block
5. `sparql_query_examples` — exactly 7, distribution 2/3/2
6. `cross_database_queries` — 1–2 if a shared endpoint exists, `examples: []` with explanatory `notes` otherwise
7. `cross_references`
8. `architectural_notes`
9. `data_statistics`
10. `anti_patterns` — 3–4, must include "schema check before text search"
    - If 2g found union inflation, add it as a dedicated anti-pattern: wrong = an unscoped join
      touching a re-declared predicate on this co-hosted endpoint (inflated rows/COUNT); correct
      = the graph-pinned form. references/anti-patterns.md already sanctions a 5th slot for a
      discovered database-specific trap.
11. `common_errors` — 2–3

**Before finalising `shape_expressions`:**

- **Every `@<ShapeRef>` must have a corresponding defined block.** Search the `shape_expressions` string for every `@<…>` reference and confirm each one resolves to a `<…Shape> { … }` definition in the same section. A referenced-but-undefined shape is a structural error — the downstream LLM will generate property-path queries that silently return nothing.

- **Mark optional co-types explicitly.** When a class is sometimes (but not always) additionally typed with a second class, write each sub-type as a separate optional constraint rather than grouping them in a single `a [ T1 T2 T3 ] +` block. The grouped form is correct ShEx but visually implies all types are always co-present:

  ```shex
  # Avoid — looks like all three are always expected:
  a [ ex:MainType ex:SubTypeA ex:SubTypeB ] + ;

  # Prefer — cardinality is explicit and verifiable:
  a [ ex:MainType ] ;
  a [ ex:SubTypeA ] ?   # ~80% of instances — confirmed by COUNT
  a [ ex:SubTypeB ] ?   # ~80% of instances — confirmed by COUNT
  ```

  Annotate the percentage in an inline comment so the figure is traceable to Phase 2e.

Line budget: 400–600 lines typical, up to 700–900 for genuinely complex databases. If you're over 900, you are probably duplicating between `shape_expressions` and `architectural_notes` — consolidate.

`references/mie-structure.md` has the detailed requirements per section, and `references/template.yaml` is the fillable skeleton.

### Phase 5 — Validate (this is the non-negotiable part)

This phase is where most MIE files go wrong, and it's where this skill diverges most from a casual "just generate the YAML" approach.

**5a. Validate every RDF example.** For each of the 3 entries in `sample_rdf_entries`, write a SELECT that retrieves exactly those triples from the endpoint and confirm it returns results. If a triple can't be retrieved, either fix it (likely the IRI or predicate is wrong) or replace the entry with one you can retrieve. **No fabricated RDF ever reaches the final file.** The downstream LLM will copy these patterns — if they're wrong, every query it writes will inherit the error.

A practical check:

```sparql
ASK WHERE {
  <http://example.org/entity1> a ex:Type ;
                               ex:required "value" .
}
```

If `ASK` returns false, the triple as written does not exist in the endpoint. Do not include it.

**5b. Test every SPARQL query.** Run all 7 of `sparql_query_examples`, every example in `cross_database_queries`, every `correct_sparql` block in `anti_patterns`, and any SPARQL embedded in `cross_references`. Every single one. If a query times out or errors, fix it or replace it — do not ship queries that don't run. If a query runs but returns zero rows when it shouldn't, that's also a failure (usually a namespace trap — investigate and document in `critical_warnings`).

For each cross-database query that returns results, additionally spot-check join validity: take one join value from the result set and run a quick `ASK` or `SELECT` against the second database to confirm it resolves to a real entity there. A query returning 3 rows when thousands are expected is a join failure, not a passing test — the IRI form used for linking likely differs between the two databases.

**5c. Verify statistics.** Every count or coverage percentage in `data_statistics` must come from a real query you ran, and must have a `verified_date`. If you can't verify a number, omit it rather than guessing.

After verifying individual counts, cross-check arithmetic consistency:

- Does `total_entities` equal (or plausibly approximate) the sum of the major `by_class` counts?
- Does each coverage percentage equal `(subset count) / (class count)` to within rounding? E.g. if 673,263 entities carry a property and there are 1,021,677 in the class, the percentage must be documented as ~65.9%, not loosely as "~66%" or "~70%".

Flag and correct any discrepancy before publishing.

**5d. Validate the YAML.** Load the file with PyYAML to confirm it parses:

```bash
python3 -c "import yaml; yaml.safe_load(open('./togo_mcp/data/mie/<db>.yaml'))"
```

If this fails, fix the YAML before calling the work done.

**5e. Audit `shape_expressions` for completeness.** For each shape block:

1. Re-run the Phase 2b predicate survey and compare against the documented predicates. Any predicate with COUNT > 0 that is absent from the shape must be either added or explicitly noted as intentionally excluded.
2. Confirm every `@<ShapeRef>` has a defined `<…Shape>` block.
3. For every predicate marked `?` (optional), confirm with a cardinality query that at least one subject has 0 values for it. For every predicate with no modifier (required), confirm its COUNT equals the class instance count.
4. **Verify `@<ShapeRef>` object-class conformance — not just that the ref resolves.** Item 2 confirms the *block exists*; this confirms the *objects actually belong to it*. For every predicate written as `<predicate> @<TargetShape>`, GROUP BY the object's `rdf:type` and confirm the result includes `<TargetShape>`'s declared anchor class. A predicate whose objects are *not* typed as the referenced shape's class — or are split across several classes — is a shape error (or an undocumented polymorphic link, cf. Phase 2's polymorphism probe): fix the `@<…>` target, or split it and document the polymorphism. A blank-node target with no `rdf:type` is itself a finding — note it explicitly rather than implying a typed class.

   ```sparql
   SELECT ?objType (COUNT(*) AS ?n) WHERE {
     GRAPH <…> { ?s a <SubjectClass> ; <predicate> ?o .
                 OPTIONAL { ?o a ?objType } }
   } GROUP BY ?objType ORDER BY DESC(?n)
   ```

5. **Probe the value type of *every* literal-valued predicate in the shape — not only the ones a query will filter on.** Phase 2's literal probe is scoped to literals you plan to match exactly; this is the blanket pass that catches a wrong `xsd:…` annotation on an incidental field. For each predicate whose shape value is a literal datatype, GROUP BY its actual datatype and confirm the shape's annotation matches the stored form. A mismatch (e.g. shape says `xsd:integer`, data stores plain or `xsd:string`), or a predicate that stores **mixed** datatypes, must be corrected in the shape and — if it affects exact matching — surfaced in `critical_warnings`.

   **Remember what this GROUP BY cannot see** (Phase 2b): it does NOT distinguish a plain literal from an `xsd:string`-typed one — both report `xsd:string` — so it can neither confirm nor refute a `xsd:string` annotation in the shape. It catches genuine type errors (`xsd:integer` vs string) and language tags only. For any literal the shape's downstream queries will match exactly, settle the form with the per-form ASK from Phase 2b and annotate the shape from THAT. A shape saying `xsd:string` is a claim about the match form; it must be earned by an ASK, not inferred from `DATATYPE()`.

   ```sparql
   SELECT (DATATYPE(?o) AS ?dt) (COUNT(*) AS ?n) WHERE {
     GRAPH <…> { ?s a <SubjectClass> ; <predicate> ?o }
   } GROUP BY (DATATYPE(?o)) ORDER BY DESC(?n)
   ```

This step is not optional. `shape_expressions` is the section a downstream LLM relies on most heavily for query construction. An unaudited shape is equivalent to an untested SPARQL example. Items 4–5 are what separate a shape that is *internally consistent* from one that is *true to the data*: a resolvable `@<ref>` pointing at the wrong object class, or a confidently-wrong datatype, both produce queries that run and silently return nothing.

**5f. Verify `critical_warnings` content.** For every predicate name and IRI string cited in `critical_warnings`, run a minimal query confirming it exists in the endpoint:

```sparql
SELECT ?s WHERE {
  GRAPH <…> { ?s <cited-predicate> ?o }
} LIMIT 1
```

If the query returns no rows, the cited predicate or IRI is wrong — fix it before publishing. A warning about a non-existent predicate is worse than no warning.

Also confirm each warning is still accurate against the current data snapshot: a trap documented in a previous MIE version may have been corrected upstream.

**5g. Verify `cross_references`.** For each cross-reference predicate documented:

1. **Confirm the IRI form** by DESCRIBEing a real entity and reading the actual object value. Do not trust the database's documentation — mint the IRI from what the endpoint actually returns. If two IRI forms are present (e.g. both an `identifiers.org` form and a canonical purl), document both and specify which is the correct join key for federation.

2. **Verify the coverage percentage** with a COUNT query:

   ```sparql
   SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {
     GRAPH <…> { ?s a <EntityClass> ; <crossRefPredicate> ?o }
   }
   ```

   Divide by the class instance count from `data_statistics`. Document the result as the coverage figure — do not estimate.

**5h. Verify prefix declarations.** For each non-standard prefix defined in `shape_expressions` or `sample_rdf_entries`, confirm the base URI is correct by running a minimal SELECT using that prefix:

```sparql
PREFIX ex: <http://suspected-base-uri/>
SELECT ?s WHERE {
  GRAPH <…> { ?s a ex:KnownClass }
} LIMIT 1
```

If the query returns no rows despite the class being known to exist, the prefix base URI is wrong. Standard W3C prefixes (`rdf:`, `rdfs:`, `owl:`, `xsd:`) do not need checking. Database-specific and ontology-specific prefixes (e.g. a Unimod prefix, a PSI-MS prefix, an internal ontology prefix) must all be confirmed.

**5i. Validate cross-graph inflation warnings (any multi-GRAPH endpoint).** If Phase 2g
recorded re-declaration, confirm each documented multiplier by re-running the 2g probe, and
confirm the SAFE PATTERN collapses it — the graph-pinned form must return the non-inflated
figure that the union form inflates. Then re-run every `sparql_query_examples` entry that is
NOT graph-scoped and confirm it does not inflate on this union endpoint; if one does, pin the
graph in the stored query. A `co_hosted_graphs` entry whose multiplier no longer reproduces
against the current snapshot is stale — fix or remove it.

**A MISSING `co_hosted_graphs` ON A MULTI-GRAPH ENDPOINT IS A REVIEW FAILURE — fail the file.**
The gate is `get_graph_list()` returning >1 graph, NOT `get_sparql_endpoints()` showing >1
database (that older wording exempted `togovar`, `glycosmos`, `pdb`, `ddbj` and `pubchem`, all
of which host multiple graphs on an endpoint of their own). Accept exactly three states:
  - probe-confirmed entries, each naming graph + predicate + multiplier + trap kind + fix;
  - the explicit string `"2g probe run YYYY-MM-DD — no re-declaration found"`;
  - a single-graph endpoint, stated as such (only `supercon` qualifies today).
Silence is not one of them.

**5i-2. Verify `data_version` provenance.** It must be either `"RDF Portal snapshot — verified
YYYY-MM-DD"` with a date you probed THIS session, or an endpoint-derived release that cites how
it was derived (e.g. Reactome's `bp:db "Reactome Database ID Release 95"`). A release number you
cannot re-derive from the endpoint right now is a failure — replace it with the dated-snapshot
form. Never carry the previous value forward unchecked when bumping `mie_updated`: that is how
`uniprot.yaml` sat at "Release 2024_06" against data modified 2026-01-28.

**5j. Verify every search-wrapper claim.** Rule 2 covers tool-behavior claims, not just
SPARQL. For each assertion the file makes about a `search_*` / `ncbi_esearch` /
`OLS4:searchClasses` tool — most live in `architectural_notes.query_strategy`, but scan the
whole file — call the tool exactly as the claim implies and confirm the result. "Tool X maps
term T to ID I" passes ONLY if the tool actually returns I *usably*: at the top, or within a
limit a caller would plausibly use — not at rank 5 behind unrelated hits, and present at the
limit the claim states. Rank matters: an ID the tool technically returns but ranks below a
PPI complex, a mouse ortholog, or other noise is not a claim a downstream LLM can rely on. If
the tool doesn't satisfy the claim, either rewrite it to what the tool actually does
(including the rank/limit caveat and the disambiguation the caller needs), or drop it. A false
tool-behavior claim is exactly the "fake example" Rule 2 forbids, aimed at a wrapper instead
of SPARQL. (Real regression: the ChEMBL MIE claimed `search_chembl_target("EGFR") → CHEMBL203`;
the tool returned CHEMBL203 at rank 5, and not at all at `limit=3`.)

### Phase 6 — Final declaration

Only after Phases 1–5 are complete, report to the user:

```
✓ MIE file written to ./togo_mcp/data/mie/<db>.yaml
  - Sample RDF entries validated: 3/3 retrievable from endpoint
  - SPARQL queries tested: N/N executed successfully (N = 7 + cross-DB + cross-ref)
  - Statistics verified: [date]
  - YAML parses cleanly
  - shape_expressions audited: all shapes verified against live predicate surveys,
    all @<ShapeRef>s resolved AND their object classes confirmed by rdf:type GROUP BY,
    all cardinality modifiers confirmed, all literal-valued predicates datatype-probed
  - critical_warnings verified: all cited predicate names and IRIs confirmed against endpoint
  - cross_references verified: IRI forms confirmed by DESCRIBE, coverage % from COUNT queries
  - schema_info.categories checked: all tokens exact-matched against list_categories()
  - prefix declarations verified: all non-standard prefixes confirmed with SELECT
  - data_statistics cross-checked: total_entities and coverage % arithmetically consistent
  - anti_patterns.correct_sparql tested: all correct_sparql blocks executed successfully
  - cross-graph inflation checked: co-hosted endpoint probed (2g), multipliers + safe pattern
    validated and recorded in co_hosted_graphs/critical_warnings — or "single-DB endpoint, N/A"
  - search-wrapper claims verified: every search_*/ncbi/OLS4 tool-behavior claim run through
    the tool and confirmed to return the stated result usably (5j) — or "no tool-behavior claims"
  - Lines: [count]
```

If any bullet can't be checked off honestly, say so and explain what's left.

## Quality bar

A complete MIE file satisfies:

- Compact (400–600 lines typical, ≤ 900 for complex)
- `critical_warnings` documents every silent-failure trap (typos in predicates, IRI namespace mismatches, mandatory performance filters)
- All entity types appear in `shape_expressions` with inline counts
- Exactly 3 `sample_rdf_entries` with a single shared `rdf_prefixes` block — **all 3 validated against the endpoint**
- 7 SPARQL queries (2/3/2), 6–7 prioritising structured lookups, ≤ 1 using text search — **all tested**
- `bif:contains` preferred over `FILTER(CONTAINS())` on Virtuoso (check `access.backend`); property paths split before `bif:contains`
- No circular reasoning (never `VALUES ?x { <results-of-search-api> }` inside a COUNT)
- Every search-wrapper behavior claim (e.g. in `architectural_notes.query_strategy`) run through the tool and confirmed to return the stated result at a usable rank/limit — **not just that the tool ran** (5j)
- Cross-DB: 1–2 examples if shared endpoint, otherwise `examples: []` + explanatory notes
- `data_statistics` contains only verified counts/coverage — no `verification_queries`, `cardinality`, or `performance_characteristics` subfields
- Valid YAML
- On a co-hosted endpoint, cross-graph re-declaration probed (2g); any union-inflation trap
  recorded in `co_hosted_graphs` + `critical_warnings` with the graph-pinned safe pattern
- Anti-patterns: 3–4, including "schema check before text search"
- Common errors: 2–3

## Reference files

- `references/query-strategy.md` — query design hierarchy, circular-reasoning trap, text-search Gate Check, Virtuoso pitfalls. **Read this before designing the query set.**
- `references/mie-structure.md` — per-section requirements, what goes where, what to omit.
- `references/template.yaml` — fillable YAML skeleton with inline comments.
- `references/anti-patterns.md` — worked examples of the four mandatory anti-patterns, plus common errors.

## One more thing about text search

Text search (`bif:contains`, `FILTER(CONTAINS())`) is seductive because it always "works" in the sense of not erroring out. It is almost never the right choice. Before using it, confirm:

- You have read the full `shape_expressions` and checked for specific IRIs
- You have checked for typed predicates with controlled vocabularies
- You have checked for hierarchical relationships (`rdfs:subClassOf`, `skos:broader`)
- You have used any available search API to find and DESCRIBE example entities
- You can write a sentence explaining why no structured alternative exists

If you cannot write that sentence, the structured alternative exists — keep looking.

Good luck. These files are a lot of work to get right, but a well-made MIE turns an unfamiliar RDF database into something the next LLM can actually query.

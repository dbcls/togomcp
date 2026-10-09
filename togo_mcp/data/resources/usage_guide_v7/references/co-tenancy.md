> Usage Guide reference file — fetched on demand with `get_workflow(name="usage-guide", path="references/co-tenancy.md")`. The always-loaded core is `TogoMCP_Usage_Guide()`.

## 🕸️ CO-TENANCY & SILENT-FAILURE TRAPS

Everything in this section fails **silently** — no error, no zero rows, no doubled
count. The result is plausible, correctly shaped, and wrong.

An unpinned query reads **every graph on the endpoint**, not just your database's. A
sibling graph that re-declares a predicate inflates counts; one that *supplies* a
predicate you assume is native narrows your query to an intersection.
`dcterms:identifier` looks like UniProt's — on `sib` only the co-hosted **OMA** graph
supplies it, so `?protein dcterms:identifier ?acc` silently becomes **UniProt INTERSECT
OMA**, dropping every protein with no OMA record. It returned a wrong count (248; truth
249) that passed every check for months.

1. **Pin every pattern.** `FROM <g>` or `GRAPH <g> { ... }`. Partial pinning still
   leaks — the unpinned patterns read the union. **"Your database" may be *several*
   graphs** (the MIE `graphs:` list), not one — list them all as repeated `FROM`
   clauses. UniProt owns **17 graphs**: protein triples live in `.../uniprot`, but a
   taxon's `scientificName`/`rank` live in `.../taxonomy` (and GO defs in `.../go`,
   diseases in `.../diseases`, …), so pinning only `.../uniprot` returns **empty** for
   a taxon-name leg (silent). Pin the *set* your DB owns — that also
   excludes the co-tenants (OMA, Bgee) without a `GRAPH{}` block per pattern.
2. **`SELECT DISTINCT` is NOT the fix.** It can absorb inflation and hand you the right
   number for the wrong reason, then break when the multiplicity changes.
3. **Check a predicate is native:** bind the subject and run
   `SELECT ?g WHERE { GRAPH ?g { <subj> <pred> ?o } }`. >1 graph → re-declared.
   Nothing from your database's graph → it was never yours.
4. **Joins multiply.** *k* re-declared patterns → **2^k** rows per entity.
5. **Single-tenant ≠ safe.** The trap is graphs, not databases (see ENDPOINTS).
6. **The pin is not ground truth.** If pinned ≠ unpinned, that gap is a **finding to
   explain**, not a number to adopt. `dataset/microbedbjp` re-declares NCBI Taxonomy at
   an **older nomenclature vintage** (Proteobacteria *and* Pseudomonadota), and
   "Superkingdom Bacteria" survives **only** there — the authoritative graph has an empty
   rank IRI since NCBI retired "superkingdom". Blind pinning turns correct answers wrong.
7. **Normalize literals with `STR(?label)`.** One predicate in one graph can carry
   **mixed literal forms** — plain, `^^xsd:string`, `@en`, or something rarer
   (`^^xsd:anyURI`, `^^rr:Literal`). They are distinct RDF terms, so `DISTINCT` won't
   collapse them, `GROUP BY` splits the group, and an exact match on the wrong form
   returns 0 with no error. Live: `ontology/fma`'s `rdfs:label` is **104,919 `@en` +
   17 `xsd:string`** — a bare `?s rdfs:label "…"` match reaches at most one of those
   populations. Scan every quoted literal against the MIE's `global_gotchas` and the
   chosen example's `traps_avoided`; `VALUES` blocks are the worst spot.
8. **Never write a `VALUES` block you did not populate from a query you ran.** An
   **empty** one is *valid SPARQL* — it returns one row of `0` instead of erroring. An
   abridged one ("representative", "…") computes a well-shaped number from the wrong set.
9. **Anchor on stable IDs, never an export-local IRI.** Ask: *does any component encode a
   release, a build, an export file, or a counter?* A Reactome BioPAX IRI
   (`.../biopax/95/48887#Pathway2258`) encodes **three**, all re-minted quarterly; the old
   one now has zero triples. Passing today proves nothing — the defect is invisible until
   the next release.

   ```sparql
   ?pathway bp:xref [ bp:db "Reactome"^^xsd:string ; bp:id "R-HSA-196807"^^xsd:string ] .
   ```

   The `^^xsd:string` is mandatory — without it the join silently returns 0.
10. **Two-argument `REGEX()` silently mishandles some metacharacters — 0 rows, no error.**
    **ALWAYS pass a third argument**; `""` is enough, `"i"` also folds case.

    ```sparql
    FILTER(REGEX(?label, "Fentanyl|Sufentanil", ""))     # <- the fix, every time
    ```

    Verified by queries needing no data on **11 of the 13 endpoints** — the original 10 (2026-08-14)
    and `wikipathways` (2026-09-15), all Virtuoso. The exceptions are `idsm` (PostgreSQL-backed)
    and `lipidmaps` (not Virtuoso, 2026-09-15), which handle both forms correctly; pass the third
    argument there anyway, so one habit is safe everywhere. Two constructs are known broken in the
    2-argument form, each returning
    **0** where the answer is not zero:
    alternation — `VALUES ?s { "Fentanyl" "Sufentanil" } FILTER(REGEX(?s, "Fentanyl|Sufentanil"))`
    → 0, want 2 (even `"A|A"` → 0); and brace quantifiers —
    `VALUES ?s { "ab" "aab" "aaab" } FILTER(REGEX(?s, "a{1,2}b"))` → 0, want 3.
    `LCASE()`/`STR()` do not rescue either. Parenthesising happens to fix both, but it needs you
    to know *which* construct is affected — and the two above are what has been **tested**, not a
    proof nothing else is. Unaffected: plain substrings, `[Ff]entanyl`, `? + *`, anchors, `.`,
    escapes, `(?:…)`. That asymmetry is why it survives review: the filter works until someone
    widens it to a family or adds a `{n,m}` count, and the empty result reads as "the database
    doesn't have those." A production session concluded MassBank had no fentanyls; it has 44.
11. **The same entity carries different IRIs in different graphs — the join returns 0, and it
    reads as "no data".** A TogoID relation graph (`dataset/togoid/relation/<a>-<b>`) keys each
    side by TogoID's canonical form for that dataset, which is frequently **not** the form the
    source database's own graph mints. ChEMBL: the `chembl` database uses
    `http://rdf.ebi.ac.uk/resource/chembl/molecule/CHEMBL25`; the relation graph holds
    `http://identifiers.org/chembl.compound/CHEMBL25`. Same molecule, no shared RDF term,
    empty join, HTTP 200.

    **Do not assume `identifiers.org` either** — the form varies per dataset. Verified
    2026-08-29: `ncbigene-go` and `ensembl_transcript-go` key on `identifiers.org/`, but
    `chebi-inchi_key` keys ChEBI as `purl.obolibrary.org/obo/CHEBI_15858`, and `nando-mondo`
    pairs `purl.obolibrary.org/obo/MONDO_…` with `nanbyodata.jp/ontology/NANDO_…`. One row
    tells you both sides before you write the join:

    ```sparql
    SELECT ?s ?o WHERE {
      GRAPH <http://rdfportal.org/dataset/togoid/relation/chembl_compound-inchi_key> { ?s ?p ?o }
    } LIMIT 1
    ```

    Why it survives review: on a sparse database an empty join is indistinguishable from a true
    negative. A production MassBank lookup (2026-08 logs) pinned `VALUES` with native ChEMBL
    IRIs and returned 0 for every compound — which is also exactly what MassBank returns for a
    compound it genuinely has no spectra for.

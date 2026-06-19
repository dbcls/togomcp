# PRISM SPARQL templates

Parameterized, copy-ready queries for each PRISM phase. Replace `«PLACEHOLDERS»`. All target the rdfportal TogoMCP endpoints; run via `run_sparql`. Read the relevant `get_MIE_file` before first use of any database.

## Table of contents
1. Hierarchy expansion (Phase R) — ontology descendants
2. Function axis (Phase R) — GO descendants → UniProt members (+ GeneID)
3. Function axis variant — UniProt keyword (single node; use only when unioning children)
4. Disease axis A (Phase I) — PubTator co-occurrence
5. Disease axis B (Phase I) — NCBI Gene curated association (esearch, not SPARQL)
6. Disease axis C (Phase I) — ClinVar gene-anchored significance × condition (single-graph)
7. Druggability axis (Phase M) — ChEMBL target check
8. Pathway membership (Phase P/M) — Reactome participants by UniProt accession
9. ID bridging (Phase S) — TogoID / UniProt GeneID xref

---

## 1. Hierarchy expansion (Phase R)

Get the transitive closure of an ontology subtree. Run against the ontology DB (`go`, or MONDO/ChEBI equivalents). Feed the result IRIs as `VALUES` into the annotation query (template 2).

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?term
WHERE {
  ?term rdfs:subClassOf+ obo:«ROOT_e_g_GO_0006869» .
  FILTER(STRSTARTS(STR(?term), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 300
```

Notes: include the root itself in your downstream `VALUES`. `subClassOf+` is correct for GO subtrees (small); avoid it on pre-flattened lineages like taxonomy. If the ontology DB lacks the hierarchy, use `OLS4:getChildren` iteratively (one level each) or `OLS4:getDescendants` if loaded.

---

## 2. Function axis — GO descendants → UniProt members (Phase R)

Human, reviewed proteins annotated to ANY term in the expanded set, with NCBI GeneID for later bridging.

```sparql
PREFIX up:   <http://purl.uniprot.org/core/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo:  <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?gene ?geneid
WHERE {
  VALUES ?goTerm { obo:«ROOT» obo:«CHILD_1» obo:«CHILD_2» «…all descendants from template 1…» }
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:classifiedWith ?goTerm ;
           up:encodedBy ?g .
  ?g skos:prefLabel ?gene .
  OPTIONAL {
    ?protein rdfs:seeAlso ?xref .
    ?xref up:database <http://purl.uniprot.org/database/GeneID> .
    BIND(STRAFTER(STR(?xref), "geneid/") AS ?geneid)
  }
}
ORDER BY ?gene
LIMIT 400
```

This is the **memory-independent functional set**. The `OPTIONAL` GeneID block makes Phase S free (no separate TogoID call needed).

---

## 3. Function axis variant — UniProt keyword

Use ONLY if unioning the relevant child keywords; a single keyword under-covers (it is one DAG node).

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX keywords: <http://purl.uniprot.org/keywords/>

SELECT DISTINCT ?gene WHERE {
  VALUES ?kw { keywords:«N1» keywords:«N2» }      # union children, don't use one node
  ?protein a up:Protein ; up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:classifiedWith ?kw ; up:encodedBy ?g .
  ?g skos:prefLabel ?gene .
}
LIMIT 400
```

---

## 4. Disease axis A — PubTator co-occurrence (Phase I)

Genes co-mentioned with a disease (MeSH IRI), ranked. Literature-volume biased — pair with templates 5 and 6.

```sparql
PREFIX oa:     <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX insdc:  <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?gene_symbol (COUNT(DISTINCT ?article) AS ?cooccurrence)
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?d dcterms:subject "Disease" ; oa:hasBody <http://identifiers.org/mesh/«MESH_e_g_D008268»> ; oa:hasTarget ?article .
    ?g dcterms:subject "Gene" ;    oa:hasBody ?geneId ; oa:hasTarget ?article .
  }
  GRAPH <http://rdfportal.org/dataset/ncbigene> { ?geneId a insdc:Gene ; rdfs:label ?gene_symbol . }
}
GROUP BY ?gene_symbol ORDER BY DESC(?cooccurrence) LIMIT 60
```

To intersect with the functional set inside SPARQL, add `VALUES ?geneId { <ncbigene IRIs…> }` — but if it times out, **anchor on the smaller set** and avoid the unfiltered disease scan; or take the top-N here and intersect by ID on the read side.

---

## 5. Disease axis B — NCBI Gene curated association (Phase I)

Not SPARQL — use `ncbi_esearch` (paginate with `start_index`). Curation-based; de-biases vs literature volume and surfaces GWAS loci.

```
ncbi_esearch(database="gene",
  query='("«DISEASE NAME»"[Disease] OR "«DISEASE NAME»") AND Homo sapiens[Organism]',
  max_results=100, start_index=0)   # then 100, 200, … to cover Total Results
```

Intersect the returned Gene IDs with the functional set's GeneIDs (Phase S).

---

## 6. Disease axis C — ClinVar gene-anchored significance (Phase I/M)

**Gene-anchored, single-graph** (the disease-anchored / cross-graph forms time out or return 0). Returns clinical-significance × condition-CUI per gene. Anchor `VALUES` = the intersection candidates (small set).

```sparql
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>
PREFIX med2rdf: <http://med2rdf.org/ontology/med2rdf#>
PREFIX sio: <http://semanticscience.org/resource/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?gene_id ?significance ?id (COUNT(DISTINCT ?variant) AS ?n)
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  VALUES ?gene_uri { <http://ncbi.nlm.nih.gov/gene/«ID1»> <http://ncbi.nlm.nih.gov/gene/«ID2»> «…» }
  ?gbn med2rdf:gene ?gene_uri .
  ?cr sio:SIO_000628 ?gbn .
  ?variant cvo:classified_record ?cr ;
           cvo:record_status "current" ;
           cvo:record_type "classified" ;          # exclude "included" (no classified_record)
           med2rdf:disease ?dis .
  ?cr cvo:classifications ?cls .
  ?cls cvo:germline_classification ?germ .
  ?germ cvo:description ?significance .
  ?dis dct:references ?ref .
  ?ref dct:source "MedGen" ; dct:identifier ?id .
  BIND(STRAFTER(STR(?gene_uri), "gene/") AS ?gene_id)
}
GROUP BY ?gene_id ?significance ?id
ORDER BY ?gene_id DESC(?n)
LIMIT 400
```

Interpretation: macular-degeneration condition CUIs include `C0024437` (Macular Degeneration), `C0242383` (ARMD), `C0854723` (Stargardt). For complex-trait diseases, expect risk loci to show "Uncertain significance"/"Conflicting"/absent rather than "Pathogenic" — Mendelian genes (e.g. ABCA4) carry the pathogenic load. To attach human-readable condition names, join MedGen with the namespace fix: `BIND(IRI(REPLACE(STR(?cv_uri),"://ncbi.nlm","://www.ncbi.nlm")) AS ?mg)`.

---

## 7. Druggability axis — ChEMBL target check (Phase M)

```
search_chembl_target(query="«gene/protein name»", limit=5)
```

Confirms a human `SINGLE PROTEIN` target row (e.g. CETP→CHEMBL3572, ABCA1→CHEMBL2362986, HMGCR→CHEMBL402). For approved/late-stage status and indication, ChEMBL gives bioactivity; confirm approval + disease indication via an external source (ClinicalTrials.gov / drug labels) — out of TogoMCP scope.

---

## 8. Pathway membership — Reactome participants by UniProt accession (Phase P/M)

Which of a candidate accession set participate in pathways matching a name (isoform-aware).

```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?gene ?pathwayName
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  VALUES (?targetAcc ?gene) { ("«ACC»"^^xsd:string "«SYMBOL»") «…» }
  ?pathway a bp:Pathway ; bp:displayName ?pathwayName ;
           bp:organism/bp:name "Homo sapiens"^^xsd:string ;
           bp:pathwayComponent+ ?reaction .
  ?pathwayName bif:contains "'«lipoprotein»'" .
  ?reaction (bp:left|bp:right) ?participant .
  ?participant bp:component* ?protein .
  ?protein a bp:Protein ; bp:entityReference/bp:xref ?x .
  ?x a bp:UnificationXref ; bp:db ?db ; bp:id ?xid .
  VALUES ?db { "UniProt"^^xsd:string "UniProt Isoform"^^xsd:string }
  FILTER(?xid = ?targetAcc || STRSTARTS(STR(?xid), CONCAT(STR(?targetAcc), "-")))
}
ORDER BY ?pathwayName ?gene
```

To enumerate a whole pathway's membership instead, drop the `VALUES` accession anchor and select `?uniprotId` from the xref.

---

## 9. ID bridging (Phase S)

Preferred: pull GeneID directly in the UniProt query (template 2's `OPTIONAL`). Otherwise:

```
togoid_countId(...)        # check convertibility first
togoid_convertId(route="uniprot → ncbigene", ids=[...])
```

Intersection is computed on the normalized IDs. When SPARQL federation is needed but unavailable (SERVICE disabled on rdfportal), run sequential queries and bridge with `VALUES`.

# ClinVar Exploration Report

## Database Overview
- **Purpose**: Aggregates genomic variation and its relationship to human health
- **Scope**: 3.5M+ variant records with clinical interpretations, gene associations, and disease conditions
- **Key data types**: Genetic variations (SNVs, deletions, duplications, indels), clinical significance classifications, gene-disease associations, submitter evidence

## Schema Analysis (from MIE file)

### Main Properties Available
- **VariationArchiveType** (main variant entity):
  - `cvo:accession` - ClinVar accession (VCV number)
  - `cvo:variation_id` - Numeric ID
  - `rdfs:label` - HGVS notation (e.g., NM_007294.4(BRCA1):c.2244dup)
  - `cvo:variation_type` - Type (single nucleotide variant, Deletion, Duplication, etc.)
  - `cvo:species` - Species (typically "Homo sapiens")
  - `cvo:record_status` - Status (current, replaced, removed)
  - `cvo:date_created` - Creation date
  - `cvo:date_last_updated` - Last update date
  - `cvo:number_of_submitters` - Evidence strength indicator
  - `cvo:classified_record` - Link to clinical classifications
  - `med2rdf:disease` - Disease associations

- **Gene properties**:
  - `cvo:gene_id` - NCBI Gene ID
  - `cvo:symbol` - Gene symbol (e.g., BRCA1)
  - `cvo:full_name` - Full gene name
  - `cvo:hgnc_id` - HGNC identifier
  - `cvo:omim` - OMIM number
  - `cvo:cytogenetic_location` - Chromosomal location (e.g., 17q21.31)
  - `faldo:location` - Genomic coordinates

- **ClassifiedRecord properties**:
  - `cvo:classifications` - Clinical interpretation
  - `cvo:germline_classification/cvo:description` - Clinical significance (Pathogenic, Benign, Uncertain significance, etc.)
  - `sio:SIO_000628` - Associated gene

- **Disease/Trait properties** (ClinAsserTraitType):
  - `cvo:type` - Type (Disease, Phenotype, etc.)
  - `cvo:id` - Trait ID
  - `dct:references` - External database references (MedGen, OMIM, MeSH)

### Important Relationships
- **Variant → Clinical Classification**: Via blank node cvo:classified_record
- **Variant → Disease**: Via blank node med2rdf:disease
- **Classification → Gene**: Via sio:SIO_000628
- **Disease → External DBs**: Via dct:references to MedGen, OMIM, MeSH
- **Gene → HGNC/OMIM**: Direct properties (cvo:hgnc_id, cvo:omim)

### Query Patterns Observed
- **Full-text search**: Use bif:contains for gene symbols and variant descriptions
- **Status filtering**: Always filter by cvo:record_status "current" to exclude deprecated entries
- **Type aggregation**: GROUP BY cvo:variation_type for variant type distribution
- **Blank node traversal**: Use property paths (/) for clinical significance: cvo:classified_record/cvo:classifications/cvo:germline_classification/cvo:description
- **Date filtering**: Use xsd:date datatype for cvo:date_created and cvo:date_last_updated
- **Evidence strength**: Filter by cvo:number_of_submitters for well-studied variants

## Search Queries Performed

1. **Query**: BRCA1 variants with bif:contains → **Results**: 20 variants including frameshifts (c.2244dup p.Asp749fs), deletions (c.1997del), SNVs (c.453T>G), insertions, and indels across various exons

2. **Query**: Variant types count → **Results**: 3.2M single nucleotide variants (90%), 160K deletions (4.5%), 73K duplications (2%), 36K microsatellites, 24K copy number gains, 22K copy number losses, plus indels, inversions, haplotypes

3. **Query**: BRCA1 variants with clinical significance → **Results**: 20 variants with classifications including Pathogenic (c.2244dup, c.1997del), Benign (c.5579A>C), Uncertain significance (c.4262A>T), Likely benign (c.4716T>G), Likely pathogenic (c.4185+1G>C), and combined (Pathogenic/Likely pathogenic)

4. **Query**: Gene information for BRCA1, BRCA2, TP53 → **Results**: BRCA1 (gene 672, 17q21.31, HGNC:1100, OMIM:113705), BRCA2 (gene 675, 13q13.1, HGNC:1101, OMIM:600185), TP53 (gene 7157, 17p13.1, HGNC:11998, OMIM:191170)

5. **Query**: Well-studied recent variants (5+ submitters, updated 2024+) → **Results**: 10 BRCA1/BRCA2 variants with 51-78 submitters, all updated in May 2025, including frameshift variants c.68_69del (78 submitters), c.5266dup (78 submitters), showing highest clinical importance

## SPARQL Queries Tested

```sparql
# Query 1: Search variants by gene symbol
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT ?variant ?label ?type ?status
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:variation_type ?type ;
           cvo:record_status ?status .
  ?label bif:contains "'BRCA1'" .
}
LIMIT 20
# Results: Retrieved 20 BRCA1 variants with various types (Duplication, single nucleotide variant, Deletion, Insertion, Indel). All have "current" status.
```

```sparql
# Query 2: Count variants by type
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT ?variation_type (COUNT(?variant) as ?count)
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           cvo:variation_type ?variation_type ;
           cvo:record_status "current" .
}
GROUP BY ?variation_type
ORDER BY DESC(?count)
LIMIT 20
# Results: Single nucleotide variants dominate (3,236,823), followed by Deletions (160,620), Duplications (73,448), Microsatellites (36,328), copy number variations, and others. Shows distribution of variant types.
```

```sparql
# Query 3: Variants with clinical significance
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT ?variant ?label ?significance
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
  ?label bif:contains "'BRCA1'" .
}
LIMIT 20
# Results: Retrieved 20 BRCA1 variants with clinical significance: Pathogenic (c.2244dup, c.1997del, c.3815dup), Benign (c.5579A>C), Uncertain significance (c.4262A>T, c.353T>G), Likely benign (c.4716T>G), Likely pathogenic (c.4185+1G>C), and combined classifications.
```

```sparql
# Query 4: Gene details with cross-references
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT DISTINCT ?gene ?symbol ?full_name ?cyto_loc ?hgnc ?omim
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?gene a cvo:Gene ;
        cvo:symbol ?symbol ;
        cvo:full_name ?full_name ;
        cvo:cytogenetic_location ?cyto_loc .
  OPTIONAL { ?gene cvo:hgnc_id ?hgnc }
  OPTIONAL { ?gene cvo:omim ?omim }
  FILTER(?symbol = "BRCA1" || ?symbol = "BRCA2" || ?symbol = "TP53")
}
ORDER BY ?symbol
# Results: Retrieved complete gene information: BRCA1 (gene/672, 17q21.31, HGNC:1100, OMIM:113705), BRCA2 (gene/675, 13q13.1, HGNC:1101, OMIM:600185), TP53 (gene/7157, 17p13.1, HGNC:11998, OMIM:191170).
```

```sparql
# Query 5: Well-studied recent variants
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?variant ?label ?num_submitters ?last_updated ?type
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:number_of_submitters ?num_submitters ;
           cvo:date_last_updated ?last_updated ;
           cvo:variation_type ?type .
  FILTER(?num_submitters >= 5)
  FILTER(?last_updated >= "2024-01-01"^^xsd:date)
  ?label bif:contains "'BRCA*'" option (score ?sc) .
}
ORDER BY DESC(?num_submitters) DESC(?last_updated)
LIMIT 10
# Results: Found 10 highly studied BRCA1/BRCA2 variants with 51-78 submitters, all updated May 2025. Top variants: c.68_69del (78 submitters, Microsatellite), c.5266dup (78 submitters, Duplication), c.5946del (73 submitters in BRCA2).
```

## Interesting Findings

### Specific Entities That Could Form Good Questions
- **VCV000856461**: BRCA1 c.2244dup (p.Asp749fs), Pathogenic frameshift duplication
- **BRCA1 c.68_69del**: 78 submitters, most studied variant, Microsatellite type
- **BRCA1 c.5266dup**: 78 submitters, frameshift duplication
- **BRCA2 c.5946del**: 73 submitters, frameshift deletion
- **TP53 gene**: Gene 7157, 17p13.1, HGNC:11998, OMIM:191170
- **BRCA1 gene**: Gene 672, 17q21.31, HGNC:1100, OMIM:113705

### Unique Properties or Patterns
- **Clinical significance levels**: Pathogenic, Likely pathogenic, Uncertain significance, Likely benign, Benign, and combined interpretations (Pathogenic/Likely pathogenic)
- **Evidence strength**: Number of submitters ranges 1-78, indicating consensus level
- **Monthly updates**: Last updated dates show continuous curation (2024-2025)
- **HGVS notation**: Standardized variant nomenclature in rdfs:label (e.g., NM_007294.4(BRCA1):c.2244dup)
- **Variant type diversity**: 20 different variation types from SNVs to complex rearrangements
- **Record status**: "current" vs deprecated variants enable version control
- **Blank node architecture**: Clinical classifications and disease associations use blank nodes

### Connections to Other Databases
- **MedGen**: ~95% of disease annotations reference MedGen for standardized disease concepts
- **OMIM**: ~40% reference OMIM for Mendelian inheritance patterns
- **MeSH**: ~30% reference MeSH for clinical terminology
- **HGNC**: ~100% of human genes have HGNC identifiers for official gene symbols
- **NCBI Gene**: Direct gene ID cross-references (gene/672 for BRCA1)

### Specific, Verifiable Facts
- **Total variants**: 3,588,969 in database
- **Single nucleotide variants**: 3,236,823 (90% of all variants)
- **Deletions**: 160,620 variants
- **Most studied BRCA1 variant**: c.68_69del with 78 submitters
- **BRCA1 location**: Chromosome 17q21.31
- **TP53 gene ID**: 7157 (NCBI Gene)
- **Clinical significance coverage**: ~90% of variants have clinical interpretations
- **Disease association coverage**: ~75% of variants have disease annotations

## Question Opportunities by Category

### Precision
- "What is the ClinVar accession number for BRCA1 variant c.2244dup?" (Answer: VCV000856461)
- "What is the clinical significance of BRCA1 variant c.2244dup?" (Answer: Pathogenic)
- "What is the HGNC identifier for BRCA1?" (Answer: HGNC:1100)
- "What is the cytogenetic location of the TP53 gene?" (Answer: 17p13.1)
- "What is the OMIM number for BRCA2?" (Answer: 600185)

### Completeness
- "How many single nucleotide variants are in ClinVar?" (Answer: 3,236,823)
- "How many submitters have reported the BRCA1 c.68_69del variant?" (Answer: 78)
- "What are all the variation types in ClinVar?" (Answer: 20 types including SNV, Deletion, Duplication, Microsatellite, copy number variants, etc.)
- "List all BRCA1 variants with pathogenic classification" (Multiple variants)
- "How many total variants are currently in ClinVar?" (Answer: 3,588,969)

### Integration
- "What is the MedGen ID associated with BRCA1 variants?" (Via dct:references)
- "Convert ClinVar gene ID 672 to HGNC identifier" (Answer: HGNC:1100)
- "Find OMIM references for TP53 gene from ClinVar" (Answer: OMIM:191170)
- "What NCBI Gene ID corresponds to the TP53 gene in ClinVar?" (Answer: 7157)
- "Link ClinVar BRCA1 variants to their MeSH disease terms" (Via dct:references)

### Currency
- "When was the BRCA1 c.5266dup variant last updated?" (Answer: 2025-05-25)
- "What variants were updated in 2024 or later?" (Thousands of variants)
- "How many submitters have contributed data since 2024?" (Evidence strength metric)
- "What is the current record status of variant VCV000856461?" (Answer: current)

### Specificity
- "What is the protein consequence of BRCA1 c.2244dup?" (Answer: p.Asp749fs - frameshift)
- "What type of variation is the BRCA1 c.68_69del?" (Answer: Microsatellite)
- "How many submitters classify BRCA2 c.5946del?" (Answer: 73)
- "What is the full gene name for gene ID 672?" (Answer: BRCA1 DNA repair associated)
- "What variants have 'Uncertain significance' classification in BRCA1?" (Multiple variants)

### Structured Query
- "Find all pathogenic frameshift variants in BRCA1" (Filter by variation_type and clinical significance)
- "List variants updated in 2024 with 5+ submitters" (Date + evidence filtering)
- "Count variants by clinical significance category" (GROUP BY germline_classification)
- "Find all genes on chromosome 17q with OMIM entries" (Cytogenetic location + OMIM filtering)
- "Retrieve variants associated with MedGen disease concepts" (Disease cross-reference query)

## Notes

### Limitations or Challenges
- **Blank node complexity**: Clinical classifications and disease associations require traversing multiple blank nodes
- **Mixed datatypes**: Some dates stored as xsd:date, others as xsd:string
- **Incomplete annotations**: Not all variants have clinical significance or disease associations
- **Performance**: Complex blank node joins can be slow (3-10 seconds)
- **Aggregation limits**: Counting 3.5M+ variants without filters can timeout
- **External references**: Some disease references may not resolve to functional URIs

### Best Practices for Querying
1. **Always specify FROM clause**: Use FROM <http://rdfportal.org/dataset/clinvar>
2. **Filter by record_status**: Add cvo:record_status "current" to exclude deprecated variants
3. **Use bif:contains** for gene/variant searches with relevance ranking
4. **Property path for classifications**: Use cvo:classified_record/cvo:classifications/cvo:germline_classification/cvo:description
5. **OPTIONAL for blank nodes**: Use OPTIONAL when querying clinical significance to include variants without classifications
6. **Date filtering**: Use xsd:date datatype for cvo:date_created and cvo:date_last_updated
7. **Evidence strength**: Filter by cvo:number_of_submitters for well-studied variants
8. **Always use LIMIT**: Required for exploratory queries to prevent timeouts
9. **Type filtering**: Add cvo:variation_type filters early for better performance
10. **Cross-reference patterns**: Use dct:references for disease/OMIM/MeSH links

### Anti-patterns to Avoid
- ❌ Omitting FROM clause (incomplete or slow results)
- ❌ Using FILTER(CONTAINS()) instead of bif:contains (slow)
- ❌ Inner joins through blank nodes without OPTIONAL (filters out variants lacking annotations)
- ❌ Aggregating without filters (timeouts on 3.5M+ records)
- ❌ Assuming all variants have clinical significance (some lack classifications)
- ❌ Not filtering by record_status (includes deprecated/replaced variants)
- ❌ Missing LIMIT on exploratory queries (timeouts)
- ❌ Querying external URIs as subjects (they're references only)

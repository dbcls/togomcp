# RDF Portal Keyword Search Instructions

This directory contains concise keyword search instruction files for each RDF Portal database. These files guide LLM agents on the most efficient way to perform keyword searches.

## File Organization

Each `{dbname}.md` file provides:
1. **Specialized API** (if available) - Use these first
2. **SPARQL Fallback** - Template queries when API unavailable
3. **Key Properties** - Main searchable properties from MIE files
4. **Notes** - Database-specific considerations

## Databases by Search Method

### Specialized APIs (Priority)
- **uniprot** - `search_uniprot_entity()`
- **pubchem** - `get_pubchem_compound_id()`
- **pdb** - `search_pdb_entity()` (3 databases: pdb, cc, prd)
- **chembl** - `search_chembl_molecule()`, `search_chembl_target()`, `search_chembl_id_lookup()`
- **reactome** - `search_reactome_entity()`
- **rhea** - `search_rhea_entity()`
- **mesh** - `search_mesh_entity()`
- **pubmed** - `PubMed:search_articles()`
- **pubtator** - Uses PubMed API + SPARQL

### OLS4 (Ontology Lookup Service)
- **chebi** - `OLS4:searchClasses(ontologyId="chebi")`
- **go** - `OLS4:searchClasses(ontologyId="go")`
- **taxonomy** - `OLS4:searchClasses(ontologyId="taxonomy")`
- **mondo** - `OLS4:searchClasses(ontologyId="mondo")`
- **nando** - `OLS4:searchClasses(ontologyId="nando")`

### SPARQL Only
- **bacdive** - Bacterial strains
- **mediadive** - Culture media
- **ddbj** - Nucleotide sequences
- **glycosmos** - Glycan structures (100+ graphs)
- **clinvar** - Genetic variants
- **ensembl** - Genome annotations (100+ species)
- **ncbigene** - Gene database (57M+ entries)
- **medgen** - Medical genetics (233K+ concepts)

## Usage Workflow

1. **Check for Specialized API** - Always try API-based search first
2. **Read MIE File** - If using SPARQL: `get_MIE_file(dbname)`
3. **Construct SPARQL** - Use MIE properties for accurate queries
4. **Test & Iterate** - Adjust filters and limits as needed

## Common Patterns

### API Search
```python
search_uniprot_entity("insulin", limit=20)
```

### OLS4 Search
```python
OLS4:searchClasses(query="apoptosis", ontologyId="go", pageSize=20)
```

### SPARQL Search
```sparql
SELECT DISTINCT ?entity ?label
WHERE {
  ?entity rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), "keyword"))
}
LIMIT 50
```

## Critical Rules

1. **Read MIE files** before writing SPARQL queries
2. **Use specialized APIs** when available (faster, more reliable)
3. **Add LIMIT clauses** to all SPARQL queries
4. **Use FROM clauses** for databases with named graphs
5. **Test queries** on small limits first

## Database Endpoints

All databases use: `https://rdfportal.org/{endpoint}/sparql`
- `/sib` - UniProt, Rhea
- `/ebi` - ChEMBL, ChEBI, Reactome, Ensembl
- `/pdb` - PDB
- `/pubchem` - PubChem
- `/ddbj` - DDBJ
- `/ncbi` - ClinVar, PubMed, PubTator, NCBI Gene, MedGen
- `/primary` - MeSH, GO, Taxonomy, MONDO, NANDO, BacDive, MediaDive
- Custom - GlyCosmos (ts.glycosmos.org)

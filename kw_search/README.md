# TogoMCP Keyword Search Reference

Quick reference for keyword searches across TogoMCP databases.

---

## 🔴 CRITICAL: Always Read MIE File First

**Before writing any SPARQL query:**

```python
mie_content = get_MIE_file(dbname="dbname")
```

The MIE file contains:
- Exact property URIs and names
- RDF data structure examples
- Working SPARQL query examples
- Relationship patterns

**Without the MIE file, you will use incorrect property URIs!**

---

## Search Method Priority

1. **Dedicated search tools** - Use when available (fastest, simplest)
2. **OLS4** - For ontologies (ChEBI, GO, MONDO, NANDO, Taxonomy)
3. **SPARQL** - After reading MIE file for complex queries

---

## Quick Navigation

| Database | Method | Critical Requirements |
|----------|--------|----------------------|
| ChEBI | **OLS4** or SPARQL | Read MIE for SPARQL |
| GO | **OLS4** or SPARQL | Read MIE for SPARQL |
| MONDO | **OLS4** or SPARQL | Read MIE for SPARQL |
| NANDO | **OLS4** or SPARQL | Read MIE for SPARQL |
| Taxonomy | **OLS4** or SPARQL | Read MIE for SPARQL |
| NCBI Gene | SPARQL | **Read MIE + organism filter** |
| Ensembl | SPARQL | **Read MIE + organism filter** |
| ClinVar | SPARQL | **Read MIE + status filter** |
| MedGen | SPARQL | **Read MIE + MGREL pattern** |
| PubChem | SPARQL | **Read MIE + MW/class filter** |
| DDBJ | SPARQL | **Read MIE + entry filter** |
| GlyCosmos | SPARQL | **Read MIE + graph selection** |
| BacDive | SPARQL | Read MIE |
| MediaDive | SPARQL | Read MIE |
| PubTator | **PubMed tool** | Don't use SPARQL for search |

---

## Dedicated Search Tools

**Use these instead of SPARQL when available:**

| Database | Tool | Notes |
|----------|------|-------|
| ChEMBL | `search_chembl_molecule`, `search_chembl_target` | Preferred |
| MeSH | `search_mesh_entity` | Preferred |
| PDB | `search_pdb_entity` | Preferred |
| UniProt | `search_uniprot_entity` | Preferred |
| PubMed | `PubMed:search_articles` | Preferred |
| Reactome | `search_reactome_entity` | Preferred |
| Rhea | `search_rhea_entity` | Preferred |

---

## OLS4 Databases

**Use OLS4 first for these ontologies:**

- **ChEBI** - `ontology_id="chebi"`
- **GO** - `ontology_id="go"`
- **MONDO** - `ontology_id="mondo"`
- **NANDO** - `ontology_id="nando"`
- **Taxonomy** - `ontology_id="ncbitaxon"`

```python
# Basic search
OLS4:searchClasses(query="insulin", ontology_id="chebi", rows=20)

# Get hierarchy
OLS4:getAncestors(ontology_id="chebi", class_iri="...")
OLS4:getDescendants(ontology_id="chebi", class_iri="...")
```

---

## Universal SPARQL Rules

1. **Read MIE file first** - Essential!
2. **Always use `FROM <graph_uri>`** - Essential for performance
3. **Always use `DISTINCT`** - Avoids duplicates
4. **Always use `LIMIT`** - Prevents timeouts (20-100 typical)
5. **Use `bif:contains`** - 10-100x faster than `FILTER(CONTAINS())`
6. **Score variables: ?sc, ?sc1, ?sc2** - Never ?score alone
7. **Use `COALESCE` for scores** - Handles NULL values

---

## SPARQL Template (After Reading MIE!)

```sparql
PREFIX [prefix]: <[URI from MIE]>

SELECT DISTINCT ?entity ?label (COALESCE(MAX(?sc), 0) AS ?score)
FROM <[graph_uri from MIE]>
WHERE {
  ?entity a [EntityClass from MIE] ;
          [labelProperty from MIE] ?label .
  
  [CRITICAL_FILTER from database docs]
  
  ?label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?score)
LIMIT 50
```

---

## Database-Specific Requirements

### MUST Filter By:
- **NCBI Gene** - Organism (57M+ genes)
- **Ensembl** - Organism (mixed species)
- **ClinVar** - Status="current" (3.5M variants)
- **PubChem** - MW range or classification (119M+ compounds)
- **DDBJ** - Entry ID (for features)
- **GlyCosmos** - Graph URI (100+ graphs)

### Special Patterns:
- **MedGen** - Relationships via MGREL entities
- **PubTator** - Use PubMed tool, not SPARQL search

---

## Getting Started

1. **Choose database** from table above
2. **Check if dedicated tool exists** - Use if available
3. **For OLS4 databases** - Try OLS4 first
4. **For SPARQL:**
   - **Read MIE file first** (`get_MIE_file`)
   - Check database-specific guide for critical filters
   - Use SPARQL template with MIE property URIs

---

## Documentation Structure

```
kw_search/
├── README.md          # This file
├── chebi.md           # OLS4 + SPARQL
├── ncbigene.md        # SPARQL (organism filter required)
├── pubchem.md         # SPARQL (filter required, no keyword search)
├── clinvar.md         # SPARQL (status filter required)
├── medgen.md          # SPARQL (MGREL pattern)
├── ddbj.md            # SPARQL (entry filter for features)
├── ensembl.md         # SPARQL (organism filter required)
├── glycosmos.md       # SPARQL (graph selection required)
├── bacdive.md         # SPARQL
├── mediadive.md       # SPARQL
└── pubtator.md        # Use PubMed tool instead
```

---

## Key Reminders

✅ **Always read MIE file first for SPARQL**  
✅ **Use dedicated tools when available**  
✅ **Use OLS4 for ontologies when possible**  
✅ **Check critical filters before querying**  
✅ **Start with LIMIT 10-20 for exploration**

---

**Last Updated:** December 2025  
**Coverage:** 12 databases with keyword search support

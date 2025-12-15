# Summary of Changes

## Recent Updates

### December 2025 - Dedicated Search Tools for Reactome and Rhea

**Changes:**
- Removed `reactome.md` - Reactome now has dedicated `search_reactome_entity` tool
- Removed `rhea.md` - Rhea now has dedicated `search_rhea_entity` tool
- Updated README.md to reflect these changes
- Updated database count: 15 databases with SPARQL templates (down from 17)

**Why:**
Reactome and Rhea now have specialized search tools that provide:
- Simpler API (no SPARQL required)
- Faster performance
- Pre-built filtering (by species, type, etc.)
- Better structured results

**Migration:**
Users should now use:
- `search_reactome_entity(query, species, types, rows)` instead of SPARQL for Reactome
- `search_rhea_entity(query, limit)` instead of SPARQL for Rhea

SPARQL is still available via TogoMCP-Test for advanced queries if needed.

---

## Previous Updates

### OLS4 Integration

**Overview:**
The keyword search documentation has been updated to prefer OLS4 when available, with SPARQL as a fallback for advanced queries.

## Files Updated

### 1. README.md
- Added OLS4 priority section at the top
- Marked 5 databases with ✨ indicator for OLS4 availability
- Updated Quick Navigation table with search method column
- Added OLS4 to dedicated search tools list
- Reorganized to emphasize OLS4-first approach

### 2. Database-Specific Files (5 files updated)

#### chebi.md
- **OLS4 ID:** `chebi`
- **SPARQL Graph:** `<http://rdf.ebi.ac.uk/dataset/chebi>`
- Now shows OLS4 examples first, SPARQL second
- Added "When to Use" section comparing both methods

#### go.md
- **OLS4 ID:** `go`
- **SPARQL Graph:** `<http://rdfportal.org/ontology/go>`
- Highlights that OLS4 automatically filters GO terms
- Notes SPARQL is useful for namespace-specific queries

#### mondo.md
- **OLS4 ID:** `mondo`
- **SPARQL Graph:** `<http://rdfportal.org/ontology/mondo>`
- Recommends OLS4 for basic searches
- Shows SPARQL for cross-reference queries

#### nando.md
- **OLS4 ID:** `nando`
- **SPARQL Graph:** `<http://nanbyodata.jp/ontology/nando>`
- OLS4 handles multilingual search automatically
- SPARQL shown for language-specific filtering

#### taxonomy.md
- **OLS4 ID:** `ncbitaxon` ⚠️ (Different from SPARQL!)
- **SPARQL Graph:** `<http://rdfportal.org/ontology/taxonomy>`
- Important note about naming difference
- Added taxon ID extraction examples

## Key Changes

### Structure of Updated Files
Each updated file now follows this structure:
1. ✨ Recommended: Use OLS4 banner
2. Quick Facts (updated with OLS4 performance)
3. Method 1: OLS4 Search (Recommended)
   - Basic search examples
   - Exact match
   - Get term details
   - Navigate hierarchy
   - Multiple search examples
4. Method 2: SPARQL (Advanced Queries)
   - Standard template
   - Advanced query examples
5. When to Use SPARQL vs OLS4
6. Critical Rules (separated by method)
7. Common Use Cases
8. Integration Examples
9. Quick Reference Card (with both methods)
10. Performance Comparison table

### OLS4 Advantages Highlighted
- Simpler API (no SPARQL knowledge required)
- Faster response times (<500ms vs ~1s)
- Better error handling
- Pre-built search capabilities
- Automatic filtering (e.g., GO terms, ChEBI compounds)

### SPARQL Use Cases Preserved
- Cross-reference queries
- Complex filtering (e.g., by rank, namespace)
- Multi-property searches with scoring
- Bulk operations
- Custom joins with other databases

## Mapping Table

| Database | OLS4 Ontology ID | TogoMCP Graph Name | Notes |
|----------|------------------|-------------------|-------|
| ChEBI | `chebi` | `chebi` | Same name |
| GO | `go` | `go` | Same name |
| MONDO | `mondo` | `mondo` | Same name |
| NANDO | `nando` | `nando` | Same name |
| Taxonomy | `ncbitaxon` | `taxonomy` | ⚠️ **Different names!** |

## Files NOT Changed (OLS4 Integration)

The following files were not changed during OLS4 integration as they don't have OLS4 equivalents:
- bacdive.md
- clinvar.md
- ddbj.md
- ensembl.md
- glycosmos.md
- medgen.md
- mediadive.md
- ncbigene.md
- pubchem.md
- pubtator.md

These continue to use SPARQL as their primary search method.

**Note:** reactome.md and rhea.md were later removed when dedicated search tools became available.

## Usage Recommendations

### For End Users
1. **Start with OLS4** for databases that support it (ChEBI, GO, MONDO, NANDO, Taxonomy)
2. **Use SPARQL** only when you need:
   - Advanced filtering
   - Cross-database queries
   - Bulk operations
   - Features not available in OLS4

### For Developers
1. OLS4 tools are simpler to use and require less SPARQL knowledge
2. SPARQL remains available for complex queries
3. Both methods are fully documented with examples
4. Performance characteristics are clearly indicated

## Testing Suggestions

To verify the updates work correctly:

1. **Test OLS4 searches:**
   ```python
   OLS4:searchClasses(query="glucose", ontology_id="chebi")
   OLS4:searchClasses(query="kinase", ontology_id="go")
   OLS4:searchClasses(query="diabetes", ontology_id="mondo")
   OLS4:searchClasses(query="Parkinson", ontology_id="nando")
   OLS4:searchClasses(query="Homo sapiens", ontology_id="ncbitaxon")
   ```

2. **Test hierarchy navigation:**
   ```python
   OLS4:getAncestors(ontology_id="go", class_iri="...")
   OLS4:getDescendants(ontology_id="mondo", class_iri="...")
   ```

3. **Verify SPARQL still works** for advanced queries in each database

4. **Check Taxonomy naming:**
   - Confirm OLS4 uses `ncbitaxon`
   - Confirm SPARQL uses `taxonomy` graph

## Version
- **Updated:** December 2025
- **Status:** Production-ready
- **Coverage:** 5 databases with OLS4 integration, 10 SPARQL-only databases, 2 with dedicated search tools

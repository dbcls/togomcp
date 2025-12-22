# Update Summary: NCBI E-utilities Integration

## Date
December 22, 2025

## Overview
Updated keyword search documentation for NCBI-based databases to use the `ncbi_esearch()` tool for efficient keyword searching.

## Files Updated

### 1. ncbigene.md
**Changes:**
- Added `ncbi_esearch()` as the primary search method
- Database parameter: "gene" or "ncbigene"
- Kept SPARQL as fallback for complex queries
- Added examples with organism and disease field tags

**Key Addition:**
```python
ncbi_esearch(database="gene", query="BRCA1 AND human[organism]", max_results=10)
```

### 2. clinvar.md
**Changes:**
- Added `ncbi_esearch()` as the primary search method
- Database parameter: "clinvar"
- Kept SPARQL as fallback for filtering by clinical_significance
- Added examples for gene and pathogenic variant searches

**Key Addition:**
```python
ncbi_esearch(database="clinvar", query="BRCA1 AND pathogenic", max_results=15)
```

### 3. medgen.md
**Changes:**
- Added `ncbi_esearch()` as the primary search method
- Database parameter: "medgen"
- Kept SPARQL as fallback for hierarchical navigation
- Added examples for disease and clinical concept searches

**Key Addition:**
```python
ncbi_esearch(database="medgen", query="breast cancer", max_results=20)
```

### 4. taxonomy.md
**Changes:**
- Added `ncbi_esearch()` as Option 1 (Recommended)
- Kept OLS4 as Option 2 (Alternative)
- Database parameter: "taxonomy"
- Clarified when to use each approach

**Key Addition:**
```python
ncbi_esearch(database="taxonomy", query="Escherichia coli", max_results=20)
```

### 5. pubmed.md
**Changes:**
- Reorganized to show both `PubMed:search_articles()` and `ncbi_esearch()`
- Recommended `PubMed:search_articles()` for most cases (richer features)
- Added `ncbi_esearch()` as alternative for consistency
- Emphasized PubMed database scope limitations

**Key Addition:**
```python
ncbi_esearch(database="pubmed", query="CRISPR gene editing", max_results=20)
```

### 6. pubtator.md
**Changes:**
- Updated to reference both PubMed APIs
- Added `ncbi_esearch()` as Option B for Step 1
- Clarified two-step workflow: PubMed search → PubTator annotation query

## Benefits of These Updates

1. **Consistency**: All NCBI databases now have a consistent search approach
2. **Efficiency**: `ncbi_esearch()` is faster than SPARQL for simple keyword searches
3. **Feature-rich**: Supports Entrez query syntax, field tags, and boolean operators
4. **Flexibility**: SPARQL remains available as fallback for complex filtering

## NCBI Databases Supported

The `ncbi_esearch()` tool supports these databases:
- **gene** / **ncbigene** - Gene information
- **taxonomy** - Organism taxonomy
- **clinvar** - Genetic variants
- **medgen** - Medical genetics concepts
- **pubmed** - Biomedical literature
- **pccompound** - PubChem compounds (not updated as it has specialized API)
- **pcsubstance** - PubChem substances (not updated as it has specialized API)
- **pcassay** - PubChem bioassays (not updated as it has specialized API)

## Query Syntax Supported

All updated files support:
- Simple keywords: "BRCA1", "breast cancer"
- Field tags: "[organism]", "[gene]", "[condition]"
- Boolean operators: AND, OR, NOT
- Combined queries: "BRCA1 AND human[organism]"

## Recommendations

- Use `ncbi_esearch()` for initial keyword searches
- Use SPARQL when you need:
  - Complex filtering by specific properties
  - Aggregations and counts
  - Precise field targeting
  - Custom relationships traversal

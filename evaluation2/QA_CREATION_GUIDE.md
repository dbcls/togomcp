# TogoMCP Question Creation Guide

Create 50 evaluation questions testing TogoMCP's ability to answer biological questions using RDF databases.

---

## FILE LOCATIONS

```
Input:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv
Track:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml
Output: /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml
```

**Tools:**
- **User files:** `Filesystem:read_text_file()` / `Filesystem:write_file()`
- **RDF databases:** `togomcp_local:get_MIE_file()` / `run_sparql()` / `search_*_entity()` / `ncbi_esearch()`

---

## REQUIREMENTS

### Database Coverage (All 23 Required)
- **Tier 1 (≥3 each):** UniProt, ChEBI, ChEMBL, Rhea, PubChem, MeSH, GO, Reactome, Taxonomy, Ensembl, NCBI_Gene
- **Tier 2-4 (≥1 each):** PDB, ClinVar, MedGen, PubMed, AMRPortal, BacDive, MediaDive, DDBJ, NANDO, PubTator, Glycosmos, MONDO

### Balance Quotas (CRITICAL)
- **UniProt: ≤35 questions (70% max)** - Target 30-40%
- **GO: ≤25 questions (50% max)** - Target 24-30%
- **Skip databases >45%** for next 3+ questions
- **Prioritize databases <5%**
- **60%+ questions must NOT use UniProt**

### Question Types
- Factoid: 10 | Yes/No: 10 | List: 10 | Summary: 10 | Choice: 20
- 60%+ must integrate 2+ databases
- All must score ≥7/9 verification

---

## WORKFLOW

### 1. Check Balance (FIRST - MANDATORY)
```yaml
Read coverage_tracker.yaml
Calculate current percentages
Identify: overused (>35%), underused (<5%), never used
Decision: Which database to FEATURE as PRIMARY?
```

### 2. Read MIE File & Check kw_search_tools

**⭐ CRITICAL: Always check MIE file's kw_search_tools field! ⭐**

```yaml
togomcp_local:get_MIE_file(dbname="database_name")

Look for:
  kw_search_tools:
    - ncbi_esearch     # Use for ClinVar, MedGen, PubMed, NCBI_Gene
    - search_*_entity  # Use for ChEMBL, PDB, UniProt, etc.

Rule: Use kw_search_tools FIRST for keyword discovery (5-10 examples)
      Then use SPARQL for structured property queries
```

**Why This Matters:**
- MIE explicitly tells you which API to use for discovery
- Wrong: Jump to SPARQL for keyword searches → Empty results, wasted time
- Right: Use kw_search_tools for discovery → Get IDs → SPARQL for structure

**Example (ClinVar):**
```yaml
✅ CORRECT:
  1. Read MIE → See "kw_search_tools: [ncbi_esearch]"
  2. ncbi_esearch(database="clinvar", query="hypertrophic cardiomyopathy pathogenic")
  3. Get variant IDs → Use in SPARQL if needed

❌ WRONG:
  1. Skip MIE's kw_search_tools field
  2. Write SPARQL keyword queries → Empty results
  3. Retry multiple times → Still empty
  4. Finally use ncbi_esearch (should have been step 1!)
```

### 3. Select Keyword
```yaml
Read keywords.tsv
Match to database's domain strength (not vice versa)
Prefer keywords enabling underutilized database
```

### 4. Formulate Question
Make question NEED the featured database, not just mention it.
- **ClinVar PRIMARY:** "Which gene has most pathogenic variants for disease X?"
- **BacDive PRIMARY:** "Which strains grow optimally at pH >9?"
- **PubTator PRIMARY:** "Which genes co-occur with 'autophagy' in literature?"

### 5. Discovery & Verification

**Stage A: Use kw_search_tools for discovery (5-10 IDs)**
```yaml
# Check MIE file first!
If MIE has kw_search_tools → Use those
If ncbi_esearch available → Use for keyword searches
If search_*_entity available → Use for entity discovery
```

**Stage B: Examine structure via SPARQL**
```sparql
SELECT ?property ?value
WHERE { <entity_uri> ?property ?value }
LIMIT 50
```

**Stage C: Query with structured properties (NOT text filters)**
```sparql
✅ GOOD: ?protein up:classifiedWith keywords:460
❌ BAD:  FILTER(CONTAINS(?name, "magnesium"))
```

**Stage D: PubMed test (15 min)**
Document why literature doesn't answer the question

### 6. Document & Update

**Create:** `question_XXX.yaml` with all required fields
**Update:** `coverage_tracker.yaml` with new counts and percentages

---

## DIVERSITY PATTERNS

**Avoid Protein-Centric Trap:**
- ❌ Default to UniProt + GO + Taxonomy for everything
- ✅ Match domain to database strength

**Domain → Primary Databases:**
- **Clinical genetics:** ClinVar, MedGen, MONDO (avoid UniProt)
- **Microbiology:** BacDive, MediaDive, AMRPortal (avoid UniProt)
- **Genomics:** DDBJ, Ensembl, NCBI_Gene (avoid UniProt)
- **Literature mining:** PubMed, PubTator, MeSH (avoid UniProt)
- **Drug discovery:** ChEMBL, PubChem (UniProt optional)
- **Glycobiology:** Glycosmos, PDB (avoid UniProt)

---

## ANTI-PATTERNS

### ❌ Wrong Tool Usage
- Using TogoMCP to read local files → Use `Filesystem:read_text_file()`
- Using Filesystem for RDF queries → Use `togomcp_local:run_sparql()`

### ❌ Ignoring MIE's kw_search_tools
- Jumping to SPARQL without checking MIE file
- Not using ncbi_esearch when MIE specifies it
- Wasting time on failed SPARQL keyword queries

### ❌ Skipping Balance Check
- Defaulting to UniProt/GO without checking percentages
- Creating questions for overused databases (>45%)
- Ignoring underutilized databases (<5%)

### ❌ Peripheral Database Usage
- Using Tier 2-4 databases as mere cross-references
- Wrong: "UniProt proteins with PDB structures" (UniProt primary)
- Right: "PDB structures with resolution <1.5Å" (PDB primary)

### ❌ Text Filtering in SPARQL
- `FILTER(CONTAINS(?name, "pattern"))` → Use structured properties
- `REGEX(?label, "pattern")` → Use ontology classifications

---

## QUALITY CHECKLIST

### Before Starting
- [ ] Read `coverage_tracker.yaml` - which databases need priority?
- [ ] Calculate current percentages - avoid overused, prioritize underused
- [ ] Identify featured database - will it be PRIMARY?

### Discovery Phase
- [ ] Read MIE file - what are the kw_search_tools?
- [ ] Use kw_search_tools FIRST for keyword discovery
- [ ] Get 5-10 example IDs before writing SPARQL
- [ ] Examine data structure with property queries

### Query Phase
- [ ] Use structured properties (not text filters)
- [ ] Follow MIE example query patterns
- [ ] Test queries return expected results

### Verification
- [ ] Question requires RDF databases (not PubMed alone)
- [ ] PubMed test shows non-answerability (15 min)
- [ ] Objectively verifiable, bounded scope
- [ ] Score ≥7/9

### Documentation
- [ ] Create `question_XXX.yaml` with all fields
- [ ] Update `coverage_tracker.yaml` with counts/percentages
- [ ] SPARQL uses `|` syntax for multiline
- [ ] RDF triples in TTL with comments

---

## SUCCESS CRITERIA

1. **Featured database is PRIMARY** (showcases unique capability)
2. **Requires RDF** (not answerable from PubMed + training)
3. **Balanced distribution** (no database >50%)
4. **Used kw_search_tools** from MIE when available
5. **Structured queries** (no text filtering)
6. **Objectively verifiable** (bounded scope)
7. **Score ≥7/9**
8. **All 23 databases covered** by end

---

## KEY LESSON

**Always check MIE's `kw_search_tools` field and use those tools FIRST for discovery!**

When MIE specifies `kw_search_tools: [ncbi_esearch]` → Use it for keyword searches BEFORE attempting SPARQL. This saves time and avoids empty results.

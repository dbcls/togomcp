# Revised 10-Step Process Summary

## Preliminary: Check Current Status
- Review existing questions, database coverage, verification scores, SPARQL complexity

## Step 0: Strategic Keyword Selection & Database Planning (45-60 min)
- Read keywords file, select ONE keyword at random
- Identify 2-4 relevant databases based on keyword category
- Read MIE files for each target database (MANDATORY)
- Decide tentative question type (prefer Tier 1-2)

## Step 1: Exploration Phase (60-90 min)
- Execute exploratory SPARQL queries
- Find 1-5 verifiable examples
- Assess verifiability before formulating question
- DON'T formulate question yet - just explore data

## Step 2: Question Formulation Phase (20-30 min)
- Select appropriate question template (Templates 1-8)
- Formulate question using template structure
- Self-check: fits template? verifiable? not PubMed-answerable? proper scope?

## Step 3: Systematic Verification Phase (90-120 min)
- Execute complete SPARQL query sequence
- Verify answer completeness definitively
- Cross-validate with alternative formulations
- Document all queries and results

## Step 4: Mandatory PubMed Test (15-30 min) ⚠️ NEW MANDATORY GATE
- **Use PubMed MCP tools**: `search_articles`, `get_article_metadata`, `get_full_text_article`
- Attempt to answer using ONLY PubMed searches (15 min max)
- Document what you find programmatically
- **Evaluation**:
  - If can answer completely → ❌ REJECT, return to Step 2
  - If can partially answer → ⚠️ BORDERLINE, consider strengthening
  - If cannot answer at all → ✅ PASS, proceed
- **Critical**: This tests if question truly requires RDF, not just makes it easier

## Step 5: RDF Triple Extraction (45-60 min)
- Extract triples from all SPARQL results
- Include linking triples (cross-database connections)
- Include quantitative triples (measurements, counts)
- Optional: minimal text snippets if needed (<20%)

## Step 6: Validation Scoring (15-20 min) ⚠️ MANDATORY GATE
- **Score three dimensions**:
  - Verifiability (0-3 points): Can you prove answer is complete?
  - RDF Necessity (0-3 points): Impossible without graph queries?
  - Scope (0-3 points): Appropriately bounded?
- **Requirements to PASS**:
  - Total score ≥7/9
  - NO zeros in any dimension
  - Passed PubMed test
- **If FAIL** → Return to Step 2, reformulate
- **If PASS** → Proceed to documentation

## Step 7: Exact Answer (5-10 min)
- Provide answer in appropriate format:
  - Factoid: "Entity (DB:ID)"
  - Yes/No: "yes" or "no"
  - List: ["Item1", "Item2", ...]
  - Count: numerical value

## Step 8: Ideal Answer (30-45 min)
- Write one-paragraph synthesis from RDF triples
- Include quantitative data, cross-database integration
- Natural prose, no meta-references to databases/queries
- State facts directly, not "According to database X..."

## Step 9: Documentation in YAML (30-40 min)
- Save complete YAML with all required fields
- Include verification score and PubMed test results
- Document all SPARQL queries with results
- Include RDF triples with provenance
- Update coverage tracker
- File naming: `question_{number}.yaml`

## Step 10: Final Validation (20-30 min)
- Validate YAML syntax and completeness
- Check reproducibility (queries → answer)
- Quality check (stand-alone, no DB names, well-written)
- Fix any issues and re-validate

---

## Total Time: 3.5-5.5 hours per question

## Critical Gates (Must Pass Both)

### Gate 1: PubMed Test (Step 4)
⛔ **Must FAIL to proceed** - If you can answer from PubMed, question is not RDF-necessary

### Gate 2: Verification Scoring (Step 6)
⛔ **Must score ≥7/9 with NO zeros** - Ensures verifiability, RDF-necessity, proper scope

## Key Changes from Original

1. ✅ **Verification-first philosophy** - Build questions around verified patterns
2. ✅ **Two mandatory gates** - PubMed test + Verification scoring
3. ✅ **Two-phase workflow** - Exploration → Verification (not linear)
4. ✅ **PubMed MCP tools** - Use programmatic search, not manual
5. ✅ **Question templates** - 8 proven templates for guaranteed success
6. ✅ **Anti-patterns** - Clear examples of what to avoid

## Remember

**"Better a simple, verified question than a complex, unverifiable one."**

# NANDO (Nanbyo Data) Exploration Report

**Date**: 2026-01-31
**Session**: 1

## Executive Summary

NANDO (Nanbyo Data) is a comprehensive Japanese intractable (rare) disease ontology containing 2,777 disease classes. It provides a specialized resource for Japanese healthcare policy, research coordination, and patient information systems.

**Key Capabilities Requiring Deep Knowledge**:
- Multilingual label handling (English, Japanese kanji, Japanese hiragana)
- Hierarchical disease taxonomy navigation
- Cross-database integration with MONDO, MeSH, and GO via primary endpoint
- Notification number-based querying for designated intractable diseases
- External resource linking (KEGG, government documents)

**Major Integration Opportunities**:
- NANDO ↔ MONDO: Direct skos:closeMatch mappings (84% coverage)
- NANDO ↔ MeSH: Keyword-based matching for literature connections
- NANDO ↔ GO: Keyword-based matching for biological process associations
- Three-way queries (NANDO + MeSH + GO) for comprehensive rare disease research

**Most Valuable Patterns Discovered**:
1. bif:contains for efficient keyword searches
2. Language tag filtering for multilingual content
3. GRAPH clauses for cross-database queries on primary endpoint
4. Pre-filtering strategies for cross-database joins

**Recommended Question Types**:
- Japanese rare disease identification and mapping
- Cross-database integration with international disease ontologies
- Hierarchical disease category queries
- Designated intractable disease enumeration

## Database Overview

- **Purpose**: Official Japanese government ontology for intractable (rare) diseases
- **Scope**: 2,777 disease classes covering designated intractable diseases eligible for government support
- **Key Data Types**: 
  - Disease classes with multilingual labels (English, Japanese kanji, Japanese hiragana)
  - Notification numbers for designated diseases
  - Cross-references to MONDO, KEGG, government documents
  - Hierarchical taxonomy with categories and specific diseases
- **Dataset Size**: 2,777 diseases (small, but specialized)
- **Access Methods**: 
  - SPARQL via primary endpoint
  - OLS4 searchClasses (limited - NANDO not directly indexed)

## Structure Analysis

### Performance Strategies

**Strategy 1: Use bif:contains for Keyword Searches**
- Why needed: REGEX is slow and doesn't support relevance ranking
- When to apply: Any text-based disease search
- Performance impact: 10-100x faster than REGEX
- Example:
  ```sparql
  ?label bif:contains "'Parkinson*'" option (score ?sc)
  ```

**Strategy 2: Pre-filtering in GRAPH Clauses**
- Why needed: Cross-database joins create Cartesian products
- When to apply: Any cross-database query (NANDO + MeSH/GO/MONDO)
- Performance impact: 99%+ reduction in join size
- Example: Filter within GRAPH clause before joining

**Strategy 3: Language Tag Filtering**
- Why needed: Multiple language variants per disease create duplicates
- When to apply: Any query retrieving labels
- Performance impact: Prevents duplicate rows
- Example:
  ```sparql
  FILTER(LANG(?label) = "en")
  FILTER(LANG(?ja_label) = "ja" && !REGEX(STR(?ja_label), "^[ぁ-ん]+$"))
  ```

**Strategy 4: STRSTARTS for Cross-Reference Filtering**
- Why needed: Efficient filtering of external URIs
- When to apply: MONDO mapping queries, external link queries
- Performance impact: Faster than CONTAINS for URI patterns
- Example:
  ```sparql
  FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))
  ```

**Strategy 5: LIMIT Clause**
- Why needed: Prevents excessive result generation
- When to apply: All exploratory queries
- Performance impact: Bounds result set size

### Common Pitfalls

**Pitfall 1: Not Filtering Language Tags**
- Cause: rdfs:label returns all language variants
- Symptoms: Duplicate rows, mixed languages
- Solution: Use LANG() filters for specific languages
- Before: Returns English, Japanese kanji, Japanese hiragana mixed
- After: Clean, separated language results

**Pitfall 2: Using REGEX Instead of bif:contains**
- Cause: Natural inclination to use standard REGEX
- Symptoms: Slow queries, no relevance ranking
- Solution: Use bif:contains with wildcard syntax
- Before: `FILTER(REGEX(?label, "Parkinson", "i"))` - slow
- After: `?label bif:contains "'Parkinson*'"` - fast with scoring

**Pitfall 3: Cross-Database Query Without GRAPH Clauses**
- Cause: Forgetting to isolate database contexts
- Symptoms: Cross-contamination, wrong results
- Solution: Always use explicit GRAPH clauses
- Example fix: Add `GRAPH <http://nanbyodata.jp/ontology/nando> { ... }`

**Pitfall 4: Not Distinguishing Kanji from Hiragana Labels**
- Cause: Both use @ja language tag
- Symptoms: Cannot separate kanji and hiragana
- Solution: Use regex pattern `^[ぁ-ん]+$` to detect hiragana
- Example:
  ```sparql
  FILTER(REGEX(STR(?ja_hira), "^[ぁ-ん]+$"))
  ```

**Pitfall 5: Cross-Database Timeout**
- Cause: Missing pre-filtering before joins
- Symptoms: Query timeout after 60 seconds
- Solution: Apply filters within source GRAPH clause
- Key insight: Reduce NANDO diseases from 2,777 before joining

### Data Organization

**Hierarchical Structure**:
- Root: NANDO:0000001 (Intractable disease)
- Level 1: NANDO:1000001 (Designated intractable disease umbrella)
- Level 2: Disease categories (NANDO:11xxxxx) - 15 categories
  - Neuromuscular disease (84 children) - largest category
  - Metabolic disease (45 children)
  - Chromosome abnormality (42 children)
  - Immune system disease (27 children)
  - And more...
- Level 3: Specific diseases (NANDO:12xxxxx)
- Level 4: Disease subtypes (NANDO:22xxxxx)

**Label Structure**:
- rdfs:label @en: English label
- rdfs:label @ja: Japanese kanji label
- rdfs:label @ja-hira: Japanese hiragana (pattern: ^[ぁ-ん]+$)
- skos:prefLabel: Preferred Japanese label
- skos:altLabel: Alternative names/synonyms

**Cross-Reference Structure**:
- skos:closeMatch: MONDO mappings (84% coverage, 2,341 diseases)
- rdfs:seeAlso: KEGG Disease, government documents
- dct:source: Official PDF documentation

### Cross-Database Integration Points

**Integration 1: NANDO → MONDO (Direct Mapping)**
- Connection relationship: skos:closeMatch
- Join point: URI matching
- Information from NANDO: Disease name, notification number, Japanese labels
- Information from MONDO: International disease definition, broader classification
- Pre-filtering needed: None (direct URI match)
- Knowledge required: MONDO graph URI, MONDO entity types
- Tested: Yes, works efficiently

**Integration 2: NANDO ↔ MeSH (Keyword-Based)**
- Connection relationship: Keyword overlap in labels
- Join point: Text matching on disease names
- Information from NANDO: Japanese rare disease classification
- Information from MeSH: Medical subject headings for literature indexing
- Pre-filtering needed: bif:contains keyword filter in both GRAPH clauses
- Knowledge required: MeSH graph URI, meshv:TopicalDescriptor type
- Tested: Yes, requires pre-filtering for performance

**Integration 3: NANDO ↔ GO (Keyword-Based)**
- Connection relationship: Keyword overlap between disease and biological processes
- Join point: Text matching on labels
- Information from NANDO: Disease name and category
- Information from GO: Biological process annotations
- Pre-filtering needed: CONTAINS filter in both GRAPH clauses
- Knowledge required: GO graph URI, hasOBONamespace property, STR() type restriction
- Tested: Yes, works with simplified CONTAINS filters

**Integration 4: Three-Way (NANDO + MeSH + GO)**
- Path: Disease → Literature terms → Biological processes
- Use case: Comprehensive rare disease research
- Pre-filtering: CRITICAL - must filter all three GRAPH clauses
- Performance: 3-5 seconds with proper filtering
- Knowledge required: All three database schemas

## Complex Query Patterns Tested

### Pattern 1: Cross-Database NANDO → MONDO Integration

**Purpose**: Map Japanese rare diseases to international disease ontology

**Category**: Integration, Cross-Database

**Naive Approach**:
Query NANDO diseases with skos:closeMatch without explicit GRAPH clauses

**What Happened**:
- Works but may cross-contaminate with other ontologies
- Unclear which database provides which data

**Correct Approach**:
```sparql
WHERE {
  GRAPH <http://nanbyodata.jp/ontology/nando> {
    ?nando a owl:Class ;
      rdfs:label ?nandoLabel ;
      skos:closeMatch ?mondo .
    FILTER(LANG(?nandoLabel) = "en")
    FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))
  }
  
  GRAPH <http://rdfportal.org/ontology/mondo> {
    ?mondo rdfs:label ?mondoLabel .
    OPTIONAL { ?mondo <http://purl.obolibrary.org/obo/IAO_0000115> ?mondoDef }
  }
}
```

**What Knowledge Made This Work**:
- NANDO graph URI: http://nanbyodata.jp/ontology/nando
- MONDO graph URI: http://rdfportal.org/ontology/mondo
- skos:closeMatch property for cross-references
- MONDO definition property: IAO_0000115
- Performance: <2 seconds

**Results Obtained**:
- Huntington's disease mapped successfully
- MONDO definitions retrieved
- 2,341 diseases have MONDO mappings

**Natural Language Question Opportunities**:
1. "What is the international MONDO equivalent for the Japanese rare disease Huntington's disease?" - Category: Integration
2. "How many Japanese designated intractable diseases are mapped to international disease ontologies?" - Category: Completeness
3. "What is the medical definition of Parkinson's disease according to MONDO?" - Category: Precision

---

### Pattern 2: Keyword-Based MeSH Integration

**Purpose**: Connect Japanese rare diseases to biomedical literature terms

**Category**: Integration, Cross-Database

**Naive Approach**:
```sparql
# BAD: Filter after join
WHERE {
  GRAPH <http://nanbyodata.jp/ontology/nando> { ?d1 ?p1 ?o1 }
  GRAPH <http://id.nlm.nih.gov/mesh> { ?d2 ?p2 ?o2 }
  FILTER(CONTAINS(?label1, "parkinson") && CONTAINS(?label2, "parkinson"))
}
```

**What Happened**:
- Timeout: Cross-product of 2,777 NANDO × 869K MeSH = 2.4 billion combinations
- Query never completes

**Correct Approach**:
```sparql
WHERE {
  GRAPH <http://nanbyodata.jp/ontology/nando> {
    ?nandoDisease a owl:Class ;
      rdfs:label ?nandoLabel .
    FILTER(LANG(?nandoLabel) = "en")
    ?nandoLabel bif:contains "'parkinson'" option (score ?sc1)
  }
  
  GRAPH <http://id.nlm.nih.gov/mesh> {
    ?meshTerm a meshv:TopicalDescriptor ;
      rdfs:label ?meshLabel .
    ?meshLabel bif:contains "'parkinson'" option (score ?sc2)
  }
}
ORDER BY DESC(?sc1)
LIMIT 10
```

**What Knowledge Made This Work**:
- Strategy 2: Pre-filtering within GRAPH clauses
- Strategy 4: bif:contains with relevance scoring
- MeSH entity type: meshv:TopicalDescriptor
- MeSH graph URI: http://id.nlm.nih.gov/mesh
- Performance: ~1-2 seconds

**Results Obtained**:
- Parkinson's disease (NANDO) matched to multiple MeSH terms
- Found: D010300 (Parkinson Disease), D010301 (Postencephalitic), etc.

**Natural Language Question Opportunities**:
1. "What MeSH terms are related to the Japanese rare disease 'Parkinson's disease'?" - Category: Integration
2. "Find literature indexing terms that correspond to Japanese neuromuscular diseases" - Category: Structured Query

---

### Pattern 3: Three-Way Cross-Database Query

**Purpose**: Connect Japanese diseases to both literature terms and biological processes

**Category**: Integration, Structured Query (Complex)

**Naive Approach**:
Using complex bif:contains in all three GRAPH clauses

**What Happened**:
- Three-way queries with complex filters can timeout or error
- Need simplified filters for stability

**Correct Approach**:
```sparql
WHERE {
  GRAPH <http://nanbyodata.jp/ontology/nando> {
    ?nandoDisease a owl:Class ;
      rdfs:label ?nandoLabel .
    FILTER(LANG(?nandoLabel) = "en")
    FILTER(CONTAINS(LCASE(?nandoLabel), "immune"))
  }
  
  GRAPH <http://id.nlm.nih.gov/mesh> {
    ?meshTerm a meshv:TopicalDescriptor ;
      rdfs:label ?meshLabel .
    FILTER(CONTAINS(LCASE(?meshLabel), "immune"))
  }
  
  GRAPH <http://rdfportal.org/ontology/go> {
    ?goTerm a owl:Class ;
      rdfs:label ?goLabel ;
      oboinowl:hasOBONamespace ?goNamespace .
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
    FILTER(CONTAINS(LCASE(?goLabel), "immune"))
    FILTER(STR(?goNamespace) = "biological_process")
  }
}
LIMIT 10
```

**What Knowledge Made This Work**:
- Use simplified CONTAINS instead of bif:contains for three-way stability
- STR() type restriction required for GO namespace comparison
- GO graph URI: http://rdfportal.org/ontology/go
- GO namespace property: oboinowl:hasOBONamespace
- Performance: 3-5 seconds

**Results Obtained**:
- Autoimmune hemolytic anemia linked to immune-related MeSH and GO terms
- Multiple GO biological processes identified

**Natural Language Question Opportunities**:
1. "What biological processes are associated with Japanese immune system diseases?" - Category: Integration
2. "Connect Japanese autoimmune diseases to both MeSH literature terms and GO molecular processes" - Category: Structured Query

---

### Pattern 4: Hierarchical Disease Category Query

**Purpose**: Navigate the NANDO disease taxonomy

**Category**: Structured Query, Completeness

**Naive Approach**:
Using unlimited rdfs:subClassOf+ traversal

**What Happened**:
- May timeout on deep hierarchies without LIMIT
- Returns large result sets

**Correct Approach**:
```sparql
SELECT ?category ?category_label (COUNT(DISTINCT ?disease) as ?disease_count)
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?category a owl:Class ;
            rdfs:subClassOf nando:1000001 ;
            rdfs:label ?category_label .
  ?disease rdfs:subClassOf ?category ;
           a owl:Class .
  FILTER(LANG(?category_label) = "en")
}
GROUP BY ?category ?category_label
ORDER BY DESC(?disease_count)
```

**What Knowledge Made This Work**:
- Understanding NANDO hierarchy: 1000001 is parent of categories
- Disease categories use rdfs:subClassOf
- Language filtering prevents duplicates

**Results Obtained**:
- 15 disease categories identified
- Neuromuscular disease: 84 children (largest)
- Metabolic disease: 45 children
- Chromosome abnormality: 42 children

**Natural Language Question Opportunities**:
1. "How many diseases are in each category of Japanese intractable diseases?" - Category: Completeness
2. "What are the main categories of Japanese rare diseases?" - Category: Specificity
3. "Which disease category has the most designated intractable diseases?" - Category: Structured Query

---

### Pattern 5: Designated Intractable Disease Enumeration

**Purpose**: Find diseases with official government notification numbers

**Category**: Specificity, Completeness

**Correct Approach**:
```sparql
SELECT ?disease ?en_label ?notif_num ?source_doc
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           rdfs:label ?en_label ;
           nando:hasNotificationNumber ?notif_num .
  OPTIONAL { ?disease dct:source ?source_doc }
  FILTER(LANG(?en_label) = "en")
}
ORDER BY xsd:integer(?notif_num)
```

**What Knowledge Made This Work**:
- nando:hasNotificationNumber property for designated diseases
- dct:source for official documentation
- xsd:integer cast for proper numeric sorting

**Results Obtained**:
- 2,454 designated diseases with notification numbers
- Spinal and bulbar muscular atrophy has notification number 1
- Government documentation links available

**Natural Language Question Opportunities**:
1. "What is the notification number for Parkinson's disease in the Japanese designated intractable disease system?" - Category: Precision
2. "How many diseases are officially designated as intractable diseases in Japan?" - Category: Completeness
3. "Which Japanese rare diseases have official government documentation?" - Category: Specificity

---

### Pattern 6: Multilingual Label Handling

**Purpose**: Retrieve and distinguish Japanese labels

**Category**: Specificity, Precision

**Correct Approach**:
```sparql
SELECT ?disease ?en_label ?ja_kanji ?ja_hira
WHERE {
  ?disease a owl:Class .
  OPTIONAL {
    ?disease rdfs:label ?en_label .
    FILTER(LANG(?en_label) = "en")
  }
  OPTIONAL {
    ?disease rdfs:label ?ja_kanji .
    FILTER(LANG(?ja_kanji) = "ja" && !REGEX(STR(?ja_kanji), "^[ぁ-ん]+$"))
  }
  OPTIONAL {
    ?disease rdfs:label ?ja_hira .
    FILTER(REGEX(STR(?ja_hira), "^[ぁ-ん]+$"))
  }
}
```

**What Knowledge Made This Work**:
- Understanding that both kanji and hiragana use @ja tag
- Regex pattern `^[ぁ-ん]+$` detects hiragana-only strings
- OPTIONAL blocks for missing labels

**Results Obtained**:
- Clean separation of English, kanji, and hiragana labels
- Parkinson's disease: "Parkinson's disease" (en), "パーキンソン病" (kanji)

**Natural Language Question Opportunities**:
1. "What is the Japanese name for Huntington's disease?" - Category: Precision
2. "Find Japanese rare diseases with both kanji and hiragana readings" - Category: Specificity

---

### Pattern 7: External Resource Linking (KEGG)

**Purpose**: Find diseases with molecular pathway information

**Category**: Integration, Specificity

**Correct Approach**:
```sparql
SELECT ?disease ?en_label ?kegg_link ?mondo
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           rdfs:label ?en_label ;
           rdfs:seeAlso ?kegg_link .
  OPTIONAL {
    ?disease skos:closeMatch ?mondo .
    FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))
  }
  FILTER(LANG(?en_label) = "en")
  FILTER(CONTAINS(STR(?kegg_link), "kegg.jp"))
}
```

**What Knowledge Made This Work**:
- rdfs:seeAlso for external links
- KEGG URL pattern filtering
- Combined with MONDO for comprehensive integration

**Results Obtained**:
- 519 diseases with KEGG links
- Includes chromosome syndromes, metabolic diseases, neurological conditions
- Links to KEGG Disease database entries

**Natural Language Question Opportunities**:
1. "Which Japanese rare diseases have molecular pathway information in KEGG?" - Category: Integration
2. "Find neuromuscular diseases with both KEGG and MONDO cross-references" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. **Search: "Parkinson"**
   - Found: NANDO:1200010 - Parkinson's disease
   - Usage: Neuromuscular disease queries, cross-database integration

2. **Search: "Huntington"**
   - Found: NANDO:1200012 - Huntington's disease
   - Usage: Disease definition queries, MONDO integration

3. **Search: "muscular"**
   - Found: Multiple muscular dystrophies (Duchenne, Becker, Limb-girdle)
   - Usage: Category enumeration, hierarchical queries

4. **Search: "ALS"**
   - Found: NANDO:1200002 - Amyotrophic lateral sclerosis
   - Usage: Neuromuscular disease queries

5. **Search: Disease categories**
   - Found: 15 categories (Neuromuscular, Metabolic, Immune, etc.)
   - Usage: Category-based completeness questions

6. **Search: Notification number 1**
   - Found: Multiple diseases including SBMA
   - Usage: Designated disease enumeration

7. **Search: KEGG-linked diseases**
   - Found: 519 diseases with KEGG cross-references
   - Usage: Integration questions with molecular databases

8. **Search: Deprecated diseases**
   - Found: 9 deprecated classes
   - Usage: Data quality questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What is the MONDO disease ontology equivalent for the Japanese rare disease Kennedy disease (SBMA)?"
   - Databases involved: NANDO, MONDO
   - Knowledge Required: skos:closeMatch property, MONDO graph URI, STRSTARTS filtering
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

2. "Which Japanese designated intractable diseases are related to Parkinson's disease according to MeSH?"
   - Databases involved: NANDO, MeSH
   - Knowledge Required: bif:contains syntax, MeSH entity types, pre-filtering strategy
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

3. "What biological processes (from Gene Ontology) are associated with Japanese immune system diseases?"
   - Databases involved: NANDO, GO
   - Knowledge Required: GO graph URI, hasOBONamespace property, STR() type restriction
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

4. "Connect Japanese autoimmune diseases to both literature indexing terms and molecular biological processes"
   - Databases involved: NANDO, MeSH, GO
   - Knowledge Required: Three-way query optimization, simplified CONTAINS filters
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

5. "What is the international disease definition (from MONDO) for Japanese Huntington's disease?"
   - Databases involved: NANDO, MONDO
   - Knowledge Required: MONDO definition property (IAO_0000115), GRAPH clauses
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

**Hierarchical/Structural Questions**:

6. "How many diseases are in each category of Japanese designated intractable diseases?"
   - Database: NANDO
   - Knowledge Required: Hierarchical structure, category identifiers, aggregation
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

7. "What diseases fall under the neuromuscular disease category in the Japanese rare disease classification?"
   - Database: NANDO
   - Knowledge Required: Category URI (NANDO:1100001), rdfs:subClassOf
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

8. "Which disease category has the highest number of designated intractable diseases in Japan?"
   - Database: NANDO
   - Knowledge Required: Aggregation with COUNT, GROUP BY, ORDER BY
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

**Designated Disease Questions**:

9. "What is the notification number for ALS (amyotrophic lateral sclerosis) in the Japanese designated intractable disease system?"
   - Database: NANDO
   - Knowledge Required: nando:hasNotificationNumber property
   - Category: Precision
   - Difficulty: Easy
   - Pattern Reference: Pattern 5

10. "How many diseases are officially designated as intractable diseases with notification numbers in Japan?"
    - Database: NANDO
    - Knowledge Required: nando:hasNotificationNumber existence check
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Pattern 5

11. "Which Japanese rare diseases have official government documentation available?"
    - Database: NANDO
    - Knowledge Required: dct:source property, rdfs:seeAlso for mhlw.go.jp links
    - Category: Specificity
    - Difficulty: Medium
    - Pattern Reference: Pattern 5

**Multilingual Questions**:

12. "What is the Japanese name (in kanji) for Huntington's disease?"
    - Database: NANDO
    - Knowledge Required: Language tag filtering, kanji vs hiragana distinction
    - Category: Precision
    - Difficulty: Medium
    - Pattern Reference: Pattern 6

**External Resource Questions**:

13. "Which Japanese rare diseases have molecular pathway information available in KEGG?"
    - Database: NANDO
    - Knowledge Required: rdfs:seeAlso property, KEGG URL pattern
    - Category: Integration
    - Difficulty: Medium
    - Pattern Reference: Pattern 7

14. "Find neuromuscular diseases with cross-references to both KEGG and MONDO"
    - Database: NANDO
    - Knowledge Required: Multiple OPTIONAL blocks, hierarchical filtering
    - Category: Structured Query
    - Difficulty: Hard
    - Pattern Reference: Pattern 7

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the NANDO identifier for Parkinson's disease?"
   - Method: Keyword search or SPARQL
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

2. "Is there a Japanese rare disease entry for Duchenne muscular dystrophy?"
   - Method: Keyword search
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "What English synonyms exist for Kennedy disease in NANDO?"
   - Method: Simple SPARQL with skos:altLabel
   - Knowledge Required: Minimal
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

1. "What is the MONDO ID corresponding to NANDO Parkinson's disease?"
   - Method: Simple skos:closeMatch lookup
   - Knowledge Required: Minimal
   - Category: Integration
   - Difficulty: Easy

**Counting Questions**:

1. "How many total disease classes are in NANDO?"
   - Method: Simple COUNT query
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source (NANDO →)**:
- → MONDO: Direct skos:closeMatch mappings (84% coverage)
- → MeSH: Keyword-based label matching
- → GO: Keyword-based label matching
- → KEGG: rdfs:seeAlso external links (embedded URLs)

**This Database as Target (→ NANDO)**:
- Limited: NANDO is primarily a source database
- Some MONDO → NANDO reverse lookups possible

**Complex Multi-Database Paths**:
- NANDO → MONDO → [other disease databases]: International disease harmonization
- NANDO → MeSH → PubMed: Literature connection for Japanese rare diseases
- NANDO + MeSH + GO: Comprehensive rare disease research triangle
- NANDO → KEGG → Pathway databases: Molecular mechanism exploration

**Shared Endpoint Advantage**:
NANDO shares the "primary" endpoint with:
- MeSH: Medical subject headings
- GO: Gene Ontology
- MONDO: Disease ontology
- Taxonomy: Organism classification
- BacDive: Bacterial diversity
- MediaDive: Culture media

This enables efficient cross-database queries without federation overhead.

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Multilingual Label Handling**: Understanding the three label types (en, ja-kanji, ja-hira) and how to distinguish them is essential for proper NANDO queries.

2. **Cross-Database Pre-filtering**: For NANDO + MeSH/GO queries, pre-filtering within GRAPH clauses before joins is critical for performance.

3. **MONDO Integration**: The 84% coverage of skos:closeMatch to MONDO enables rich international disease harmonization.

4. **Hierarchical Structure**: Understanding the NANDO ID patterns (11xxxxx for categories, 12xxxxx for diseases) helps navigate the taxonomy.

5. **Notification Numbers**: The nando:hasNotificationNumber property is key to identifying officially designated intractable diseases.

### Common Pitfalls Discovered

1. **Three-way query complexity**: Using bif:contains in all three GRAPH clauses can cause errors - simplified CONTAINS works better.

2. **Language tag confusion**: Both kanji and hiragana use @ja tag - regex pattern needed to distinguish.

3. **Missing STRSTARTS filter**: MONDO cross-reference queries need STRSTARTS to filter out non-MONDO URIs.

4. **Deprecated diseases**: 9 diseases are deprecated - may need filtering for current data.

### Recommendations for Question Design

1. **Focus on integration**: NANDO's main value is connecting Japanese rare disease classification to international resources.

2. **Test multilingual handling**: Questions involving Japanese labels test important database features.

3. **Include hierarchical queries**: The disease taxonomy enables meaningful category-based questions.

4. **Leverage designation status**: Notification numbers provide unique filtering capability.

### Performance Notes

- Single-database NANDO queries: <1 second
- Two-database cross-queries: 1-3 seconds
- Three-database queries: 3-5 seconds
- bif:contains: 10-100x faster than REGEX
- Pre-filtering: 99%+ reduction in join size

---

## Notes and Observations

1. **NANDO vs MONDO**: While MONDO is the international standard, NANDO provides Japan-specific information including notification numbers and government documentation links.

2. **Limited OLS4 coverage**: NANDO is not directly searchable through OLS4 - must use SPARQL for direct access.

3. **Data quality**: High coverage of core fields (100% identifiers, 88% notification numbers, 84% MONDO mappings).

4. **External resource stability**: KEGG links are most stable; government document URLs may change.

5. **Cross-database potential**: The primary endpoint co-location with MeSH, GO, MONDO enables powerful integration queries without federation.

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database integration (NANDO-MONDO, NANDO-MeSH), hierarchical category queries, designated disease enumeration
- Avoid: Questions requiring OLS4 search (NANDO not indexed), very deep hierarchy traversals
- Focus areas: Japanese rare disease research, international disease harmonization, government designation system

**Further Exploration Needed** (if any):
- NANDO → PubMed integration via MeSH (complex path)
- NANDO → Gene integration via MONDO → gene associations
- Time-based queries (if NANDO has versioning)

---

**Session Complete - Ready for Next Database**

```
Database: nando
Status: ✅ COMPLETE
Report: /evaluation/exploration/nando_exploration.md
Patterns Tested: 7 complex patterns + multiple simple queries
Questions Identified: ~25 complex + ~8 simple
Integration Points: 6 (MONDO direct, MeSH keyword, GO keyword, three-way, KEGG external, government docs)
```

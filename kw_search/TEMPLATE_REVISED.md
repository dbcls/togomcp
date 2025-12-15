# [DATABASE NAME] - Keyword Search Guide

**📋 Quick Info:** [Purpose] | [Entity Count] | [Critical Requirements]

---

## 🔴 CRITICAL: Read MIE File First

**ALWAYS get the MIE file before writing any SPARQL queries:**

```python
mie_content = get_MIE_file(dbname="[dbname]")
```

The MIE file contains:
- ShEx schema with exact property names and URIs
- RDF examples showing actual data structure
- SPARQL examples for common queries
- Property paths and relationships

**Without the MIE file, you may use incorrect:**
- Property URIs (predicates)
- Entity class names
- Graph names
- Relationship patterns

---

## Quick Start Template

```sparql
PREFIX [common_prefix]: <[URI]>

SELECT DISTINCT ?entity ?label (COALESCE(MAX(?sc), 0) AS ?score)
FROM <[graph_uri]>
WHERE {
  ?entity a [EntityClass] ;
          [labelProperty] ?label .
  
  [CRITICAL_FILTER]
  
  ?label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?score)
LIMIT 50
```

---

## Essential Properties

| Property | Usage | Example |
|----------|-------|---------|
| [prop1] | [usage] | [example] |
| [prop2] | [usage] | [example] |

---

## Critical Rules

1. **[Most important rule]**
2. **[Second most important rule]**
3. Always use `FROM <graph_uri>`
4. Always use `DISTINCT`
5. Always use `LIMIT`

---

## Common Queries

### [Use Case 1]
```sparql
[Minimal query example]
```

### [Use Case 2]
```sparql
[Minimal query example]
```

---

## Anti-Patterns

❌ **[Common mistake]**
```sparql
# WRONG
[bad example]

# CORRECT
[good example]
```

---

## Additional Resources

- Website: [URL]
- Endpoint: [URL]

# Human Enzyme Distribution by EC Class

**Date:** 2026-05-01  
---

## Databases & Tools Used

### RDF Databases
| Database | Role |
|---|---|
| **UniProt** (Swiss-Prot) | Source of human enzyme annotations via `up:enzyme` predicate |

### MCP Tools
| Tool | Purpose |
|---|---|
| `TogoMCP:get_MIE_file` | Retrieved the UniProt MIE (Metadata Interoperability Exchange) schema file to understand predicates, IRI patterns, and query best practices |
| `TogoMCP:run_sparql` | Executed SPARQL query against the UniProt RDF endpoint (`https://rdfportal.org/sib/sparql`) |

### SPARQL Endpoint
- **SIB endpoint:** `https://rdfportal.org/sib/sparql`

---

## Query

```sparql
PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?ecClass (COUNT(DISTINCT ?protein) AS ?count)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:enzyme ?ecIRI .
  BIND(STRBEFORE(STRAFTER(STR(?ecIRI), "http://purl.uniprot.org/enzyme/"), ".") AS ?ecClass)
}
GROUP BY ?ecClass
ORDER BY ?ecClass
```

**Filters applied:**
- `up:reviewed 1` — Swiss-Prot (manually curated) entries only, excludes ~244M TrEMBL entries
- `up:organism <http://purl.uniprot.org/taxonomy/9606>` — Homo sapiens only
- EC class extracted by stripping the IRI prefix and taking the first digit before `.`

---

## Results

| EC Class | Name | # Proteins | Share |
|---|---|---:|---:|
| EC 1 | Oxidoreductases | 546 | 11.7% |
| EC 2 | Transferases | 1,832 | 39.4% |
| EC 3 | Hydrolases | 1,732 | 37.2% |
| EC 4 | Lyases | 155 | 3.3% |
| EC 5 | Isomerases | 160 | 3.4% |
| EC 6 | Ligases | 124 | 2.7% |
| EC 7 | Translocases | 103 | 2.2% |
| **Total** | | **4,652** | **100%** |

> **Note:** A single protein may carry more than one EC number (e.g. bifunctional enzymes), so counts reflect unique protein–EC-class associations, not unique proteins.

---

## Key Observations

- **Transferases (EC 2, 39.4%)** are the dominant class, driven by the large diversity of human kinases, methyltransferases, glycosyltransferases, and acetyltransferases — central to signalling, epigenetics, and metabolism.
- **Hydrolases (EC 3, 37.2%)** come in a close second, reflecting the breadth of proteases, phosphatases, lipases, and nucleases in the human proteome.
- Together, EC 2 and EC 3 account for **~77%** of all human enzyme annotations.
- **Oxidoreductases (EC 1, 11.7%)** form a substantial third tier, covering cytochrome P450s, dehydrogenases, and peroxidases.
- **Lyases (EC 4), Isomerases (EC 5), Ligases (EC 6), and Translocases (EC 7)** together make up only ~12%, reflecting their more specialised metabolic roles.
- The strong EC 2/EC 3 dominance is a well-known feature of eukaryotic (especially metazoan) proteomes, where reversible phosphorylation and proteolytic processing underpin virtually every signalling and regulatory pathway.
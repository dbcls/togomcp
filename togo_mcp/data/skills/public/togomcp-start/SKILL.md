---
name: togomcp-start
description: >
  Start here before using any TogoMCP tool: questions about genes, proteins,
  compounds, reactions, pathways, diseases, variants or literature answered from
  RDF Portal and other life-science databases (UniProt, ChEMBL, PubChem, Reactome,
  Rhea, MeSH, PDB, NCBI, TogoID, TogoVar, and more) via SPARQL or search tools.
  Says which tool to call first and where TogoMCP's multi-step workflows are.
metadata:
  version: "1.0"
  role: entry
  catalog: "Entry point: call TogoMCP_Usage_Guide before the first TogoMCP query"
---
# TogoMCP: start here

1. Before the first TogoMCP query in this conversation, call the
   `TogoMCP_Usage_Guide` tool and follow it. It holds the database catalog and the
   query rules that keep SPARQL results correct. They change with each database
   release, so they are not copied here.
2. TogoMCP's multi-step analysis workflows are the other skills served by this
   same server. Load one only when the question matches it. If your host does not
   list them, call `get_workflow()`.
3. Single-fact lookups need no workflow.

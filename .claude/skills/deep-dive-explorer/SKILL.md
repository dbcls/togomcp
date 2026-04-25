---
name: deep-dive-explorer
description: >
  Systematically explore a biological or chemical entity, mechanism, or finding across TogoMCP RDF databases.
  Use this skill whenever you have a starting point — a protein name, compound, pathway, disease, or a partial
  finding — and want to map what's known, fill gaps, and surface the next level of understanding.
  Trigger when the user says things like: "tell me more about X", "what's the mechanism behind Y?",
  "go deeper on this finding", "what other databases have info on this?", "I found X is associated with Y,
  what else should I look into?", "深掘りして", "もっと詳しく調べて", or when a previous TogoMCP exploration
  surfaces a promising lead that deserves follow-up. Works without a research paper — any biological entity,
  protein, compound, pathway, or incomplete finding can be the starting seed.
---

# Deep-Dive Explorer

The full workflow lives in the TogoMCP server as a tool. Call it now and follow the guide it returns:

→ Call `TogoMCP:Deep_Dive_Explorer_Guide()` — returns the four-phase exploration workflow (seed definition,
  anchor-ID acquisition, targeted SPARQL, synthesis with Next Steps).

Then proceed by:
1. Calling `TogoMCP:TogoMCP_Usage_Guide()` if not already loaded this session.
2. Following the phases returned by `Deep_Dive_Explorer_Guide()` exactly.

The canonical source is [togo_mcp/data/resources/deep_dive_explorer.md](../../../togo_mcp/data/resources/deep_dive_explorer.md);
this skill is a thin trigger so the same content is available to any MCP client (Claude Desktop, custom
clients) without needing access to repo-local skills.

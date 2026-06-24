---
name: intro-page-updater
description: Update the public TogoMCP intro/landing page at `togo_mcp/data/docs/togomcp-intro.html` whenever the catalog of databases, the catalog of MCP tools, or any other surface fact shown on the page changes. Trigger when the user adds/removes/renames a database (MIE file, `endpoints.csv` row), adds/removes/renames a tool (any `@mcp.tool` decorator in `togo_mcp/*.py`), updates the preprint citation, changes setup instructions for a host (Claude/ChatGPT/Gemini), revises the recommended companion MCP servers, or otherwise edits something the landing page advertises. Also trigger when the user says "update the intro page", "regenerate the landing page", "refresh togomcp-intro.html", "the intro is out of date", or similar — even if they don't name the file. Spec for what the page should contain is `togo_mcp/data/docs/make_intro.md`; the rendered page is `togo_mcp/data/docs/togomcp-intro.html`.
---

# TogoMCP Intro Page Updater

The intro page (`togo_mcp/data/docs/togomcp-intro.html`) is the public landing page at <https://togomcp.rdfportal.org/>. It is a single self-contained HTML file with inline CSS and JS — there is no build step. Every section advertises some surface fact about the project; if that fact changes elsewhere in the repo, this page must be edited to match.

## The hard rule

**The page is hand-edited HTML, not generated.** Do not regenerate the entire file from scratch. Edit only the section(s) affected by the change. The file is large (~1300 lines), so use `Edit` with surrounding context as the anchor.

## Spec vs. rendered page

| File                                          | Role                                                  |
|-----------------------------------------------|-------------------------------------------------------|
| `togo_mcp/data/docs/make_intro.md`            | Spec — what the page should contain, style requirements |
| `togo_mcp/data/docs/togomcp-intro.html`       | Rendered page — the artifact users see                  |

If a structural change crosses what the spec says (e.g. a new top-level section, a new menu tab), update **both** files. For routine catalog updates (a new database card, a renamed tool), only the HTML changes.

## Sources of truth — what is canonical for each section

When a section is out of date, do not re-derive it from memory. Read the canonical source and reflect it in the HTML.

| Section                  | Canonical source                                                                       |
|--------------------------|----------------------------------------------------------------------------------------|
| **Available Databases**  | `togo_mcp/data/mie/*.yaml` (one card per file, **excluding `supercon.yaml`**) + `togo_mcp/data/resources/endpoints.csv` |
| **Available Tools**      | `@mcp.tool(...)` decorators in `togo_mcp/*.py` (root server, plus `togoid.py` and `ncbi_tools.py` mounted as `togoid_*` and `ncbi_*`) |
| **Preprint**             | `README.md` (top-level) — citation block                                                |
| **Setup Guide**          | `make_intro.md` (Claude/ChatGPT/Gemini blocks) + the URLs for each platform's MCP docs |
| **Other MCP Servers**    | `make_intro.md` recommended companion servers                                          |
| **Related Resources**    | `make_intro.md` (RDF Portal, TogoID, DBCLS) — verify URLs are alive                    |
| **Source code**          | `https://github.com/dbcls/togomcp` (DBCLS canonical repo)                              |
| **Hero endpoint URL**    | The production MCP endpoint: `https://togomcp.rdfportal.org/mcp`                       |

## Triggering edits — common scenarios

### Scenario 1: New database added

A new database appears when there is a new `togo_mcp/data/mie/<db>.yaml` AND a new row in `togo_mcp/data/resources/endpoints.csv`. (One without the other is incomplete onboarding — flag it.)

To add the card:

1. Read the new MIE file's `schema_info.title` and `schema_info.description`.
2. Condense the description to **one or two sentences** (~150–250 chars), preserving concrete numbers (record counts, version, what's covered). Match the tone of existing cards — declarative, no marketing language.
3. Insert a `<div class="db-card">…</div>` block in the `#databases` section. **Pick the position by domain affinity** with neighboring cards (proteins block, chemistry block, gene/genomics block, disease/clinical block, vocabulary/ontology block, taxonomy block, microbiology block, sequence block, etc.) — do not just append. The visual grouping matters because the grid auto-flows by source order.
4. **Skip `supercon.yaml`** — it is intentionally excluded per the spec.

### Scenario 2: Database removed or renamed

1. Delete the corresponding `<div class="db-card">` block.
2. If renamed, also update any other section that mentioned it (Summary card list, Examples that name it, etc.).

### Scenario 3: New tool added

Find the `@mcp.tool` decorator in `togo_mcp/*.py`. Tools are registered on three servers:

- Root `mcp` (in `rdf_portal.py`, `api_tools.py`) — exposed as `<tool_name>`
- `togoid_mcp` (in `togoid.py`) — exposed as `togoid_<tool_name>`
- `ncbi_mcp` (in `ncbi_tools.py`) — exposed as `ncbi_<tool_name>`

Place the new `<div class="tool-item">…</div>` in the appropriate `<div class="tool-group">` based on category:

| Group header                    | Belongs in this group                                                |
|---------------------------------|----------------------------------------------------------------------|
| 📋 Database & Information       | List/get tools for databases, endpoints, graphs, MIE                 |
| 🔍 Keyword Search Tools         | `search_*` tools that hit a database's keyword-search API           |
| ⚡ SPARQL Query                 | `run_sparql` and any new direct-query tools                          |
| 🔄 ID Conversion (TogoID)       | `togoid_*` tools                                                     |
| 🧬 NCBI E-utilities             | `ncbi_*` tools                                                       |
| 🧪 PubChem-specific             | PubChem-specific helpers                                             |

The `tool-item-desc` should be **one short sentence** — the *user-facing purpose*, not the function signature. Look at existing entries for tone.

### Scenario 4: Tool removed or renamed

Delete the `<div class="tool-item">` block. Also check **Examples** (the three `example-card` blocks) — they list tools used in `<span class="tool-tag">` elements. If a removed/renamed tool appears there, update or replace it.

### Scenario 5: Preprint, setup instructions, or external URLs change

For URLs in the Setup Guide, footer, or Related Resources: when changing, verify the URL is alive (e.g. with `WebFetch` or by checking the documented support article still exists). Dead links on the landing page are worse than missing entries.

## Style guide — conventions baked into the existing page

These are not strict rules but the patterns to match unless there's a reason to deviate:

- **Database card descriptions**: 1–2 sentences, lead with what it is, follow with a concrete number or scope. No hyperbole. Examples to imitate: the existing UniProt, ChEMBL, Ensembl, PDB cards.
- **Tool item descriptions**: ≤1 sentence, ≤120 chars, imperative ("Search …", "Get …", "Convert …"). No "This tool…" preamble.
- **Database card name**: matches the canonical brand (UniProt, ChEMBL, BacDive — not all-caps, not lowercase). For ambiguous cases, use the form in the MIE `schema_info.title`. For very-uncommon abbreviations, expand in parentheses on first use (e.g. `PDB (Protein Data Bank)`, `OMA (Orthologous MAtrix)` — but the existing page uses the bare abbreviation for OMA; match the local pattern).
- **Tool name**: the actual tool name as registered on the MCP server (with the mount prefix where applicable: `togoid_convertId`, `ncbi_esearch`).
- **Numbers**: when citing scale (e.g. "444M+ proteins"), prefer the figure from the MIE `data_statistics` over outside knowledge. If `data_statistics` is empty, omit the figure rather than invent one.
- **No emojis in card/item content** — the section headers already use them.

## Pre-finalisation checklist

- [ ] Every `togo_mcp/data/mie/<db>.yaml` (except `supercon.yaml`) has a corresponding `<div class="db-card">` and vice versa
- [ ] Every `@mcp.tool` in `togo_mcp/*.py` has a corresponding `<div class="tool-item">` and vice versa (with correct mount prefix)
- [ ] Tool tags in the three Examples reference real, current tool names
- [ ] Hero endpoint URL is `https://togomcp.rdfportal.org/mcp`
- [ ] Preprint citation matches the top-level `README.md`
- [ ] No reference to a deprecated tool (e.g. `get_shex`, `get_sparql_example` — both removed) anywhere on the page
- [ ] Sticky nav `<ul>` items still match the actual `<section id="…">` anchors

## Common pitfalls

- ❌ Regenerating the file end-to-end from `make_intro.md`. The spec is a guide, not a generator — running it through an LLM produces a different page each time and erases hand-tuning. Edit in place.
- ❌ Adding a card by appending to the end of the grid. The grouping is intentional.
- ❌ Including `supercon.yaml` in the database list — it is excluded by spec.
- ❌ Inventing record counts or coverage figures. If you don't have a verified number, drop the figure.
- ❌ Forgetting the mount prefix on `togoid_*` / `ncbi_*` tools.
- ❌ Editing only the rendered HTML when a structural change should also update `make_intro.md`.

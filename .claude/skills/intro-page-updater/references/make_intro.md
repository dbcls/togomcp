# Create an introductory HTML page for TogoMCP
TogoMCP is a comprehensive Model Context Protocol (MCP) server that provides LLM agents with access to a vast ecosystem of life sciences databases through SPARQL queries, RDF data exploration, and ID conversion services. It integrates over 30 major biological and biomedical databases, offering researchers a powerful toolkit for cross-database queries, data integration, and knowledge discovery.

The TogoMCP endpoint is available at https://togomcp.rdfportal.org/mcp.
It is developed by DBCLS.

## Goal
Create an HTML page for researchers in biology and medicine who are not necessarily familiar with bioinformatics, explaining what TogoMCP is and how it can help their research. It should contain the following.
- Summary of TogoMCP
- What's new
- Publication
- Usage examples
- Setup guide
- List of available databases
- List of available tools
- Other MCP Servers
- Related Resources
- Source code

## Summary

## What's new
A short, curated list of the most recent **user-facing** updates (new databases, new/changed tools, capability changes) — the newest ~5, each one line with a date, newest first. A light section immediately after Summary, with a "What's New" menu-tab entry after Summary.

- **GENERATED, not hand-edited.** The `<li>` items live between `<!-- WHATSNEW:START -->` / `<!-- WHATSNEW:END -->` sentinels and are rendered by `scripts/generate_whatsnew.py` from markers in `CHANGELOG.md`. Do not edit the items by hand.
- **Source of truth: `CHANGELOG.md` markers.** Add one HTML-comment marker where the change is recorded (under its release heading, or `[Unreleased]` for non-release news):
  `<!-- whatsnew: 2026-07-24 | one user-facing sentence (may use <code>/<em>/<a>) -->`
  Include only what a *user* would notice; skip internal refactors/tests. Then run `python scripts/generate_whatsnew.py`. The `whatsnew.yml` CI + `tests/test_whatsnew_in_sync.py` fail if the page is stale.
- End with a "Full changelog →" link to `https://github.com/dbcls/togomcp/blob/main/CHANGELOG.md`.

## Publication
Cite the paper using the reference from the top-level `README.md`:

> Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

Link the DOI. Include the authors, year, and journal as shown.

## Style
- Use https://togomcp.rdfportal.org/ as a template.
- Follow the style of DBCLS's default CSS at https://dbcls.rois.ac.jp/style/default.css.
- However, make it readable both on PC and smartphone.
- Put the DBCLS Logo with the link at the page top.
- Mind the contrast! 
- The hero section should show the MCP endpoint URL.

## Study TogoMCP
Explore the TogoMCP tools to study how they work and the available databases.

## Usage examples
Read the following files that contain example conversations. 
Give the prompt of each session, followed by a summary of the response.
Include the description of the TogoMCP tools used.

- example1.md   (alongside this spec, in the skill's references/)
- example2.md
- example3.md

Each example should be presented in the following form:
```
Example 1.
Prompt: (The prompt provided by the user)
Response: 
(The summary of the process of finding the results)
Tools Used: 
(the list of TogoMCP tools used along the way)
Key Results:
(The summary of findings)
```

## Setup guide
Read the following webpages carefully and write a concise, accurate setup guide for each.
- **Claude** ([custom connectors article](https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp)) — unlike OpenAI's help centre, `support.claude.com` **is** fetchable (200), so verify against it directly rather than from memory. It carries an "Updated" date. As of 2026-07-30:
  * Custom connectors work on Claude, Claude Desktop **and Cowork**, on **ALL plans** — Free, Pro, Max, Team, Enterprise. Free is capped at one connector; paid plans uncapped. Do not describe this as paid-only.
  * Method 1 path is **Settings → Customize → Connectors → "+" → "Add custom connector"**. Not "Settings → Connectors", and not a button "at the bottom of the page" — both were wrong on the page until 2026-07-30.
  * **Team/Enterprise need an owner to add it org-wide FIRST** (Organization settings → Connectors → Add → hover Custom → Web); members then connect individually. Members cannot self-add before that, so omitting this step strands every Team/Enterprise user.
  * Method 2 (`claude_desktop_config.json` + `npx mcp-remote`) is a **community bridge, not an Anthropic-documented path** — the article says that file is for genuinely local MCP servers. Keep it as an optional fallback only; since Method 1 covers Free, its original "for people without a paid plan" rationale is gone.
- [ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt) (Developer Mode, beta). **This help-center article is the ONLY canonical source for plan eligibility** — it carries an "Updated" date and is revised often. As of 2026-07-29: Business/Enterprise/Edu get full MCP (admin must enable *and publish*); **Pro is read/fetch only**; **Plus has no custom MCP at all**. Web only, no mobile.

  Two traps, both hit on 2026-07-29:
  - **`developers.openai.com/api/docs/guides/developer-mode` is STALE and must not be used for eligibility.** It claims "Available to Pro, Plus, Business, Enterprise, and Education accounts on the web" with full read+write — contradicted by the help-center article on both Plus and Pro. It carries no date, no changelog and no beta label, so its staleness is invisible; that undateability is itself the reason not to trust it.
  - **The help-center article is Cloudflare-blocked (403) to WebFetch and to curl even with a browser UA**, so it cannot be checked by a tool or from CI. A human must open it in a browser. Do not conclude from the 403 that the link is dead, and do not "fix" it by switching to a fetchable-but-wrong source — that is exactly the mistake made on 2026-07-29.

  Because eligibility genuinely differs by tier, **do state it** — a Plus user who follows the setup steps will otherwise just fail. Pair it with the fact that resolves the read/fetch restriction: TogoMCP needs only read access (every tool is a query/search/ID conversion, and all 29 declare `readOnlyHint`), so Pro's read-only limit does not constrain it.
- **Antigravity CLI** ([config docs](https://antigravity.google/docs/mcp)) — the tab formerly labelled "Gemini CLI". **Gemini CLI was retired 2026-06-18** for the free tier, Google AI Pro, Ultra and Google One, replaced by Antigravity CLI (official announcement: [Google Developers Blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/), [repo discussion #27274](https://github.com/google-gemini/gemini-cli/discussions/27274)). Gemini CLI survives only for Gemini Code Assist Standard/Enterprise, Google Cloud access, and paid Gemini API keys — so the Antigravity config is the primary one and Gemini CLI is the footnote, not the reverse.

  The two are **not** interchangeable, and getting it wrong fails silently:

  | | Antigravity | Gemini CLI (legacy) |
  |---|---|---|
  | file | `~/.gemini/config/mcp_config.json` (or `.agents/mcp_config.json` per project) | `~/.gemini/settings.json` |
  | key | `serverUrl` | `httpUrl` |

  Antigravity's docs are explicit that "legacy fields like `url` or `httpUrl` are not supported". Either way TogoMCP is **Streamable HTTP, not SSE** (`url` means SSE in Gemini CLI).

  **Link only to first-party docs**: `antigravity.google/docs/mcp` and `google-gemini.github.io/gemini-cli/docs/`. The page previously linked `geminicli.com`, which is one of several unofficial mirrors (`gemini-cli.xyz`, `geminicli.cloud`, `geminicli.work`) — they return 200 and look official, which is exactly the hazard. A mirror kept serving Gemini CLI instructions six weeks after the product was retired.


## List available databases
Create a list of available databases with a summary of each. Exclude SuperCon from the list.

## List available tools.
Create a list of available tools, each with a brief description of its functionality.

## Other MCP servers
These MCP servers are strongly recommended to be used with TogoMCP.
- [PubDictionary MCP server](https://pubdictionaries.org/mcp) TogoMCP works well with PubDictionaries MCP server.
- [PubMed MCP server](https://support.claude.com/en/articles/12614801-using-the-pubmed-connector-in-claude)
- [OLS4 MCP server](https://www.ebi.ac.uk/ols4/mcp)

## Related resources
List the following resources with summaries. Search the Web if necessary.
- [RDF Portal](https://rdfportal.org)
- [TogoID](https://togoid.dbcls.jp)
- [TogoVar](https://grch38.togovar.org/)
- [DBCLS](https://dbcls.rois.jp)

## Source code
The link to the GitHub repository should be included.
- https://github.com/dbcls/togomcp

## Footer
The footer should include the following
```html
    <img src="https://dbcls.rois.ac.jp/img/logo_dbcls.svg" alt="" class="footer__logo">
    <div class='footer__organism-text'>
        <p class="footer__organism-main">Database Center for Life Science</p>
        <p class="footer__organism-sub">BioData Science Initiative (BSI)</p>
        <p class="footer__organism-sub">National Institute of Genetics</p>
        <p class="footer__organism-sub">Research Organization of Information and Systems</p>
    </div>
```
- Also add the link to each item in the organisation block:
  * Database Center for Life Science → https://dbcls.rois.ac.jp/en/
  * BioData Science Initiative (BSI) → https://bsi.rois.ac.jp/
  * National Institute of Genetics → https://www.nig.ac.jp/en/
  * Research Organization of Information and Systems → https://www.rois.ac.jp/en/
- Below the organisation block, include a row of footer links (`.footer-links`):
  * [DBCLS Home](https://dbcls.rois.ac.jp/en/)
  * [TogoMCP Home](https://togomcp.rdfportal.org/)
  * [RDF Portal](https://rdfportal.org)
  * [TogoID](https://togoid.dbcls.jp)
  * [GitHub](https://github.com/dbcls/togomcp)
  * [Contact](https://dbcls.rois.ac.jp/contact-en.html)
  * [Site Policy](https://bsi.nig.ac.jp/policy)
- Make sure all the links are alive and correct.

**IMPORTANT!**
- Make sure to follow the style of DBCLS's default CSS at https://dbcls.rois.ac.jp/style/default.css in the footer.
- The footer should be center-aligned.

## Menu tab
- Add a menu tab near the top of the page.
- The menu tab should be sticky so the user can always see it when scrolling.
- The menu tab should include the pointers to all the sections.
  * Summary
  * What's New
  * Publication
  * Examples
  * Setup
  * Databases
  * Tools
  * Other MCP Servers
  * Resources
  * [Contact](https://dbcls.rois.ac.jp/contact-en.html)

## Back-to-top button
- 🔵 Circular button in DBCLS blue (#004098)
- ⬆️ Simple arrow symbol (↑)
- 📍 Fixed position in bottom-right corner
- ✨ Smooth shadow and hover effects
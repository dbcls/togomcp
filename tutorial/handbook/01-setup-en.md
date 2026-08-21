# 01. Setup

There are three routes. <!-- workshop-only -->**In the workshop we use route A only.** Read B and C later if you need them.<!-- /workshop-only --><!-- public-only -->**Start with route A.** No installation, three minutes. B and C can wait until you need them.<!-- /public-only -->

| Route | For | Time | Installation |
|---|---|---|---|
| **A. Claude custom connector** | almost everyone | 3 min | **none** |
| B. Claude Code (CLI) | people who work on the command line | 5 min | Claude Code only |
| C. Local stdio | developers, and anyone using KEGG | 15 min | Python, uv, git |

None of the routes require a TogoMCP account or an API key (only if you use the NCBI tools do you need an NCBI API key → appendix).

---

## Route A: Claude custom connector (recommended)

Works on **every plan** of Claude (Web / desktop / Cowork). The Free plan allows one custom connector; paid plans have no limit.

### Steps

1. Open Claude and go to **Settings → Customize → Connectors**
2. **"+"** → **"Add custom connector"**
3. Enter the MCP server URL:

   ```
   https://togomcp.rdfportal.org/mcp
   ```

4. After adding it, click the **"+"** button in the chat screen, choose **Connectors**, and enable it for that conversation

### On a Team / Enterprise plan

**An organization owner has to take one step first.** Individual members cannot add it themselves.

1. The owner goes to **Organization settings → Connectors → Add**, hovers over **Custom**, chooses **Web**, and adds it for the whole organization
2. After that, each member connects for themselves from **Customize → Connectors**

<!-- workshop-only -->> 💡 **For workshop organizers:** if your participants are on Team/Enterprise accounts, **nobody will be able to connect unless this is done before the day.** Put it in the advance instructions without fail.<!-- /workshop-only --><!-- public-only -->> 💡 If your organization is on a Team/Enterprise plan, **you cannot add it yourself.** Ask your administrator.<!-- /public-only -->

### If custom connectors are unavailable in your environment

There is a way through a local bridge called `mcp-remote`. It is a community tool, not an official Anthropic procedure, but it works.

Add the following to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "togomcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://togomcp.rdfportal.org/mcp"]
    }
  }
}
```

---

## Route B: Claude Code (CLI)

Run the following **in the terminal** (before you enter a Claude session).

```bash
claude mcp add --scope user --transport http togomcp https://togomcp.rdfportal.org/mcp
```

Adding `--scope user` makes it **available in every project**. Without it, it is only active in that one directory.

| Scope | Stored in | Applies to |
|---|---|---|
| `--scope local` (default) | the per-project entry in `~/.claude.json` | that project only, and only you |
| `--scope project` | `.mcp.json` at the project root | everyone who clones the repository |
| `--scope user` | the top level of `~/.claude.json` | **all of your projects** ← recommended |

### Checking the connection

```bash
claude mcp list
```

If **`✔ Connected`** appears next to `togomcp`, you are done.

| Display | Meaning |
|---|---|
| `✔ Connected` | success |
| `✘ Failed to connect` | the URL is not being reached. Check the trailing `/mcp` |
| `! Connected · tools fetch failed` | connected, but the tool list did not come back |
| `! Needs authentication` | waiting on authentication (should not happen with TogoMCP) |

Inside a Claude session, typing `/mcp` shows you the same state.

### Removing and inspecting

```bash
claude mcp list              # list
claude mcp remove togomcp    # remove
claude mcp remove togomcp --scope user   # remove within a specified scope
```

### Common mistakes

1. **Typing `claude mcp add` inside a Claude session.** This is a command you type **in the terminal**. It will not work once you have typed `claude` and entered the session.
2. **Dropping the trailing `/mcp` from the URL.** You get a 404.
3. **Forgetting the scope.** The default `local` only works in that one directory. Most cases of "but it worked yesterday" are this.
4. **Putting the config file in the wrong place.** Claude Code reads only `~/.claude.json` and `.mcp.json` at the project root. Files like `~/.claude/.mcp.json` are not read.

> The above was confirmed on Claude Code v2.1.210 and later. `claude --version` tells you which version you have.

---

## Route C: Local stdio

For developers, and **the only route if you want to use the KEGG tools**. The steps are collected in the [appendix](99-appendix-local-install-en.md).

---

## Checking that you are connected (all routes)

Ask Claude this.

```
What databases can you use from TogoMCP?
```

**What you should see:** in about ten seconds, a list of 37 databases including UniProt, PDB, ChEMBL and TogoVar, organized by field.

**If it does not work:**

| Symptom | What to check |
|---|---|
| It never mentions TogoMCP and answers in generalities | whether the connector is **enabled** for that conversation (on route A you have to select it from "+" in each conversation) |
| It tells you it has no tools available | the URL, and the state shown by `claude mcp list` |
| It tries to call a tool and fails | the network. Possibly a corporate proxy or VPN |

For details, go to [08. Troubleshooting](08-troubleshooting-en.md).

---

## Note: using it from ChatGPT / Gemini

TogoMCP is not Claude-only. But each host has its quirks.

- **ChatGPT:** Developer Mode (Web only, not supported on mobile). Pro has read/fetch only, but **that is enough**. Plus cannot use custom MCP connectors.
  ⚠️ **ChatGPT records the tool list once, when the connector is added, and never re-fetches it automatically.** Tools added later stay invisible. If it tells you a tool that should exist is not there, **run Scan Tools again**, or delete the connector and add it back. Note that **adding databases is not affected** (the database catalog is delivered at query time, so it is always current).
- **Gemini / Antigravity:** specify it as `"serverUrl"` in `~/.gemini/config/mcp_config.json`. Note that TogoMCP is **Streamable HTTP, not SSE**.

---

## MCP servers that are strong alongside it

TogoMCP works on its own, but using it together with the following widens what you can handle. Some of the skills in Chapter 5 assume them.

| Server | URL | Role |
|---|---|---|
| **PubMed** | [official Claude connector](https://support.claude.com/en/articles/12614801-using-the-pubmed-connector-in-claude) | literature search and full-text retrieval |
| **OLS4** (EMBL-EBI) | `https://www.ebi.ac.uk/ols4/mcp` | exploring ontology terms and hierarchies |
| **PubDictionaries** | `https://pubdictionaries.org/mcp` | natural-language labels → ontology IDs |

The typical combination is "settle the canonical term ID in OLS4 → query with that ID in TogoMCP." Chapter 6 shows why that order works.

---

Next → [02. The First Demo](02-first-demo-en.md)

# Appendix: Local Installation (Route C)

For developers, and **the only route if you want to use the KEGG tools**.

It is not needed for ordinary use. [Route A (the custom connector)](01-setup-en.md) is fully functional. You need what follows only if:

- you want to use the KEGG tools (restricted to those affiliated with an academic institution)
- you are writing or fixing MIE files
- you are developing the server itself
- you are hosting it yourself inside your organization

---

## Prerequisites

- Python >= 3.11
- The [uv](https://docs.astral.sh/uv/) package manager

### Installing uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Installation

```bash
git clone https://github.com/dbcls/togomcp.git
cd togomcp
uv sync
```

### NCBI API key (mandatory if you use the NCBI tools)

Get a key from [the NCBI documentation](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/), then:

```bash
export NCBI_API_KEY="your-key-here"
```

---

## Configuring Claude Desktop

Where the configuration file lives:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `~\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
    "mcpServers": {
        "togomcp": {
            "command": "/path/to/uv",
            "args": [
                "--directory",
                "/path/to/togomcp",
                "run",
                "togo-mcp-local"
            ],
            "env": {
                "NCBI_API_KEY": "your-key-here"
            }
        }
    }
}
```

> 💡 You can find the absolute path to `uv` with `which uv` (macOS/Linux) or `where uv` (Windows). A relative path, or just `uv`, will not work.

After configuring, **quit Claude Desktop completely and restart it**.

---

## KEGG (opt-in, local stdio only)

> **KEGG is off by default. You do not need it. TogoMCP is fully functional without KEGG.**
> This section is relevant only if you are eligible and you want to use it.

The eight tools `kegg_find` / `kegg_get_entry` / `kegg_conv` / `kegg_link` / `kegg_pathway_graph` / `kegg_pathway_neighborhood` / `kegg_pathway_paths` / `kegg_pathway_cycles` become available **only when both of the following hold**.

1. You are running it through the local stdio entry point `togo-mcp-local`
2. You have set `TOGOMCP_ENABLE_KEGG=1`

### Why there are two gates — the reasons are separate

**(1) The restriction on the transport route is structural, and configuration cannot change it.**

The [KEGG API](https://www.kegg.jp/kegg/rest/) is provided "for academic use by academic users belonging to academic institutions," and **providing a service** that uses KEGG requires a separate academic service-provider licence ([KEGG's terms of use](https://www.kegg.jp/kegg/legal.html)).

A public server cannot verify the affiliation of the caller. Therefore **no HTTP deployment reaches `rest.kegg.jp`**, including togomcp.rdfportal.org. **No environment variable changes this** — `TOGOMCP_ENABLE_KEGG` has no effect whatsoever on the HTTP path.

**(2) The opt-in exists because the claim of eligibility is yours.**

Under stdio, **you yourself** are the caller. But whether your institution's access rights cover you is something only you can know.

Enabling KEGG by default would mean **placing an API call you may not be entitled to make on the path of least resistance**. An AI assistant uses the tools it can see. For a user whose use is not academic, leaving the variable unset is the correct configuration, and it has no other consequences.

### Enabling it

```json
"env": {
    "NCBI_API_KEY": "your-key-here",
    "TOGOMCP_ENABLE_KEGG": "1"
}
```

### Constraints

- Calls are limited to **3 requests per second** (enforced across the whole process. There is no retry on 403/429)
- **KEGG is not part of RDF Portal.** It has no SPARQL endpoint, so `database="kegg"` in `run_sparql` is invalid
- To connect it to the RDF databases, use `kegg_conv` to convert KEGG identifiers into UniProt / NCBI Gene / NCBI Protein / ChEBI / PubChem first

---

## Docker

```bash
cp .env.example .env                                # fill in NCBI_API_KEY
docker build -t localhost/togo-mcp:latest .
docker compose up -d togomcp-main                   # port 8000
```

`compose.yaml` defines two services, `togomcp-main` (8000) and `togomcp-test` (8001), so you can run production and testing side by side from the same image.

```bash
docker compose logs -f togomcp-main    # logs
docker compose down                    # stop and remove
```

### Putting it behind a reverse proxy

**Two environment variables come into play. Both break in ways that are easy to misdiagnose.**

**`TOGOMCP_ALLOWED_HOSTS`** — the `Host` header is validated (a defence against DNS rebinding), and any host not on the allow list gets a **421**. The default is localhost and the DBCLS public vhost only. **Unless you add your own hostname, every request through the proxy is rejected.**

**`TOGOMCP_FORWARDED_ALLOW_IPS`** — which peer addresses are allowed to set `X-Forwarded-Proto` / `-For`. uvicorn trusts only `127.0.0.1` by default, and a container reached through a published port does not arrive as loopback. Get this wrong and the headers are **not rejected — they are silently discarded**. The app then believes it is serving plain HTTP, and emits redirects that downgrade `https://` to `http://`.

**The proxy side has to send `X-Forwarded-Proto` as well.** nginx does not send it by default:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

Caddy and Traefik do send it. **It only works when both are in place. One alone will not do.**

---

## Tool-call logging (optional)

TogoMCP can log every tool call as one JSON object per line (timestamp, tool name, arguments, status, elapsed milliseconds, session/request/client ID, transport, client IP). SPARQL calls additionally carry the endpoint URL, the HTTP code, the row and byte counts, and the SHA-256 of the query.

**It is useful for benchmarking, for improving the MIEs, and for reconstructing procedures that span several tools.** You can also use it to automate the reproducibility records of Chapter 7.

On and off is a single environment variable, `TOGOMCP_QUERY_LOG`. Unset = disabled (zero overhead). Set it to a writable file path and it is enabled.

For Claude Desktop (local stdio), add it to the `env` block. **Use an absolute path** (the working directory of the launched process is unpredictable) and **create the parent directory first**:

```json
"env": {
    "NCBI_API_KEY": "your-key-here",
    "TOGOMCP_QUERY_LOG": "/Users/you/togomcp-logs/togomcp.jsonl"
}
```

```bash
mkdir -p ~/togomcp-logs
```

Then restart Claude Desktop completely.

> ⚠️ **Privacy:** IPs are recorded as a salted hash (`ip_hash`) by default. Setting `TOGOMCP_LOG_RAW_IP=1` records them in the clear as well, which makes it possible to identify and block abusers — but **it makes the log personal data**. For the details of each field, see `log_file_specs.md` in the repository.

---

## Adding a database (for developers)

**There are five places. Not two.** Only the first two affect the server's validation; the rest are documentation surfaces that drift out of sync silently. The tests catch that.

1. `togo_mcp/data/resources/endpoints.csv` — the registration row (**this alone determines the valid `database=` values**)
2. `togo_mcp/data/mie/<db>.yaml` — the MIE file (the specification is in `togo_mcp/data/docs/`)
3. `uv run python scripts/generate_usage_guide_catalog.py` — regenerate the database catalogue in the usage guide
4. `togo_mcp/data/resources/usage_guide_v6/02_budgets_and_discovery.md` — **a hand-written copy the generator does not touch**. Update both the counts and the keys
5. `togo_mcp/data/docs/togomcp-intro.html` — the landing-page card (not generated)

---

[← Back to the table of contents](../README-en.md)

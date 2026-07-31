"""KEGG REST wrapper — a THIN layer over `togo_mcp.kgml`.

STDIO ONLY — READ THIS BEFORE MOVING ANY OF IT
----------------------------------------------
The KEGG API is licensed "for academic use by academic users belonging to
academic institutions" (https://www.kegg.jp/kegg/rest/), and offering a service
built on KEGG additionally requires an academic *service provider* license
(https://www.kegg.jp/kegg/legal.html). `togomcp.rdfportal.org` is a public DBCLS
host that cannot verify a caller's affiliation, so this sub-server is mounted
**only** on the stdio entry point (`togo-mcp-local`), where the user running the
process is the academic user. See `main.py:setup(local=...)`.

That gate is STRUCTURAL, not an env flag, and deliberately so: `deploy.sh`
forwards env vars by a fixed list, and a knob missing from that list is silently
inert in production — a failure that happened twice in one week (see CLAUDE.md,
"Deployment"). A licence boundary must not depend on that.

WHY THIS MODULE IS THIN
-----------------------
All the graph logic lives in `kgml.py`, which is pure (stdlib only, no network)
and unit-tested without HTTP — the same split as `togovar._build_variant_query`.
Anything here beyond fetch/validate/shape belongs there instead.

MODULE CONVENTIONS (same as togovar.py — keep uniform)
------------------------------------------------------
* Raise `ValueError` on bad parameters AND on HTTP error
  (`raise_for_status_with_body`). Never return an `{"error": ...}` payload.
* No "fall back to SPARQL" hint: KEGG has no RDF Portal endpoint.
* List-style results return a JSON string of a BARE ARRAY, so empty and
  non-empty share one wire shape. `dict` returns are exempt.
* Every tool carries `annotations=READ_ONLY_TOOL`.

RATE LIMIT
----------
KEGG asks for <= 3 requests/second and blocks abusers. The limiter below is
process-wide (one shared token gate), not per-tool: an LLM-driven session issues
dozens of calls across several tools and a per-tool budget would multiply past
the cap. KGML is additionally memoized in-process, since a single reasoning
chain re-reads the same map repeatedly.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import re
import time
from collections import OrderedDict
from typing import Annotated, Any

import httpx
from pydantic import Field

from .kgml import (
    KGMLParseError,
    find_cycles,
    find_paths,
    metabolic_gaps,
    neighborhood,
    parse_kgml,
    resolve_seeds,
)
from .server import *

kegg_mcp = FastMCP("KEGG API server")

_client = httpx.AsyncClient(base_url="https://rest.kegg.jp", timeout=30.0)


def _close_client():
    """Close the shared httpx client on interpreter shutdown."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_client.aclose())
    except RuntimeError:
        asyncio.run(_client.aclose())


atexit.register(_close_client)


# --------------------------------------------------------------------------- #
# Rate limiting — process-wide, not per-tool.
#
# "Please also limit your API calls up to 3 times per second. Otherwise, your
# access will be blocked." (https://www.kegg.jp/kegg/rest/). The lock serializes
# request STARTS and spaces them by _MIN_INTERVAL; requests still overlap on the
# wire, which is what the cap actually governs.
# --------------------------------------------------------------------------- #
_MIN_INTERVAL = 1 / 3
_rate_lock = asyncio.Lock()
_last_request_at = 0.0

# Retries are for transient upstream failures only. 403/429 are NEVER retried:
# they are the licence/rate-limit signals, and hammering them is exactly what
# gets an institution blocked.
_MAX_ATTEMPTS = 3
_BACKOFF_BASE = 0.5


async def _throttle() -> None:
    global _last_request_at
    async with _rate_lock:
        wait = _last_request_at + _MIN_INTERVAL - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = time.monotonic()


async def _kegg_get(path: str, *, context: str) -> str:
    """GET one KEGG REST path, honoring the rate cap. Returns the raw body.

    An EMPTY body with HTTP 200 is KEGG's "no match" answer (it does not 404),
    so callers must treat "" as an empty result rather than assuming success
    implies content. Raises ValueError on any non-2xx, on 403/429 (without
    retrying), and after _MAX_ATTEMPTS transient failures.
    """
    for attempt in range(_MAX_ATTEMPTS):
        await _throttle()
        try:
            response = await _client.get(path)
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            if attempt + 1 < _MAX_ATTEMPTS:
                await asyncio.sleep(_BACKOFF_BASE * 2**attempt)
                continue
            raise ValueError(
                f"{context}: could not reach rest.kegg.jp after {_MAX_ATTEMPTS} "
                f"attempts ({exc.__class__.__name__}: {exc}). KEGG is reachable "
                "only from a network permitted by your institution's access to "
                "the KEGG API."
            ) from exc

        if response.status_code in (403, 429):
            raise ValueError(
                f"{context}: HTTP {response.status_code} from {response.url} — "
                "RATE LIMIT EXCEEDED OR ACCESS RESTRICTED. The KEGG API allows at "
                "most 3 requests/second and is licensed to academic users at "
                "academic institutions. Do NOT retry: repeated calls after this "
                "response are what cause an address to be blocked outright."
            )

        if response.status_code >= 500 and attempt + 1 < _MAX_ATTEMPTS:
            await asyncio.sleep(_BACKOFF_BASE * 2**attempt)
            continue

        raise_for_status_with_body(
            response,
            context=context,
            client_error_hint=(
                "Check the database name, entry identifiers, and option against "
                "https://www.kegg.jp/kegg/rest/keggapi.html. Do not retry the "
                "same request unchanged."
            ),
        )
        return response.text

    # Unreachable: the loop either returns or raises on its last iteration.
    raise ValueError(f"{context}: exhausted retries against rest.kegg.jp.")


# --------------------------------------------------------------------------- #
# KEGG vocabularies (https://www.kegg.jp/kegg/rest/keggapi.html)
# --------------------------------------------------------------------------- #

# /find/<database>/<query>
_FIND_DATABASES = frozenset([
    "pathway", "brite", "module", "ko", "genes", "vg", "vp", "ag", "genome",
    "ligand", "compound", "glycan", "reaction", "rclass", "enzyme", "network",
    "variant", "disease", "drug", "dgroup",
])

# /find option (compound/drug-family databases only).
_FIND_OPTIONS = frozenset(["formula", "exact_mass", "mol_weight", "nop"])
_CHEMICAL_DATABASES = frozenset(["compound", "drug", "glycan", "ligand", "dgroup"])

# Databases usable as either side of /link.
_LINK_DATABASES = _FIND_DATABASES | frozenset(
    ["atc", "jtc", "ndc", "yj", "pubmed"]
)

# /conv operates on two disjoint ID families; crossing them is a hard error
# upstream, so it is caught here with a message that says which family is which.
_CONV_GENE_OUTSIDE = frozenset(["ncbi-geneid", "ncbi-proteinid", "uniprot"])
_CONV_CHEM_KEGG = frozenset(["drug", "compound", "glycan"])
_CONV_CHEM_OUTSIDE = frozenset(["pubchem", "chebi"])

# KEGG organism codes: 3-4 lowercase alphanumerics (hsa, eco, mmu, dme) or a
# T-number genome id. Matched by shape rather than enumerated — KEGG carries
# thousands of organisms and the list changes with every release.
_ORG_CODE = re.compile(r"^[a-z][a-z0-9]{2,3}$")
_T_NUMBER = re.compile(r"^T\d{5}$")

# A pathway map id, with the optional `path:` prefix KEGG itself emits.
_PATHWAY_ID = re.compile(r"^(?:path:)?([a-z]{2,4})(\d{5})$")

# Response soft cap, mirroring togovar._MAX_RESPONSE_CHARS.
_MAX_RESPONSE_CHARS = 90_000

# Default graph-size ceilings for kegg_pathway_graph. hsa05200 ("Pathways in
# cancer"), the largest map in the validation set, is 255 nodes / 311 edges, so
# these clear every ordinary map and only bite on member-expanded ones.
_DEFAULT_MAX_NODES = 400
_DEFAULT_MAX_EDGES = 1200

# In-process KGML memo. A single reasoning chain calls kegg_pathway_graph and
# kegg_pathway_neighborhood on the same map repeatedly; without this each one is
# another request against a 3/s budget.
_KGML_CACHE_MAX = 32
_kgml_cache: OrderedDict[str, str] = OrderedDict()


def _is_org(token: str) -> bool:
    return bool(_ORG_CODE.match(token) or _T_NUMBER.match(token))


def _as_list(value: str | list[str]) -> list[str]:
    """Coerce a str-or-list argument to a clean list[str].

    A string is split on commas, whitespace and '+' so the LLM-favoured
    "hsa:10458, hsa:5290" and KEGG's own "hsa:10458+hsa:5290" both work.
    """
    if isinstance(value, str):
        return [tok for tok in re.split(r"[,\s+]+", value) if tok]
    out: list[str] = []
    for v in value:
        out.extend(tok for tok in re.split(r"[,\s+]+", str(v)) if tok)
    return out


def _check_path_token(token: str, *, label: str) -> str:
    """Reject anything that would alter the REST path rather than fill a slot."""
    if not token or not token.strip():
        raise ValueError(f"`{label}` must not be empty.")
    token = token.strip()
    if "/" in token or any(c.isspace() for c in token):
        raise ValueError(
            f"Invalid {label} {token!r}: it must be a single KEGG identifier or "
            "database name with no '/' and no spaces. Do not retry the same value."
        )
    return token


def _normalize_pathway(pathway: str) -> str:
    """'path:hsa04151' / 'hsa04151' -> 'hsa04151'; reject anything else."""
    token = _check_path_token(pathway, label="pathway")
    m = _PATHWAY_ID.match(token)
    if not m:
        raise ValueError(
            f"Invalid pathway id {token!r}. Expected an organism/reference prefix "
            "plus a five-digit map number, e.g. 'hsa04151' (human PI3K-Akt), "
            "'eco00010' (E. coli glycolysis), 'ko00010' (reference/KO map), or "
            "'map00010'. Do not retry with the same value."
        )
    return f"{m.group(1)}{m.group(2)}"


# --------------------------------------------------------------------------- #
# Flat-file parsing (pure — /get returns KEGG's own column-12 record format)
# --------------------------------------------------------------------------- #


def _parse_flat_file(text: str) -> list[dict[str, Any]]:
    """Parse KEGG's flat-file format into one dict per entry.

    The format is field-name in column 0, value from column 12, continuation
    lines indented, records terminated by a line of `///`. Field names never
    contain a space, so the split is on the first whitespace run rather than a
    fixed column — a few field names run past column 11 and fixed-width slicing
    would truncate them.

    Every value is a `list[str]` of lines, uniformly. Collapsing single-line
    fields to a bare string would make the shape depend on the data, which is
    the thing that makes a return contract unusable for a caller.
    """
    records: list[dict[str, Any]] = []
    for block in text.split("\n///"):
        if not block.strip():
            continue
        fields: dict[str, list[str]] = {}
        current: str | None = None
        for line in block.splitlines():
            if not line.strip():
                continue
            if line[0].isspace():
                if current is not None:
                    fields[current].append(line.strip())
                continue
            key, _, value = line.partition(" ")
            key = key.strip()
            if not key:
                continue
            current = key
            fields.setdefault(key, [])
            if value.strip():
                fields[key].append(value.strip())

        if not fields:
            continue
        record: dict[str, Any] = {}
        entry_line = (fields.get("ENTRY") or [""])[0].split()
        record["entry_id"] = entry_line[0] if entry_line else None
        # The ENTRY line's trailing tokens name the record class (Compound, CDS,
        # Pathway, …) plus, for genes, the T-number of the genome.
        record["entry_type"] = " ".join(entry_line[1:]) or None
        record["fields"] = fields
        records.append(record)
    return records


def _bounded(payload: Any, *, note: str) -> str:
    """Serialize, and if it blows the soft cap say so instead of truncating mutely."""
    out = json.dumps(payload, ensure_ascii=False)
    if len(out) <= _MAX_RESPONSE_CHARS:
        return out
    if isinstance(payload, list):
        kept = list(payload)
        while kept and len(json.dumps(kept, ensure_ascii=False)) > _MAX_RESPONSE_CHARS:
            del kept[-max(1, len(kept) // 4):]
        return json.dumps(
            {
                "results": kept,
                "truncated": {
                    "reason": "response exceeded the size cap",
                    "returned": len(kept),
                    "total": len(payload),
                    "hint": note,
                },
            },
            ensure_ascii=False,
        )
    payload = dict(payload)
    payload["truncated"] = {"reason": "response exceeded the size cap", "hint": note}
    return json.dumps(payload, ensure_ascii=False)


def _parse_tsv_pairs(text: str) -> list[tuple[str, str]]:
    """KEGG /find, /link and /conv all return two tab-separated columns."""
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        left, _, right = line.partition("\t")
        pairs.append((left.strip(), right.strip()))
    return pairs


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def find(
    database: Annotated[
        str,
        Field(description="KEGG database to search, e.g. 'compound', 'pathway', 'hsa'."),
    ] = "",
    query: Annotated[str | list[str], Field(description="Keyword(s); combined with AND.")] = "",
    option: Annotated[
        str, Field(description="'formula' | 'exact_mass' | 'mol_weight' | 'nop'.")
    ] = "",
    limit: Annotated[int, Field(ge=1, le=1000)] = 100,
) -> str:
    """Keyword-search a KEGG database and get back matching entry IDs.

    This is the entry point to KEGG: almost everything else here takes an entry
    ID this tool produces. KEGG IDs are not RDF-resolvable — convert them with
    `kegg_conv` before using them in any downstream RDF query.

    RETURNS a JSON string of a bare array of `{"entry": str, "definition": str}`,
    e.g. `[{"entry": "cpd:C00031", "definition": "D-Glucose; Grape sugar; ..."}]`.
    Empty and non-empty results share the same `[...]` shape — an empty array
    means KEGG matched nothing (KEGG answers "no match" with an empty HTTP 200,
    not a 404). With `option="formula"`/`"exact_mass"`/`"mol_weight"` the
    `definition` field carries that chemical property instead of the name.

    RAISES ValueError on an unknown database/option and on any HTTP error,
    including HTTP 403/429, which means the KEGG rate limit (3 requests/second)
    or an access restriction was hit — that error must not be retried.

    Args:
        database: One of pathway, brite, module, ko, genes, genome, ligand,
            compound, glycan, reaction, rclass, enzyme, network, variant,
            disease, drug, dgroup, vg, vp, ag — or a KEGG organism code
            (e.g. "hsa" human, "eco" E. coli, "mmu" mouse) to search that
            organism's genes. "genes" searches ALL organisms and is slow.
        query: Keyword(s). Several keywords (a list, or one space-separated
            string) are combined with AND. For `option="exact_mass"` or
            `"mol_weight"` a numeric range like "300-310" is accepted.
        option: For compound/drug-family databases only. "formula" searches by
            chemical formula, "exact_mass"/"mol_weight" by mass, "nop" disables
            KEGG's query preprocessing.
        limit: Maximum rows to return, in [1, 1000]. Default 100. KEGG has no
            server-side limit, so this trims client-side.

    Returns:
        str: JSON array of `{"entry", "definition"}` objects.
    """
    database = _check_path_token(database, label="database")
    if database not in _FIND_DATABASES and not _is_org(database):
        raise ValueError(
            f"Unknown KEGG database {database!r}. Valid: "
            f"{', '.join(sorted(_FIND_DATABASES))}, or an organism code such as "
            "'hsa', 'eco', 'mmu'. Do not retry with the same value."
        )

    terms = _as_list(query)
    if not terms:
        raise ValueError(
            "Missing search term. Pass one or more keywords via `query`, "
            "e.g. database='compound', query='glucose'."
        )

    path = f"/find/{database}/{'+'.join(terms)}"
    if option:
        option = _check_path_token(option, label="option")
        if option not in _FIND_OPTIONS:
            raise ValueError(
                f"Unknown find option {option!r}. Valid: "
                f"{', '.join(sorted(_FIND_OPTIONS))}. Do not retry with the same value."
            )
        if database not in _CHEMICAL_DATABASES:
            raise ValueError(
                f"Option {option!r} applies only to the chemical databases "
                f"({', '.join(sorted(_CHEMICAL_DATABASES))}), not to {database!r}."
            )
        path += f"/{option}"

    text = await _kegg_get(path, context="KEGG find")
    results = [
        {"entry": entry, "definition": definition}
        for entry, definition in _parse_tsv_pairs(text)
    ][:limit]
    return _bounded(results, note="narrow the query or lower `limit`.")


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def get_entry(
    entries: Annotated[
        str | list[str],
        Field(description="Up to 10 KEGG entry IDs, e.g. 'hsa:10458' or 'C00031'."),
    ] = "",
    sequence: Annotated[
        str, Field(description="'' (flat file), 'aaseq' or 'ntseq' (FASTA).")
    ] = "",
) -> str:
    """Retrieve full KEGG entries (compound, gene, pathway, enzyme, drug, …).

    Use this after `kegg_find` to read what an entry actually says: names,
    formula/mass, EC numbers, ORTHOLOGY, pathway membership, and DBLINKS (the
    cross-references that let you carry a result onward via `kegg_conv`).

    RETURNS a JSON string of a bare array with one object per entry:
    `{"entry_id": str, "entry_type": str|null, "fields": {FIELD: [line, ...]}}`.
    `fields` holds KEGG's own flat-file field names (ENTRY, NAME, FORMULA,
    DBLINKS, ORTHOLOGY, PATHWAY, …), each value ALWAYS a list of lines even when
    there is only one — the shape does not vary with the data. An empty array
    means no entry matched (KEGG returns an empty HTTP 200, not a 404). With
    `sequence="aaseq"`/`"ntseq"` each object is instead
    `{"entry_id", "header", "sequence"}` carrying the FASTA record.

    RAISES ValueError if more than 10 entries are requested (KEGG's documented
    per-request cap), on a malformed identifier, and on any HTTP error —
    including HTTP 403/429 for the 3 requests/second rate limit, which must not
    be retried.

    Args:
        entries: Up to 10 KEGG entry IDs. Accepts a list or a single
            comma/space/'+'-separated string. Database-qualified ("hsa:10458",
            "cpd:C00031", "ec:2.7.1.1") and bare ("C00031", "hsa04151") forms
            both work.
        sequence: Leave empty for the parsed flat file. "aaseq" returns the
            amino-acid FASTA and "ntseq" the nucleotide FASTA — gene entries
            only. KEGG's other /get options (image, kgml, json) are NOT exposed:
            use `kegg_pathway_graph` for KGML, which returns a usable graph
            rather than raw XML.

    Returns:
        str: JSON array of entry objects.
    """
    ids = _as_list(entries)
    if not ids:
        raise ValueError(
            "Missing entry identifier(s). Pass up to 10 KEGG IDs via `entries`, "
            "e.g. 'hsa:10458' or 'C00031'."
        )
    if len(ids) > 10:
        raise ValueError(
            f"KEGG /get accepts at most 10 entries per request; got {len(ids)}. "
            "Split the request into batches of 10."
        )
    ids = [_check_path_token(i, label="entry") for i in ids]

    path = f"/get/{'+'.join(ids)}"
    if sequence:
        sequence = _check_path_token(sequence, label="sequence")
        if sequence not in ("aaseq", "ntseq"):
            raise ValueError(
                f"Unknown sequence option {sequence!r}. Valid: 'aaseq' (protein), "
                "'ntseq' (nucleotide), or leave empty for the parsed flat-file "
                "entry. Do not retry with the same value."
            )
        path += f"/{sequence}"

    text = await _kegg_get(path, context="KEGG get")
    if not text.strip():
        return "[]"

    if sequence:
        records: list[dict[str, Any]] = []
        for chunk in text.split(">"):
            if not chunk.strip():
                continue
            header, _, body = chunk.partition("\n")
            records.append({
                "entry_id": header.split()[0] if header.split() else None,
                "header": header.strip(),
                "sequence": "".join(body.split()),
            })
        return _bounded(records, note="request fewer entries per call.")

    return _bounded(
        _parse_flat_file(text), note="request fewer entries per call."
    )


async def _fetch_kgml(pathway: str) -> str:
    """Fetch (and memoize) one map's KGML."""
    cached = _kgml_cache.get(pathway)
    if cached is not None:
        _kgml_cache.move_to_end(pathway)
        return cached

    text = await _kegg_get(f"/get/{pathway}/kgml", context="KEGG KGML")
    if not text.strip():
        raise ValueError(
            f"KEGG has no KGML for {pathway!r} (empty response). Not every KEGG "
            "map has a KGML file — global/overview maps (e.g. 01100, 01110) and "
            "some BRITE-style maps have none. Pick a regular pathway map, e.g. "
            "'hsa04151' or 'hsa00010'."
        )

    _kgml_cache[pathway] = text
    _kgml_cache.move_to_end(pathway)
    while len(_kgml_cache) > _KGML_CACHE_MAX:
        _kgml_cache.popitem(last=False)
    return text


async def _load_graph(pathway: str, **options: Any) -> tuple[str, dict[str, Any]]:
    """Resolve a pathway id, fetch its KGML, and parse it into a graph."""
    pathway = _normalize_pathway(pathway)
    text = await _fetch_kgml(pathway)
    try:
        return pathway, parse_kgml(text, **options)
    except KGMLParseError as exc:
        raise ValueError(f"KEGG returned unusable KGML for {pathway}: {exc}") from exc


def _signal_quality(graph: dict[str, Any]) -> dict[str, Any]:
    """How much of this map's regulation is actually signed, and how connected.

    Both numbers exist to stop a caller over-reading the graph. The signed
    FRACTION swings hugely between maps — PI3K-Akt (hsa04151) is 98% signed
    while MAPK (hsa04010) is 40%, the rest being `binding/association` or
    `phosphorylation` relations where KGML simply does not say whether the
    effect is activating or inhibiting. A `net_sign` of 0 therefore means
    UNKNOWN, never "no effect".

    Fragmentation is likewise expected, not a parse failure: `hsa05200`
    ("Pathways in cancer") wires its sub-modules together through 22 cross-map
    pointers, which are deliberately excluded (they point at other maps, so
    including them would fabricate interactions), leaving the map in ~32 pieces.
    """
    stats = graph["stats"]
    edges = stats["edge_count"]
    signed = stats["signed_edge_count"]
    return {
        "signed_edge_count": signed,
        "edge_count": edges,
        "signed_edge_fraction": round(signed / edges, 3) if edges else 0.0,
        "component_count": stats["component_count"],
        "largest_component": stats["largest_component"],
        "node_count": stats["node_count"],
        "caveats": [
            (
                f"Only {signed}/{edges} edges carry a direction of regulation. "
                "An unsigned edge (sign 0) means KGML records a MECHANISM "
                "(phosphorylation, binding/association, …) without saying whether "
                "the effect activates or inhibits — read net_sign 0 as UNKNOWN, "
                "not as 'no effect'."
            ),
            (
                f"The map parses into {stats['component_count']} weakly-connected "
                f"component(s) (largest {stats['largest_component']} of "
                f"{stats['node_count']} nodes). Fragmentation is normal: KEGG "
                "links sub-modules through pointers to OTHER maps, which are "
                "reported separately as `map_links` and excluded from the graph "
                "because treating them as edges would invent interactions that "
                "were never asserted. Do not read it as 'the pathway is broken'."
            ),
        ],
    }


def _cycle_interpretation(
    graph: dict[str, Any],
    counts: dict[str, int],
    selected: list[dict[str, Any]],
    artifacts_excluded: int,
) -> list[str]:
    """Say what a cycle result does and does not license the caller to conclude.

    Cycle detection is the most misread thing this server returns, because its
    normal answer on real data is "nothing" and the obvious reading of nothing is
    "this pathway has no feedback". Measured over the six-map validation set it
    found ZERO signed cycles, so the empty and all-unsigned cases are the RULE,
    not an edge case, and each needs its own explanation attached to the result
    rather than left in a docstring the caller may not re-read.
    """
    notes: list[str] = []
    signed = counts["negative"] + counts["positive"]

    if not selected:
        notes.append(
            "NO CYCLE FOUND — this is the usual outcome and is NOT evidence that "
            "the pathway lacks feedback. A KEGG map is a drawing of one process, "
            "not a complete interaction model, so a real loop routinely has an arm "
            "that is absent from THIS map (on hsa05200, MDM2 -| TP53 is drawn but "
            "TP53 -> MDM2 is not). Do not report 'no feedback loops' to the user. "
            "For a signed claim use kegg_pathway_paths, whose net_sign needs only a "
            "path and not a closed cycle."
        )
    elif not signed:
        notes.append(
            "Every cycle found is `unsigned`, i.e. its direction is UNKNOWN — at "
            "least one edge on each loop records only a mechanism "
            "(phosphorylation, binding) or is metabolic. These are structural "
            "loops; they do NOT support calling anything negative or positive "
            "feedback."
        )

    if artifacts_excluded:
        notes.append(
            f"{artifacts_excluded} two-cycle(s) were excluded as reversible-reaction "
            "artifacts: a reversible reaction A<->B is emitted in both directions "
            "and so is a cycle by construction, with no feedback meaning. Pass "
            "include_reversible_artifacts=True to see them."
        )

    if not graph["stats"]["signed_edge_count"]:
        notes.append(
            "This map has NO signed edges at all (typical of metabolic maps), so a "
            "negative/positive result is impossible here by construction. Ask this "
            "question of a signaling map instead."
        )
    return notes


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def pathway_graph(
    pathway: Annotated[
        str, Field(description="KEGG map id, e.g. 'hsa04151', 'eco00010', 'ko00010'.")
    ] = "",
    expand_members: Annotated[
        bool, Field(description="One node per gene instead of one per KEGG entry box.")
    ] = False,
    include_maplink: Annotated[
        bool, Field(description="Treat cross-map pointers as ordinary edges.")
    ] = False,
    max_nodes: Annotated[int, Field(ge=10, le=5000)] = _DEFAULT_MAX_NODES,
    max_edges: Annotated[int, Field(ge=10, le=20000)] = _DEFAULT_MAX_EDGES,
) -> str:
    """Fetch a KEGG pathway map as a normalized SIGNED DIRECTED GRAPH.

    This is what TogoMCP adds over raw KEGG: KGML is coordinate-heavy XML whose
    edges reference drawing-box ids rather than genes, and eight distinct traps
    make a naive read wrong (one entry box is a whole paralog family; complexes
    are indirection nodes; ECrel edges run through a metabolite; cross-map
    pointers are not interactions; a reaction's id is its ENZYME's box; the
    enzyme and compound layers are never joined; the same molecule is drawn
    several times with different ids). All of that is resolved here. Reactome RDF
    also carries signed regulation (61,819 BioPAX controlType statements), but its
    sign says whether an entity promotes a REACTION, whereas KGML's says whether
    one molecule ultimately up- or down-regulates another — the level this returns.

    RETURNS a JSON string of an object with `pathway` (id, title, org), `nodes`,
    `edges`, `groups` (protein complexes), `map_links` (pointers to other maps,
    deliberately NOT edges), `metabolic_gaps`, `signal_quality` and `stats`.
    Each edge carries `sign` (+1 activation, -1 inhibition, 0 UNKNOWN),
    `class` (PPrel/GErel/PCrel/ECrel/reaction/catalysis), `direct` (false for
    ECrel, which acts through a metabolite), `effects` and `mechanisms`.
    `signal_quality.signed_edge_fraction` says how much of the map is signed at
    all — READ IT BEFORE trusting any sign, since it ranges from 0.40 to 0.98
    across maps and is 0 for purely metabolic ones. `metabolic_gaps` is a
    RESULT, not an error: in an organism map KEGG keeps the reference layout and
    leaves the steps that organism LACKS as bare ortholog boxes, so this lists
    the metabolic steps the organism cannot perform. If the map exceeds
    `max_nodes`/`max_edges` the arrays are trimmed to the highest-degree
    subgraph and a `truncated` object states what was dropped; `stats` always
    describes the FULL map.

    RAISES ValueError on a malformed map id, when the map has no KGML at all
    (global/overview maps like 01100 do not), when `expand_members` would
    produce more than `max_edges` edges, and on any HTTP error — including
    HTTP 403/429 for the 3 requests/second rate limit, which must not be retried.

    Args:
        pathway: KEGG map id, with or without the `path:` prefix. An organism
            map ("hsa04151", "eco00010") gives that organism's genes; a `ko`
            map ("ko00010") is the reference superset of orthologs; `map00010`
            is the bare reference layout. For "which genes are in this pathway"
            use the ORGANISM map, not the ko map.
        expand_members: False (default) emits one node per KEGG entry box, which
            is what a relation actually connects; each node lists its `members`.
            True emits one node per gene — right for "is gene A upstream of gene
            B", but the edge count grows as the product of member counts, so it
            is refused when the estimate exceeds `max_edges`.
        include_maplink: False (default) keeps cross-map pointers out of the
            graph and reports them under `map_links`. Set True only if you
            specifically want them as edges, knowing they connect molecules
            across DIFFERENT maps and are not asserted interactions.
        max_nodes: Node ceiling before the returned arrays are trimmed to the
            highest-degree subgraph. Default 400.
        max_edges: Edge ceiling, applied the same way, and the cap that governs
            whether `expand_members` is allowed. Default 1200.

    Returns:
        str: JSON object as described above.
    """
    # Parse unexpanded first: it is the cheap way to estimate the member-expanded
    # fan-out before paying for it (an edge between two 20-member boxes becomes
    # 400 edges, and hsa05200 carries 564 identifiers over 311 edges).
    pathway, graph = await _load_graph(
        pathway, expand_members=False, include_maplink=include_maplink
    )

    if expand_members:
        size = {n["id"]: max(len(n["members"]), 1) for n in graph["nodes"]}
        estimate = sum(
            size.get(e["source"], 1) * size.get(e["target"], 1) for e in graph["edges"]
        )
        if estimate > max_edges:
            raise ValueError(
                f"expand_members=True would produce roughly {estimate} edges for "
                f"{pathway}, over the {max_edges} cap. One KEGG entry box is a whole "
                "paralog family, so expanding turns an edge between two boxes into "
                "the product of their member counts. Either keep expand_members="
                "False (each node still lists its `members`), narrow the question "
                "with kegg_pathway_neighborhood, or raise `max_edges` deliberately."
            )
        _, graph = await _load_graph(
            pathway, expand_members=True, include_maplink=include_maplink
        )

    gaps = metabolic_gaps(graph)
    stats = graph["stats"]

    nodes = graph["nodes"]
    edges = graph["edges"]
    truncated: dict[str, Any] | None = None
    if len(nodes) > max_nodes or len(edges) > max_edges:
        # Degrade to the best-connected core rather than an arbitrary prefix: the
        # hub nodes are what a caller asking about a pathway is actually after.
        degree: dict[str, int] = {}
        for e in edges:
            degree[e["source"]] = degree.get(e["source"], 0) + 1
            degree[e["target"]] = degree.get(e["target"], 0) + 1
        nodes = sorted(nodes, key=lambda n: -degree.get(n["id"], 0))[:max_nodes]
        kept = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in kept and e["target"] in kept][
            :max_edges
        ]
        truncated = {
            "reason": "map exceeded max_nodes/max_edges",
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "total_nodes": stats["node_count"],
            "total_edges": stats["edge_count"],
            "selection": "highest-degree nodes and the edges among them",
            "hint": (
                "`stats` still describes the full map. Use "
                "kegg_pathway_neighborhood for a focused view, or raise "
                "max_nodes/max_edges."
            ),
        }

    result: dict[str, Any] = {
        "pathway": {**graph["pathway"], "id": pathway},
        "signal_quality": _signal_quality(graph),
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
        "groups": graph["groups"],
        "map_links": graph["map_links"],
        "metabolic_gaps": gaps,
        "metabolic_gaps_note": (
            "Ortholog boxes this organism's map draws but has no gene for — the "
            "white boxes in KEGG's rendered image. These are metabolic steps the "
            "organism CANNOT perform, i.e. a result, not a parsing error. Empty "
            "for reference (ko/map) maps, which by definition lack nothing."
        ),
        "options": graph["options"],
    }
    if truncated:
        result["truncated"] = truncated
    return _bounded(result, note="lower max_nodes/max_edges or use a neighborhood query.")


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def pathway_neighborhood(
    pathway: Annotated[
        str, Field(description="KEGG map id, e.g. 'hsa04151'.")
    ] = "",
    seeds: Annotated[
        str | list[str],
        Field(description="Start point(s): gene symbol, 'hsa:5290', or a node id."),
    ] = "",
    direction: Annotated[
        str, Field(description="'downstream' | 'upstream' | 'both'.")
    ] = "downstream",
    depth: Annotated[int, Field(ge=1, le=6)] = 2,
    signed_only: Annotated[
        bool, Field(description="Traverse only activation/inhibition edges.")
    ] = False,
    limit: Annotated[int, Field(ge=1, le=2000)] = 300,
) -> str:
    """Walk up- or downstream from a gene/compound within one KEGG pathway map.

    Answers "what does this gene activate or inhibit, and how far", which needs
    KGML's signed relation subtypes. BioPAX controls can also express signed
    regulation, but of a REACTION rather than between two molecules, so reaching
    the same statement from an RDF query would mean inferring the net effect of
    each reaction yourself.

    RETURNS a JSON string of an object with `seeds` (the node ids the query
    resolved to), `unresolved` (seeds that matched NOTHING in this map — check
    it, since a typo or a gene absent from the map otherwise looks like a
    biological negative), `reached`, `edges`, and `signal_quality`. Each
    `reached` entry is `{"id", "label", "members", "distance", "net_sign"}`,
    where `net_sign` is the product of edge signs along the discovered path:
    +1 net activation, -1 net inhibition, and 0 meaning UNKNOWN — some edge on
    the path records only a mechanism (phosphorylation, binding) or is a
    metabolic step, so KGML never states the direction. Check
    `signal_quality.signed_edge_fraction` before reading signs at all: it is
    0.98 on hsa04151 but 0.40 on hsa04010 and 0 on metabolic maps. An empty
    `reached` with an empty `unresolved` means the seed is in the map but has no
    edges in that direction.

    RAISES ValueError on a malformed map id or direction, when the map has no
    KGML, and on any HTTP error — including HTTP 403/429 for the 3
    requests/second rate limit, which must not be retried.

    Args:
        pathway: KEGG map id, e.g. "hsa04151". Use the ORGANISM map for a
            question about that organism's genes.
        seeds: One or more start points. A gene symbol as drawn on the map
            ("AKT1"), a KEGG gene id ("hsa:5290"), a bare id ("5290"), a
            compound ("C00031") or a node id all resolve.
        direction: "downstream" (what the seed affects, the default),
            "upstream" (what affects the seed), or "both".
        depth: Maximum number of edges from the seed, in [1, 6]. Default 2.
            KEGG maps are dense — depth 3+ on a signaling map often reaches most
            of the graph and stops being informative.
        signed_only: If True, traverse ONLY edges that state activation or
            inhibition, so every `net_sign` is +1 or -1. This drops mechanism-
            only edges entirely, which on a map like hsa04010 (40% signed) is
            most of them — a smaller, more confident answer.
        limit: Maximum `reached` rows to return, in [1, 2000]. Default 300.

    Returns:
        str: JSON object as described above.
    """
    if direction not in ("downstream", "upstream", "both"):
        raise ValueError(
            f"Invalid direction {direction!r}. Valid: 'downstream' (what the seed "
            "affects), 'upstream' (what affects it), 'both'. Do not retry with the "
            "same value."
        )
    starts = _as_list(seeds)
    if not starts:
        raise ValueError(
            "Missing `seeds`. Pass at least one start point, e.g. seeds='AKT1' or "
            "seeds='hsa:5290'."
        )

    pathway, graph = await _load_graph(pathway)
    result = neighborhood(
        graph, starts, direction=direction, depth=depth, signed_only=signed_only
    )

    reached = result["reached"]
    payload: dict[str, Any] = {
        "pathway": {**graph["pathway"], "id": pathway},
        "seeds": result["seeds"],
        "unresolved": result["unresolved"],
        "direction": direction,
        "depth": depth,
        "signed_only": signed_only,
        "reached_count": len(reached),
        "reached": reached[:limit],
        "edges": result["edges"],
        "signal_quality": _signal_quality(graph),
    }
    if len(reached) > limit:
        payload["truncated"] = {
            "reason": "reached more nodes than `limit`",
            "returned": limit,
            "total": len(reached),
            "hint": "lower `depth`, set signed_only=True, or raise `limit`.",
        }
    if result["unresolved"]:
        payload["unresolved_note"] = (
            "These seeds matched no node in this map. That is a LOOKUP failure, "
            "not a biological finding — the gene may simply not be drawn on this "
            "map. Confirm membership with kegg_link(target=<org>, "
            "source=<pathway>) or pick a different map."
        )
    return _bounded(payload, note="lower `depth` or `limit`.")


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def pathway_paths(
    pathway: Annotated[
        str, Field(description="KEGG map id, e.g. 'hsa04151'.")
    ] = "",
    source: Annotated[
        str, Field(description="Start node: gene symbol, 'hsa:5290', or compound id.")
    ] = "",
    target: Annotated[
        str, Field(description="End node, same accepted forms as `source`.")
    ] = "",
    max_length: Annotated[int, Field(ge=1, le=12)] = 6,
    max_paths: Annotated[int, Field(ge=1, le=200)] = 20,
) -> str:
    """Enumerate the routes from one molecule to another within a KEGG map.

    Answers "HOW does A reach B, and is the net effect activating or
    inhibiting" — the mechanism behind a `kegg_pathway_neighborhood` hit. Needs
    KGML's signed relation subtypes, which state the net effect between molecules
    directly rather than per reaction as Reactome's BioPAX controls do.

    RETURNS a JSON string of an object with `source_nodes`/`target_nodes` (what
    the endpoints resolved to), `unresolved`, `path_count` and `paths`. Each path
    is `{"nodes": [{"id","label"}], "length", "net_sign", "edges": [...]}`, where
    `net_sign` is the product of the edge signs: +1 net activation, -1 net
    inhibition, 0 meaning UNKNOWN — some edge states only a mechanism
    (phosphorylation, binding) or is metabolic, so KGML never gives a direction.
    Each edge carries its `reaction` accession, which is what tells two parallel
    routes apart: the same node sequence via two different reactions is two
    genuinely different rows, not a duplicate.

    AN EMPTY `paths` HAS TWO DIFFERENT MEANINGS — check `unresolved` first. A
    non-empty `unresolved` is a LOOKUP failure (typo, or the molecule is not drawn
    on this map) and says nothing biological. An empty `unresolved` with no paths
    means both endpoints are present but no directed route of at most
    `max_length` edges connects them.

    ON METABOLIC MAPS, RAISE `max_length`. Compounds are joined through their
    enzyme (substrate → enzyme → product), so the hop count is roughly DOUBLE the
    number of reactions: glucose to pyruvate in glycolysis (~10 reactions) needs
    `max_length` around 12 and returns nothing at the default 6.

    RAISES ValueError on a malformed map id, a missing endpoint, or when the map
    has no KGML, and on any HTTP error — including HTTP 403/429 for the 3
    requests/second rate limit, which must not be retried.

    Args:
        pathway: KEGG map id, e.g. "hsa04151". Use the ORGANISM map for a
            question about that organism's genes.
        source: Start point. A gene symbol as drawn on the map ("PIK3CA"), a KEGG
            gene id ("hsa:5290"), a bare id ("5290"), a compound ("C00031") or a
            node id all resolve.
        target: End point, same forms.
        max_length: Maximum edges per path, in [1, 12]. Default 6 — right for
            signaling maps; see the metabolic note above. Cost grows steeply with
            this on dense maps, so raise it deliberately rather than by default.
        max_paths: Maximum paths to return, in [1, 200]. Default 20. Enumeration
            STOPS at this cap, so the result is not exhaustive when it is hit —
            `truncated` says when that happened.

    Returns:
        str: JSON object as described above.
    """
    if not source or not source.strip() or not target or not target.strip():
        raise ValueError(
            "`source` and `target` are both required, e.g. source='PIK3CA', "
            "target='MTOR'."
        )
    source, target = source.strip(), target.strip()

    pathway, graph = await _load_graph(pathway)

    # find_paths() returns [] both when an endpoint matched nothing and when the
    # endpoints are fine but unconnected. Those need different reactions from the
    # caller, so resolve them here and report the difference explicitly.
    source_nodes = resolve_seeds(graph, [source])
    target_nodes = resolve_seeds(graph, [target])
    unresolved = [
        label
        for label, hits in ((source, source_nodes), (target, target_nodes))
        if not hits
    ]

    paths = (
        find_paths(graph, source, target, max_length=max_length, max_paths=max_paths)
        if not unresolved
        else []
    )

    payload: dict[str, Any] = {
        "pathway": {**graph["pathway"], "id": pathway},
        "source": source,
        "target": target,
        "source_nodes": source_nodes,
        "target_nodes": target_nodes,
        "unresolved": unresolved,
        "max_length": max_length,
        "path_count": len(paths),
        "paths": paths,
        "signal_quality": _signal_quality(graph),
    }
    if unresolved:
        payload["unresolved_note"] = (
            f"{unresolved} matched no node in this map, so no path could be "
            "computed. That is a LOOKUP failure, not a biological finding — the "
            "molecule may simply not be drawn on this map. Confirm membership "
            "with kegg_link(target=<org>, source=<pathway>) or pick another map."
        )
    elif not paths:
        payload["no_path_note"] = (
            "Both endpoints are present on this map, but no directed route of at "
            f"most {max_length} edges connects them. On a METABOLIC map raise "
            "`max_length`: compounds are joined through their enzyme, so the hop "
            "count is about double the number of reactions."
        )
    if len(paths) >= max_paths:
        payload["truncated"] = {
            "reason": "enumeration stopped at `max_paths`",
            "returned": len(paths),
            "hint": "the path list is NOT exhaustive; raise `max_paths` to see more.",
        }
    return _bounded(payload, note="lower `max_length` or `max_paths`.")


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def pathway_cycles(
    pathway: Annotated[
        str, Field(description="KEGG map id, e.g. 'hsa04010'.")
    ] = "",
    feedback: Annotated[
        str, Field(description="Filter: '' (all) | 'negative' | 'positive' | 'unsigned'.")
    ] = "",
    max_length: Annotated[int, Field(ge=2, le=8)] = 5,
    max_cycles: Annotated[int, Field(ge=1, le=500)] = 50,
    include_reversible_artifacts: Annotated[
        bool, Field(description="Keep 2-cycles that are just a reversible reaction.")
    ] = False,
) -> str:
    """Find closed feedback loops drawn within a single KEGG pathway map.

    A directed cycle is a feedback loop, and the product of its edge signs says
    which kind: negative (self-limiting) or positive (self-reinforcing).

    EXPECT ZERO, AND READ ZERO CORRECTLY. Measured across six real maps this
    returns NO signed cycles at all: hsa04151 has no cycles despite being 98%
    signed; hsa04010 and hsa05200 have 4 and 3, every one of them `unsigned`. A
    KEGG map is a DRAWING of one process, not a complete interaction model, so a
    textbook loop usually has an arm missing — on hsa05200 `MDM2 -| TP53` is
    drawn but `TP53 -> MDM2` is not (its induction arm lives on another map), so
    p53/MDM2 cannot close here at any depth. An empty result therefore means
    "NOT DRAWN as a closed loop on THIS map", never "no feedback exists", and it
    is not evidence of anything biological.

    PREFER `kegg_pathway_paths` FOR ANY SIGNED CLAIM. Its `net_sign` needs only a
    path, not a closed cycle, so it survives the missing arm that defeats this
    tool — `kegg_pathway_paths(source="MDM2", target="TP53")` returns the -1
    inhibition that the cycle search cannot see.

    RETURNS a JSON string of an object with `counts` (cycles per feedback class,
    over the whole map), `cycle_count`, `cycles`, `interpretation` and
    `signal_quality`. Each cycle is `{"nodes": [{"id","label"}], "length",
    "net_sign", "feedback", "reactions", "artifact"}`. `feedback` is "negative"
    (net_sign -1), "positive" (+1) or "unsigned" (0) — and `unsigned` means
    UNKNOWN, not neutral: some edge in the loop records only a mechanism
    (phosphorylation, binding) or is metabolic, so KGML never states its
    direction.

    DO NOT USE THIS ON A METABOLIC MAP. Such a map has no signed edges at all, so
    negative/positive is impossible by construction, and it is dense with cycles
    that mean nothing: ko00010 yields over 5,000 at `max_length` 6, dominated by
    long unsigned ones. A reversible reaction A<->B is also emitted in both
    directions and so IS a 2-cycle by construction (82 of ko00010's 102
    two-cycles); those specific ones are dropped by default and counted under
    `artifacts_excluded`, but that is a small cleanup — 69 of 5,001 — and does
    NOT make the result meaningful. Ask this question of a signaling map.

    THE `feedback` FILTER IS APPLIED AFTER THE `max_cycles` CAP, so on a dense map
    the cap can fill with cycles the filter then removes, leaving a zero that is
    not real. `truncated` is present whenever the cap was reached — if it is,
    raise `max_cycles` before concluding anything.

    RAISES ValueError on a malformed map id or filter value, when the map has no
    KGML, and on any HTTP error — including HTTP 403/429 for the 3
    requests/second rate limit, which must not be retried.

    Args:
        pathway: KEGG map id, e.g. "hsa04010". Signaling maps are the only place
            this is informative; metabolic maps are unsigned throughout.
        feedback: Keep only one class: "negative", "positive" or "unsigned".
            Empty (default) returns all; `counts` always describes the whole map.
        max_length: Maximum nodes in a cycle, in [2, 8]. Default 5.
        max_cycles: Maximum cycles to collect BEFORE filtering, in [1, 500].
            Default 50.
        include_reversible_artifacts: Keep the 2-cycles that are just one
            reversible reaction drawn both ways. Default False — they are a
            representation artifact, not feedback, and they swamp metabolic maps.

    Returns:
        str: JSON object as described above.
    """
    if feedback and feedback not in ("negative", "positive", "unsigned"):
        raise ValueError(
            f"Invalid feedback filter {feedback!r}. Valid: 'negative', 'positive', "
            "'unsigned', or empty for all. Do not retry with the same value."
        )

    pathway, graph = await _load_graph(pathway)
    found = find_cycles(graph, max_length=max_length, max_cycles=max_cycles)
    cap_reached = len(found) >= max_cycles

    artifacts = [c for c in found if c.get("artifact")]
    cycles = found if include_reversible_artifacts else [
        c for c in found if not c.get("artifact")
    ]

    counts = {"negative": 0, "positive": 0, "unsigned": 0}
    for c in cycles:
        counts[c["feedback"]] = counts.get(c["feedback"], 0) + 1

    selected = [c for c in cycles if c["feedback"] == feedback] if feedback else cycles

    payload: dict[str, Any] = {
        "pathway": {**graph["pathway"], "id": pathway},
        "feedback_filter": feedback or "all",
        "max_length": max_length,
        "counts": counts,
        "artifacts_excluded": 0 if include_reversible_artifacts else len(artifacts),
        "cycle_count": len(selected),
        "cycles": selected,
        "interpretation": _cycle_interpretation(
            graph, counts, selected, len(artifacts) if not include_reversible_artifacts else 0
        ),
        "signal_quality": _signal_quality(graph),
    }
    if cap_reached:
        payload["truncated"] = {
            "reason": "enumeration stopped at `max_cycles`",
            "collected": len(cycles),
            "hint": (
                "the cycle list is NOT exhaustive. The `feedback` filter runs "
                "AFTER this cap, so an empty filtered result here does not mean "
                "the map has none — raise `max_cycles` and look again."
            ),
        }
    return _bounded(payload, note="lower `max_length` or `max_cycles`.")


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def link(
    target: Annotated[
        str, Field(description="Target database, e.g. 'pathway', 'compound', 'pubmed'.")
    ] = "",
    source: Annotated[
        str,
        Field(description="Source database ('hsa') or entry id(s) ('hsa:10458')."),
    ] = "",
    limit: Annotated[int, Field(ge=1, le=5000)] = 1000,
) -> str:
    """Find KEGG entries related to other KEGG entries (gene↔pathway, ↔compound, ↔pubmed).

    This is how you get a pathway's gene list, a gene's pathways, the compounds
    in a reaction, or the literature behind an entry, without parsing any entry
    text. For "which genes are in pathway X", call it as
    `target=<organism code>, source=<pathway id>`.

    RETURNS a JSON string of a bare array of `{"source": str, "target": str}`
    pairs, e.g. `[{"source": "hsa:10458", "target": "path:hsa04810"}]`. Empty
    and non-empty results share the same `[...]` shape; an empty array means
    KEGG has no such links (it answers with an empty HTTP 200, not a 404). These
    are KEGG-namespaced IDs and are not RDF-resolvable — pass them through
    `kegg_conv` first.

    RAISES ValueError on an unknown database and on any HTTP error, including
    HTTP 403/429 for the 3 requests/second rate limit, which must not be retried.

    Args:
        target: The database to link TO: pathway, brite, module, ko, genome,
            compound, glycan, reaction, rclass, enzyme, network, variant,
            disease, drug, dgroup, pubmed, atc, jtc, ndc, yj, or an organism
            code such as "hsa".
        source: Either a database name (links EVERY entry in it — large; e.g.
            target="pathway", source="hsa" returns all human gene-pathway pairs)
            or specific entry id(s) such as "hsa:10458" or "path:hsa04151".
            Multiple ids may be given as a list or a comma/space-separated
            string.
        limit: Maximum pairs to return, in [1, 5000]. Default 1000. KEGG applies
            no server-side limit, so a whole-database link is trimmed here.

    Returns:
        str: JSON array of `{"source", "target"}` pairs.
    """
    target = _check_path_token(target, label="target")
    if target not in _LINK_DATABASES and not _is_org(target):
        raise ValueError(
            f"Unknown link target database {target!r}. Valid: "
            f"{', '.join(sorted(_LINK_DATABASES))}, or an organism code such as "
            "'hsa'. Do not retry with the same value."
        )

    sources = [_check_path_token(s, label="source") for s in _as_list(source)]
    if not sources:
        raise ValueError(
            "Missing `source`. Pass a database name (e.g. 'hsa') or entry id(s) "
            "(e.g. 'path:hsa04151')."
        )

    text = await _kegg_get(
        f"/link/{target}/{'+'.join(sources)}", context="KEGG link"
    )
    pairs = [{"source": a, "target": b} for a, b in _parse_tsv_pairs(text)][:limit]
    return _bounded(pairs, note="link specific entries instead of a whole database.")


@kegg_mcp.tool(annotations=READ_ONLY_TOOL)
async def conv(
    target: Annotated[
        str, Field(description="Target namespace, e.g. 'uniprot', 'chebi', 'hsa'.")
    ] = "",
    source: Annotated[
        str, Field(description="Source namespace or entry id(s), e.g. 'hsa:10458'.")
    ] = "",
    limit: Annotated[int, Field(ge=1, le=5000)] = 1000,
) -> str:
    """Convert KEGG IDs to/from UniProt, NCBI Gene/Protein, ChEBI and PubChem.

    THIS IS THE BRIDGE OUT OF KEGG. KEGG-namespaced IDs are not RDF-resolvable,
    so any KEGG result you want to join against a life-science knowledge graph
    must be converted here first. Conversely, convert an external identifier to
    KEGG before calling the other KEGG tools.

    Two disjoint identifier families are supported, and mixing them is an error:
    GENES convert between an organism code (hsa, eco, mmu …) and ncbi-geneid,
    ncbi-proteinid or uniprot; CHEMICALS convert between compound, drug or
    glycan and pubchem or chebi.

    RETURNS a JSON string of a bare array of
    `{"source", "target", "source_id", "target_id"}`, e.g.
    `[{"source": "hsa:10458", "target": "up:P50570", "source_id": "10458",
       "target_id": "P50570"}]`. `source_id`/`target_id` are the same values with
    KEGG's namespace prefix stripped — those are the forms downstream query and
    ID-conversion tools accept; the prefixed forms are what the KEGG tools take.
    Empty and non-empty results share the `[...]` shape, and an empty array means
    no mapping exists (KEGG answers with an empty HTTP 200, not a 404).

    RAISES ValueError when the two sides belong to different identifier families
    or an unknown namespace is given, and on any HTTP error — including HTTP
    403/429 for the 3 requests/second rate limit, which must not be retried.

    Args:
        target: Namespace to convert TO. Genes: an organism code ("hsa"),
            "ncbi-geneid", "ncbi-proteinid", "uniprot". Chemicals: "compound",
            "drug", "glycan", "pubchem", "chebi".
        source: Either the namespace to convert FROM (converts the WHOLE
            namespace, e.g. target="hsa", source="uniprot" maps all human
            UniProt accessions) or specific entry id(s) — "hsa:10458",
            "up:P50570", "cpd:C00031", "chebi:15377". Multiple ids may be given
            as a list or a comma/space-separated string.
        limit: Maximum pairs to return, in [1, 5000]. Default 1000. A
            whole-namespace conversion is trimmed client-side.

    Returns:
        str: JSON array of `{"source", "target", "source_id", "target_id"}`.
    """
    target = _check_path_token(target, label="target")
    sources = [_check_path_token(s, label="source") for s in _as_list(source)]
    if not sources:
        raise ValueError(
            "Missing `source`. Pass a namespace (e.g. 'uniprot') or entry id(s) "
            "(e.g. 'hsa:10458')."
        )

    def _family(token: str) -> str | None:
        """Which identifier family a bare NAMESPACE belongs to (None if it is an entry)."""
        bare = token.split(":", 1)[0] if ":" in token else token
        if ":" in token:
            # An entry id: classify by its prefix, but do not reject unknowns —
            # KEGG carries many prefixes and the API is the authority.
            if bare in _CONV_CHEM_KEGG or bare in _CONV_CHEM_OUTSIDE or bare in (
                "cpd", "dr", "gl"
            ):
                return "chemical"
            if bare in _CONV_GENE_OUTSIDE or bare in ("up", "ncbi-geneid") or _is_org(bare):
                return "gene"
            return None
        if token in _CONV_CHEM_KEGG or token in _CONV_CHEM_OUTSIDE:
            return "chemical"
        if token in _CONV_GENE_OUTSIDE or _is_org(token):
            return "gene"
        return None

    target_family = _family(target)
    if target_family is None:
        raise ValueError(
            f"Unknown conversion namespace {target!r}. Genes: an organism code "
            f"(e.g. 'hsa'), {', '.join(sorted(_CONV_GENE_OUTSIDE))}. Chemicals: "
            f"{', '.join(sorted(_CONV_CHEM_KEGG))}, "
            f"{', '.join(sorted(_CONV_CHEM_OUTSIDE))}. Do not retry with the same value."
        )

    source_families = {f for f in (_family(s) for s in sources) if f is not None}
    if source_families and target_family not in source_families:
        raise ValueError(
            f"Cannot convert between identifier families: target {target!r} is a "
            f"{target_family} namespace but source {source!r} is "
            f"{'/'.join(sorted(source_families))}. KEGG /conv maps genes to genes "
            "(organism code <-> ncbi-geneid / ncbi-proteinid / uniprot) and "
            "chemicals to chemicals (compound / drug / glycan <-> pubchem / chebi). "
            "Do not retry with the same pair."
        )

    text = await _kegg_get(
        f"/conv/{target}/{'+'.join(sources)}", context="KEGG conv"
    )

    def _bare(token: str) -> str:
        return token.split(":", 1)[1] if ":" in token else token

    pairs = [
        {"source": a, "target": b, "source_id": _bare(a), "target_id": _bare(b)}
        for a, b in _parse_tsv_pairs(text)
    ][:limit]
    return _bounded(pairs, note="convert specific entries instead of a whole namespace.")

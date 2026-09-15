"""PubCaseFinder REST wrapper — phenotype-driven ranking and case reports.

WHY A MOUNTED SUB-SERVER, AND WHY ONLY TWO TOOLS
------------------------------------------------
PubCaseFinder (DBCLS) also ships as RDF (`database="pubcasefinder"`), so most of
its REST API is SPARQList over data `run_sparql` already reaches. Two things are
not in the RDF and cannot be rebuilt from it:

* the RANKING — an information-content-weighted similarity between a set of HPO
  terms and every disease's (or gene's) phenotype profile, computed over the HPO
  hierarchy. A SPARQL "diseases annotated with all of these terms" query returns
  an unordered set and drops every partial match; that is not the same answer.
* CASE REPORTS per MONDO disease — PubMed case reports selected by text mining,
  plus Japanese J-STAGE articles. The selection is not MeSH-based: of the 1,615
  Marfan syndrome reports also present in the pubmed RDF, 507 carry no Marfan
  syndrome MeSH heading (2026-09-15), and a MeSH match on the pubmed RDF needs a
  STRSTARTS scan over descriptor+qualifier IRIs that did not finish in 200 s.

Neither is a keyword search in front of a SPARQL database, so these do not belong
with the flat `search_*` wrappers in api_tools.py.

MODULE CONVENTIONS (same as togovar.py / kegg.py — keep uniform)
----------------------------------------------------------------
* Raise `ValueError` on bad parameters AND on HTTP error
  (`raise_for_status_with_body`). Never return an `{"error": ...}` payload.
* Every tool carries `annotations=READ_ONLY_TOOL`.

ENDPOINT PATHS — READ BEFORE "FIXING" THEM
------------------------------------------
The published OpenAPI spec (https://pubcasefinder.dbcls.jp/api) documents the
ranking as `/api/pcf_get_ranked_list`. It returned HTTP 404 during a service
outage in 2026-09 and 200 again once the service was back (2026-09-15), but it
answers with every candidate plus its full description: ~10 MB and ~11 s for a
single HPO term. The PubCaseFinder web app itself calls
`/pcf_get_ranking_by_hpo_id` (no `/api` prefix, `phenotype=` rather than
`hpo_id=`), which returns compact rows (~1.8 MB, ~1.5 s for two terms); that is
what is used here, with names fetched separately for the returned rows only. If
it starts failing, compare with the web app's `pcf-content.js` before switching
to the documented path.

RATE LIMIT — A SHARED, SMALL BUDGET
-----------------------------------
DBCLS asks API users to stay within 10 requests/minute, 100/hour and 1,000/day.
On the HTTP deployment every TogoMCP user shares ONE client address, so those
numbers are a budget for the whole server, not per user. Hence:

* a process-wide sliding-window limiter (`_RATE_WINDOWS`) that waits briefly for
  the per-minute window and otherwise refuses with a ValueError rather than
  exceeding the published limits;
* in-process caches for rankings, entity names and case reports, since an agent
  typically re-asks the same question while refining it, and every cache hit is
  a request not spent.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import re
import time
from collections import OrderedDict, deque
from typing import Annotated, Any, Literal

import httpx
from pydantic import Field

from .server import *


def _user_agent() -> str:
    try:
        from importlib.metadata import version

        return f"TogoMCP/{version('togo-mcp')} (+https://togomcp.rdfportal.org)"
    except Exception:
        return "TogoMCP (+https://togomcp.rdfportal.org)"


_BASE_URL = "https://pubcasefinder.dbcls.jp"

# A gene-target ranking took 14.5 s on 2026-09-15; the disease targets ~2 s.
_client = httpx.AsyncClient(
    base_url=_BASE_URL,
    timeout=60.0,
    headers={"Accept": "application/json", "User-Agent": _user_agent()},
)


def _close_client():
    """Close the shared httpx client on interpreter shutdown."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_client.aclose())
    except RuntimeError:
        # No running loop: the loop owning the sockets is already closed. The OS
        # reclaims them; opening a new loop here only raises "Event loop is closed".
        pass


atexit.register(_close_client)

pubcasefinder_mcp = FastMCP("PubCaseFinder API server")


# --------------------------------------------------------------------------- #
# Rate limiting — process-wide sliding windows.
# --------------------------------------------------------------------------- #
# (window seconds, max requests, label). Published limits, 2026-09-15.
_RATE_WINDOWS: tuple[tuple[float, int, str], ...] = (
    (60.0, 10, "10 requests per minute"),
    (3600.0, 100, "100 requests per hour"),
    (86400.0, 1000, "1,000 requests per day"),
)
# Waiting longer than this for the per-minute window turns into an error: a tool
# call that silently hangs for a minute looks like a dead server to the caller.
_MAX_RATE_WAIT = 20.0

_rate_lock = asyncio.Lock()
_request_times: deque[float] = deque()


def _rate_wait(now: float) -> tuple[float, str | None]:
    """Seconds until one more request fits every window, and the binding window.

    Pure over `_request_times`, so it is unit-testable without sleeping.
    """
    horizon = max(w for w, _, _ in _RATE_WINDOWS)
    while _request_times and now - _request_times[0] >= horizon:
        _request_times.popleft()
    wait, binding = 0.0, None
    for window, cap, label in _RATE_WINDOWS:
        recent = [t for t in _request_times if now - t < window]
        if len(recent) >= cap:
            # The slot frees when the oldest request still inside the window ages out.
            free_at = recent[len(recent) - cap] + window
            if free_at - now > wait:
                wait, binding = free_at - now, label
    return wait, binding


async def _acquire_slot() -> None:
    async with _rate_lock:
        wait, binding = _rate_wait(time.monotonic())
        if wait > _MAX_RATE_WAIT:
            raise ValueError(
                f"PubCaseFinder rate budget exhausted ({binding}; the limit is shared by "
                f"every user of this TogoMCP server). Next request possible in about "
                f"{int(wait // 60)} min {int(wait % 60)} s. Do not retry immediately. "
                "Disease-phenotype and gene-disease annotations themselves can still be "
                "queried with run_sparql(database='pubcasefinder')."
            )
        if wait > 0:
            await asyncio.sleep(wait)
        _request_times.append(time.monotonic())


async def _pcf_get(path: str, params: dict[str, str], *, context: str) -> Any:
    """One rate-limited GET against PubCaseFinder, returning parsed JSON."""
    await _acquire_slot()
    try:
        response = await _client.get(path, params=params)
    except httpx.TimeoutException as exc:
        raise ValueError(
            f"{context}: PubCaseFinder did not answer within 60 s. Gene-target rankings "
            "are the slowest; retry at most once, later."
        ) from exc
    except httpx.HTTPError as exc:
        raise ValueError(
            f"{context}: could not reach {_BASE_URL} ({exc.__class__.__name__}: {exc})."
        ) from exc
    if response.status_code in (403, 429):
        raise ValueError(
            f"{context}: HTTP {response.status_code} from PubCaseFinder — rate limit or "
            "access restriction. Do NOT retry: repeated calls are what get the server's "
            "address blocked."
        )
    raise_for_status_with_body(
        response,
        context=context,
        client_error_hint="Check the identifiers. Do not retry the same request unchanged.",
    )
    try:
        return response.json()
    except ValueError as exc:
        raise ValueError(
            f"{context}: PubCaseFinder returned non-JSON ({response.text[:200]!r})."
        ) from exc


# --------------------------------------------------------------------------- #
# Caches — LRU with a TTL. Upstream data changes with releases, not by the hour.
# --------------------------------------------------------------------------- #
_CACHE_TTL = 24 * 3600.0


class _TTLCache:
    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()

    def get(self, key: Any) -> Any:
        hit = self._data.get(key)
        if hit is None:
            return None
        stamp, value = hit
        if time.monotonic() - stamp > _CACHE_TTL:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def put(self, key: Any, value: Any) -> None:
        self._data[key] = (time.monotonic(), value)
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


# A ranking is the full candidate list (8,288 OMIM rows, ~1.9 MB of JSON), so few.
_ranking_cache = _TTLCache(16)
_record_cache = _TTLCache(4096)   # (kind, id) -> record dict, or {} if upstream has none
_case_report_cache = _TTLCache(64)


# --------------------------------------------------------------------------- #
# Identifier normalization (pure)
# --------------------------------------------------------------------------- #
_HPO_RE = re.compile(r"^(?:.*[/#])?(?:HP[:_])?(\d{7})$", re.IGNORECASE)
_MONDO_RE = re.compile(r"^(?:.*[/#])?(?:MONDO[:_])?(\d{7})$", re.IGNORECASE)

TARGETS = ("omim", "orphanet", "gene")
MAX_PHENOTYPES = 100
MAX_LIMIT = 100


def _as_list(value: str | list[str]) -> list[str]:
    """Split a comma/whitespace-separated string (or a list of them) into tokens."""
    items = [value] if isinstance(value, str) else list(value)
    return [tok for item in items for tok in re.split(r"[,\s]+", str(item)) if tok]


def _normalize_hpo_ids(value: str | list[str]) -> list[str]:
    """'HP:0001166' / 'HP_0001166' / '0001166' / an obo IRI -> 'HP:0001166'.

    Order-preserving and de-duplicated. Raises on anything that is not an HPO
    identifier, because upstream answers an unrecognized ID with a silent `[]`.
    """
    tokens = _as_list(value)
    if not tokens:
        raise ValueError(
            "Missing phenotypes. Pass HPO IDs via `hpo_ids`, e.g. "
            "['HP:0001166', 'HP:0001083']. Resolve phenotype names to HPO IDs first "
            "(OLS4, or run_sparql on database='ontology' / 'pubcasefinder')."
        )
    out: list[str] = []
    bad: list[str] = []
    for tok in tokens:
        m = _HPO_RE.match(tok.strip())
        if not m:
            bad.append(tok)
            continue
        norm = f"HP:{m.group(1)}"
        if norm not in out:
            out.append(norm)
    if bad:
        raise ValueError(
            f"Not HPO identifiers: {bad}. Expected the form HP:0001166 (7 digits). "
            "Do not retry with the same values."
        )
    if len(out) > MAX_PHENOTYPES:
        raise ValueError(f"At most {MAX_PHENOTYPES} HPO IDs per call; got {len(out)}.")
    return out


def _normalize_mondo_id(value: str) -> str:
    """'MONDO:0007947' / 'MONDO_0007947' / '0007947' / an IRI -> 'MONDO:0007947'."""
    token = (value or "").strip()
    if not token:
        raise ValueError(
            "Missing disease. Pass a MONDO ID via `mondo_id`, e.g. 'MONDO:0007947'. "
            "pubcasefinder_rank_by_phenotypes returns `mondo_ids` for each disease."
        )
    m = _MONDO_RE.match(token)
    if not m:
        raise ValueError(
            f"Not a MONDO identifier: {token!r}. Expected MONDO:0007947 (7 digits). "
            "Map OMIM/Orphanet IDs to MONDO first (e.g. rdfs:seeAlso in "
            "database='pubcasefinder', or togoid_convertId). Do not retry the same value."
        )
    return f"MONDO:{m.group(1)}"


def _split_ids(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [tok for tok in re.split(r"[,\s]+", str(value)) if tok]


# --------------------------------------------------------------------------- #
# Projection (pure)
# --------------------------------------------------------------------------- #
def _project_candidate(row: dict[str, Any], record: dict[str, Any], target: str) -> dict[str, Any]:
    """One ranking row + its entity record -> the row this tool returns."""
    out: dict[str, Any] = {
        "rank": row.get("rank"),
        "score": round(float(row.get("score") or 0.0), 4),
        "id": row.get("id"),
    }
    if target == "gene":
        out["gene_symbol"] = record.get("hgnc_gene_symbol")
        out["name_en"] = record.get("full_name")
        out["hgnc_id"] = record.get("hgnc_gene_id")
        out["mondo_ids"] = _split_ids(record.get("mondo_id"))
    else:
        prefix = "omim" if target == "omim" else "orpha"
        out["name_en"] = record.get(f"{prefix}_disease_name_en")
        out["name_ja"] = record.get(f"{prefix}_disease_name_ja")
        out["mondo_ids"] = _split_ids(record.get("mondo_id"))
        out["gene_ids"] = _split_ids(row.get("gene_id")) or _split_ids(record.get("ncbi_gene_id"))
        out["gene_symbols"] = _split_ids(record.get("hgnc_gene_symbol"))
        inheritance = record.get("inheritance_en")
        out["inheritance"] = sorted(inheritance.values()) if isinstance(inheritance, dict) else []
    out["matched_hpo_ids"] = _split_ids(row.get("matched_hpo_id"))
    out["annotated_hpo_count"] = row.get("annotation_hp_num")
    return out


def _cutoff_ties(ranking: list[dict[str, Any]], limit: int) -> dict[str, Any] | None:
    """If the row at the cutoff shares its rank with rows beyond it, say how many."""
    if limit >= len(ranking) or limit == 0:
        return None
    last_rank = ranking[limit - 1].get("rank")
    beyond = sum(1 for r in ranking[limit:] if r.get("rank") == last_rank)
    return {"rank": last_rank, "tied_rows_not_returned": beyond} if beyond else None


def _project_case_report(row: dict[str, Any], lang: str) -> dict[str, Any]:
    year = row.get("pyear")
    try:
        year = int(year)
    except (TypeError, ValueError):
        pass
    if lang == "en":
        pmid = row.get("id")
        return {
            "pmid": str(pmid) if pmid is not None else None,
            "title": row.get("title"),
            "journal": row.get("journal"),
            "year": year,
            "url": row.get("url"),
        }
    # Japanese rows carry display placeholders ("Go to J-STAGE") in `id` and
    # pre-rendered <a><img> HTML; keep only the data.
    return {
        "title": row.get("title"),
        "journal": row.get("journal"),
        "year": year,
        "jstage_url": row.get("url") or None,
        "jglobal_url": row.get("url_jglobal") or None,
    }


# --------------------------------------------------------------------------- #
# Upstream fetches (cached)
# --------------------------------------------------------------------------- #
_RECORD_ENDPOINTS = {
    # kind: (path, query parameter)
    "hpo": ("/api/pcf_get_hpo_data_by_hpo_id", "hpo_id"),
    "omim": ("/api/pcf_get_omim_data_by_omim_id", "omim_id"),
    "orphanet": ("/api/pcf_get_orpha_data_by_orpha_id", "orpha_id"),
    "gene": ("/api/pcf_get_gene_data_by_ncbi_gene_id", "ncbi_gene_id"),
}


async def _records(kind: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    """Batch-fetch entity records (names etc.), one upstream call for all misses.

    Upstream silently omits IDs it does not know; those are cached as `{}` so the
    caller can tell "unknown" from "not fetched".
    """
    found: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for i in ids:
        cached = _record_cache.get((kind, i))
        if cached is None:
            missing.append(i)
        else:
            found[i] = cached
    if missing:
        path, param = _RECORD_ENDPOINTS[kind]
        data = await _pcf_get(
            path, {param: ",".join(missing)}, context=f"PubCaseFinder {kind} records"
        )
        data = data if isinstance(data, dict) else {}
        for i in missing:
            record = data.get(i) if isinstance(data.get(i), dict) else {}
            _record_cache.put((kind, i), record)
            found[i] = record
    return found


async def _ranking(target: str, hpo_ids: list[str]) -> list[dict[str, Any]]:
    key = (target, tuple(sorted(hpo_ids)))
    cached = _ranking_cache.get(key)
    if cached is not None:
        return cached
    data = await _pcf_get(
        "/pcf_get_ranking_by_hpo_id",
        {"target": target, "phenotype": ",".join(hpo_ids)},
        context="PubCaseFinder ranking",
    )
    rows = data if isinstance(data, list) else []
    _ranking_cache.put(key, rows)
    return rows


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@pubcasefinder_mcp.tool(annotations=READ_ONLY_TOOL)
async def rank_by_phenotypes(
    hpo_ids: Annotated[
        str | list[str],
        Field(description="A patient's HPO phenotype IDs, e.g. ['HP:0001166', 'HP:0001083']."),
    ],
    target: Annotated[
        Literal["omim", "orphanet", "gene"],
        Field(description="Rank OMIM diseases, Orphanet diseases, or genes."),
    ] = "omim",
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = 20,
) -> str:
    """Rank rare diseases (or genes) by how well they match a set of HPO phenotypes.

    PubCaseFinder's differential-diagnosis ranking: an information-content-weighted
    similarity between the given phenotypes and every OMIM disease, Orphanet disease
    or gene profile, computed over the HPO hierarchy — a disease annotated with a
    more specific child term still matches. SPARQL cannot reproduce this: an "all of
    these phenotypes" query returns an unordered set and drops partial matches.
    It is decision support over annotations, NOT a diagnosis.

    RETURNS a JSON object string: `target`; `query_phenotypes` (each
    `{hpo_id, name_en, name_ja}` — check these are the phenotypes you meant);
    `unrecognized_hpo_ids` (IDs PubCaseFinder does not know, ignored by the ranking:
    usually obsolete terms); `total_count` (candidates scored); `returned`;
    `has_more`; `ties_at_cutoff` (`{rank, tied_rows_not_returned}` when the last
    returned rank continues past `limit`, else null); and `results`, best first.
    Disease rows: `{rank, score, id ("OMIM:154700"/"ORPHA:558"), name_en, name_ja,
    mondo_ids, gene_ids ("GENEID:2200"), gene_symbols, inheritance, matched_hpo_ids,
    annotated_hpo_count}`. Gene rows: `{rank, score, id ("GENEID:2200"), gene_symbol,
    name_en, hgnc_id, mondo_ids, matched_hpo_ids, annotated_hpo_count}`.
    `score` is normalized so the best match is 1.0; ranks are competition ranks, so
    several rows can share rank 1. `matched_hpo_ids` are the candidate's annotated
    terms that matched, which may be descendants of the query terms. Pass a
    `mondo_ids` entry to pubcasefinder_get_case_reports for literature.

    Counts differ from database='pubcasefinder' RDF (different release): do not
    compare `annotated_hpo_count` with SPARQL counts.

    RAISES ValueError on a malformed HPO ID, when NONE of the IDs is recognized,
    when the shared PubCaseFinder rate budget (10/min, 100/h, 1,000/day for the whole
    server) is exhausted, and on any HTTP error. Each call costs up to 3 upstream
    requests (names, ranking, candidate names); repeated calls are cached.

    Args:
        hpo_ids: HPO IDs as a list or a comma/space-separated string. Accepts
            HP:0001166, HP_0001166, 0001166 or the obo IRI. At most 100.
        target: "omim" (default, ~8,300 diseases), "orphanet" (~3,900 diseases) or
            "gene" (~4,900 genes; slowest, up to ~15 s uncached).
        limit: Rows to return, in [1, 100]. Default 20.
    """
    if target not in TARGETS:
        raise ValueError(f"Unknown target {target!r}. Valid: {', '.join(TARGETS)}.")
    ids = _normalize_hpo_ids(hpo_ids)

    phenotypes = await _records("hpo", ids)
    known = [i for i in ids if phenotypes.get(i)]
    unrecognized = [i for i in ids if not phenotypes.get(i)]
    if not known:
        raise ValueError(
            f"None of {ids} is a phenotype PubCaseFinder knows (obsolete or nonexistent "
            "HPO IDs), so the ranking would be empty. Look up current IDs (OLS4 'hp', or "
            "run_sparql on database='ontology') and do not retry the same IDs."
        )

    ranking = await _ranking(target, known)
    top = ranking[:limit]
    records = await _records(target, [str(r.get("id")) for r in top if r.get("id")])

    result = {
        "target": target,
        "query_phenotypes": [
            {
                "hpo_id": i,
                "name_en": phenotypes[i].get("name_en"),
                "name_ja": phenotypes[i].get("name_ja"),
            }
            for i in known
        ],
        "unrecognized_hpo_ids": unrecognized,
        "total_count": len(ranking),
        "returned": len(top),
        "has_more": len(ranking) > len(top),
        "ties_at_cutoff": _cutoff_ties(ranking, limit),
        "results": [
            _project_candidate(r, records.get(str(r.get("id"))) or {}, target) for r in top
        ],
    }
    return json.dumps(result, ensure_ascii=False)


@pubcasefinder_mcp.tool(annotations=READ_ONLY_TOOL)
async def get_case_reports(
    mondo_id: Annotated[
        str, Field(description="MONDO disease ID, e.g. 'MONDO:0007947' (Marfan syndrome).")
    ],
    lang: Annotated[
        Literal["en", "ja"],
        Field(description="'en' = PubMed case reports; 'ja' = Japanese J-STAGE articles."),
    ] = "en",
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = 20,
) -> str:
    """List published case reports for a rare disease, newest first.

    PubCaseFinder's curated case-report index per MONDO disease. `lang="en"` lists
    PubMed case reports; `lang="ja"` lists Japanese-language articles from J-STAGE
    (with J-GLOBAL links), which no other TogoMCP source covers. The selection is
    text-mining based, so it is NOT reproducible with a MeSH query over the pubmed
    RDF (for Marfan syndrome, 507 of the 1,615 reports also in that RDF carry no
    Marfan syndrome MeSH heading).

    RETURNS a JSON object string: `{mondo_id, lang, total_count, returned, has_more,
    results}`. English rows are `{pmid, title, journal, year, url}`; Japanese rows are
    `{title, journal, year, jstage_url, jglobal_url}`. `total_count` 0 means no
    reports are indexed for that ID — upstream answers an unknown MONDO ID the same
    way, so confirm the ID (e.g. from pubcasefinder_rank_by_phenotypes `mondo_ids`)
    before reporting "no case reports".

    RAISES ValueError on a malformed MONDO ID, when the shared PubCaseFinder rate
    budget (10/min, 100/h, 1,000/day for the whole server) is exhausted, and on any
    HTTP error. Repeated calls are cached.

    Args:
        mondo_id: MONDO ID as MONDO:0007947, MONDO_0007947, 0007947 or the IRI.
        lang: "en" (PubMed, default) or "ja" (J-STAGE).
        limit: Rows to return, in [1, 100]. Default 20.
    """
    if lang not in ("en", "ja"):
        raise ValueError(f"Unknown lang {lang!r}. Valid: 'en', 'ja'.")
    mondo = _normalize_mondo_id(mondo_id)

    key = (mondo, lang)
    rows = _case_report_cache.get(key)
    if rows is None:
        params = {"id": mondo}
        if lang == "ja":
            params["lang"] = "ja"
        data = await _pcf_get("/api/pcf_get_case_report", params, context="PubCaseFinder case reports")
        rows = data if isinstance(data, list) else []
        _case_report_cache.put(key, rows)

    top = rows[:limit]
    return json.dumps(
        {
            "mondo_id": mondo,
            "lang": lang,
            "total_count": len(rows),
            "returned": len(top),
            "has_more": len(rows) > len(top),
            "results": [_project_case_report(r, lang) for r in top],
        },
        ensure_ascii=False,
    )

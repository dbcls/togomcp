"""Usage-log analysis for TogoMCP.

Reads the JSONL written by ``_ToolCallLogger`` (see :mod:`togo_mcp.server`),
aggregates monthly tool-call and SPARQL statistics, and powers the ``/stats``
dashboard. Pure standard library; reading the log has no effect on the running
MCP server.

Privacy: aggregation only ever *counts*. Raw ``args``, ``ip``, and query text
never appear in any output produced here — only derived categories and tallies.
That holds even when the log itself carries raw client IPs (``TOGOMCP_LOG_RAW_IP``):
the reach column is ``len(distinct addresses)``, never the addresses. Reading a
raw address is what ``/stats/log`` is for.

What the collection layer records today (per JSONL line):
  ts, tool, args, status (ok|error), elapsed_ms, session_id/request_id/...,
  ip_hash (plus raw ip when opted in), error_class, error_message, and for
  SPARQL an ``extra`` dict with
  endpoint_url, query_sha256, sparql_status (ok|timeout|endpoint_unresponsive|
  pool_exhausted|network_error|http_4xx|http_5xx|http_gateway), http_code,
  n_bytes, n_rows, and — when the liveness probe ran — liveness_probe
  (passed|failed).

This module derives, per calendar month (UTC):
  * per-tool: call count, error count/rate, duration p50/p95/mean
  * SPARQL failure classification (syntax/timeout/empty/huge/endpoint-down/...)
  * per-database usage, split by call kind (query / graphs / search / MIE /
    other) so "read the MIE" is never confused with "queried the endpoint",
    oriented toward surfacing MIE-improvement candidates
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

log = logging.getLogger(__name__)

# A result larger than this (bytes) is flagged "huge" — likely an unbounded
# query the MIE should steer away from (missing LIMIT / over-broad pattern).
HUGE_BYTES = 10_000_000

# SPARQL failure taxonomy surfaced in the dashboard. "ok" and "empty_result"
# are successful HTTP responses; the rest are errors.
SPARQL_CLASSES = (
    "ok",
    "empty_result",
    "huge_result",
    "syntax_error",
    "timeout",
    "endpoint_down",
    "pool_exhausted",
    "server_error",
    "other_error",
)

# Front-door tools whose target database is implied by the tool name (no
# ``database`` arg). Keeps per-database stats from undercounting keyword search.
# Add a row here whenever a database-specific wrapper tool is added to
# api_tools.py / chembl.py — `test_search_tool_db_covers_all_wrapper_tools`
# fails if one is missed, because an unmapped wrapper silently drops out of the
# per-database table entirely.
_SEARCH_TOOL_DB = {
    "search_uniprot_entity": "uniprot",
    "search_reactome_entity": "reactome",
    "search_rhea_entity": "rhea",
    "search_pdb_entity": "pdb",
    "search_mesh_descriptor": "mesh",
    "search_chembl_molecule": "chembl",
    "search_chembl_target": "chembl",
    "search_chembl_id_lookup": "chembl",
    "get_pubchem_compound_id": "pubchem",
    "get_compound_attributes_from_pubchem": "pubchem",
}

# Per-database call kinds. `calls` alone conflated "read the MIE" with "queried
# the endpoint", which made two opposite rows unreadable: massbank showed 229
# calls / 176 SPARQL (the gap was 53 get_MIE_file, not a REST API massbank does
# not have), and rhea showed 228 calls / 1 SPARQL (223 of them MIE reads by two
# automated clients). Classification is by TOOL IDENTITY, not by transport —
# the ChEMBL search wrappers are SPARQL-backed, so counting them as "query"
# would recreate the same confusion in mirror image: 1,215 of chembl's 7,410
# endpoint hits in 2026-07 were wrapper calls, not queries anyone wrote.
CALL_KINDS = ("query", "graphs", "search", "mie", "other")

# Co-query attribution. A record gets exactly ONE primary database (the
# ``database`` arg), which hides cross-database work: in 2026-08 all 532 queries
# using rhea: predicates were filed under uniprot, because they joined UniProt to
# Rhea on the co-hosted SIB endpoint and passed database=uniprot. rhea's own row
# read 1 query, which looks like "nobody uses Rhea" and is the opposite of true.
#
# `query_shape.predicates` (present on 100% of logged SPARQL) carries qnames, so
# a namespace prefix OWNED by one database is evidence that database was touched.
# Inclusion rule, deliberately precision-biased: the prefix must be declared in
# at least one MIE file AND bind to a namespace owned by exactly one RDF Portal
# database. That excludes shared community vocabularies (obo:, sio:, bp:, orth:,
# faldo:, med2rdf:, schema:, d3o:, skos:, dcterms:) — see _SHARED_PREFIXES.
#
# Known limitation: several databases are expressed ENTIRELY in shared
# vocabularies and are therefore invisible here — go, chebi and mondo live under
# obo:, reactome under bp:, oma/bgee under orth:/genex:, hgnc/brenda under d3o:.
# A zero in the co-query column means "not detectable", not "not co-queried",
# for those. Fixing it properly needs the collection layer to record namespace
# IRIs rather than prefix strings, since a prefix string is the client's choice,
# not the data's. (bacdive/mediadive are NOT in this list: they own a real
# namespace, they just bind it to a colliding prefix — see
# _AMBIGUOUS_PREFIX_QNAMES, which recovers them.)
SIGNATURE_PREFIXES = {
    "up": "uniprot",            # http://purl.uniprot.org/core/ — 1,914 records
    "uniprot": "uniprot",       # http://purl.uniprot.org/uniprot/
    "uniprotkb": "uniprot",
    "rhea": "rhea",             # http://rdf.rhea-db.org/ — 532 records
    "cco": "chembl",            # http://rdf.ebi.ac.uk/terms/chembl# — 8,620
    "mb": "massbank",           # http://www.massbank.jp/ontology/
    "pdbo": "pdb",              # http://rdf.wwpdb.org/schema/pdbx-*
    "compound": "pubchem",      # http://rdf.ncbi.nlm.nih.gov/pubchem/compound/
    "vocab": "pubchem",         # http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#
    "tgvo": "togovar",          # http://togovar.biosciencedbc.jp/vocabulary/
    "cvo": "clinvar",           # http://purl.jp/bio/10/clinvar/
    "meshv": "mesh",            # http://id.nlm.nih.gov/mesh/vocab#
    "mesh": "mesh",             # http://id.nlm.nih.gov/mesh/
    "jpost": "jpostdb",         # http://rdf.jpostdb.org/ontology/jpost.owl#
    "glycan": "glycosmos",      # http://purl.jp/bio/12/glyco/glycan#
    "gc": "glycosmos",          # http://purl.jp/bio/12/glyco/conjugate#
    "glytoucan": "glycosmos",
    "glycodm": "glycosmos",
    "sb": "glycosmos",          # http://rdf.glycoinfo.org/SugarBind/ontology#
    "nando": "nando",           # http://nanbyodata.jp/ontology/NANDO_
    "mogplus": "mogplus",       # http://identifiers.org/mogplus/ontology#
    "snpeff": "mogplus",
    "vcf": "mogplus",
    "vep": "mogplus",
    "ensg": "ensembl",          # http://rdf.ebi.ac.uk/resource/ensembl/
    "gwas": "gwascatalog",      # http://rdf.ebi.ac.uk/terms/gwas/
    "amr": "amrportal",         # http://example.org/ebiamr#
    "mccv": "nbrc",             # http://purl.jp/bio/10/mccv#
    "mpo": "nbrc",              # http://purl.jp/bio/10/mpo/
    "ncbio": "ncbigene",        # https://dbcls.github.io/ncbigene-rdf/ontology.ttl#
    "pubtator": "pubtator",     # http://purl.jp/bio/10/pubtator-central/ontology#
    "hco": "hco",
    "mco": "mco",
    "taxon": "taxonomy",        # http://identifiers.org/taxonomy/
    "nuc": "ddbj",              # http://ddbj.nig.ac.jp/ontologies/nucleotide/
    "insdc": "ddbj",
}

# Prefix strings that bind to DIFFERENT namespaces in different databases, so
# the prefix alone is worthless — but the LOCAL NAME resolves it. `schema:` is
# the live case: bacdive, mediadive and taxonomy bind it to DSMZ's own
# <https://purl.dsmz.de/schema/>, while massbank binds it to real schema.org.
# In this log 128 records used schema: under a massbank primary and 10 under
# bacdive; mapping the bare prefix to either one would have mis-credited the
# other. Qnames exclusive to one database are listed here and win over
# SIGNATURE_PREFIXES; genuinely shared terms (schema:Strain, schema:hasBacDiveID,
# schema:partOfMedium \u2014 the bacdive\u2194mediadive join vocabulary) are
# deliberately absent, because they really do belong to both.
#
# Derived from the MIE corpus and kept in sync by
# `test_ambiguous_prefix_qnames_match_the_mie_corpus`, which re-derives the sets
# and fails when a database's vocabulary moves.
_AMBIGUOUS_PREFIX_QNAMES: dict[str, dict[str, frozenset[str]]] = {
    "schema": {
        "bacdive": frozenset({
            "CellMotility", "Enzyme", "GramStain", "GrowthCondition",
            "OxygenTolerance", "Pathogenicity", "RiskAssessment", "SaltTolerance",
            "SporeFormation", "describesStrain", "fromSequenceDB", "hasAbility",
            "hasActivity", "hasBiosafetyLevel", "hasDesignation", "hasECNumber",
            "hasGramStain", "hasLink", "hasMediaLink", "hasOxygenTolerance",
            "hasPhylum", "hasSaltConcentrationRangeEnd", "hasSaltType",
            "hasSequenceAccession", "hasTestAbility", "hasTestType", "isHumanPathogen",
            "isMotile", "isTypeStrain",
        }),
        "massbank": frozenset({
            "ChemicalSubstance", "chemicalsubstance", "inChIKey", "molecularFormula",
            "name", "smiles",
        }),
        "mediadive": frozenset({
            "Equipment", "GasComponent", "Ingredient", "Medium", "Modification",
            "OperationalStep", "SolutionRecipe", "belongsTaxGroup", "growthPH",
            "hasCAS", "hasChEBI", "hasDSMNumber", "hasFinalPH", "hasGMO", "hasKEGG",
            "hasLinkToSource", "hasMetaCyc", "hasMinPH", "hasOxygenRequirement",
            "hasPubChem", "includesIngredient", "includesSolution", "ingredientAmount",
            "ingredientUnit", "isComplex", "mmolPerLiter", "partOfSolution",
        }),
    },
}

# Prefixes deliberately NOT in SIGNATURE_PREFIXES: each binds to a vocabulary
# shared by several databases (or by none in particular), so its presence says
# nothing about which database was queried. Listed so the exclusion is a
# decision on the record rather than an omission, and enforced by a test.
# `schema:` is NOT here: it collides rather than being shared, and is resolved
# by local name in _AMBIGUOUS_PREFIX_QNAMES.
_SHARED_PREFIXES = frozenset({
    "rdf", "rdfs", "owl", "xsd", "skos", "dc", "dct", "dcterms", "foaf",
    "obo", "oboInOwl", "oboinowl", "sio", "bp", "biopax", "chemrof", "faldo",
    "orth", "lscr", "genex", "med2rdf", "m2r", "d3o", "idt", "so",
    "ro", "bfo", "oa", "bibo", "prism", "olo", "org", "fabio", "oban", "mo",
    "sty", "unimod", "fma", "bif", "tid", "togoid", "terms", "gvo", "taxo",
    "cv", "keywords", "Schema", "ref", "smp",
})

_MIE_TOOL = "get_MIE_file"
_GRAPHS_TOOL = "get_graph_list"


# --------------------------------------------------------------------------- #
# SPARQL query shape (privacy-safe structural fingerprint)
# --------------------------------------------------------------------------- #
# Matches string literals (triple-quoted, double, single) so their CONTENTS can
# be stripped before any feature extraction — user literals never leak into the
# shape. IRIs live in <...> and are handled separately (only FROM graphs kept).
_LITERAL_RE = re.compile(
    r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''
)
# prefix:local — schema terms (predicates/classes), e.g. up:reviewed, bp:db,
# xsd:string, bif:contains. The local part requirement (`:[A-Za-z_]`) means bare
# "up:" in a PREFIX decl and "http://" inside an IRI do NOT match.
_QNAME_RE = re.compile(r"\b[A-Za-z][\w.-]*:[A-Za-z_]\w*")
_FROM_RE = re.compile(r"\bfrom\s+(?:named\s+)?<([^>]+)>", re.IGNORECASE)
_FLAG_WORDS = (
    "filter", "optional", "union", "values", "service",
    "limit", "offset", "order", "group", "minus", "having",
)


def sparql_shape(query: str) -> dict[str, Any]:
    """Privacy-safe structural fingerprint of a SPARQL query.

    String-literal CONTENTS are stripped first, so no user-supplied text can
    leak. What remains is schema-level: query form, FROM graphs, the set of
    qname predicates/classes used, structural flags, and length. This is the
    signal MIE-improvement analysis needs ("reactome queries using bp:db but
    not xsd:string return 0 rows") without storing the raw query.
    """
    q = query or ""
    stripped = _LITERAL_RE.sub('""', q)
    low = stripped.lower()

    form = "other"
    for f in ("select", "ask", "construct", "describe"):
        if re.search(rf"\b{f}\b", low):
            form = f
            break

    qnames = sorted(set(_QNAME_RE.findall(stripped)))
    flags = {w: bool(re.search(rf"\b{w}\b", low)) for w in _FLAG_WORDS}
    flags["bif_contains"] = "bif:contains" in low

    return {
        "form": form,
        "from": sorted(set(_FROM_RE.findall(stripped)))[:20],
        "predicates": qnames[:60],
        "n_predicates": len(qnames),
        "flags": {k: v for k, v in flags.items() if v},  # only present flags
        "len": len(q),
    }


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def log_paths(base: str) -> list[str]:
    """Return the active log file plus any rotated siblings (base.1, base.2…).

    ``RotatingFileHandler`` writes ``base`` (newest) and ``base.1`` … ``base.N``
    (older). We read all that exist; order does not matter (records carry ``ts``).
    """
    if not base:
        return []
    out = [base] if os.path.exists(base) else []
    i = 1
    while True:
        p = f"{base}.{i}"
        if not os.path.exists(p):
            break
        out.append(p)
        i += 1
    return out


def iter_records(paths: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield one parsed record per JSONL line, silently skipping bad lines."""
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(rec, dict):
                        yield rec
        except OSError:
            continue


def load_endpoint_groups(endpoints_csv: str) -> dict[str, str]:
    """Map endpoint_url -> endpoint group name (e.g. .../ebi/sparql -> 'ebi')."""
    groups: dict[str, str] = {}
    try:
        with open(endpoints_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                url = (row.get("endpoint_url") or "").strip()
                name = (row.get("endpoint_name") or "").strip()
                if url and name:
                    groups.setdefault(url, name)
    except OSError:
        pass
    return groups


# --------------------------------------------------------------------------- #
# Classification helpers
# --------------------------------------------------------------------------- #
def month_of(rec: dict[str, Any]) -> str | None:
    """UTC 'YYYY-MM' bucket for a record, or None if the timestamp is unusable."""
    ts = rec.get("ts")
    if not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def _args(rec: dict[str, Any]) -> dict[str, Any]:
    a = rec.get("args")
    return a if isinstance(a, dict) else {}


# Tool-name prefixes whose ``db``/``database`` argument names a database in a
# FOREIGN namespace, not an RDF Portal one. NCBI E-utilities take db=pubmed /
# clinvar / medgen / gene / taxonomy / sra — and pubmed, clinvar, medgen and
# taxonomy are ALSO RDF Portal database keys, so the two namespaces silently
# merged: in 2026-08 the pubmed row read 3,589 calls when its real RDF usage was
# 48, and clinvar 1,513 against a real 48. The E-utilities calls also have no
# endpoint and no MIE, so they can never be actionable here. database_of()
# always documented this exclusion — it just never implemented it.
_FOREIGN_DB_NAMESPACE_TOOLS = ("ncbi_",)


def _arg_database(rec: dict[str, Any]) -> str:
    a = _args(rec)
    for key in ("database", "db", "dbname"):
        v = a.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def database_of(rec: dict[str, Any], endpoint_groups: dict[str, str]) -> str | None:
    """Best-effort database attribution for a record.

    Priority: foreign-namespace exclusion > explicit ``database`` arg >
    tool-name implied DB > endpoint group (for cross-DB SPARQL that used
    endpoint_name/url). Returns None when the call is not database-specific
    (togoid_*, list_*) or names a database outside RDF Portal (ncbi_*, see
    _FOREIGN_DB_NAMESPACE_TOOLS).
    """
    tool = rec.get("tool")
    if isinstance(tool, str) and tool.startswith(_FOREIGN_DB_NAMESPACE_TOOLS):
        return None

    db = _arg_database(rec)
    if db:
        return db

    if isinstance(tool, str) and tool in _SEARCH_TOOL_DB:
        return _SEARCH_TOOL_DB[tool]

    extra = rec.get("extra")
    if isinstance(extra, dict):
        url = extra.get("endpoint_url")
        if isinstance(url, str) and url:
            group = endpoint_groups.get(url)
            return f"{group} (cross-db)" if group else "unknown-endpoint"
    return None


def sparql_class(rec: dict[str, Any]) -> str | None:
    """Classify a SPARQL record, or None if the record is not a SPARQL call."""
    extra = rec.get("extra")
    if not isinstance(extra, dict) or "sparql_status" not in extra:
        return None
    status = extra.get("sparql_status")
    if status == "ok":
        if (extra.get("n_rows") or 0) == 0:
            return "empty_result"
        if (extra.get("n_bytes") or 0) >= HUGE_BYTES:
            return "huge_result"
        return "ok"
    if status == "timeout":
        return "timeout"
    if status in ("network_error", "endpoint_unresponsive"):
        # endpoint_unresponsive is a liveness-probe verdict: the endpoint was not
        # answering ANYTHING. Filing it here rather than under "timeout" keeps an
        # upstream outage out of TRAP_CLASSES — otherwise every query issued
        # during a portal outage counts as evidence that some MIE is wrong.
        return "endpoint_down"
    if status == "pool_exhausted":
        return "pool_exhausted"
    if status == "http_gateway":
        # A proxy 502/503/504 whose endpoint passed a liveness check right after:
        # a server-side failure, but not one the query can be blamed for.
        return "server_error"
    if status == "http_5xx":
        return "server_error"
    if status == "http_4xx":
        # A 4xx from a SPARQL endpoint is almost always a malformed query.
        return "syntax_error"
    return "other_error"


def client_of(rec: dict[str, Any]) -> str:
    """Reporting MCP client name ('claude-code', 'openai-mcp', …) or '<unknown>'."""
    meta = rec.get("meta")
    if isinstance(meta, dict):
        client = meta.get("client")
        if isinstance(client, dict):
            name = client.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return "<unknown>"


def call_kind(rec: dict[str, Any]) -> str:
    """Classify what a call *was*, for the per-database breakdown.

    Tool identity wins over transport (see CALL_KINDS): `get_graph_list` and the
    ChEMBL search wrappers both hit a SPARQL endpoint, but neither is a user
    query. The five kinds partition every record, so they sum to ``calls``.
    """
    tool = rec.get("tool")
    if tool == _MIE_TOOL:
        return "mie"
    if tool == _GRAPHS_TOOL:
        return "graphs"
    if tool in _SEARCH_TOOL_DB:
        return "search"
    if sparql_class(rec) is not None:
        return "query"
    return "other"


def co_queried_databases(rec: dict[str, Any], primary: str | None = None) -> set[str]:
    """Databases a SPARQL record touched *besides* its primary attribution.

    Derived from the namespace prefixes in ``extra.query_shape.predicates`` via
    SIGNATURE_PREFIXES. Empty for non-SPARQL records and for records logged
    before query_shape existed. See SIGNATURE_PREFIXES for what this cannot see.
    """
    extra = rec.get("extra")
    if not isinstance(extra, dict):
        return set()
    shape = extra.get("query_shape")
    if not isinstance(shape, dict):
        return set()
    out = set()
    for qname in shape.get("predicates") or []:
        prefix, _, local = str(qname).partition(":")
        if not local:
            continue
        by_local = _AMBIGUOUS_PREFIX_QNAMES.get(prefix)
        if by_local is not None:
            # Colliding prefix: only an exclusive local name identifies a database.
            for db, names in by_local.items():
                if local in names:
                    out.add(db)
            continue
        db = SIGNATURE_PREFIXES.get(prefix)
        if db is not None:
            out.add(db)
    out.discard(primary)
    if isinstance(primary, str):
        # An endpoint-group primary ("togovar (cross-db)") names the same
        # database; crediting it as its own co-query would be pure noise.
        out.discard(primary.removesuffix(" (cross-db)"))
    return out


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    rank = pct / 100 * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac, 2)


def parse_excluded_clients(raw: str | None) -> frozenset[str]:
    """Parse TOGOMCP_STATS_EXCLUDE_CLIENTS ('mcp, glyconavi') into a name set."""
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def aggregate(
    records: Iterable[dict[str, Any]],
    endpoint_groups: dict[str, str] | None = None,
    mie_dates: dict[str, str] | None = None,
    exclude_clients: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Roll records up into a JSON-serializable monthly statistics structure.

    ``exclude_clients`` drops whole clients by reported name — the escape hatch
    for a known self-inflicted source (a benchmark harness, a catalog sweeper).
    It is empty by default and never inferred: which traffic is "real" is an
    operator's judgement, and a wrong guess silently deletes real users. What
    was dropped is always reported back in ``excluded_clients``.
    """
    endpoint_groups = endpoint_groups or {}
    mie_dates = mie_dates or {}
    excluded = frozenset(exclude_clients or ())
    records = list(records)  # consumed twice: monthly rollup + trap feed
    n_excluded = 0
    if excluded:
        kept = [r for r in records if client_of(r) not in excluded]
        n_excluded = len(records) - len(kept)
        records = kept

    # month -> accumulators
    tool_durs: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    tool_counts: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"count": 0, "errors": 0, "ips": set()})
    )
    # month -> client name -> reach. Call counts alone cannot tell demand from a
    # benchmark harness: in 2026-08 `mcp` (the SDK default name) sent 8,415 calls
    # from 11 ip_hashes over 10 days, while openai-mcp sent 693 from 355. Distinct
    # ip_hash is the discriminator; distinct SESSIONS is not, and is deliberately
    # not reported — ChatGPT connectors are stateless, so their calls-per-session
    # is 1.00 for the same reason a scripted sweep's is.
    clients: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {"calls": 0, "errors": 0, "ips": set(), "days": set(),
                     "tools": defaultdict(int)}
        )
    )
    sparql: dict[str, dict[str, int]] = defaultdict(
        lambda: {c: 0 for c in SPARQL_CLASSES}
    )
    # month -> db -> tally
    dbs: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "calls": 0,
                "sparql": 0,
                **{k: 0 for k in CALL_KINDS},
                "errors": 0,
                "empty": 0,
                "huge": 0,
                "rows_sum": 0,
                "rows_n": 0,
                "co_query": 0,
                "ips": set(),
                "clients": set(),
                "fail_classes": defaultdict(int),
            }
        )
    )
    # month -> (primary db, co-queried db) -> count
    co_pairs: dict[str, dict[tuple[str, str], int]] = defaultdict(
        lambda: defaultdict(int)
    )
    months: set[str] = set()
    n_total = 0
    n_skipped_no_month = 0

    for rec in records:
        n_total += 1
        month = month_of(rec)
        if month is None:
            n_skipped_no_month += 1
            continue
        months.add(month)
        tool = rec.get("tool") or "<unknown>"
        is_error = rec.get("status") == "error"

        ip = rec.get("ip_hash") or rec.get("ip")
        client = client_of(rec)

        tc = tool_counts[month][tool]
        tc["count"] += 1
        if is_error:
            tc["errors"] += 1
        if ip:
            tc["ips"].add(ip)

        cl = clients[month][client]
        cl["calls"] += 1
        if is_error:
            cl["errors"] += 1
        if ip:
            cl["ips"].add(ip)
        day = day_of(rec)
        if day:
            cl["days"].add(day)
        cl["tools"][tool] += 1
        dur = rec.get("elapsed_ms")
        if isinstance(dur, (int, float)):
            tool_durs[month][tool].append(float(dur))

        cls = sparql_class(rec)
        if cls is not None:
            sparql[month][cls] += 1

        db = database_of(rec, endpoint_groups)
        if cls is not None:
            # Credit every database whose namespace the query actually touched.
            # Recorded on its own counter, never folded into `calls`/`sparql` —
            # one query legitimately credits several databases, so mixing them
            # would make a row's numbers stop adding up.
            for co in co_queried_databases(rec, db):
                dbs[month][co]["co_query"] += 1
                if db is not None:
                    co_pairs[month][(db, co)] += 1
        if db is not None:
            d = dbs[month][db]
            d["calls"] += 1
            d[call_kind(rec)] += 1
            if ip:
                d["ips"].add(ip)
            d["clients"].add(client)
            if is_error:
                d["errors"] += 1
            if cls is not None:
                d["sparql"] += 1
                d["fail_classes"][cls] += 1
                if cls == "empty_result":
                    d["empty"] += 1
                elif cls == "huge_result":
                    d["huge"] += 1
                extra = rec.get("extra") or {}
                rows = extra.get("n_rows")
                if isinstance(rows, (int, float)):
                    d["rows_sum"] += rows
                    d["rows_n"] += 1

    by_month: dict[str, Any] = {}
    for month in sorted(months):
        tools_out = {}
        total_calls = total_errors = 0
        for tool, c in sorted(tool_counts[month].items()):
            durs = sorted(tool_durs[month].get(tool, []))
            total_calls += c["count"]
            total_errors += c["errors"]
            tools_out[tool] = {
                "count": c["count"],
                "errors": c["errors"],
                "ips": len(c["ips"]),
                "error_rate": round(c["errors"] / c["count"], 4) if c["count"] else 0,
                "p50_ms": _percentile(durs, 50),
                "p95_ms": _percentile(durs, 95),
                "mean_ms": round(sum(durs) / len(durs), 2) if durs else 0.0,
            }

        sp = dict(sparql[month])
        sp_total = sum(sp.values())
        sp_fail = sp_total - sp["ok"] - sp["empty_result"]

        dbs_out = {}
        for db, d in sorted(dbs[month].items()):
            dbs_out[db] = {
                "calls": d["calls"],
                # Endpoint hits (query + graphs + SPARQL-backed search wrappers).
                # Kept because the MIE-candidate feed scores against it; the
                # human-readable split is the CALL_KINDS breakdown below.
                "sparql": d["sparql"],
                **{k: d[k] for k in CALL_KINDS},
                "errors": d["errors"],
                "empty": d["empty"],
                "huge": d["huge"],
                "avg_rows": round(d["rows_sum"] / d["rows_n"], 1) if d["rows_n"] else None,
                "co_query": d["co_query"],
                "ips": len(d["ips"]),
                "clients": len(d["clients"]),
                "fail_classes": dict(d["fail_classes"]),
            }

        by_month[month] = {
            "tool_calls": total_calls,
            "errors": total_errors,
            "error_rate": round(total_errors / total_calls, 4) if total_calls else 0,
            "tools": tools_out,
            "sparql": {"total": sp_total, "failures": sp_fail, "classes": sp},
            "databases": dbs_out,
            "clients": [
                {
                    "client": name,
                    "calls": c["calls"],
                    "errors": c["errors"],
                    "ips": len(c["ips"]),
                    "days": len(c["days"]),
                    "calls_per_ip": round(c["calls"] / len(c["ips"]), 1) if c["ips"] else None,
                    "top_tools": [
                        t for t, _ in sorted(c["tools"].items(), key=lambda kv: -kv[1])[:3]
                    ],
                }
                for name, c in sorted(
                    clients[month].items(), key=lambda kv: -kv[1]["calls"]
                )
            ],
            "co_query_pairs": [
                {"primary": a, "co_queried": b, "queries": n}
                for (a, b), n in sorted(
                    co_pairs[month].items(), key=lambda kv: (-kv[1], kv[0])
                )
            ],
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_records": n_total,
        "excluded_clients": {
            "names": sorted(excluded),
            "n_records": n_excluded,
        },
        "n_skipped_no_timestamp": n_skipped_no_month,
        "months": sorted(months),
        "by_month": by_month,
        "mie_candidates": _mie_candidates(by_month),
        "mie_trap_candidates": mie_trap_candidates(records, endpoint_groups, mie_dates),
    }


def _mie_candidates(by_month: dict[str, Any]) -> list[dict[str, Any]]:
    """Rank (database, month) cells by how strongly the logs suggest the MIE
    needs work: failed SPARQL + empty results are the signal. Higher = more
    worth investigating. This is the MIE-improvement-candidate feed."""
    out: list[dict[str, Any]] = []
    for month, m in by_month.items():
        for db, d in m.get("databases", {}).items():
            fails = sum(
                n for c, n in d.get("fail_classes", {}).items()
                if c not in ("ok", "empty_result")
            )
            empties = d.get("empty", 0)
            sparql = d.get("sparql", 0)
            if sparql == 0:
                continue
            # Empty results count half — they are softer evidence than errors.
            score = fails + 0.5 * empties
            if score <= 0:
                continue
            out.append({
                "month": month,
                "database": db,
                "sparql_calls": sparql,
                "failures": fails,
                "empty_results": empties,
                "fail_rate": round((fails + empties) / sparql, 4) if sparql else 0,
                "score": round(score, 1),
                "fail_classes": d.get("fail_classes", {}),
            })
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# MIE-trap candidates — the *filtered* feed (the signal you can act on)
# --------------------------------------------------------------------------- #
# The raw `mie_candidates` ranking above overcounts: it double-counts a single
# stuck session that retried one bad query N times, and it flags failures that a
# since-published MIE edit already fixed. This feed applies four corrections so a
# non-zero entry is genuinely worth a human's time:
#   1. date-filter — drop failures that predate the database's current MIE
#      (`mie_updated`/`mie_created`); those were likely already addressed.
#   2. dedup by query_sha256 — one distinct query, with a `retries` count, not N.
#   3. exclude schema-probe queries — predicate surveys / cardinality probes an
#      MIE *author* runs; they empty/time-out by design, not signal.
#   4. refine the taxonomy — only empty/timeout/huge on a well-formed query is a
#      MIE trap; 4xx is a SPARQL grammar/dialect error (counted separately).
# Nothing is dropped silently: every exclusion is tallied in the return value.

# Only these SPARQL outcomes point at an MIE gap (wrong predicate, missing filter,
# unbounded pattern). syntax_error (4xx) is a grammar error, reported separately.
TRAP_CLASSES = ("empty_result", "timeout", "huge_result")

# A GROUP BY query touching at most this many concrete predicates is treated as a
# schema-introspection probe (e.g. `SELECT ?p (COUNT(*)) … GROUP BY ?p`), not a
# real query. Conservative by design — it under-catches multi-predicate probes
# rather than risk excluding a legitimate user aggregation.
SCHEMA_PROBE_MAX_PREDICATES = 1


def day_of(rec: dict[str, Any]) -> str | None:
    """UTC 'YYYY-MM-DD' for a record, or None if the timestamp is unusable."""
    ts = rec.get("ts")
    if not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


MIE_SPEC_EXPECTED = 3


def load_mie_dates(mie_dir: str) -> dict[str, str]:
    """Map database -> the date its MIE was last FULLY confirmed ('YYYY-MM-DD').

    A failure at time T is only actionable if it postdates this date, so the value
    must be the point at which the whole file was known good.

    MIN, not max, of every example's `verified.date`. Only 1-2 of a file's 8-15
    examples typically carry the newest date (re-verifying one chembl example moved
    that file's max by 29 days), so max() would let a single touched example suppress
    a month of genuine trap signal for the whole database. min() advances only on a
    full re-verification sweep, which is exactly the claim being made.

    YAML-parsed, NOT regex: `verified:` ships in three syntactic shapes across the
    corpus - inline flow, flow spanning several lines, and block - and the word
    "verified" also appears in section comments. pyyaml is a hard dependency, so the
    v2-era "no YAML dependency" constraint this function used to carry bought nothing.

    Skips any file not declaring `mie_spec: 3`. The v2->v3 flip silently stranded the
    previous implementation (it scanned for `mie_created`/`mie_updated`, absent from
    v3, and returned {} for a month); an unreadable format must be visible, not empty.
    """
    out: dict[str, str] = {}
    try:
        paths = sorted(Path(mie_dir).glob("*.yaml"))
    except OSError:
        return out
    for path in paths:
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(doc, dict) or doc.get("mie_spec") != MIE_SPEC_EXPECTED:
            log.warning(
                "load_mie_dates: skipping %s - mie_spec=%r, expected %d",
                path.name, (doc or {}).get("mie_spec") if isinstance(doc, dict) else None,
                MIE_SPEC_EXPECTED,
            )
            continue
        dates = [
            str(ex["verified"]["date"])
            for ex in (doc.get("examples") or [])
            if isinstance(ex, dict)
            and isinstance(ex.get("verified"), dict)
            and ex["verified"].get("date")
        ]
        if dates:
            out[path.stem] = min(dates)
    return out


def is_schema_probe(shape: Any) -> bool:
    """True if a query_shape looks like schema introspection, not a real query.

    Predicate/cardinality surveys (`GROUP BY ?p`) carry the `group` flag and touch
    at most SCHEMA_PROBE_MAX_PREDICATES concrete qnames (the surveyed predicate is
    a variable, so it never appears as a qname). Returns False when the shape is
    missing (older records predate query_shape) — better to keep than to guess.
    """
    if not isinstance(shape, dict):
        return False
    flags = shape.get("flags") or {}
    return bool(flags.get("group")) and shape.get("n_predicates", 0) <= SCHEMA_PROBE_MAX_PREDICATES


def mie_trap_candidates(
    records: Iterable[dict[str, Any]],
    endpoint_groups: dict[str, str] | None = None,
    mie_dates: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Filtered, deduped MIE-trap feed. See section header for the four filters.

    Returns a dict: ``candidates`` (distinct post-MIE traps, ranked by retries then
    recency) plus transparency tallies of everything excluded.
    """
    endpoint_groups = endpoint_groups or {}
    mie_dates = mie_dates or {}
    by_query: dict[str, dict[str, Any]] = {}
    excluded_pre_mie = excluded_probe = grammar_errors = 0

    for rec in records:
        cls = sparql_class(rec)
        if cls is None:
            continue
        if cls == "syntax_error":
            grammar_errors += 1
            continue
        if cls not in TRAP_CLASSES:
            continue
        extra = rec.get("extra") or {}
        shape = extra.get("query_shape")
        if is_schema_probe(shape):
            excluded_probe += 1
            continue
        db = database_of(rec, endpoint_groups)
        day = day_of(rec)
        mdate = mie_dates.get(db) if db else None
        if mdate and day and day <= mdate:  # failure predates the current MIE
            excluded_pre_mie += 1
            continue
        sha = extra.get("query_sha256") or f"nohash:{id(rec)}"
        cand = by_query.get(sha)
        if cand is None:
            preds = shape.get("predicates", []) if isinstance(shape, dict) else []
            cand = by_query[sha] = {
                "database": db,
                # Other databases the failing query actually touched. A trap in
                # a UniProt-primary query can be a *Rhea* MIE gap; without this
                # the rhea row shows 1 query and the trap is unfindable there.
                "co_databases": sorted(co_queried_databases(rec, db)),
                "sparql_class": cls,
                "query_sha256": sha[:16],
                "predicates": preds[:20],
                "retries": 0,
                "first_seen": day,
                "last_seen": day,
            }
        cand["retries"] += 1
        if day:
            if not cand["first_seen"] or day < cand["first_seen"]:
                cand["first_seen"] = day
            if not cand["last_seen"] or day > cand["last_seen"]:
                cand["last_seen"] = day

    candidates = sorted(
        by_query.values(),
        key=lambda c: (c["retries"], c["last_seen"] or ""),
        reverse=True,
    )
    return {
        "candidates": candidates,
        "distinct_queries": len(candidates),
        "excluded_pre_mie": excluded_pre_mie,
        "excluded_schema_probe": excluded_probe,
        "grammar_errors": grammar_errors,
    }


# --------------------------------------------------------------------------- #
# Convenience: load + aggregate from the configured log path
# --------------------------------------------------------------------------- #
def compute_stats(
    log_path: str | None = None,
    endpoints_csv: str | None = None,
    mie_dir: str | None = None,
) -> dict[str, Any]:
    """Load the configured log (TOGOMCP_QUERY_LOG) and return the aggregate."""
    log_path = log_path if log_path is not None else os.getenv("TOGOMCP_QUERY_LOG", "").strip()
    groups = load_endpoint_groups(endpoints_csv) if endpoints_csv else {}
    mie_dates = load_mie_dates(mie_dir) if mie_dir else {}
    paths = log_paths(log_path)
    excluded = parse_excluded_clients(os.getenv("TOGOMCP_STATS_EXCLUDE_CLIENTS"))
    out = aggregate(iter_records(paths), groups, mie_dates, excluded)
    # Describe the bytes behind the aggregate so the dashboard's raw-log download
    # can state its size up front, and so a downloaded file is verifiably the
    # same input the numbers came from (the download serves exactly `paths`).
    out["log_files"] = {
        "n_files": len(paths),
        "n_bytes": sum(os.path.getsize(p) for p in paths if os.path.exists(p)),
    }
    return out


def _human_bytes(n: Any) -> str:
    """Format a byte count for the dashboard ('2.6 MB'). Non-numeric → '?'."""
    if not isinstance(n, (int, float)):
        return "?"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def render_html(stats: dict[str, Any]) -> str:
    """Render the aggregate as a self-contained HTML dashboard (no external JS/CSS)."""
    from html import escape

    def cell(v: Any) -> str:
        return escape("" if v is None else str(v))

    months = stats.get("months", [])
    parts: list[str] = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>TogoMCP usage stats</title><style>",
        "body{font:14px/1.5 system-ui,sans-serif;margin:2rem;color:#1a1a1a;background:#fafafa}",
        "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem;border-bottom:2px solid #ddd;padding-bottom:.2rem}",
        "h3{font-size:.95rem;margin:1rem 0 .3rem;color:#444}",
        "table{border-collapse:collapse;margin:.4rem 0 1rem;font-size:.85rem;background:#fff}",
        "th,td{border:1px solid #ddd;padding:.25rem .5rem;text-align:right}",
        "th:first-child,td:first-child{text-align:left}",
        "th{background:#f0f0f0}tr:nth-child(even) td{background:#f8f8f8}",
        ".muted{color:#888}.warn{color:#b00}.tag{font-size:.75rem;color:#666}",
        "</style></head><body>",
        "<h1>TogoMCP usage statistics</h1>",
        f"<p class='muted'>Generated {cell(stats.get('generated_at'))} · "
        f"{cell(stats.get('n_records'))} records · months: {cell(', '.join(months)) or '—'}</p>",
    ]
    _exc = stats.get("excluded_clients") or {}
    if _exc.get("names"):
        parts.append(
            f"<p class='warn'>Excluding {cell(_exc.get('n_records', 0))} records from "
            f"client(s) {cell(', '.join(_exc['names']))} "
            "(<code>TOGOMCP_STATS_EXCLUDE_CLIENTS</code>). Every number below is "
            "computed without them.</p>"
        )

    # Raw-log download. Sits at the top because it is the escape hatch: every
    # aggregate below is lossy, and the questions worth asking next are usually
    # ones no pre-computed table answers.
    _lf = stats.get("log_files") or {}
    _nb, _nf = _lf.get("n_bytes"), _lf.get("n_files")
    if _nf:
        parts.append(
            # Absolute: the dashboard is served at /stats with NO trailing slash,
            # so a relative "log" would resolve to /log, not /stats/log.
            "<p><a href='/stats/log' download>⬇ Download raw log (JSONL)</a> "
            f"<span class='tag'>{cell(_human_bytes(_nb))} · "
            f"{cell(_nf)} file{'s' if _nf != 1 else ''}, active + rotated · "
            "exactly the records these tables aggregate</span></p>"
        )

    cand = stats.get("mie_candidates", [])
    parts.append("<h2>MIE-improvement candidates</h2>")
    if cand:
        parts.append("<p class='muted'>Ranked by failed + empty SPARQL (per database / month). "
                     "High score = the MIE most likely needs work.</p>")
        parts.append("<table><tr><th>month</th><th>database</th><th>SPARQL</th>"
                     "<th>failures</th><th>empty</th><th>fail rate</th><th>score</th>"
                     "<th>classes</th></tr>")
        for r in cand[:50]:
            classes = ", ".join(f"{k}:{v}" for k, v in sorted(r.get("fail_classes", {}).items())
                                if k not in ("ok",))
            parts.append(
                f"<tr><td>{cell(r['month'])}</td><td>{cell(r['database'])}</td>"
                f"<td>{cell(r['sparql_calls'])}</td><td class='warn'>{cell(r['failures'])}</td>"
                f"<td>{cell(r['empty_results'])}</td><td>{cell(r['fail_rate'])}</td>"
                f"<td>{cell(r['score'])}</td><td class='tag'>{cell(classes)}</td></tr>"
            )
        parts.append("</table>")
    else:
        parts.append("<p class='muted'>No failed/empty SPARQL recorded.</p>")

    # Filtered, deduped MIE-trap feed — the actionable list.
    trap = stats.get("mie_trap_candidates") or {}
    tcand = trap.get("candidates", [])
    parts.append("<h2>MIE traps to fix (filtered)</h2>")
    parts.append(
        "<p class='muted'>Distinct queries that empty/time-out <em>after</em> the current MIE "
        "(deduped by query hash; schema-probe surveys and pre-MIE failures removed). "
        f"Excluded: {cell(trap.get('excluded_pre_mie', 0))} pre-MIE · "
        f"{cell(trap.get('excluded_schema_probe', 0))} schema-probe · "
        f"{cell(trap.get('grammar_errors', 0))} grammar-error (4xx, not MIE traps). "
        "A non-empty row here is worth a look; verify against the live endpoint before editing. "
        "<b>also touched</b> lists other databases the query used predicates from — the trap may "
        "be in <em>their</em> MIE, not the one the call named.</p>"
    )
    if tcand:
        parts.append("<table><tr><th>database</th><th>also touched</th><th>class</th>"
                     "<th>retries</th>"
                     "<th>first seen</th><th>last seen</th><th>query</th><th>predicates</th></tr>")
        for r in tcand[:50]:
            preds = ", ".join(r.get("predicates", [])[:8])
            parts.append(
                f"<tr><td>{cell(r['database'])}</td>"
                f"<td class='tag'>{cell(', '.join(r.get('co_databases') or []))}</td>"
                f"<td>{cell(r['sparql_class'])}</td>"
                f"<td class='warn'>{cell(r['retries'])}</td><td>{cell(r['first_seen'])}</td>"
                f"<td>{cell(r['last_seen'])}</td><td class='tag'>{cell(r['query_sha256'])}</td>"
                f"<td class='tag'>{cell(preds)}</td></tr>"
            )
        parts.append("</table>")
    else:
        parts.append("<p class='muted'>No post-MIE traps after filtering — "
                     "the logged failures are already-fixed or schema-probe noise.</p>")

    for month in reversed(months):
        m = stats["by_month"][month]
        parts.append(f"<h2>{cell(month)}</h2>")
        parts.append(
            f"<p>{cell(m['tool_calls'])} tool calls · {cell(m['errors'])} errors "
            f"(<span class='warn'>{cell(round(m['error_rate'] * 100, 1))}%</span>)</p>"
        )

        sp = m["sparql"]
        parts.append("<h3>SPARQL outcomes</h3><table><tr>"
                     + "".join(f"<th>{cell(c)}</th>" for c in SPARQL_CLASSES)
                     + "<th>total</th><th>failures</th></tr><tr>"
                     + "".join(f"<td>{cell(sp['classes'].get(c, 0))}</td>" for c in SPARQL_CLASSES)
                     + f"<td>{cell(sp['total'])}</td><td class='warn'>{cell(sp['failures'])}</td></tr></table>")

        cl = m.get("clients") or []
        if cl:
            parts.append("<h3>Per client</h3>")
            parts.append(
                "<p class='muted'>Who the traffic is. <b>calls/IP</b> is the "
                "concentration tell: ~2 is a crowd, several hundred is one "
                "operator or a sweep. Read this table before reading any number "
                "above as demand.</p>"
            )
            parts.append("<table><tr><th>client</th><th>calls</th><th>IPs</th>"
                         "<th>calls/IP</th><th>days</th><th>errors</th>"
                         "<th>top tools</th></tr>")
            for c in cl[:30]:
                parts.append(
                    f"<tr><td>{cell(c['client'])}</td><td>{cell(c['calls'])}</td>"
                    f"<td>{cell(c['ips'])}</td><td>{cell(c['calls_per_ip'])}</td>"
                    f"<td>{cell(c['days'])}</td><td>{cell(c['errors'])}</td>"
                    f"<td class='tag'>{cell(', '.join(c['top_tools']))}</td></tr>"
                )
            parts.append("</table>")

        parts.append("<h3>Per database</h3>")
        parts.append(
            "<p class='muted'>calls = query + graphs + search + MIE + other. "
            "<b>query</b> = run_sparql; <b>graphs</b> = get_graph_list; "
            "<b>search</b> = that database\u2019s wrapper tool "
            "(SPARQL-backed for ChEMBL, REST elsewhere); <b>MIE</b> = get_MIE_file, "
            "which reads a bundled YAML and never touches the endpoint. "
            "errors is over all calls; empty / huge / avg rows are over endpoint "
            "hits only (query + graphs + search).</p>"
        )
        parts.append(
            "<p class='muted'><b>co-query</b> counts queries that used this "
            "database\u2019s namespace but were filed under another database "
            "(they passed a different <code>database=</code>). It is NOT part of "
            "calls \u2014 one query can credit several databases. Detection is by "
            "namespace prefix, so databases expressed only in shared vocabularies "
            "(go, chebi, mondo, reactome, oma, bgee, hgnc, brenda) always read 0 "
            "here \u2014 undetectable, not unused.</p>"
        )
        parts.append(
            "<p class='muted'><b>IPs</b> is the number of distinct clients "
            "(hashed source addresses), and it is the column that separates "
            "demand from a script: 229 calls from 150 IPs is many people, 228 "
            "calls from 9 IPs is a handful of automated runs. Distinct "
            "<em>sessions</em> is deliberately not shown \u2014 stateless clients "
            "open one per call, so it measures transport, not use. Caveat: if "
            "<code>TOGOMCP_LOG_HASH_SALT</code> is unset the salt is regenerated "
            "each process, so one client counts once per server restart.</p>"
        )
        parts.append("<table><tr><th>database</th><th>calls</th><th>query</th>"
                     "<th>graphs</th><th>search</th><th>MIE</th><th>other</th>"
                     "<th>co-query</th><th>IPs</th><th>clients</th>"
                     "<th>errors</th><th>empty</th><th>huge</th>"
                     "<th>avg rows</th></tr>")
        for db, d in sorted(m["databases"].items(), key=lambda kv: kv[1]["calls"], reverse=True):
            parts.append(
                f"<tr><td>{cell(db)}</td><td>{cell(d['calls'])}</td>"
                + "".join(f"<td>{cell(d.get(k, 0))}</td>" for k in CALL_KINDS)
                + f"<td>{cell(d.get('co_query', 0))}</td>"
                + f"<td>{cell(d.get('ips', 0))}</td><td>{cell(d.get('clients', 0))}</td>"
                + f"<td>{cell(d['errors'])}</td><td>{cell(d['empty'])}</td>"
                f"<td>{cell(d['huge'])}</td><td>{cell(d['avg_rows'])}</td></tr>"
            )
        parts.append("</table>")

        pairs = m.get("co_query_pairs") or []
        if pairs:
            parts.append("<h3>Cross-database joins</h3>")
            parts.append("<p class='muted'>Queries filed under one database that "
                         "used another\u2019s namespace \u2014 the co-hosted-endpoint "
                         "work the per-database rows cannot show.</p>")
            parts.append("<table><tr><th>filed under</th><th>also queried</th>"
                         "<th>queries</th></tr>")
            for pr in pairs[:25]:
                parts.append(
                    f"<tr><td>{cell(pr['primary'])}</td><td>{cell(pr['co_queried'])}</td>"
                    f"<td>{cell(pr['queries'])}</td></tr>"
                )
            parts.append("</table>")

        parts.append("<h3>Per tool</h3><table><tr><th>tool</th><th>calls</th><th>IPs</th>"
                     "<th>errors</th>"
                     "<th>error rate</th><th>p50 ms</th><th>p95 ms</th><th>mean ms</th></tr>")
        for tool, t in sorted(m["tools"].items(), key=lambda kv: kv[1]["count"], reverse=True):
            parts.append(
                f"<tr><td>{cell(tool)}</td><td>{cell(t['count'])}</td>"
                f"<td>{cell(t.get('ips', 0))}</td><td>{cell(t['errors'])}</td>"
                f"<td>{cell(t['error_rate'])}</td><td>{cell(t['p50_ms'])}</td>"
                f"<td>{cell(t['p95_ms'])}</td><td>{cell(t['mean_ms'])}</td></tr>"
            )
        parts.append("</table>")

    parts.append("</body></html>")
    return "".join(parts)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Aggregate TogoMCP usage logs.")
    ap.add_argument("log_path", nargs="?", default=os.getenv("TOGOMCP_QUERY_LOG", ""),
                    help="JSONL log path (default: $TOGOMCP_QUERY_LOG)")
    ap.add_argument("--endpoints", default="", help="endpoints.csv for DB attribution")
    ap.add_argument("--mie", default="", help="MIE dir for date-filtering trap candidates")
    args = ap.parse_args(argv)
    if not args.log_path:
        ap.error("no log path given and TOGOMCP_QUERY_LOG is unset")
    stats = aggregate(
        iter_records(log_paths(args.log_path)),
        load_endpoint_groups(args.endpoints) if args.endpoints else {},
        load_mie_dates(args.mie) if args.mie else {},
    )
    print(json.dumps(stats, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

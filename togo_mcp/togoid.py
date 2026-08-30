import atexit
import difflib
import json
import re

import httpx

from .server import *


def _ids_to_tokens(ids: str | list[str]) -> list[str]:
    """Normalize an `ids` argument (list or separated string) to a token list."""
    if isinstance(ids, str):
        return [s.strip() for s in re.split(r"[,\s]+", ids) if s.strip()]
    return [str(i).strip() for i in ids if str(i).strip()]


def _ids_to_csv(ids: str | list[str]) -> str:
    """Normalize an `ids` argument (list or separated string) to a CSV string."""
    return ",".join(_ids_to_tokens(ids))

_client = httpx.AsyncClient(base_url="https://api.togoid.dbcls.jp")


def _close_client():
    """Close the shared httpx client on interpreter shutdown."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_client.aclose())
    except RuntimeError:
        # No running loop: the interpreter is shutting down and the loop that
        # OWNS these sockets is already closed. Opening a fresh one to close
        # them reaches into the dead loop and raises "Event loop is closed",
        # which atexit prints as a 38-line traceback after a clean exit. The OS
        # reclaims the sockets either way, so leave them.
        pass


atexit.register(_close_client)

togoid_mcp = FastMCP("TogoID API server")


# ============================================================================
# DATASET-CONFIG HELPERS
#
# TogoID publishes each dataset's ID pattern with .NET/JavaScript-style named
# groups — `(?<id>...)`. Python's `re` rejects that syntax outright
# (`error: unknown extension ?<i`), and all 119 datasets are affected, so the
# `regex` field is unusable from Python as served. Worse, a consumer who wraps
# the compile in a bare try/except silently turns "this ID matches nothing"
# into a wrong answer (dbcls/togomcp#213).
#
# We keep `regex` byte-identical to upstream and ADD a `regex_python` twin plus
# a `regex_flavor` label, so a caller knows which dialect it holds instead of
# having to discover the incompatibility at runtime.
# ============================================================================

# Only rewrites a group OPENER: the lookahead requires a name character, which
# is what keeps lookbehind (`(?<=`, `(?<!`) intact. No TogoID pattern uses
# lookbehind today, but the guard costs nothing and the corpus is not ours.
_NAMED_GROUP_OPEN_RE = re.compile(r"\(\?<(?=[A-Za-z_])")

# Dataset keys an LLM reaches for that TogoID does not define. Values are the
# real keys, most likely first. difflib alone is not enough here: the observed
# failure `ncbi_protein` is lexically closest to `ensembl_protein`, and no
# edit-distance metric can know that a GenBank protein accession is filed
# under `insdc_cds`.
_DATASET_ALIAS_HINTS: dict[str, tuple[str, ...]] = {
    "ncbi_protein": ("insdc_cds", "refseq_protein"),
    "ncbiprotein": ("insdc_cds", "refseq_protein"),
    "genbank": ("insdc_cds", "insdc"),
    "genbank_protein": ("insdc_cds",),
    "ena": ("insdc", "insdc_cds"),
    "ddbj": ("insdc", "insdc_cds"),
    "embl": ("insdc", "insdc_cds"),
    "ncbi_nucleotide": ("insdc", "refseq_rna", "refseq_genomic"),
    "nucleotide": ("insdc", "refseq_rna", "refseq_genomic"),
    "protein": ("uniprot", "insdc_cds", "refseq_protein"),
    "refseq": ("refseq_protein", "refseq_rna", "refseq_genomic"),
    "ncbi_gene": ("ncbigene",),
    "entrez_gene": ("ncbigene",),
    "entrez": ("ncbigene",),
    "gene": ("ncbigene", "hgnc", "ensembl_gene"),
    "gene_symbol": ("hgnc_symbol",),
    "symbol": ("hgnc_symbol",),
    "uniprotkb": ("uniprot",),
    "swissprot": ("uniprot",),
    "trembl": ("uniprot",),
    "kegg": (),  # KEGG is genuinely absent from TogoID — say so, suggest nothing
    "chembl": ("chembl_compound", "chembl_target"),
    "pubchem": ("pubchem_compound", "pubchem_substance"),
    "cid": ("pubchem_compound",),
    "reactome": ("reactome_pathway", "reactome_reaction"),
    "ncbi_taxonomy": ("taxonomy",),
    "taxid": ("taxonomy",),
    "rsid": ("dbsnp",),
    "rs": ("dbsnp",),
    "omim": ("omim_gene", "omim_phenotype"),
    "hpo": ("hp_phenotype", "hp_inheritance"),
    "pdb_id": ("pdb",),
    "pdbj": ("pdb",),
    "sra": ("sra_run", "sra_experiment", "sra_sample", "sra_project"),
    "mgi": ("mgi_gene", "mgi_allele", "mgi_genotype"),
    "ensembl": ("ensembl_gene", "ensembl_transcript", "ensembl_protein"),
}


def _to_python_regex(pattern: str) -> str:
    """Rewrite `(?<name>...)` named groups to Python's `(?P<name>...)`."""
    return _NAMED_GROUP_OPEN_RE.sub("(?P<", pattern)


def _augment_dataset(config: dict) -> dict:
    """Return `config` with a Python-compilable twin of its `regex` field.

    `regex` is left exactly as TogoID served it; `regex_python` and
    `regex_flavor` are added beside it.
    """
    if not isinstance(config, dict) or "regex" not in config:
        return config
    pattern = config["regex"]
    if not isinstance(pattern, str):
        return config
    augmented = dict(config)
    augmented["regex_flavor"] = "ecmascript"
    augmented["regex_python"] = _to_python_regex(pattern)
    return augmented


def _orient_relations(payload, *, registered: bool = False):
    """Label a relation payload with the direction TogoID registered it in.

    When `registered` is False the payload came from the SWAPPED pair, so its
    `forward`/`reverse` labels are back-to-front relative to what the caller
    asked; swap them so both fields always read in the caller's orientation.
    """
    if not isinstance(payload, list):
        return payload
    direction = "source-target" if registered else "target-source"
    oriented = []
    for relation in payload:
        if not isinstance(relation, dict):
            oriented.append(relation)
            continue
        entry = dict(relation)
        if not registered and ("forward" in entry or "reverse" in entry):
            entry["forward"], entry["reverse"] = (
                entry.get("reverse"),
                entry.get("forward"),
            )
        entry["registered_direction"] = direction
        oriented.append(entry)
    return oriented


_dataset_config_cache: dict | None = None


async def _dataset_config(*, refresh: bool = False) -> dict:
    """Fetch (and memoise) TogoID's full dataset config.

    Used to validate dataset keys BEFORE spending a request on a route that
    cannot exist. A fetch failure returns `{}`, which disables validation
    rather than blocking the call the caller actually asked for.

    `refresh=True` discards the memo. The cache has no TTL, and this server
    runs for weeks — so a dataset TogoID registers after startup would be
    rejected as nonexistent until a redeploy. Rather than expire the cache on a
    timer, `_validate_dataset_keys` re-fetches once on the error path only: a
    key we are about to reject is exactly the case where staleness matters, and
    nothing else pays for it.
    """
    global _dataset_config_cache, _collision_cache
    if refresh:
        _dataset_config_cache = None
        _collision_cache = None
    if _dataset_config_cache is not None:
        return _dataset_config_cache
    try:
        response = await _client.get("/config/dataset")
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    _dataset_config_cache = payload
    return payload


def _suggest_datasets(unknown: str, known: list[str]) -> list[str]:
    """Best guesses at what `unknown` was meant to be, curated hints first."""
    hinted = _DATASET_ALIAS_HINTS.get(unknown.strip().lower(), ())
    suggestions = [k for k in hinted if k in known]
    for candidate in difflib.get_close_matches(unknown, known, n=3, cutoff=0.6):
        if candidate not in suggestions:
            suggestions.append(candidate)
    return suggestions[:4]


async def _validate_dataset_keys(keys: list[str], *, context: str) -> None:
    """Raise a deterministic ValueError if any key is not a TogoID dataset.

    Without this the caller gets TogoID's `no route: ncbi_protein <> uniprot`,
    which is true but does not say that `ncbi_protein` is the part that does
    not exist, nor what to use instead.
    """
    config = await _dataset_config()
    if not config:
        return
    unknown = [k for k in keys if k and k not in config]
    if unknown:
        # Before rejecting, make sure we are not judging against a config
        # memoised before TogoID registered the key.
        config = await _dataset_config(refresh=True) or config
        unknown = [k for k in keys if k and k not in config]
    if not unknown:
        return
    known = sorted(config)
    parts = []
    for key in unknown:
        suggestions = _suggest_datasets(key, known)
        if suggestions:
            parts.append(f"{key!r} (did you mean: {', '.join(suggestions)}?)")
        else:
            parts.append(f"{key!r} (no close match — TogoID may not carry it)")
    raise ValueError(
        f"{context}: not a TogoID dataset key: {'; '.join(parts)}. "
        "Do not retry the same key. Call getAllDataset() for the full list of "
        "119 keys, or identifyId() to resolve a bare accession to its dataset."
    )


# ============================================================================
# DISCOVERY TOOLS — Use these EARLY in multi-database workflows
# ============================================================================


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def getAllRelation() -> dict:
    """Discover all available ID conversion routes between databases.

    ⚡ PLANNING TOOL — Call this EARLY when a question involves 2+ databases
    that are on DIFFERENT SPARQL endpoints and you need to map IDs between them.

    Returns a map of all source→target database pairs that TogoID can convert.
    Use this to plan your cross-database strategy BEFORE attempting SPARQL joins
    or manual ID lookups.

    Common conversion routes include:
        - ncbigene ↔ uniprot (Gene IDs to/from protein accessions)
        - uniprot ↔ pdb (Protein accessions to/from 3D structure IDs)
        - ncbigene ↔ ensembl_gene (NCBI Gene to/from Ensembl gene IDs)
        - chembl_target ↔ uniprot (Drug targets to/from protein accessions)
        - ncbigene ↔ hgnc (Gene IDs to/from HGNC symbols)
        - pubchem_compound ↔ chembl_compound (Compound IDs across databases)

    When to use:
        - Question references 2+ databases on different SPARQL endpoints
        - You need to bridge identifiers (e.g., "find UniProt proteins for
          these NCBI Gene IDs")
        - Before writing complex multi-step SPARQL to join databases manually

    When NOT to use:
        - Both databases share a SPARQL endpoint (use a single SPARQL query)
        - You only need data from one database
        - NCBI esearch can already cross-reference what you need

    Returns:
        Dictionary mapping database pairs to their relationship metadata.
        Each entry shows source, target, and the nature of the link.
    """
    response = await _client.get("/config/relation")
    raise_for_status_with_body(response, context="TogoID getAllRelation")
    return response.json()


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def getRelation(source: str, target: str) -> str:
    """Check if a specific ID conversion route exists and get its details.

    Use this to verify that a particular source→target conversion is available
    before calling convertId. Also reveals the nature of the relationship
    (e.g., "encoded by", "has structure", "is target of").

    This is a single-hop, pairwise check: pass `source` and `target` as two
    separate args (unlike convertId, which takes one comma-joined `route`).

    RETURNS a JSON string of a bare array of relationship objects, each with
    `forward` (label from source to target), `reverse` (label from target to
    source), and `description` (explanation of the link). An empty array means
    no direct route exists.

    DIRECTION IS NOT A CONSTRAINT ON TRAVERSAL. TogoID registers each pair in
    one direction only (270 of 302 pairs have no reverse entry), but convertId
    and countId traverse a pair BOTH ways. So this tool falls back to the
    swapped pair when the requested orientation is unregistered: the labels are
    swapped into YOUR orientation and the object carries
    `"registered_direction": "target-source"` to say so. A non-empty result
    means the conversion works in the direction you asked for.

    Args:
        source: Source database key (e.g., 'uniprot', 'ncbigene', 'chembl_target')
        target: Target database key (e.g., 'pdb', 'ensembl_gene', 'hgnc')

    Returns:
        JSON string: a bare array of relationship objects with:
        - forward: relationship label from source to target
        - reverse: relationship label from target to source
        - description: explanation of the link
        - registered_direction: "source-target" if TogoID registers the pair in
          the orientation you asked for, "target-source" if it registers only
          the reverse (the conversion still works either way)

    Example:
        >>> getRelation('ncbigene', 'uniprot')
        # Shows: ncbigene → uniprot via "encoded by" relationship

        >>> getRelation('uniprot', 'pdb')
        # Shows: uniprot → pdb via "has structure" relationship

        >>> getRelation('insdc_cds', 'uniprot')
        # TogoID registers only uniprot-insdc_cds; the route is still returned,
        # oriented insdc_cds → uniprot, with registered_direction target-source
    """
    response = await _client.get(f"/config/relation/{source}-{target}")
    if response.status_code == 404:
        # TogoID's relation config is authored one directory per DIRECTED pair,
        # so a perfectly traversable route 404s here whenever the pair happens
        # to be registered the other way round. /count/ and /convert accept
        # both orientations, which made this tool the only surface that denied
        # a route the rest of the API happily walks (dbcls/togomcp#213).
        reverse = await _client.get(f"/config/relation/{target}-{source}")
        if reverse.status_code == 200:
            return json.dumps(_orient_relations(reverse.json()))
    raise_for_status_with_body(
        response,
        context="TogoID getRelation",
        client_error_hint=(
            "Verify both source and target dataset names (getAllDataset lists "
            "them). Neither orientation of this pair is registered, so no direct "
            "route exists — getAllRelation() lists every registered pair."
        ),
    )
    return json.dumps(_orient_relations(response.json(), registered=True))


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def getAllDataset() -> dict:
    """List all databases registered in TogoID with their ID formats.

    Returns configuration for every dataset TogoID knows about, including:
    - label: Human-readable database name
    - regex: Pattern for validating IDs, AS SERVED BY TogoID
    - regex_flavor: dialect of `regex` — currently always "ecmascript"
    - regex_python: the same pattern rewritten for Python's `re` (ADDED HERE)
    - prefix: URI prefix for linked data
    - examples: Sample IDs you can use to test conversions

    ⚠️ `regex` IS NOT PYTHON-COMPATIBLE. TogoID publishes .NET/JavaScript named
    groups — `(?<id>...)` — which `re.compile` rejects outright for all 119
    datasets. **Use `regex_python`**, which this tool adds beside the original.
    Never wrap the compile of `regex` in a bare try/except: that converts
    "cannot compile" into "matches nothing", i.e. a silently wrong answer.

    Useful for:
        - Discovering which databases are available for ID conversion
        - Checking the expected ID format (e.g., UniProt accession vs entry name)
        - Finding example IDs to test with countId before bulk conversion

    To go the other way — bare accession → dataset key — use identifyId().

    Returns:
        Dictionary mapping dataset keys (e.g., 'uniprot', 'ncbigene', 'pdb')
        to their configuration objects.
    """
    response = await _client.get("/config/dataset")
    raise_for_status_with_body(response, context="TogoID getAllDataset")
    payload = response.json()
    if not isinstance(payload, dict):
        return payload
    return {key: _augment_dataset(cfg) for key, cfg in payload.items()}


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def getDataset(dataset: str) -> dict:
    """Get configuration for a specific database in TogoID.

    Retrieves detailed metadata about a single dataset, including its ID format,
    URI prefix, example IDs, and available annotations.

    RETURNS a dict with `label` (human-readable name), `regex` (the ID-validation
    pattern exactly as TogoID serves it), `regex_flavor` ("ecmascript"),
    `regex_python` (the same pattern rewritten for Python's `re` — ADDED HERE),
    `prefix` (URI prefixes for linking), `examples` (sample IDs — test with
    countId before bulk conversion), and `annotations` (available annotation
    types).

    ⚠️ `regex` uses .NET/JavaScript named groups `(?<id>...)`, which Python's
    `re.compile` rejects. **Use `regex_python`.** A bare try/except around the
    compile silently degrades to "matches nothing" — a wrong answer, not an error.

    Args:
        dataset: Dataset key (e.g., 'uniprot', 'ncbigene', 'pdb', 'chembl_target',
                 'ensembl_gene', 'hgnc', 'pubchem_compound')

    Returns:
        Dictionary with:
        - label: Human-readable name
        - regex: ID validation pattern as served (ECMAScript named groups)
        - regex_flavor: "ecmascript"
        - regex_python: the same pattern, compilable by Python's `re`
        - prefix: URI prefixes for linking
        - examples: Sample IDs (use with countId to test before bulk conversion)
        - annotations: Available annotation types for this dataset
    """
    response = await _client.get(f"/config/dataset/{dataset}")
    raise_for_status_with_body(
        response,
        context="TogoID getDataset",
        client_error_hint=(
            "Verify the dataset name. Use getAllDataset() to list valid datasets."
        ),
    )
    return _augment_dataset(response.json())


_collision_cache: dict[str, int] | None = None


def _collision_scores(config: dict) -> dict[str, int]:
    """How many OTHER datasets' example IDs each dataset's pattern also matches.

    A data-derived specificity measure, and a far better one than anything
    syntactic: nearly every TogoID pattern contains a `+` or `*` somewhere (the
    optional `(?:\\.\\d+)?` version suffix alone), so counting quantifiers ranks
    everything as loose. Every dataset publishes ~10 real `examples`, giving
    1,840 probe IDs; running all 119 patterns over all of them takes ~0.03s and
    is memoised for the process.

    The result separates the genuinely specific from the catch-all: `uniprot`
    collides with 10, `insdc_cds` with 73, and `hgnc_symbol` with 1,474 —
    upstream authored it as `^(?<id>[A-Z0-9_(?:orf)\\-]+\\@?)$`, where the
    `(?:orf)` was meant as an alternation but sits INSIDE the character class,
    making `(`, `?`, `:`, `o`, `r`, `f`, `)` literal members. It matches almost
    any token, `CHEBI:15377` included. Bare-numeric datasets (ncbigene, pubmed,
    chebi, ...) all score 170 because they genuinely cannot be told apart by
    shape — the tie is the honest answer, not a ranking failure.
    """
    global _collision_cache
    if _collision_cache is not None:
        return _collision_cache

    probes: list[tuple[str, str]] = []
    for key, cfg in config.items():
        for group in cfg.get("examples") or []:
            for example in group if isinstance(group, list) else [group]:
                probes.append((key, str(example)))

    scores: dict[str, int] = {}
    for key, cfg in config.items():
        pattern = cfg.get("regex")
        if not isinstance(pattern, str):
            continue
        try:
            matcher = re.compile(_to_python_regex(pattern))
        except re.error:
            continue
        scores[key] = sum(
            1 for owner, probe in probes if owner != key and matcher.fullmatch(probe)
        )
    _collision_cache = scores
    return scores


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def identifyId(ids: str | list[str], category: str | None = None) -> str:
    """Resolve a bare accession to the TogoID dataset key(s) it could belong to.

    The inverse of getDataset: you have an identifier like `AEK21611` or
    `P38398` and need the `route` key convertId expects. Call this INSTEAD of
    guessing a plausible-sounding key — `ncbi_protein`, `entrez_gene` and
    `uniprotkb` are not TogoID datasets and every call using one fails.

    RETURNS a JSON string of a bare array, one object per input ID, each with
    `id` and `candidates` (possibly empty). Each candidate carries `dataset`
    (the key to put in a route), `label`, `category`, and `pattern_collisions`.

    Candidates are ordered most-specific first, by `pattern_collisions` — how
    many of the OTHER 118 datasets' published example IDs this dataset's ID
    pattern also matches. Low means a distinctive format (`uniprot`: 10); high
    means a catch-all (`hgnc_symbol`: 1474, which matches nearly any token).

    ⚠️ ORDER IS EVIDENCE, NOT AN ANSWER. Accession formats genuinely collide:
    `P38398` is a valid UniProt accession AND a valid GenBank CDS accession,
    and all the bare-numeric datasets (ncbigene, pubmed, chebi, ...) are
    indistinguishable by shape — they tie at 170 for that reason. When two
    candidates are close, disambiguate with `category`, with what you know
    about where the ID came from, or by running countId on each and keeping the
    one that resolves. An empty `candidates` list means no registered dataset's
    pattern matches — that ID is not convertible by TogoID.

    Matching uses each dataset's published ID pattern, rewritten to Python
    syntax (see getAllDataset's `regex_python`). A CURIE or full IRI
    disambiguates far better than a bare accession — pass `insdc.cds:AEK21611`
    rather than `AEK21611` when you have it.

    Args:
        ids: Identifiers to resolve. A list of strings, or a comma/whitespace
            separated string (e.g. "AEK21611,P38398").
        category: Optional filter on the dataset's category, matched
            case-insensitively — e.g. 'Gene', 'Protein', 'Compound',
            'Transcript', 'Variant', 'Pathway', 'Phenotype'. Use it to break
            ties when you know what kind of thing the ID names.

    Example:
        >>> identifyId("AEK21611")
        # insdc (63), insdc_cds (73), hgnc_symbol (1474)
        >>> identifyId("AEK21611", category="Protein")
        # narrows to insdc_cds — the key convertId wants
    """
    tokens = _ids_to_tokens(ids)
    if not tokens:
        raise ValueError("TogoID identifyId: no identifiers supplied.")

    config = await _dataset_config()
    if not config:
        raise ValueError(
            "TogoID identifyId: could not fetch the dataset config from "
            "api.togoid.dbcls.jp. Retry, or call getAllDataset() directly."
        )

    wanted = category.strip().lower() if category else None
    if wanted and not any(
        str(cfg.get("category", "")).lower() == wanted for cfg in config.values()
    ):
        known = sorted({str(c.get("category")) for c in config.values() if c.get("category")})
        raise ValueError(
            f"TogoID identifyId: unknown category {category!r}. "
            f"Valid categories: {', '.join(known)}."
        )

    collisions = _collision_scores(config)
    compiled: list[tuple[int, str, re.Pattern, dict]] = []
    for key, cfg in config.items():
        pattern = cfg.get("regex")
        if not isinstance(pattern, str):
            continue
        if wanted and str(cfg.get("category", "")).lower() != wanted:
            continue
        try:
            matcher = re.compile(_to_python_regex(pattern))
        except re.error:
            # A pattern we cannot compile even after rewriting is upstream's to
            # fix; skip it rather than failing every lookup.
            continue
        score = collisions.get(key, 0)
        compiled.append((score, key, matcher, {
            "dataset": key,
            "label": cfg.get("label"),
            "category": cfg.get("category"),
            "pattern_collisions": score,
        }))
    compiled.sort(key=lambda entry: (entry[0], entry[1]))

    resolved = [
        {
            "id": token,
            "candidates": [
                meta for _, _, matcher, meta in compiled if matcher.fullmatch(token)
            ],
        }
        for token in tokens
    ]
    return json.dumps(resolved)


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def getDescription() -> dict:
    """Get human-readable descriptions for all databases in TogoID.

    Returns names, descriptions (in English and Japanese), and organization info
    for each registered database. Useful for understanding what each database
    contains when planning cross-database queries.

    Returns:
        Dictionary keyed by dataset name with description metadata.
    """
    response = await _client.get("/config/descriptions")
    raise_for_status_with_body(response, context="TogoID getDescription")
    return response.json()


# ============================================================================
# CONVERSION TOOLS — Use these AFTER planning with discovery tools above
# ============================================================================


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def convertId(
    ids: str | list[str],
    route: str,
    limit: int = 10000,
    offset: int = 0,
) -> str:
    """Convert identifiers from one database to another.

    Maps IDs between biological databases — e.g., NCBI Gene IDs to UniProt
    accessions, or UniProt accessions to PDB structure IDs.

    RETURNS a JSON string of a bare array of [source_id, target_id] pairs,
    e.g. '[["672", "P38398"], ["675", "O15129"]]'. An empty array means none
    of the input IDs converted along the route.

    IMPORTANT WORKFLOW:
        1. First call getAllRelation() or getRelation() to verify the conversion
           route exists
        2. Optionally call countId() to check how many IDs will convert
        3. Then call convertId() with your IDs

    Route keys are validated against TogoID's dataset list BEFORE the request,
    so a key that does not exist comes back naming itself with suggestions.
    Guessed names are the most common failure: NCBI/GenBank/ENA/DDBJ **protein**
    accessions (e.g. AEK21611) are `insdc_cds`, not `ncbi_protein`; NCBI Gene
    IDs are `ncbigene`; UniProt is `uniprot`. Use identifyId() when you have a
    bare accession and do not know its dataset.

    Args:
        ids: Source IDs. Accepts either a list of strings
            (e.g., ["672", "675", "7157"]) or a comma-separated string
            ("672,675,7157").
            Examples: "672,675,7157" (NCBI Gene IDs), "P38398,P04637" (UniProt)
        route: Comma-separated pair of dataset keys: 'source,target'. NOTE: this
            is a single joined string, NOT separate `source`/`target` args (as in
            countId/getRelation) — because a route may be multi-hop (3+ datasets).
            Examples:
                - 'ncbigene,uniprot' (Gene → Protein)
                - 'uniprot,pdb' (Protein → 3D Structure)
                - 'ncbigene,ensembl_gene' (NCBI Gene → Ensembl Gene)
                - 'chembl_target,uniprot' (Drug Target → Protein)
                - 'uniprot,chembl_target' (Protein → Drug Target)
                - 'ncbigene,hgnc' (Gene → HGNC symbol)
            Multi-hop routes are also supported:
                - 'ncbigene,uniprot,pdb' (Gene → Protein → Structure)
        limit: Maximum number of results (default 10000)
        offset: Pagination offset for large result sets

    Returns:
        JSON string: a bare array of [source_id, target_id] pairs.
        Example: '[["672", "P38398"], ["675", "O15129"]]'

    Common use cases:
        - Bridging databases on different SPARQL endpoints
        - Mapping gene IDs to protein accessions for UniProt SPARQL queries
        - Finding PDB structures for a set of proteins
        - Identifying ChEMBL drug targets for a list of genes
    """
    route_keys = [k.strip() for k in route.split(",") if k.strip()]
    if len(route_keys) < 2:
        raise ValueError(
            f"TogoID convertId: route must name at least two datasets "
            f"('source,target'), got {route!r}."
        )
    await _validate_dataset_keys(route_keys, context="TogoID convertId")

    params = {
        "ids": _ids_to_csv(ids),
        "route": ",".join(route_keys),
        "report": "pair",
        "format": "json",
        "limit": limit,
        "offset": offset,
        "noheader": "0",
    }

    response = await _client.get("/convert", params=params)
    raise_for_status_with_body(
        response,
        context="TogoID convertId",
        client_error_hint=(
            "Verify the route exists (getAllRelation lists valid routes) and that "
            "the IDs match the source dataset's expected format (getDataset shows "
            "the format pattern). Common cause: wrong source/target ordering, or "
            "no direct route between the two datasets."
        ),
    )
    # `results` is absent (not []) when nothing converts — coalesce so the
    # return stays a bare array, never null.
    return json.dumps(response.json().get("results") or [])


@togoid_mcp.tool(annotations=READ_ONLY_TOOL)
async def countId(source: str, target: str, ids: str | list[str]) -> dict:
    """Check how many of your IDs can be converted before doing bulk conversion.

    A lightweight pre-check: tells you how many source IDs have mappings in the
    target database WITHOUT actually returning the mapped IDs. Use this to:
        - Verify your IDs are in the correct format
        - Estimate result size before a large convertId call
        - Check if a conversion route works for your specific IDs

    This is a single-hop, pairwise check: pass `source` and `target` as two
    separate args (unlike convertId, which takes one comma-joined `route`).

    Args:
        source: Source database key (e.g., 'ncbigene', 'uniprot')
        target: Target database key (e.g., 'uniprot', 'pdb')
        ids: Source IDs to check. Accepts either a list of strings or a
            comma-separated string (e.g., ["672", "675"] or "672,675").

    Returns:
        Dictionary with:
        - source count: number of input IDs recognized
        - target count: number of target IDs found

    Example:
        >>> countId('ncbigene', 'uniprot', '672,675,7157')
        # Returns: {"source": 3, "target": 5}
        # (3 genes map to 5 UniProt entries — some genes have multiple proteins)
    """
    await _validate_dataset_keys([source, target], context="TogoID countId")
    response = await _client.get(
        f"/count/{source}-{target}", params={"ids": _ids_to_csv(ids)}
    )
    raise_for_status_with_body(
        response,
        context="TogoID countId",
        client_error_hint=(
            "Verify the route exists (getAllRelation) and IDs match the source "
            "dataset's format (getDataset)."
        ),
    )
    return response.json()

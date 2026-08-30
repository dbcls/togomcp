"""Regression tests for dbcls/togomcp#213 — the TogoID discovery surface.

Three separate ways the TogoID wrappers misled a caller, each verified against
the live API before being fixed here:

1. **All 119 dataset regexes are unusable from Python.** TogoID publishes
   .NET/JavaScript named groups `(?<id>...)`; `re.compile` raises
   `error: unknown extension ?<i`. The reporter's pipeline wrapped the compile
   in a try/except, which turned "cannot compile" into "matches nothing" — a
   silently wrong answer rather than a failure.

2. **`getRelation` denied routes `convertId` traverses.** TogoID's relation
   config is one directory per DIRECTED pair; only 32 of 302 pairs are
   registered both ways. `/count/` and `/convert` accept either orientation, so
   `getRelation` was the sole surface that 404'd on a working route.

3. **No way to ask "which dataset is this accession?"** — so an LLM guessed,
   and `ncbi_protein` (which does not exist) burned a call per attempt.

The upstream causes of 1 and 2 belong to togoid/togoid-config; these tests pin
the wrapper-side compensation, which is what our callers actually see.
"""

import json
import re

import httpx
import pytest
import respx

from togo_mcp import togoid
from togo_mcp.togoid import (
    _augment_dataset,
    _collision_scores,
    _suggest_datasets,
    _to_python_regex,
    convertId,
    countId,
    getAllDataset,
    getDataset,
    getRelation,
    identifyId,
)

_TOGOID = "https://api.togoid.dbcls.jp"

# Verbatim upstream patterns, copied from /config/dataset on 2026-08-31.
_INSDC_CDS_REGEX = (
    r"^(?:insdc.cds:)?(?<id>([A-Z]\d{5}|[A-Z]{2}\d{6}|[A-Z]{3}\d{5}"
    r"|[A-Z]{4}\d{8}|[A-J][A-Z]{2}\d{5}))(?:\.\d+)?$"
)
_UNIPROT_REGEX = (
    r"^(?:(?<id1>[A-NR-Z][0-9](?:[A-Z][A-Z0-9][A-Z0-9][0-9]){1,2}(?:-\d+)?)"
    r"|(?<id2>[OPQ][0-9][A-Z0-9][A-Z0-9][A-Z0-9][0-9](?:-\d+)?)(?:\.\d+)?)$"
)
# Upstream bug: the `(?:orf)` was meant as an alternation but sits inside the
# character class, so `(`, `?`, `:`, `o`, `r`, `f`, `)` are literal members and
# the pattern matches nearly any token.
_HGNC_SYMBOL_REGEX = r"^(?<id>[A-Z0-9_(?:orf)\-]+\@?)$"

_DATASET_CONFIG = {
    "insdc_cds": {
        "label": "GenBank/ENA/DDBJ CDS",
        "category": "Protein",
        "regex": _INSDC_CDS_REGEX,
        "examples": [["ABU85686", "BAH11229", "DAA12165"]],
    },
    "uniprot": {
        "label": "UniProt",
        "category": "Protein",
        "regex": _UNIPROT_REGEX,
        "examples": [["P38398", "Q9NYF8"]],
    },
    "hgnc_symbol": {
        "label": "HGNC gene symbol",
        "category": "Gene",
        "regex": _HGNC_SYMBOL_REGEX,
        "examples": [["BRCA1", "TP53"]],
    },
    "ncbigene": {
        "label": "NCBI Gene",
        "category": "Gene",
        "regex": r"^(?:ncbigene:)?(?<id>\d+)$",
        "examples": [["672", "7157"]],
    },
    "refseq_protein": {
        "label": "RefSeq protein",
        "category": "Protein",
        "regex": r"^(?<id>[NXWAY]P_\d+)(?:\.\d+)?$",
        "examples": [["NP_009225"]],
    },
}


@pytest.fixture(autouse=True)
def _clear_caches():
    """The dataset config and collision table are memoised for the process."""
    togoid._dataset_config_cache = None
    togoid._collision_cache = None
    yield
    togoid._dataset_config_cache = None
    togoid._collision_cache = None


def _mock_dataset_config(router: respx.Router) -> None:
    router.get(f"{_TOGOID}/config/dataset").mock(
        return_value=httpx.Response(200, json=_DATASET_CONFIG)
    )


# ---------------------------------------------------------------------------
# 1. Regex portability
# ---------------------------------------------------------------------------


class TestRegexPortability:
    def test_upstream_pattern_is_not_python_compilable(self) -> None:
        """The premise. If this ever stops raising, upstream fixed it and the
        `regex_python` twin can become a pass-through."""
        with pytest.raises(re.error):
            re.compile(_INSDC_CDS_REGEX)

    @pytest.mark.parametrize(
        "pattern", [_INSDC_CDS_REGEX, _UNIPROT_REGEX, _HGNC_SYMBOL_REGEX]
    )
    def test_rewritten_pattern_compiles(self, pattern: str) -> None:
        re.compile(_to_python_regex(pattern))

    def test_rewrite_preserves_matching_behaviour(self) -> None:
        matcher = re.compile(_to_python_regex(_INSDC_CDS_REGEX))
        assert matcher.fullmatch("AEK21611").group("id") == "AEK21611"
        assert matcher.fullmatch("insdc.cds:AEK21611").group("id") == "AEK21611"
        assert matcher.fullmatch("not-an-accession") is None

    def test_lookbehind_is_not_rewritten(self) -> None:
        """`(?<=` and `(?<!` are lookbehind, not named groups. No TogoID pattern
        uses them today, but the corpus is upstream's to change."""
        assert _to_python_regex(r"(?<=A)B") == r"(?<=A)B"
        assert _to_python_regex(r"(?<!A)B") == r"(?<!A)B"
        assert _to_python_regex(r"(?<=X)(?<id>\d+)") == r"(?<=X)(?P<id>\d+)"

    def test_multiple_named_groups_all_rewritten(self) -> None:
        """uniprot and the ensembl_* datasets carry id1..id10, not a single id."""
        rewritten = _to_python_regex(_UNIPROT_REGEX)
        assert "(?<" not in rewritten
        assert re.compile(rewritten).fullmatch("P38398")

    def test_augment_keeps_upstream_regex_byte_identical(self) -> None:
        augmented = _augment_dataset(_DATASET_CONFIG["insdc_cds"])
        assert augmented["regex"] == _INSDC_CDS_REGEX
        assert augmented["regex_flavor"] == "ecmascript"
        assert re.compile(augmented["regex_python"]).fullmatch("AEK21611")

    def test_augment_does_not_mutate_input(self) -> None:
        original = dict(_DATASET_CONFIG["uniprot"])
        _augment_dataset(_DATASET_CONFIG["uniprot"])
        assert _DATASET_CONFIG["uniprot"] == original

    def test_augment_tolerates_a_dataset_without_a_regex(self) -> None:
        assert _augment_dataset({"label": "x"}) == {"label": "x"}

    @pytest.mark.asyncio
    async def test_get_all_dataset_augments_every_entry(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = await getAllDataset()
        assert set(result) == set(_DATASET_CONFIG)
        for key, cfg in result.items():
            assert cfg["regex"] == _DATASET_CONFIG[key]["regex"]
            re.compile(cfg["regex_python"])

    @pytest.mark.asyncio
    async def test_get_dataset_augments_the_single_entry(self) -> None:
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/dataset/insdc_cds").mock(
                return_value=httpx.Response(200, json=_DATASET_CONFIG["insdc_cds"])
            )
            result = await getDataset(dataset="insdc_cds")
        assert result["regex_flavor"] == "ecmascript"
        assert re.compile(result["regex_python"]).fullmatch("AEK21611")


# ---------------------------------------------------------------------------
# 2. getRelation direction
# ---------------------------------------------------------------------------


_RELATION_BODY = [
    {
        "forward": {"display_label": "encodes", "id": "TIO_000001"},
        "reverse": {"display_label": "is encoded by", "id": "TIO_000002"},
    }
]


class TestGetRelationDirection:
    @pytest.mark.asyncio
    async def test_registered_orientation_is_labelled_source_target(self) -> None:
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/relation/uniprot-insdc_cds").mock(
                return_value=httpx.Response(200, json=_RELATION_BODY)
            )
            result = json.loads(await getRelation(source="uniprot", target="insdc_cds"))
        assert result[0]["registered_direction"] == "source-target"
        assert result[0]["forward"]["display_label"] == "encodes"

    @pytest.mark.asyncio
    async def test_unregistered_orientation_falls_back_to_the_swapped_pair(self) -> None:
        """The bug: convertId('insdc_cds,uniprot') works, but getRelation 404'd."""
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/relation/insdc_cds-uniprot").mock(
                return_value=httpx.Response(404, json={"message": "no database config found"})
            )
            router.get(f"{_TOGOID}/config/relation/uniprot-insdc_cds").mock(
                return_value=httpx.Response(200, json=_RELATION_BODY)
            )
            result = json.loads(await getRelation(source="insdc_cds", target="uniprot"))
        assert result[0]["registered_direction"] == "target-source"

    @pytest.mark.asyncio
    async def test_fallback_labels_are_reoriented_to_the_callers_direction(self) -> None:
        """`forward` must read source→target for the pair the CALLER asked about,
        or the label says the opposite of what it means."""
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/relation/insdc_cds-uniprot").mock(
                return_value=httpx.Response(404, json={})
            )
            router.get(f"{_TOGOID}/config/relation/uniprot-insdc_cds").mock(
                return_value=httpx.Response(200, json=_RELATION_BODY)
            )
            result = json.loads(await getRelation(source="insdc_cds", target="uniprot"))
        assert result[0]["forward"]["display_label"] == "is encoded by"
        assert result[0]["reverse"]["display_label"] == "encodes"

    @pytest.mark.asyncio
    async def test_both_orientations_missing_still_raises(self) -> None:
        """A genuinely absent pair must stay an error — the fallback must not
        turn "no such route" into an empty success."""
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/relation/uniprot-nosuchdb").mock(
                return_value=httpx.Response(404, json={"message": "no database config found"})
            )
            router.get(f"{_TOGOID}/config/relation/nosuchdb-uniprot").mock(
                return_value=httpx.Response(404, json={"message": "no database config found"})
            )
            with pytest.raises(ValueError, match="Neither orientation"):
                await getRelation(source="uniprot", target="nosuchdb")


# ---------------------------------------------------------------------------
# 3. Dataset-key validation and accession resolution
# ---------------------------------------------------------------------------


class TestRouteValidation:
    @pytest.mark.asyncio
    async def test_unknown_route_key_names_itself_and_suggests(self) -> None:
        """The observed failure: TogoID's own 400 says `no route: ncbi_protein
        <> uniprot`, which does not reveal WHICH half is wrong."""
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            with pytest.raises(ValueError) as excinfo:
                await convertId(ids="AEK21611", route="ncbi_protein,uniprot")
        message = str(excinfo.value)
        assert "'ncbi_protein'" in message
        assert "insdc_cds" in message
        assert "Do not retry" in message

    @pytest.mark.asyncio
    async def test_validation_happens_before_the_convert_request(self) -> None:
        with respx.mock(using="httpx", assert_all_called=False) as router:
            _mock_dataset_config(router)
            convert = router.get(f"{_TOGOID}/convert").mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            with pytest.raises(ValueError):
                await convertId(ids="AEK21611", route="ncbi_protein,uniprot")
        assert not convert.called

    @pytest.mark.asyncio
    async def test_valid_route_is_untouched(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            router.get(f"{_TOGOID}/convert").mock(
                return_value=httpx.Response(
                    200, json={"results": [["AEK21611", "G0YV74"]]}
                )
            )
            result = await convertId(ids="AEK21611", route="insdc_cds,uniprot")
        assert json.loads(result) == [["AEK21611", "G0YV74"]]

    @pytest.mark.asyncio
    async def test_multi_hop_route_validates_every_hop(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            with pytest.raises(ValueError, match="'pdb_structure'"):
                await convertId(
                    ids="672", route="ncbigene,uniprot,pdb_structure"
                )

    @pytest.mark.asyncio
    async def test_single_element_route_is_rejected(self) -> None:
        with respx.mock(using="httpx"):
            with pytest.raises(ValueError, match="at least two datasets"):
                await convertId(ids="672", route="ncbigene")

    @pytest.mark.asyncio
    async def test_countid_validates_too(self) -> None:
        with respx.mock(using="httpx", assert_all_called=False) as router:
            _mock_dataset_config(router)
            count = router.get(f"{_TOGOID}/count/ncbi_protein-uniprot").mock(
                return_value=httpx.Response(200, json={"source": 0, "target": 0})
            )
            with pytest.raises(ValueError, match="'ncbi_protein'"):
                await countId(source="ncbi_protein", target="uniprot", ids="AEK21611")
        assert not count.called

    @pytest.mark.asyncio
    async def test_rejection_refetches_the_config_first(self) -> None:
        """The memo has no TTL and the server runs for weeks, so a dataset
        registered after startup must not be rejected as nonexistent."""
        added = dict(_DATASET_CONFIG, brand_new={
            "label": "Brand new", "category": "Gene",
            "regex": r"^(?<id>BN\d+)$", "examples": [["BN1"]],
        })
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/dataset").mock(
                side_effect=[
                    httpx.Response(200, json=_DATASET_CONFIG),
                    httpx.Response(200, json=added),
                ]
            )
            router.get(f"{_TOGOID}/convert").mock(
                return_value=httpx.Response(200, json={"results": [["BN1", "P38398"]]})
            )
            result = await convertId(ids="BN1", route="brand_new,uniprot")
        assert json.loads(result) == [["BN1", "P38398"]]

    @pytest.mark.asyncio
    async def test_config_fetch_failure_disables_validation(self) -> None:
        """A TogoID outage must not block a call that would otherwise work."""
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/dataset").mock(
                return_value=httpx.Response(503, text="upstream down")
            )
            router.get(f"{_TOGOID}/convert").mock(
                return_value=httpx.Response(200, json={"results": [["672", "P38398"]]})
            )
            result = await convertId(ids="672", route="ncbigene,uniprot")
        assert json.loads(result) == [["672", "P38398"]]

    def test_alias_hints_beat_edit_distance(self) -> None:
        """`ncbi_protein` is lexically closest to `ensembl_protein`; the answer
        is `insdc_cds`, which no string metric can reach."""
        known = sorted(_DATASET_CONFIG)
        assert _suggest_datasets("ncbi_protein", known)[0] == "insdc_cds"
        assert _suggest_datasets("entrez_gene", known)[0] == "ncbigene"
        assert _suggest_datasets("uniprotkb", known)[0] == "uniprot"

    def test_alias_hints_are_filtered_to_datasets_that_exist(self) -> None:
        """The hint table is hand-written; it must never suggest a key that
        TogoID has since dropped."""
        assert "insdc_cds" not in _suggest_datasets("ncbi_protein", ["uniprot"])


class TestIdentifyId:
    @pytest.mark.asyncio
    async def test_resolves_the_accession_from_the_issue(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids="AEK21611"))
        keys = [c["dataset"] for c in result[0]["candidates"]]
        assert "insdc_cds" in keys

    @pytest.mark.asyncio
    async def test_catch_all_patterns_rank_last(self) -> None:
        """hgnc_symbol matches nearly any token; it must never crowd out a
        specific hit, or the first candidate is worse than useless."""
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids="P38398"))
        keys = [c["dataset"] for c in result[0]["candidates"]]
        assert keys[0] == "uniprot"
        assert keys[-1] == "hgnc_symbol"

    @pytest.mark.asyncio
    async def test_collision_score_is_exposed_and_ordered(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids="P38398"))
        scores = [c["pattern_collisions"] for c in result[0]["candidates"]]
        assert scores == sorted(scores)

    @pytest.mark.asyncio
    async def test_curie_disambiguates(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids="insdc.cds:AEK21611"))
        assert [c["dataset"] for c in result[0]["candidates"]] == ["insdc_cds"]

    @pytest.mark.asyncio
    async def test_category_narrows_candidates(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids="AEK21611", category="protein"))
        assert [c["dataset"] for c in result[0]["candidates"]] == ["insdc_cds"]

    @pytest.mark.asyncio
    async def test_unknown_category_is_rejected_with_the_valid_list(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            with pytest.raises(ValueError, match="unknown category"):
                await identifyId(ids="AEK21611", category="Proteins")

    @pytest.mark.asyncio
    async def test_unmatched_id_returns_an_empty_candidate_list(self) -> None:
        """Not an error: "no dataset claims this ID" is a real answer, and a
        better one than a guess."""
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids="!!! not an id !!!"))
        assert result == [{"id": "!!!", "candidates": []},
                          {"id": "not", "candidates": []},
                          {"id": "an", "candidates": []},
                          {"id": "id", "candidates": []},
                          {"id": "!!!", "candidates": []}]

    @pytest.mark.asyncio
    async def test_accepts_a_list_and_returns_one_row_per_id(self) -> None:
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = json.loads(await identifyId(ids=["AEK21611", "672"]))
        assert [row["id"] for row in result] == ["AEK21611", "672"]

    @pytest.mark.asyncio
    async def test_returns_a_json_string_of_a_bare_array(self) -> None:
        """Module convention: empty and non-empty share one wire shape."""
        with respx.mock(using="httpx") as router:
            _mock_dataset_config(router)
            result = await identifyId(ids="AEK21611")
        assert isinstance(result, str)
        assert json.loads(result)[0]["id"] == "AEK21611"

    @pytest.mark.asyncio
    async def test_empty_input_is_rejected(self) -> None:
        with respx.mock(using="httpx"):
            with pytest.raises(ValueError, match="no identifiers"):
                await identifyId(ids="   ")

    def test_collision_scores_rank_the_catch_all_highest(self) -> None:
        scores = _collision_scores(_DATASET_CONFIG)
        assert scores["hgnc_symbol"] == max(scores.values())
        assert scores["uniprot"] < scores["hgnc_symbol"]

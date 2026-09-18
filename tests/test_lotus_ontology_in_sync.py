"""The LOTUS vocabulary must describe exactly what the converter emits.

`scripts/lotus/lotus_csv_to_rdf.py` is where the properties are actually
chosen, so a vocabulary maintained anywhere else drifts the moment someone adds
a CSV column. The drift is silent — the graph still loads, the new property is
simply undefined — which is the shape of defect this repo keeps getting bitten
by. These tests make it loud.

Retargeted for the #243 model, in which the converter emits a field in one of
THREE ways, and the split is the thing worth guarding:

1. **a reused standard predicate** — Schema.org, Darwin Core, Dublin Core or
   BIBO, via `PROPERTY_IRIS`. We define nothing and must not pretend to.
2. **an `rdfs:seeAlso` IRI link** — `TAXON_LINKS` plus the intercepted `pmcid`.
   An external identifier is a pointer to another resource, not a property of
   the Wikidata subject, so it never becomes a `lotus:` term.
3. **a residual `lotus:` term** — everything with no standard equivalent. These
   are defined inline by `builtin_ontology()`, which is now the source of truth.

`lotus_ontology.ttl` is the pre-#243 vocabulary and is deliberately NOT that
source any more: it is in the retired `http://rdfportal.org/ontology/lotus#`
namespace, and the converter actively rejects it (see the legacy test below).
"""
from __future__ import annotations

import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest

LOTUS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lotus"
SCRIPT = LOTUS_DIR / "lotus_csv_to_rdf.py"
LEGACY_ONTOLOGY = LOTUS_DIR / "lotus_ontology.ttl"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"


def _load_converter():
    spec = importlib.util.spec_from_file_location("lotus_csv_to_rdf", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def converter():
    return _load_converter()


@pytest.fixture(scope="module")
def triples(converter):
    """The vocabulary the converter ships and emits by default."""
    return converter.builtin_ontology()


@pytest.fixture(scope="module")
def declared(converter, triples):
    """{local name: set of declared types} for every term in the lotus namespace."""
    out: dict[str, set[str]] = {}
    for subject, predicate, obj in triples:
        if predicate == converter.RDF_TYPE and subject.startswith(converter.LOTUS):
            out.setdefault(subject[len(converter.LOTUS) :], set()).add(obj.strip("<>"))
    return out


def _classes(declared):
    return {k for k, v in declared.items() if f"{OWL}Class" in v}


def _properties(declared):
    return {
        k
        for k, v in declared.items()
        if v & {f"{OWL}ObjectProperty", f"{OWL}DatatypeProperty"}
    }


def _sink_lotus_calls() -> set[str]:
    """Field names passed to sink.lotus() as a literal, from the source."""
    return set(re.findall(r'sink\.lotus\([^,]+,\s*"([A-Za-z0-9]+)"', SCRIPT.read_text("utf-8")))


def _emitted(converter) -> set[str]:
    """Every field the converter can write, from both sources of truth."""
    props = {prop for _, prop, _ in converter.STRUCTURE_ATTRS}
    props |= {prop for _, prop, _ in converter.ORGANISM_ATTRS}
    props |= {prop for prop, _ in converter.REF_WD_PROPS.values()}
    # The rest are written inline by the emit_* functions.
    props |= _sink_lotus_calls()
    return props


def _link_fields(converter) -> set[str]:
    """Fields emitted as an rdfs:seeAlso IRI rather than as a property value."""
    return set(converter.TAXON_LINKS) | {"pmcid"}


def _residual(converter) -> set[str]:
    """Emitted fields that stay in the lotus namespace, so we must define them."""
    return _emitted(converter) - set(converter.PROPERTY_IRIS) - _link_fields(converter)


def test_every_emitted_property_is_defined(converter, declared):
    undefined = sorted(_residual(converter) - _properties(declared))
    assert not undefined, (
        f"the converter emits lotus: properties the vocabulary never defines: {undefined}. "
        "Add them to builtin_ontology(), or map them to a standard predicate in PROPERTY_IRIS."
    )


def test_no_dead_terms_in_the_ontology(converter, declared):
    dead = sorted(_properties(declared) - _residual(converter))
    assert not dead, (
        f"builtin_ontology() defines lotus: properties the converter never emits: {dead}. "
        "Either emit them or drop them — a vocabulary describing absent data misleads."
    )


def test_every_term_carries_a_label_and_a_comment(converter, triples, declared):
    have = {(subject, predicate) for subject, predicate, _ in triples}
    missing = [
        f"{term} ({field})"
        for term in sorted(_classes(declared) | _properties(declared))
        for field in ("label", "comment")
        if (converter.LOTUS + term, f"{RDFS}{field}") not in have
    ]
    assert not missing, f"terms without an rdfs:label/rdfs:comment: {missing}"


def test_repeatable_properties_are_not_functional(converter, declared):
    """Declaring these functional would license a reasoner to merge real values.

    A compound of mixed biosynthetic origin carries several NPClassifier terms.
    `inchikey` is the other genuinely repeatable field (multi-valued on 87
    structures in v11) but is now `schema:inChIKey`, so its cardinality is
    Schema.org's to state, not ours — hence the separate reuse test below.
    """
    repeatable = {
        "npclassifierPathway",
        "npclassifierSuperclass",
        "npclassifierClass",
    }
    assert repeatable <= _residual(converter), "these should still be lotus: terms"
    offenders = sorted(
        term for term in repeatable if f"{OWL}FunctionalProperty" in declared.get(term, set())
    )
    assert not offenders, f"genuinely repeatable properties declared functional: {offenders}"


def test_only_the_occurrence_links_are_functional(converter, declared):
    """`reference` joined `structure`/`organism` as functional until #243.

    It is now `dcterms:references`, so we no longer declare its cardinality.
    """
    functional = {k for k, v in declared.items() if f"{OWL}FunctionalProperty" in v}
    assert functional == {"structure", "organism"}
    assert converter.PROPERTY_IRIS["reference"] == "http://purl.org/dc/terms/references"


def test_reused_predicates_leave_the_lotus_namespace(converter):
    """A mapping that still points at a lotus: IRI is reuse in name only."""
    fake = sorted(
        field
        for field, iri in converter.PROPERTY_IRIS.items()
        if iri.startswith(converter.LOTUS) or iri.startswith(converter.LEGACY_LOTUS)
    )
    assert not fake, f"PROPERTY_IRIS entries still in the lotus namespace: {fake}"
    assert not (set(converter.PROPERTY_IRIS) & _residual(converter)), (
        "a field cannot be both mapped to a standard predicate and a residual lotus: term"
    )


def test_link_fields_never_become_lotus_properties(converter):
    """An external identifier is a pointer, not a property of the subject.

    `pmcid` is the subtle one: it is listed in REF_WD_PROPS but intercepted in
    fold_reference_slices and emitted as an rdfs:seeAlso PMC IRI, so it must
    never reach sink.lotus.
    """
    leaked = sorted(_link_fields(converter) & _sink_lotus_calls())
    assert not leaked, f"link fields emitted as lotus: properties: {leaked}"


def test_turtle_subset_reader_rejects_what_it_cannot_parse(converter):
    with pytest.raises(converter.TurtleSubsetError, match=r":4: unsupported Turtle"):
        converter.parse_turtle_subset(
            '@prefix lotus: <http://purl.jp/bio/lotus/ontology/> .\n'
            "\n"
            "lotus:Thing a lotus:Class ;\n"
            '    lotus:x [ lotus:y "z" ] .\n',
            "bad.ttl",
        )


def test_turtle_subset_reader_rejects_an_undeclared_prefix(converter):
    with pytest.raises(converter.TurtleSubsetError, match="undeclared prefix owl:"):
        converter.parse_turtle_subset(
            "@prefix lotus: <http://purl.jp/bio/lotus/ontology/> .\n"
            "\n"
            "lotus:Thing a owl:Class .\n",
            "bad.ttl",
        )


def test_ontology_is_emitted_by_default(converter, triples):
    """The flag defaults ON: the vocabulary was left out of the first draft entirely.

    `emit_ontology` drops `rdfs:isDefinedBy` — the graph is the definition here,
    so pointing at an external document would be a promise the graph cannot keep.
    """
    sink = converter.Sink(io.StringIO(), dedupe=True)
    emitted = converter.emit_ontology(sink, triples)
    defined_by = sum(1 for _, p, _ in triples if p == f"{RDFS}isDefinedBy")
    assert emitted == len(triples) - defined_by
    assert not hasattr(converter, "DEFAULT_ONTOLOGY"), (
        "the default vocabulary is builtin_ontology(), not a file on disk"
    )


def test_emit_ontology_strips_is_defined_by(converter):
    sink = converter.Sink(io.StringIO(), dedupe=True)
    written = converter.emit_ontology(
        sink,
        [
            (converter.LOTUS + "x", f"{RDFS}label", '"x"'),
            (converter.LOTUS + "x", f"{RDFS}isDefinedBy", "<http://example.org/v>"),
        ],
    )
    assert written == 1


def test_the_legacy_vocabulary_file_is_rejected(converter):
    """lotus_ontology.ttl predates #243 and must not be loadable as --ontology.

    It is still in the repo, still parses, and is still in the retired
    namespace — which is exactly why passing it would silently re-attach
    obsolete class constraints to the reused standard terms.
    """
    text = LEGACY_ONTOLOGY.read_text("utf-8")
    parsed = converter.parse_turtle_subset(text, str(LEGACY_ONTOLOGY))
    assert any(
        converter.LEGACY_LOTUS in term for triple in parsed for term in triple
    ), "the legacy file no longer uses the retired namespace — retire this test with it"

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--metadata", str(LEGACY_ONTOLOGY),
         "--ontology", str(LEGACY_ONTOLOGY)],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "legacy LOTUS vocabulary detected" in proc.stderr

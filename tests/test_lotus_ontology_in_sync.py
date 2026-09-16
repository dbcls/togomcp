"""The LOTUS vocabulary must describe exactly what the converter emits.

`scripts/lotus/lotus_ontology.ttl` is hand-authored and
`scripts/lotus/lotus_csv_to_rdf.py` is where the properties are actually
chosen, so the two drift the moment someone adds a CSV column. The drift is
silent — the graph still loads, the new property is simply undefined — which is
the shape of defect this repo keeps getting bitten by. These tests make it loud.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

LOTUS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lotus"
ONTOLOGY = LOTUS_DIR / "lotus_ontology.ttl"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"


def _load_converter():
    spec = importlib.util.spec_from_file_location(
        "lotus_csv_to_rdf", LOTUS_DIR / "lotus_csv_to_rdf.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def converter():
    return _load_converter()


@pytest.fixture(scope="module")
def triples(converter):
    return converter.parse_turtle_subset(ONTOLOGY.read_text(encoding="utf-8"), str(ONTOLOGY))


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


def _emitted(converter) -> set[str]:
    """Every lotus: property the converter can write, from both sources of truth."""
    props = {prop for _, prop, _ in converter.STRUCTURE_ATTRS}
    props |= {prop for _, prop, _ in converter.ORGANISM_ATTRS}
    props |= {prop for prop, _ in converter.REF_WD_PROPS.values()}
    # The rest are written inline by the emit_* functions.
    source = (LOTUS_DIR / "lotus_csv_to_rdf.py").read_text(encoding="utf-8")
    props |= set(re.findall(r'sink\.lotus\([^,]+,\s*"([A-Za-z0-9]+)"', source))
    return props


def test_every_emitted_property_is_defined(converter, declared):
    undefined = sorted(_emitted(converter) - _properties(declared))
    assert not undefined, (
        f"the converter emits lotus: properties the ontology never defines: {undefined}. "
        f"Add them to {ONTOLOGY.name}."
    )


def test_no_dead_terms_in_the_ontology(converter, declared):
    dead = sorted(_properties(declared) - _emitted(converter))
    assert not dead, (
        f"{ONTOLOGY.name} defines lotus: properties the converter never emits: {dead}. "
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


def test_repeatable_properties_are_not_functional(declared):
    """Declaring these functional would license a reasoner to merge real values.

    lotus:inchikey is multi-valued on 87 structures in v11, and a compound of
    mixed biosynthetic origin carries several NPClassifier terms.
    """
    repeatable = {
        "inchikey",
        "npclassifierPathway",
        "npclassifierSuperclass",
        "npclassifierClass",
    }
    offenders = sorted(
        term for term in repeatable if f"{OWL}FunctionalProperty" in declared.get(term, set())
    )
    assert not offenders, f"genuinely repeatable properties declared functional: {offenders}"


def test_only_the_occurrence_links_are_functional(declared):
    functional = {k for k, v in declared.items() if f"{OWL}FunctionalProperty" in v}
    assert functional == {"structure", "organism", "reference"}


def test_turtle_subset_reader_rejects_what_it_cannot_parse(converter):
    with pytest.raises(converter.TurtleSubsetError, match=r":4: unsupported Turtle"):
        converter.parse_turtle_subset(
            '@prefix lotus: <http://rdfportal.org/ontology/lotus#> .\n'
            "\n"
            "lotus:Thing a lotus:Class ;\n"
            '    lotus:x [ lotus:y "z" ] .\n',
            "bad.ttl",
        )


def test_turtle_subset_reader_rejects_an_undeclared_prefix(converter):
    with pytest.raises(converter.TurtleSubsetError, match="undeclared prefix owl:"):
        converter.parse_turtle_subset(
            "@prefix lotus: <http://rdfportal.org/ontology/lotus#> .\n"
            "\n"
            "lotus:Thing a owl:Class .\n",
            "bad.ttl",
        )


def test_ontology_is_emitted_by_default(converter):
    """The flag defaults ON: the vocabulary was left out of the first draft entirely."""
    import io

    triples = converter.parse_turtle_subset(ONTOLOGY.read_text(encoding="utf-8"), str(ONTOLOGY))
    sink = converter.Sink(io.StringIO(), dedupe=True)
    assert converter.emit_ontology(sink, triples) == len(triples)
    assert converter.DEFAULT_ONTOLOGY == ONTOLOGY

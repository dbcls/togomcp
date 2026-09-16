#!/usr/bin/env python3
"""Convert the LOTUS frozen CSV export into RDF (N-Triples).

LOTUS publishes no RDF. Its releases are frozen CSV tables on Zenodo (v11 =
2026-04-13, DOI 10.5281/zenodo.19360665), regenerated from live Wikidata by the
project's own exporter. This script turns those tables into the graph
described in `lotus_schema.md`, so RDF Portal can host a *dated, citable*
LOTUS instead of re-deriving a moving target from Wikidata at query time.

Entity identity is the Wikidata IRI (`wd:Q…`) for structures, organisms and
references, so the graph joins to Wikidata itself and to IDSM's Wikidata
compound mirror without any mapping table. Cross-reference IRIs use the same
forms as the RDF Portal databases they point at (PubChem compound, NCBI
taxonomy, PubMed), so a federated join needs no rewriting.

A release ships TWO tables and they disagree. The metadata table carries all
the attributes, but the **core table is authoritative for which triples exist**:
in v11 the core table holds 48 (structure, organism, reference) triples the
metadata table never mentions, and flags 2 manually-validated triples the
metadata table does not. Converting from `--metadata` alone therefore drops
them silently, so pass `--core` as well; it adds what is missing and leaves
everything else untouched.

Two more properties of the source drive the design:

* The CSV is DENORMALIZED and its entity attributes are MULTI-VALUED: one
  (structure, organism, reference) triple can span several rows because a
  compound carries two PubChem CIDs or an organism two GBIF ids (57,759 of
  709,740 rows in v11). Entity attributes therefore get set semantics, and an
  occurrence is keyed by the triple, not by the row.
* `manual_validation` is `Y` on only 187 rows and `NA` otherwise; `NA` means
  "not manually checked", not "false", so it is emitted only when true.

The reference rows carry just a DOI. Titles, dates and PMIDs are not in the
CSV despite what the Zenodo description says, so `--refs-nt` optionally folds
in the reference slices of a Wikidata CONSTRUCT export (see `export_lotus.sh`).

The 290-triple vocabulary in `lotus_ontology.ttl` is emitted BY DEFAULT, into
the same named graph as the data, so a conversion cannot ship 9.1 M triples
whose every `lotus:` term is undefined. It is a separate file because it is
hand-authored prose on a review cycle of its own, and it goes in the same
graph because a TogoMCP query pins its graph — a vocabulary in a second graph
is invisible under that pin. `--no-ontology` opts out; `--ontology PATH`
points elsewhere.

Usage:
    # both tables: --metadata for the attributes, --core for completeness
    python scripts/lotus/lotus_csv_to_rdf.py \
        --metadata 260413_frozen_metadata.csv.gz \
        --core 260413_frozen.csv.gz \
        --out lotus.nt.gz --version v11 --issued 2026-04-13

    # and fold in reference titles/dates/PMIDs from a Wikidata export
    python scripts/lotus/lotus_csv_to_rdf.py ... --refs-nt out/

Output is N-Triples, deduplicated in memory (~400 MB peak for v11). With
`--no-dedupe` the memory goes away and duplicate lines do not: pipe the result
through `LC_ALL=C sort -u` instead.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any
from urllib.parse import quote

LOTUS = "http://rdfportal.org/ontology/lotus#"
DATASET = "http://rdfportal.org/dataset/lotus"
DEFAULT_ONTOLOGY = Path(__file__).resolve().parent / "lotus_ontology.ttl"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_SEEALSO = "http://www.w3.org/2000/01/rdf-schema#seeAlso"
SKOS_EXACT = "http://www.w3.org/2004/02/skos/core#exactMatch"
XSD = "http://www.w3.org/2001/XMLSchema#"

PUBCHEM_CID = "http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID"
NCBI_TAXON = "http://identifiers.org/taxonomy/"
PUBMED = "http://rdf.ncbi.nlm.nih.gov/pubmed/"
DOI_ORG = "https://doi.org/"
GBIF_SPECIES = "https://www.gbif.org/species/"

# (csv column, property local name, value kind). "decimal"/"integer" are typed
# literals; "string" is a plain one. Values are validated before typing —
# a malformed number is dropped rather than emitted as a lie. "multi" is a
# cell packing several values behind MULTI_SEP, which the NPClassifier columns
# do on up to 11.6% of rows ("Fatty acids $ Polyketides"); each becomes its own
# triple, or a class filter silently misses every co-classified compound.
STRUCTURE_ATTRS: tuple[tuple[str, str, str], ...] = (
    ("structure_inchikey", "inchikey", "string"),
    ("structure_inchi", "inchi", "string"),
    ("structure_smiles", "smiles", "string"),
    ("structure_smiles_2D", "smiles2D", "string"),
    ("structure_molecular_formula", "molecularFormula", "string"),
    ("structure_exact_mass", "exactMass", "decimal"),
    ("structure_xlogp", "xlogp", "decimal"),
    ("structure_nameIupac", "iupacName", "string"),
    ("structure_nameTraditional", "traditionalName", "string"),
    ("structure_stereocenters_total", "stereocenterCount", "integer"),
    ("structure_stereocenters_unspecified", "unspecifiedStereocenterCount", "integer"),
    ("structure_taxonomy_npclassifier_01pathway", "npclassifierPathway", "multi"),
    ("structure_taxonomy_npclassifier_02superclass", "npclassifierSuperclass", "multi"),
    ("structure_taxonomy_npclassifier_03class", "npclassifierClass", "multi"),
    ("structure_taxonomy_classyfire_01kingdom", "classyfireKingdom", "string"),
    ("structure_taxonomy_classyfire_02superclass", "classyfireSuperclass", "string"),
    ("structure_taxonomy_classyfire_03class", "classyfireClass", "string"),
    ("structure_taxonomy_classyfire_04directparent", "classyfireDirectParent", "string"),
)

ORGANISM_ATTRS: tuple[tuple[str, str, str], ...] = (
    ("organism_name", "scientificName", "string"),
    ("organism_taxonomy_gbifid", "gbifTaxonId", "string"),
    ("organism_taxonomy_ncbiid", "ncbiTaxonId", "string"),
    ("organism_taxonomy_ottid", "ottTaxonId", "string"),
    ("organism_taxonomy_01domain", "taxonDomain", "string"),
    ("organism_taxonomy_02kingdom", "taxonKingdom", "string"),
    ("organism_taxonomy_03phylum", "taxonPhylum", "string"),
    ("organism_taxonomy_04class", "taxonClass", "string"),
    ("organism_taxonomy_05order", "taxonOrder", "string"),
    ("organism_taxonomy_06family", "taxonFamily", "string"),
    ("organism_taxonomy_07tribe", "taxonTribe", "string"),
    ("organism_taxonomy_08genus", "taxonGenus", "string"),
    ("organism_taxonomy_09species", "taxonSpecies", "string"),
    ("organism_taxonomy_10varietas", "taxonVarietas", "string"),
)

# Wikidata properties folded in by --refs-nt, keyed by the wdt: IRI.
REF_WD_PROPS: dict[str, tuple[str, str]] = {
    "http://www.wikidata.org/prop/direct/P577": ("publicationDate", "date"),
    "http://www.wikidata.org/prop/direct/P698": ("pmid", "string"),
    "http://www.wikidata.org/prop/direct/P932": ("pmcid", "string"),
    "http://www.wikidata.org/prop/direct/P1433": ("publishedIn", "iri"),
    RDFS_LABEL: ("title", "string"),
}

MULTI_SEP = " $ "

_DECIMAL_RE = re.compile(r"-?\d+(\.\d+)?$")
_INTEGER_RE = re.compile(r"\d+$")
_NT_ESCAPES = str.maketrans(
    {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
)
_NT_UNESCAPES = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\", "'": "'"}
_UNESCAPE_RE = re.compile(r"\\([nrt\"\\'])")


def lit(value: str) -> str:
    """A plain N-Triples literal."""
    return f'"{value.translate(_NT_ESCAPES)}"'


def iri_ref(value: str) -> str:
    """An N-Triples IRI reference, percent-encoding characters IRIs forbid.

    Needed for DOIs: Wiley minted thousands in the shape
    `10.1002/1099-0690(200104)2001:8<1459::AID-EJOC1459>3.0.CO;2-0`, and an
    unescaped `>` closes the IRI early — a file that looks fine until a parser
    rejects two lines out of nine million.
    """
    return "<{}>".format(quote(value, safe="!#$&'()*+,-./:;=?@[]_~%"))


def typed(value: str, datatype: str) -> str:
    return f'"{value.translate(_NT_ESCAPES)}"^^<{XSD}{datatype}>'


def obj_for(value: str, kind: str) -> str | None:
    """Render one CSV cell as an N-Triples object, or None if unusable."""
    if kind == "string":
        return lit(value)
    if kind == "decimal":
        return typed(value, "decimal") if _DECIMAL_RE.match(value) else None
    if kind == "integer":
        return typed(value, "integer") if _INTEGER_RE.match(value) else None
    if kind == "date":
        # Wikidata dates arrive as 1998-01-01T00:00:00Z.
        return typed(value[:10], "date") if re.match(r"\d{4}-\d{2}-\d{2}", value) else None
    if kind == "iri":
        return iri_ref(value)
    raise ValueError(f"unknown value kind: {kind}")


class Sink:
    """Writes N-Triples, optionally dropping lines it has already written."""

    def __init__(self, out: IO[str], *, dedupe: bool) -> None:
        self._out = out
        self._seen: set[int] | None = set() if dedupe else None
        self.written = 0

    def triple(self, subject: str, predicate: str, obj: str) -> None:
        line = f"<{subject}> <{predicate}> {obj} .\n"
        if self._seen is not None:
            h = hash(line)
            if h in self._seen:
                return
            self._seen.add(h)
        self._out.write(line)
        self.written += 1

    def lotus(self, subject: str, prop: str, obj: str) -> None:
        self.triple(subject, f"{LOTUS}{prop}", obj)


def open_csv(path: Path) -> IO[str]:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def rows_of(path: Path) -> Iterator[dict[str, str]]:
    with open_csv(path) as fh:
        yield from csv.DictReader(fh)


def emit_structure(sink: Sink, row: dict[str, str]) -> str:
    iri = row["structure_wikidata"]
    sink.triple(iri, RDF_TYPE, f"<{LOTUS}Structure>")
    for column, prop, kind in STRUCTURE_ATTRS:
        value = row.get(column, "")
        if not value:
            continue
        if kind == "multi":
            for part in value.split(MULTI_SEP):
                if part := part.strip():
                    sink.lotus(iri, prop, lit(part))
        elif obj := obj_for(value, kind):
            sink.lotus(iri, prop, obj)
    if name := row.get("structure_nameTraditional", ""):
        sink.triple(iri, RDFS_LABEL, lit(name))
    # ClassyFire's numeric id, padded to the canonical CHEMONTID form. Left as a
    # literal on purpose: ChemOnt has no agreed resolvable IRI namespace.
    chemont = row.get("structure_taxonomy_classyfire_chemontid", "")
    if chemont and _INTEGER_RE.match(chemont):
        sink.lotus(iri, "chemontId", lit(f"CHEMONTID:{int(chemont):07d}"))
    cid = row.get("structure_cid", "")
    if cid and _INTEGER_RE.match(cid):
        sink.lotus(iri, "pubchemCompoundId", lit(cid))
        sink.triple(iri, SKOS_EXACT, iri_ref(f"{PUBCHEM_CID}{cid}"))
    return iri


def emit_organism(sink: Sink, row: dict[str, str]) -> str:
    iri = row["organism_wikidata"]
    sink.triple(iri, RDF_TYPE, f"<{LOTUS}Organism>")
    for column, prop, kind in ORGANISM_ATTRS:
        value = row.get(column, "")
        if value and (obj := obj_for(value, kind)):
            sink.lotus(iri, prop, obj)
    if name := row.get("organism_name", ""):
        sink.triple(iri, RDFS_LABEL, lit(name))
    taxid = row.get("organism_taxonomy_ncbiid", "")
    if taxid and _INTEGER_RE.match(taxid):
        sink.triple(iri, SKOS_EXACT, iri_ref(f"{NCBI_TAXON}{taxid}"))
    gbif = row.get("organism_taxonomy_gbifid", "")
    if gbif and _INTEGER_RE.match(gbif):
        sink.triple(iri, RDFS_SEEALSO, iri_ref(f"{GBIF_SPECIES}{gbif}"))
    return iri


def emit_reference(sink: Sink, row: dict[str, str]) -> str:
    iri = row["reference_wikidata"]
    sink.triple(iri, RDF_TYPE, f"<{LOTUS}Reference>")
    if doi := row.get("reference_doi", ""):
        sink.lotus(iri, "doi", lit(doi))
        sink.triple(iri, RDFS_SEEALSO, iri_ref(f"{DOI_ORG}{doi}"))
    return iri


def occurrence_iri(structure: str, organism: str, reference: str) -> str:
    """Deterministic IRI for one (structure, organism, reference) triple.

    Built from the three QIDs so a re-run of the same release reproduces the
    same IRIs byte for byte, and two releases can be diffed directly.
    """
    return "{}/occurrence/{}_{}_{}".format(
        DATASET,
        structure.rsplit("/", 1)[-1],
        organism.rsplit("/", 1)[-1],
        reference.rsplit("/", 1)[-1],
    )


def emit_occurrence(
    sink: Sink, structure: str, organism: str, reference: str, *, validated: bool
) -> str:
    iri = occurrence_iri(structure, organism, reference)
    sink.triple(iri, RDF_TYPE, f"<{LOTUS}Occurrence>")
    sink.lotus(iri, "structure", f"<{structure}>")
    sink.lotus(iri, "organism", f"<{organism}>")
    sink.lotus(iri, "reference", f"<{reference}>")
    if validated:
        sink.lotus(iri, "manuallyValidated", typed("true", "boolean"))
    return iri


class Corpus:
    """What the metadata pass saw, so later passes can extend without re-reading."""

    def __init__(self) -> None:
        self.structures: set[str] = set()
        self.organisms: set[str] = set()
        self.references: set[str] = set()
        self.occurrences: set[str] = set()
        self.rows = 0
        self.validated: set[str] = set()

    def stats(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "occurrences": len(self.occurrences),
            "structures": len(self.structures),
            "organisms": len(self.organisms),
            "references": len(self.references),
            "manually_validated": len(self.validated),
        }


def convert(metadata: Path, sink: Sink) -> Corpus:
    corpus = Corpus()
    for row in rows_of(metadata):
        corpus.rows += 1
        structure = emit_structure(sink, row)
        organism = emit_organism(sink, row)
        reference = emit_reference(sink, row)
        corpus.structures.add(structure)
        corpus.organisms.add(organism)
        corpus.references.add(reference)

        iri = occurrence_iri(structure, organism, reference)
        if iri in corpus.occurrences:
            continue
        validated = row.get("manual_validation", "") == "Y"
        emit_occurrence(sink, structure, organism, reference, validated=validated)
        corpus.occurrences.add(iri)
        if validated:
            corpus.validated.add(iri)
    return corpus


def fold_core(sink: Sink, core: Path, corpus: Corpus) -> dict[str, int]:
    """Add the occurrences the CORE table has and the metadata table lacks.

    The core table — not the metadata table — is authoritative for which
    triples the release contains. In v11 it holds 48 triples absent from the
    metadata table and flags 2 manually-validated triples the metadata table
    does not, so converting from `--metadata` alone silently drops them.

    Core carries only InChIKey, organism name and DOI, so entities reached this
    way are thin. That is the correct trade: an occurrence with three
    attributes is recoverable, a missing one is invisible.
    """
    added_occurrences = 0
    added_validations = 0
    for row in rows_of(core):
        structure = row["structure_wikidata"]
        organism = row["organism_wikidata"]
        reference = row["reference_wikidata"]
        iri = occurrence_iri(structure, organism, reference)
        validated = row.get("manual_validation", "") == "Y"

        if iri not in corpus.occurrences:
            emit_occurrence(sink, structure, organism, reference, validated=validated)
            corpus.occurrences.add(iri)
            added_occurrences += 1
            if inchikey := row.get("structure_inchikey", ""):
                sink.triple(structure, RDF_TYPE, f"<{LOTUS}Structure>")
                sink.lotus(structure, "inchikey", lit(inchikey))
                corpus.structures.add(structure)
            sink.triple(organism, RDF_TYPE, f"<{LOTUS}Organism>")
            corpus.organisms.add(organism)
            if name := row.get("organism_name", ""):
                sink.lotus(organism, "scientificName", lit(name))
                sink.triple(organism, RDFS_LABEL, lit(name))
            emit_reference(sink, row)
            corpus.references.add(reference)
        elif validated and iri not in corpus.validated:
            sink.lotus(iri, "manuallyValidated", typed("true", "boolean"))
            added_validations += 1

        if validated:
            corpus.validated.add(iri)

    return {
        "core_only_occurrences": added_occurrences,
        "core_only_validations": added_validations,
    }


_NT_LINE = re.compile(r"^<([^>]+)> <([^>]+)> (.+) \.$")


def fold_reference_slices(sink: Sink, refs_dir: Path, references: set[str]) -> int:
    """Add title/date/PMID/PMCID/venue from a Wikidata CONSTRUCT export.

    Only references that the CSV already names are folded in, so a stale or
    broader export cannot widen the dataset.
    """
    added = 0
    for path in sorted(refs_dir.glob("ref_*.nt")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                m = _NT_LINE.match(line.rstrip("\n"))
                if not m:
                    continue
                subject, predicate, raw = m.groups()
                if subject not in references or predicate not in REF_WD_PROPS:
                    continue
                prop, kind = REF_WD_PROPS[predicate]
                value = raw[1:-1] if raw.startswith("<") else _plain_literal(raw)
                if value is None:
                    continue
                if (obj := obj_for(value, kind)) is not None:
                    before = sink.written
                    sink.lotus(subject, prop, obj)
                    if prop == "title":
                        sink.triple(subject, RDFS_LABEL, lit(value))
                    if prop == "pmid" and _INTEGER_RE.match(value):
                        sink.triple(subject, SKOS_EXACT, iri_ref(f"{PUBMED}{value}"))
                    added += sink.written - before
    return added


def _plain_literal(raw: str) -> str | None:
    """Unwrap `"text"`, `"text"@en` or `"text"^^<dt>` to its lexical form."""
    if not raw.startswith('"'):
        return None
    end = raw.rfind('"')
    if end <= 0:
        return None
    return _UNESCAPE_RE.sub(lambda m: _NT_UNESCAPES[m.group(1)], raw[1:end])


class TurtleSubsetError(ValueError):
    """The ontology file uses Turtle this reader deliberately does not accept."""


# A small Turtle reader, enough for `lotus_ontology.ttl` and nothing more.
# Supported: @prefix, `a`, IRIs, prefixed names, plain/long/typed/language
# literals, `;` and `,` lists, `#` comments. NOT supported: blank nodes, `[]`,
# collections, numeric and boolean shorthand, @base. Anything else raises with
# a line number rather than being guessed at — the alternative to a parser here
# is a second, drifting copy of the vocabulary inside this file.
_TTL_TOKEN = re.compile(
    r"""  (?P<ws>\s+)
        | (?P<comment>\#[^\n]*)
        | (?P<directive>@prefix\b)
        | (?P<longstr>\"\"\"(?:[^"\\]|\\.|"(?!""))*\"\"\")
        | (?P<string>"(?:[^"\\\n]|\\.)*")
        | (?P<iri><[^>\s]*>)
        | (?P<pname>[A-Za-z][A-Za-z0-9_-]*:(?:[A-Za-z0-9_][A-Za-z0-9_-]*)?)
        | (?P<lang>@[A-Za-z]+(?:-[A-Za-z0-9]+)*)
        | (?P<dtsep>\^\^)
        | (?P<keyword>a(?![A-Za-z0-9_:-]))
        | (?P<punct>[;,.])
    """,
    re.VERBOSE,
)


_TTL_BAD_ESCAPE = re.compile(r"\\(?![nrt\"\\'])")


def _ttl_tokens(text: str, label: str) -> list[tuple[str, str, int]]:
    tokens: list[tuple[str, str, int]] = []
    pos, line = 0, 1
    while pos < len(text):
        m = _TTL_TOKEN.match(text, pos)
        if m is None:
            snippet = text[pos : pos + 40].split("\n", 1)[0]
            raise TurtleSubsetError(f"{label}:{line}: unsupported Turtle at {snippet!r}")
        kind, value = m.lastgroup, m.group()
        if kind not in ("ws", "comment"):
            tokens.append((kind or "", value, line))
        line += value.count("\n")
        pos = m.end()
    return tokens


def parse_turtle_subset(text: str, label: str) -> list[tuple[str, str, str]]:
    """Parse the ontology file into (subject IRI, predicate IRI, N-Triples object)."""
    tokens = _ttl_tokens(text, label)
    prefixes: dict[str, str] = {}
    triples: list[tuple[str, str, str]] = []
    i, n = 0, len(tokens)

    def fail(what: str) -> TurtleSubsetError:
        got, line = (tokens[i][1], tokens[i][2]) if i < n else ("end of file", "EOF")
        return TurtleSubsetError(f"{label}:{line}: expected {what}, got {got!r}")

    def take(*kinds: str, what: str) -> tuple[str, str, int]:
        nonlocal i
        if i >= n or tokens[i][0] not in kinds:
            raise fail(what)
        token = tokens[i]
        i += 1
        return token

    def take_punct(char: str) -> None:
        nonlocal i
        if i >= n or tokens[i][0] != "punct" or tokens[i][1] != char:
            raise fail(f"{char!r}")
        i += 1

    def at_punct(char: str) -> bool:
        return i < n and tokens[i][0] == "punct" and tokens[i][1] == char

    def as_iri(kind: str, value: str, line: int) -> str:
        if kind == "iri":
            return value[1:-1]
        prefix, _, local = value.partition(":")
        if prefix not in prefixes:
            raise TurtleSubsetError(f"{label}:{line}: undeclared prefix {prefix}:")
        return prefixes[prefix] + local

    def read_object() -> str:
        nonlocal i
        kind, value, line = take("iri", "pname", "string", "longstr", what="an object")
        if kind in ("iri", "pname"):
            return f"<{as_iri(kind, value, line)}>"
        body = value[3:-3] if kind == "longstr" else value[1:-1]
        # \uXXXX and friends would survive unescaping as literal backslash text
        # and then be re-escaped into the output — wrong, and silently so.
        if _TTL_BAD_ESCAPE.search(body):
            raise TurtleSubsetError(
                f"{label}:{line}: unsupported string escape; this reader takes only "
                r"\n \r \t \" \\ \' — write the character itself, the file is UTF-8"
            )
        obj = lit(_UNESCAPE_RE.sub(lambda m: _NT_UNESCAPES[m.group(1)], body))
        if i < n and tokens[i][0] == "lang":
            tag = tokens[i][1]
            i += 1
            return obj + tag
        if i < n and tokens[i][0] == "dtsep":
            i += 1
            dt_kind, dt_value, dt_line = take("iri", "pname", what="a datatype IRI")
            return f"{obj}^^<{as_iri(dt_kind, dt_value, dt_line)}>"
        return obj

    while i < n:
        if tokens[i][0] == "directive":
            i += 1
            prefix_token = take("pname", what="a prefix such as `lotus:`")
            if not prefix_token[1].endswith(":"):
                raise TurtleSubsetError(
                    f"{label}:{prefix_token[2]}: expected a bare prefix such as "
                    f"`lotus:`, got {prefix_token[1]!r}"
                )
            namespace = take("iri", what="a namespace IRI")[1]
            take_punct(".")
            prefixes[prefix_token[1][:-1]] = namespace[1:-1]
            continue

        subject = as_iri(*take("iri", "pname", what="a subject IRI"))
        while True:
            kind, value, line = take("iri", "pname", "keyword", what="a predicate")
            predicate = RDF_TYPE if kind == "keyword" else as_iri(kind, value, line)
            while True:
                triples.append((subject, predicate, read_object()))
                if not at_punct(","):
                    break
                i += 1
            if at_punct(";"):
                i += 1
                if at_punct("."):  # trailing `;` before the terminator
                    break
                continue
            break
        take_punct(".")

    return triples


def emit_ontology(sink: Sink, triples: list[tuple[str, str, str]]) -> int:
    """Write the vocabulary into the same graph as the data.

    Not a separate graph, deliberately. Every TogoMCP query pins its graph, and
    a vocabulary sitting in a second graph is invisible under that pin: schema
    discovery through SPARQL returns 0 rows and the properties look
    undocumented. RDF Portal's `taxonomy` graph carries its DDBJ TBox inline
    the same way, and 290 triples against 9.1 M costs nothing.
    """
    before = sink.written
    for subject, predicate, obj in triples:
        sink.triple(subject, predicate, obj)
    return sink.written - before


def emit_dataset_metadata(
    sink: Sink, *, version: str, issued: str, source: str, endpoint: str
) -> None:
    """VoID/PAV header: what release this is, and where it came from.

    This is the point of converting the frozen CSV rather than querying
    Wikidata live — the graph can state which LOTUS release it holds.
    """
    dcterms = "http://purl.org/dc/terms/"
    pav = "http://purl.org/pav/"
    void = "http://rdfs.org/ns/void#"
    sink.triple(DATASET, RDF_TYPE, f"<{void}Dataset>")
    sink.triple(DATASET, f"{dcterms}title", lit("LOTUS natural products occurrences"))
    sink.triple(DATASET, f"{dcterms}description", lit(
        "Structure-organism occurrences of natural products, each documented by "
        "a literature reference. Converted from the LOTUS frozen CSV export."
    ))
    sink.triple(DATASET, f"{pav}version", lit(version))
    sink.triple(DATASET, f"{dcterms}issued", typed(issued, "date"))
    sink.triple(DATASET, f"{pav}retrievedFrom", f"<{source}>")
    sink.triple(DATASET, f"{dcterms}source", f"<{source}>")
    sink.triple(DATASET, f"{pav}createdOn", typed(
        datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "dateTime"
    ))
    sink.triple(DATASET, f"{dcterms}creator", lit("The LOTUS Initiative"))
    sink.triple(DATASET, f"{dcterms}publisher", lit("Database Center for Life Science (DBCLS)"))
    sink.triple(DATASET, f"{void}sparqlEndpoint", f"<{endpoint}>")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", required=True, type=Path, help="*_frozen_metadata.csv[.gz]")
    ap.add_argument("--out", type=Path, help="output .nt or .nt.gz (default: stdout)")
    ap.add_argument("--version", default="v11", help="LOTUS release label, e.g. v11")
    ap.add_argument("--issued", default="2026-04-13", help="release date (YYYY-MM-DD)")
    ap.add_argument(
        "--source",
        default="https://doi.org/10.5281/zenodo.19360665",
        help="DOI/URL the CSV was downloaded from",
    )
    ap.add_argument(
        "--endpoint",
        default="https://rdfportal.org/primary/sparql",
        help="endpoint this graph will be served from (DBCLS decides which)",
    )
    ap.add_argument(
        "--core",
        type=Path,
        help="*_frozen.csv[.gz] — RECOMMENDED. The core table is authoritative for "
        "which triples the release contains: in v11 it holds 48 occurrences the "
        "metadata table lacks, and 2 manual-validation flags it lacks.",
    )
    ap.add_argument(
        "--refs-nt",
        type=Path,
        help="directory of ref_*.nt slices from a Wikidata export, for reference "
        "titles/dates/PMIDs (absent from the CSV)",
    )
    ap.add_argument(
        "--ontology",
        type=Path,
        default=DEFAULT_ONTOLOGY,
        help=f"vocabulary to emit into the same graph as the data (default: {DEFAULT_ONTOLOGY.name})",
    )
    ap.add_argument(
        "--no-ontology",
        action="store_true",
        help="build the graph WITHOUT its vocabulary — every lotus: term then goes undefined",
    )
    ap.add_argument("--no-dedupe", action="store_true", help="skip in-memory dedupe; pipe through `sort -u`")
    args = ap.parse_args(argv)

    # Read and parse the vocabulary BEFORE touching the output: a typo in the
    # Turtle should cost a second, not 100 s of conversion and a 1.3 GB file.
    ontology: list[tuple[str, str, str]] = []
    if not args.no_ontology:
        if not args.ontology.is_file():
            ap.error(
                f"ontology file not found: {args.ontology}\n"
                "Pass --ontology PATH, or --no-ontology to build a graph whose "
                "lotus: terms are all undefined."
            )
        try:
            ontology = parse_turtle_subset(
                args.ontology.read_text(encoding="utf-8"), str(args.ontology)
            )
        except TurtleSubsetError as exc:
            print(f"error: {exc}", file=sys.stderr)
            print(
                "This reader takes only the Turtle subset the vocabulary uses "
                "(see the header of lotus_ontology.ttl).",
                file=sys.stderr,
            )
            return 1

    if args.out and args.out.suffix == ".gz":
        out: IO[str] = gzip.open(args.out, "wt", encoding="utf-8")  # noqa: SIM115
    elif args.out:
        out = args.out.open("wt", encoding="utf-8")
    else:
        out = sys.stdout

    try:
        sink = Sink(out, dedupe=not args.no_dedupe)
        ontology_triples = emit_ontology(sink, ontology)
        emit_dataset_metadata(
            sink,
            version=args.version,
            issued=args.issued,
            source=args.source,
            endpoint=args.endpoint,
        )
        corpus = convert(args.metadata, sink)
        extra = fold_core(sink, args.core, corpus) if args.core else {}
        stats = corpus.stats() | extra
        stats["ontology_triples"] = ontology_triples
        if args.refs_nt:
            stats["reference_triples_folded_in"] = fold_reference_slices(
                sink, args.refs_nt, corpus.references
            )
        stats["triples"] = sink.written
    finally:
        if out is not sys.stdout:
            out.close()

    for key, value in stats.items():
        print(f"{key}: {value:,}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Convert the LOTUS frozen CSV export into RDF (N-Triples).

LOTUS publishes no RDF. Its releases are frozen CSV tables on Zenodo (v11 =
2026-04-13, DOI 10.5281/zenodo.19360665), regenerated from live Wikidata by the
project's own exporter. This script turns the metadata table into the graph
described in `lotus_schema.md`, so RDF Portal can host a *dated, citable*
LOTUS instead of re-deriving a moving target from Wikidata at query time.

Entity identity is the Wikidata IRI (`wd:Q…`) for structures, organisms and
references, so the graph joins to Wikidata itself and to IDSM's Wikidata
compound mirror without any mapping table. Cross-reference IRIs use the same
forms as the RDF Portal databases they point at (PubChem compound, NCBI
taxonomy, PubMed), so a federated join needs no rewriting.

Two properties of the source drive the design:

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

Usage:
    python scripts/lotus/lotus_csv_to_rdf.py \
        --metadata 260413_frozen_metadata.csv.gz \
        --out lotus.nt.gz --version v11 --issued 2026-04-13

    # fold in reference titles/dates/PMIDs from a Wikidata export
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


def convert(metadata: Path, sink: Sink) -> dict[str, Any]:
    structures: set[str] = set()
    organisms: set[str] = set()
    references: set[str] = set()
    occurrences: set[str] = set()
    rows = 0
    validated = 0

    for row in rows_of(metadata):
        rows += 1
        structure = emit_structure(sink, row)
        organism = emit_organism(sink, row)
        reference = emit_reference(sink, row)
        structures.add(structure)
        organisms.add(organism)
        references.add(reference)

        iri = occurrence_iri(structure, organism, reference)
        if iri not in occurrences:
            occurrences.add(iri)
            sink.triple(iri, RDF_TYPE, f"<{LOTUS}Occurrence>")
            sink.lotus(iri, "structure", f"<{structure}>")
            sink.lotus(iri, "organism", f"<{organism}>")
            sink.lotus(iri, "reference", f"<{reference}>")
            if row.get("manual_validation", "") == "Y":
                validated += 1
                sink.lotus(iri, "manuallyValidated", typed("true", "boolean"))

    return {
        "rows": rows,
        "occurrences": len(occurrences),
        "structures": len(structures),
        "organisms": len(organisms),
        "references": len(references),
        "manually_validated": validated,
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
        "--refs-nt",
        type=Path,
        help="directory of ref_*.nt slices from a Wikidata export, for reference "
        "titles/dates/PMIDs (absent from the CSV)",
    )
    ap.add_argument("--no-dedupe", action="store_true", help="skip in-memory dedupe; pipe through `sort -u`")
    args = ap.parse_args(argv)

    if args.out and args.out.suffix == ".gz":
        out: IO[str] = gzip.open(args.out, "wt", encoding="utf-8")  # noqa: SIM115
    elif args.out:
        out = args.out.open("wt", encoding="utf-8")
    else:
        out = sys.stdout

    try:
        sink = Sink(out, dedupe=not args.no_dedupe)
        emit_dataset_metadata(
            sink,
            version=args.version,
            issued=args.issued,
            source=args.source,
            endpoint=args.endpoint,
        )
        stats = convert(args.metadata, sink)
        if args.refs_nt:
            references = {
                row["reference_wikidata"] for row in rows_of(args.metadata)
            }
            stats["reference_triples_folded_in"] = fold_reference_slices(
                sink, args.refs_nt, references
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

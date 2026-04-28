#!/usr/bin/env python3
"""Suggest `keywords` and `categories` fields for each MIE file's schema_info.

Reads togo_mcp/data/mie/*.yaml, extracts title + description, runs simple
heuristics, and emits a YAML file of suggestions for human review at
scripts/mie_keyword_suggestions.yaml. Does NOT modify any MIE file.

Workflow:
    uv run python scripts/bootstrap_mie_keywords.py
    # review scripts/mie_keyword_suggestions.yaml
    # hand-edit each MIE's schema_info to add the approved fields
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MIE_DIR = REPO_ROOT / "togo_mcp" / "data" / "mie"
OUTPUT = REPO_ROOT / "scripts" / "mie_keyword_suggestions.yaml"

# Hand-curated category taxonomy. Add new categories here as the corpus grows.
# Each value is a list of substring rules; presence of any rule in title+description
# (case-insensitive) tags the database with the category.
CATEGORY_RULES: dict[str, list[str]] = {
    "protein": ["protein", "swiss-prot", "swissprot", "trembl", "uniprot", "amino acid"],
    "gene": ["gene ", " gene", "transcript", "ensembl", "ncbi gene"],
    "variant": ["variant", "mutation", "polymorphism", "snp ", "clinvar"],
    "compound": ["compound", "small molecule", "ligand", "chemical", "chebi", "pubchem"],
    "drug_target": ["drug target", "chembl", "bioactivity", "ic50", "binding affinity"],
    "pathway": ["pathway", "reactome", "metabolic"],
    "reaction": ["reaction", "rhea", "enzyme reaction"],
    "ontology": ["ontology", "go term", "mesh", "mondo", "nando", "obo"],
    "structure": ["structure", "pdb", "3d ", "crystal", "cryo-em"],
    "literature": ["pubmed", "publication", "article", "literature", "citation"],
    "taxonomy": ["taxonomy", "taxon", "organism", "species"],
    "microbe": ["bacdive", "mediadive", "bacterial", "culture media", "growth condition"],
    "glycan": ["glycan", "glycosylation", "glycomics", "sugar"],
    "antimicrobial": ["amr", "antibiotic resistance", "antimicrobial"],
    "sequence": ["ddbj", "sequence database", "nucleotide"],
    "disease": ["disease", "phenotype", "clinical"],
    "materials": ["materials science", "crystal structure", "lattice parameter", "alloy", "oxide", "superconductor", "supercon"],
    "physics": ["superconductor", "supercon", "critical temperature", " tc ", "magnetic field", "conductivity", "physical property"],
    "enzymology": ["enzyme", "ec number", "kinetic", "brenda", "kcat", "km value", "turnover", "substrate"],
    "genomics": ["genome", "genomic", "hgnc", "gene nomenclature", "official symbol", "ensembl"],
}

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "these", "those", "are",
    "was", "were", "have", "has", "had", "will", "would", "could", "should", "may",
    "must", "can", "all", "any", "some", "not", "only", "also", "more", "most",
    "other", "such", "than", "too", "very", "just", "into", "through", "between",
    "across", "over", "under", "rdf", "data", "database", "contains", "includes",
    "used", "using", "entries", "etc", "see", "many", "well", "above", "below",
    "after", "before", "during", "via", "ie", "eg", "csv", "yaml", "based", "each",
    "which", "where", "when", "what", "while", "their", "them", "they", "your",
    "available", "provides", "providing", "include", "including", "covers",
}


def tokenize(text: str) -> list[str]:
    """Lowercase tokens length >= 4, stopwords/digits dropped."""
    tokens = re.findall(r"[a-z0-9_-]+", text.lower())
    return [t for t in tokens if len(t) >= 4 and t not in STOPWORDS and not t.isdigit()]


def suggest_keywords(title: str, description: str, top_n: int = 12) -> list[str]:
    """Frequency rank with title boost. Stable on ties (alphabetical)."""
    counts: dict[str, int] = {}
    for tok in tokenize(title):
        counts[tok] = counts.get(tok, 0) + 3
    for tok in tokenize(description):
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return [t for t, _ in ranked[:top_n]]


def suggest_categories(title: str, description: str) -> list[str]:
    haystack = (title + " " + description).lower()
    return [cat for cat, rules in CATEGORY_RULES.items() if any(r in haystack for r in rules)]


def main() -> int:
    if not MIE_DIR.is_dir():
        print(f"Error: {MIE_DIR} not found", file=sys.stderr)
        return 1

    suggestions: dict[str, dict[str, object]] = {}
    for path in sorted(MIE_DIR.glob("*.yaml")):
        db_name = path.stem
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Skipping {db_name}: {e}", file=sys.stderr)
            continue
        si = data.get("schema_info") if isinstance(data, dict) else None
        if not isinstance(si, dict):
            si = {}
        title = str(si.get("title") or "").strip()
        desc = str(si.get("description") or "").strip()
        suggestions[db_name] = {
            "title": title,
            "description_excerpt": (desc[:240] + "...") if len(desc) > 240 else desc,
            "current_keywords": si.get("keywords"),
            "current_categories": si.get("categories"),
            "suggested_keywords": suggest_keywords(title, desc),
            "suggested_categories": suggest_categories(title, desc),
        }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(suggestions, f, sort_keys=False, allow_unicode=True, width=120)

    uncategorized = [db for db, s in suggestions.items() if not s["suggested_categories"]]
    print(f"Wrote {len(suggestions)} suggestions to {OUTPUT.relative_to(REPO_ROOT)}")
    if uncategorized:
        print(f"  ({len(uncategorized)} DBs got no category match — review manually): {', '.join(uncategorized)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

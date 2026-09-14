#!/usr/bin/env python3
"""
Benchmark-leakage checker for TogoMCP MIE files (MIE_v3_spec.md §4.6).

An MIE example teaches a ROUTE; the entity it uses is only the vehicle. If that vehicle is
a benchmark question's exact subject, the corpus "knows" the answer and the evaluation
scores the MIE instead of the agent. It happened twice while the v3 corpus was drafted —
uniprot `keyword_enum` used LIM domain (q066) and even carried q066's first-step count,
chebi `enum_has_role` used antimicrobial agent (q075) — and both were caught only because
someone happened to look. §4.6 prescribed "a one-line grep" at authoring time; nothing
ran it. This script is that grep, made exhaustive and wired to CI.

What counts as a subject
------------------------
For every question, and for every database in its `togomcp_databases_used` that has an MIE:
  keyword       `inspiration_keyword.name` ("LIM domain")
  keyword-id    `inspiration_keyword.keyword_id` in every form SPARQL spells it:
                KW-0440, keywords:440, keywords/440
  answer        the head of each `exact_answer` item — the text before " (", " — ", ": "
                or "; " ('ALOX5 (ChEMBL:CHEMBL215)' -> 'ALOX5'). yes/no/empty are skipped.
  answer-id     prefixed identifiers inside an answer ('ChEMBL:CHEMBL215' -> CHEMBL215,
                'UniProt:Q8WWI1' -> Q8WWI1) and InChIKeys
Each is searched, whole-word and case-insensitive (case-SENSITIVE for tokens of four
characters or fewer, where "TK" would otherwise match every "tk"), across every text field
of that database's examples: id, intent, question, sparql, verified, teaches, traps_avoided.

It runs in BOTH directions on purpose: a new example that picks up a question's subject,
and a new question written about a subject an existing example already carries. Either is
the same leak.

Numbers are reported, not gated
-------------------------------
q066's leak included a count (71). An integer `exact_answer` found in a `verified:` block
of the same database is printed as a NOTE for a human to look at, but does not fail the
run: small integers recur by coincidence far too often to gate on.

Waivers
-------
Generic domain vocabulary produces true-but-harmless matches: q077's keyword is
"Chromosome", which every mco example mentions. Those are waived in
`scripts/mie_leakage_waivers.yaml`, one entry per (question, database, token) with a
`reason`. A waiver that no longer matches anything FAILS the run, so the file cannot
silently accumulate exemptions for leaks that were long since fixed — or hide a new one
behind an old excuse. `canonical:` lists subjects §4.6 names as always fine (ATP, TP53…).

Exit code = un-waived hits + stale waivers + malformed waivers (capped at 125). Exits 0 with
a note when `benchmark/questions/` is absent (the questions live on branches some checkouts
do not carry), because nothing can be checked, not because nothing leaked.

Usage:
    uv run python scripts/check_mie_leakage.py              # all MIEs x all questions
    uv run python scripts/check_mie_leakage.py uniprot chebi
"""
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: uv sync")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
MIE_DIR = ROOT / "togo_mcp" / "data" / "mie"
QUESTIONS_DIR = ROOT / "benchmark" / "questions"
WAIVERS_FILE = Path(__file__).resolve().parent / "mie_leakage_waivers.yaml"

# Example fields a reader sees. `check:` blocks are stripped before serving (§3.6), but a
# subject inside one would still be the author's choice of vehicle, so they are searched too.
EXAMPLE_TEXT_FIELDS = ("id", "intent", "question", "sparql", "verified", "teaches",
                       "traps_avoided")

_SKIP_ANSWERS = {"", "yes", "no"}
_HEAD_SPLIT = re.compile(r"\s+\(|\s+—\s+|:\s|;\s")
_PREFIXED_ID = re.compile(r"[A-Za-z][A-Za-z .]*?:\s?([A-Za-z0-9_.-]+)")
_INCHIKEY = re.compile(r"\b([A-Z]{14}-[A-Z]{10}-[A-Z])\b")
_SHORT_TOKEN = 4


@dataclass(frozen=True)
class Subject:
    kind: str      # keyword | keyword-id | answer | answer-id
    token: str     # what a human reads in the report and writes in a waiver
    pattern: str   # the regex actually searched


@dataclass(frozen=True)
class Hit:
    question: str
    database: str
    example: str
    subject: Subject
    context: str


def _word_pattern(token):
    # "_" is a boundary so a UniProt mnemonic (LMO7_HUMAN) still matches its gene (LMO7).
    return r"(?<![A-Za-z0-9-])" + re.escape(token) + r"(?![A-Za-z0-9-])"


def _flags(token):
    return 0 if len(token) <= _SHORT_TOKEN else re.IGNORECASE


def _answer_items(answer):
    if isinstance(answer, list):
        return [str(a) for a in answer]
    if isinstance(answer, str):
        return [answer]
    return []  # int answers are numbers: reported, not gated


def question_subjects(q):
    """Every subject a question scores on, de-duplicated by token."""
    out = {}

    def add(kind, token, pattern=None):
        token = token.strip()
        if token and token.lower() not in out:
            out[token.lower()] = Subject(kind, token, pattern or _word_pattern(token))

    kw = q.get("inspiration_keyword") or {}
    if kw.get("name"):
        add("keyword", kw["name"])
    m = re.fullmatch(r"KW-(\d+)", str(kw.get("keyword_id", "")))
    if m:
        num = int(m.group(1))
        add("keyword-id", kw["keyword_id"])
        add("keyword-id", f"keywords:{num}", rf"(?<![\w-])keywords[:/]0*{num}(?!\d)")

    for item in _answer_items(q.get("exact_answer")):
        if item.strip().lower() in _SKIP_ANSWERS:
            continue
        add("answer", _HEAD_SPLIT.split(item.strip())[0])
        for val in _PREFIXED_ID.findall(item):
            if len(val) >= 4 and re.search(r"\d", val):
                add("answer-id", val)
        for key in _INCHIKEY.findall(item):
            add("answer-id", key)
    return list(out.values())


def _flatten(value):
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    return "" if value is None else str(value)


def example_text(example):
    return " ".join(_flatten(example.get(f)) for f in EXAMPLE_TEXT_FIELDS)


def find_hits(questions, mies):
    """questions: list of question dicts. mies: {database: parsed MIE dict}."""
    hits = []
    for q in questions:
        subjects = question_subjects(q)
        for db in q.get("togomcp_databases_used") or []:
            for ex in (mies.get(db) or {}).get("examples") or []:
                text = example_text(ex)
                for s in subjects:
                    m = re.search(s.pattern, text, _flags(s.token))
                    if m:
                        ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 50):m.end() + 50])
                        hits.append(Hit(q["id"], db, str(ex.get("id")), s, ctx))
    return hits


def find_number_notes(questions, mies):
    """Integer exact answers (>= 10) that appear in a same-DB example's `verified:` block."""
    notes = []
    for q in questions:
        ans = q.get("exact_answer")
        if isinstance(ans, bool) or not isinstance(ans, int) or ans < 10:
            continue
        pat = rf"(?<![\w.,-]){ans}(?![\w]|[.,]\d)"  # not C10H16, 1.10, 10.5
        for db in q.get("togomcp_databases_used") or []:
            for ex in (mies.get(db) or {}).get("examples") or []:
                verified = ex.get("verified")
                if isinstance(verified, dict):  # "22" is in every "2026-07-22"
                    verified = {k: v for k, v in verified.items() if k != "date"}
                if re.search(pat, _flatten(verified)):
                    notes.append((q["id"], db, str(ex.get("id")), ans))
    return notes


def load_waivers(path):
    """Returns (canonical tokens lowercased, waiver list, malformed messages)."""
    if not path.exists():
        return set(), [], []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    canonical = {str(t).lower() for t in data.get("canonical") or []}
    waivers, malformed = [], []
    for i, w in enumerate(data.get("waivers") or []):
        missing = [k for k in ("question", "database", "token", "reason")
                   if not isinstance(w, dict) or not str(w.get(k) or "").strip()]
        if missing:
            malformed.append(f"waivers[{i}]: missing {', '.join(missing)}")
        else:
            waivers.append(w)
    return canonical, waivers, malformed


def apply_waivers(hits, canonical, waivers):
    """Returns (unwaived hits, stale waivers)."""
    used = set()
    unwaived = []
    for h in hits:
        if h.subject.token.lower() in canonical:
            continue
        match = next((i for i, w in enumerate(waivers)
                      if w["question"] == h.question and w["database"] == h.database
                      and str(w["token"]).lower() == h.subject.token.lower()), None)
        if match is None:
            unwaived.append(h)
        else:
            used.add(match)
    stale = [w for i, w in enumerate(waivers) if i not in used]
    return unwaived, stale


def load_corpus(mie_dir, questions_dir, dbs=None):
    mies = {}
    for f in sorted(mie_dir.glob("*.yaml")):
        if dbs and f.stem not in dbs:
            continue
        mies[f.stem] = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    questions = [yaml.safe_load(f.read_text(encoding="utf-8"))
                 for f in sorted(questions_dir.glob("question_*.yaml"))]
    return [q for q in questions if isinstance(q, dict) and q.get("id")], mies


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dbs", nargs="*", help="database names to check (default: all)")
    args = ap.parse_args()

    if not QUESTIONS_DIR.is_dir():
        print(f"No {QUESTIONS_DIR.relative_to(ROOT)}/ in this checkout — nothing to check.")
        sys.exit(0)

    questions, mies = load_corpus(MIE_DIR, QUESTIONS_DIR, set(args.dbs) or None)
    canonical, waivers, malformed = load_waivers(WAIVERS_FILE)
    if args.dbs:  # a partial run can't judge waivers for databases it didn't scan
        waivers = [w for w in waivers if w["database"] in mies]
    hits = find_hits(questions, mies)
    unwaived, stale = apply_waivers(hits, canonical, waivers)
    notes = find_number_notes(questions, mies)

    for h in unwaived:
        print(f"  ✗  {h.database} {h.example} ← {h.question} [{h.subject.kind}] "
              f"{h.subject.token!r}\n       …{h.context}…")
    for w in stale:
        print(f"  !  STALE waiver {w['question']} / {w['database']} / {w['token']!r} "
              "— matches nothing now; delete it")
    for m in malformed:
        print(f"  !  MALFORMED {m}")
    for qid, db, ex, n in notes:
        print(f"  ·  note: {db} {ex} verified: contains {n}, the exact answer of {qid} "
              "(numbers are not gated — check it is a coincidence)")

    print("\n" + "=" * 70)
    print(f"MIE LEAKAGE CHECK — {len(questions)} questions × {len(mies)} MIEs: "
          f"{len(hits)} match(es), {len(hits) - len(unwaived)} waived, {len(unwaived)} leak(s), "
          f"{len(stale)} stale waiver(s), {len(malformed)} malformed, {len(notes)} number note(s)")
    print("=" * 70)
    if unwaived:
        print("\nA leak is fixed in the MIE, not here: swap the example's subject for a neutral "
              "member of the same class and re-verify it live (spec §4.6). Waive only generic "
              "vocabulary that is not what the question scores on.")
    sys.exit(min(len(unwaived) + len(stale) + len(malformed), 125))


if __name__ == "__main__":
    main()

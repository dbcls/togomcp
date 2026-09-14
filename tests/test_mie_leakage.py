"""Tests for `scripts/check_mie_leakage.py` (MIE_v3_spec.md §4.6 — no benchmark leakage).

Two halves. The corpus test is the gate itself: no MIE example may carry a benchmark
question's subject for a database that question uses, except where a waiver explains why
the match is generic vocabulary — and no waiver may outlive its match. The unit tests pin
the matching rules, starting with the two leaks that motivated §4.6, so a "simplification"
of the tokenizer that would have let them through fails here.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_mie_leakage", ROOT / "scripts" / "check_mie_leakage.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_mie_leakage"] = mod
    spec.loader.exec_module(mod)
    return mod


checker = _load_checker()


def _question(qid="question_900", name="Some keyword", kw="KW-0001", answer="yes", dbs=("uniprot",)):
    return {"id": qid, "inspiration_keyword": {"keyword_id": kw, "name": name},
            "exact_answer": answer, "togomcp_databases_used": list(dbs)}


def _mie(**example):
    base = {"id": "ex", "intent": "", "question": "", "sparql": "", "teaches": "",
            "verified": {"date": "2026-07-22"}}
    base.update(example)
    return {"examples": [base]}


def _tokens(hits):
    return {h.subject.token for h in hits}


@pytest.mark.skipif(not checker.QUESTIONS_DIR.is_dir(), reason="benchmark/questions not in checkout")
class TestCorpus:
    def test_no_unwaived_leak_and_no_stale_waiver(self) -> None:
        questions, mies = checker.load_corpus(checker.MIE_DIR, checker.QUESTIONS_DIR)
        canonical, waivers, malformed = checker.load_waivers(checker.WAIVERS_FILE)
        unwaived, stale = checker.apply_waivers(checker.find_hits(questions, mies), canonical, waivers)
        assert not malformed, malformed
        assert not unwaived, "\n".join(
            f"{h.database} {h.example} carries {h.question}'s {h.subject.kind} "
            f"{h.subject.token!r}: …{h.context}…" for h in unwaived)
        assert not stale, [(w["question"], w["database"], w["token"]) for w in stale]

    def test_every_question_database_has_an_mie(self) -> None:
        # A question naming a database with no MIE would be silently skipped by the scan.
        questions, mies = checker.load_corpus(checker.MIE_DIR, checker.QUESTIONS_DIR)
        missing = {(q["id"], db) for q in questions
                   for db in q.get("togomcp_databases_used") or [] if db not in mies}
        assert not missing, sorted(missing)


class TestTheLeaksThatMotivatedTheRule:
    def test_q066_lim_domain_in_uniprot_keyword_enum(self) -> None:
        q = _question(qid="question_066", name="LIM domain", kw="KW-0440")
        mie = _mie(id="keyword_enum",
                   sparql="?protein up:classifiedWith keywords:440 .  # KW-0440 = LIM domain")
        assert _tokens(checker.find_hits([q], {"uniprot": mie})) == {"LIM domain", "KW-0440", "keywords:440"}

    def test_q075_antimicrobial_in_chebi_enum_has_role(self) -> None:
        q = _question(qid="question_075", name="Antimicrobial", kw="KW-0929", answer="", dbs=("chebi",))
        mie = _mie(id="enum_has_role", question="Which compounds have the role 'antimicrobial agent'?")
        assert _tokens(checker.find_hits([q], {"chebi": mie})) == {"Antimicrobial"}


class TestMatching:
    def test_keyword_iri_does_not_match_a_longer_number(self) -> None:
        q = _question(kw="KW-0072")
        mie = _mie(sparql="up:classifiedWith keywords:727 .")
        assert checker.find_hits([q], {"uniprot": mie}) == []

    def test_keyword_iri_matches_slash_and_zero_padded_forms(self) -> None:
        q = _question(kw="KW-0072")
        mie = _mie(sparql="<http://purl.uniprot.org/keywords/0072>")
        assert _tokens(checker.find_hits([q], {"uniprot": mie})) == {"keywords:72"}

    def test_only_databases_the_question_uses_are_scanned(self) -> None:
        q = _question(name="LIM domain", dbs=("uniprot",))
        assert checker.find_hits([q], {"pdb": _mie(intent="LIM domain")}) == []

    def test_whole_word_only(self) -> None:
        q = _question(name="Kinase")
        assert checker.find_hits([q], {"uniprot": _mie(intent="kinases and phosphokinase")}) == []

    def test_short_tokens_are_case_sensitive(self) -> None:
        q = _question(answer=["TK"])
        assert checker.find_hits([q], {"uniprot": _mie(sparql="?tk a ?class")}) == []
        assert _tokens(checker.find_hits([q], {"uniprot": _mie(intent="the TK group")})) == {"TK"}

    def test_answer_head_and_prefixed_ids_are_extracted(self) -> None:
        q = _question(answer=["ALOX5 (ChEMBL:CHEMBL215)", "LMO7 (UniProt:Q8WWI1); 50 distinct"])
        tokens = {s.token for s in checker.question_subjects(q)}
        assert {"ALOX5", "CHEMBL215", "LMO7", "Q8WWI1"} <= tokens
        assert "50 distinct" not in tokens

    def test_yes_no_and_int_answers_are_not_subjects(self) -> None:
        for answer in ("yes", "no", 24):
            kinds = {s.kind for s in checker.question_subjects(_question(answer=answer))}
            assert kinds == {"keyword", "keyword-id"}

    def test_verified_block_is_searched(self) -> None:
        q = _question(answer=["LMO7 (UniProt:Q8WWI1)"])
        mie = _mie(verified={"first_row": "Q8WWI1 LMO7_HUMAN", "date": "2026-07-22"})
        assert _tokens(checker.find_hits([q], {"uniprot": mie})) == {"LMO7", "Q8WWI1"}


class TestWaivers:
    def _hit(self, token="Chromosome", qid="question_077", db="mco"):
        s = checker.Subject("keyword", token, checker._word_pattern(token))
        return checker.Hit(qid, db, "ex", s, "")

    def test_waiver_matches_case_insensitively(self) -> None:
        w = {"question": "question_077", "database": "mco", "token": "chromosome", "reason": "r"}
        assert checker.apply_waivers([self._hit()], set(), [w]) == ([], [])

    def test_waiver_is_scoped_to_its_database(self) -> None:
        w = {"question": "question_077", "database": "ensembl", "token": "Chromosome", "reason": "r"}
        unwaived, stale = checker.apply_waivers([self._hit()], set(), [w])
        assert len(unwaived) == 1 and stale == [w]

    def test_canonical_subject_is_always_exempt(self) -> None:
        assert checker.apply_waivers([self._hit(token="ATP")], {"atp"}, []) == ([], [])

    def test_waiver_without_reason_is_malformed(self, tmp_path: Path) -> None:
        f = tmp_path / "w.yaml"
        f.write_text("waivers:\n  - {question: question_077, database: mco, token: Chromosome}\n")
        _, waivers, malformed = checker.load_waivers(f)
        assert waivers == [] and malformed and "reason" in malformed[0]


class TestNumberNotes:
    def test_date_and_formula_digits_are_not_numbers(self) -> None:
        q = _question(answer=22, dbs=("chebi",))
        mie = _mie(verified={"formula": "C22H30", "ratio": "1.22", "date": "2026-07-22"})
        assert checker.find_number_notes([q], {"chebi": mie}) == []

    def test_standalone_count_is_noted(self) -> None:
        q = _question(answer=71)
        mie = _mie(verified={"n": 71, "date": "2026-07-22"})
        assert checker.find_number_notes([q], {"uniprot": mie}) == [("question_900", "uniprot", "ex", 71)]

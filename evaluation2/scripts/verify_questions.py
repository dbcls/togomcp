#!/usr/bin/env python3
"""
Verification script for TogoMCP benchmark questions (YAML format).

Validates question_XXX.yaml files against QUESTION_FORMAT.md specification.
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_PATH = Path("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions")

VALID_TYPES = {"yes_no", "factoid", "list", "summary", "choice"}

VALID_DATABASES = {
    "uniprot", "rhea", "pubchem", "pdb", "chembl", "chebi", "reactome",
    "ensembl", "amrportal", "mesh", "go", "taxonomy", "mondo", "nando",
    "bacdive", "mediadive", "clinvar", "pubmed", "pubtator", "ncbigene",
    "medgen", "ddbj", "glycosmos",
}

# Top-level required fields (present in every question)
REQUIRED_FIELDS = [
    "id", "type", "body",
    "inspiration_keyword", "togomcp_databases_used",
    "verification_score", "pubmed_test",
    "sparql_queries", "rdf_triples",
    "exact_answer", "ideal_answer",
    "question_template_used", "time_spent",
]

INSPIRATION_KEYWORD_FIELDS = ["keyword_id", "name", "category"]
VERIFICATION_SCORE_FIELDS   = ["biological_insight", "multi_database",
                                "verifiability", "rdf_necessity", "total", "passed"]
PUBMED_TEST_FIELDS          = ["time_spent", "method", "result", "conclusion"]
SPARQL_QUERY_FIELDS         = ["query_number", "database", "description", "query",
                                "result_count"]
TIME_SPENT_FIELDS           = ["exploration", "formulation", "verification",
                                "pubmed_test", "extraction", "documentation", "total"]

# For the RDF triple comment format check
RDF_COMMENT_RE = re.compile(
    r"#\s*Database:\s*.+?\s*\|\s*Query:\s*\d+\s*\|\s*Comment:\s*.+",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def load_yaml(path: Path):
    """Load a YAML file, return (data, error_string)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            return None, "Top-level structure is not a mapping"
        return data, None
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"
    except OSError as exc:
        return None, f"Cannot read file: {exc}"


def check(cond: bool, ok_msg: str, err_msg: str,
          issues: list, warnings: list, *, is_warning=False):
    """Print a check result and record failures."""
    if cond:
        print(f"    ✓ {ok_msg}")
    else:
        if is_warning:
            print(f"    ⚠  {err_msg}")
            warnings.append(err_msg)
        else:
            print(f"    ❌ {err_msg}")
            issues.append(err_msg)


# ---------------------------------------------------------------------------
# Per-question validation
# ---------------------------------------------------------------------------

def verify_question(filepath: Path, issues_out: list, warnings_out: list):
    """Validate a single question YAML file.

    Appends error strings to issues_out / warnings_out.
    Returns True if no hard errors were found.
    """
    filename = filepath.name
    prefix   = filename  # used as prefix in issue messages

    def issue(msg):   issues_out.append(f"{prefix}: {msg}")
    def warning(msg): warnings_out.append(f"{prefix}: {msg}")

    print(f"\n  {filename}:")

    # -- Load YAML ----------------------------------------------------------
    data, err = load_yaml(filepath)
    if err:
        print(f"    ❌ {err}")
        issue(err)
        return False

    # -- Required top-level fields -----------------------------------------
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        print(f"    ❌ Missing required fields: {missing}")
        issue(f"Missing required fields: {missing}")
    else:
        print(f"    ✓ All required top-level fields present")

    # -- id -----------------------------------------------------------------
    q_id = data.get("id", "")
    expected_id = filepath.stem  # e.g. "question_001"
    if not q_id:
        print(f"    ❌ 'id' is missing or empty")
        issue("'id' is missing or empty")
    elif q_id != expected_id:
        print(f"    ❌ id '{q_id}' does not match filename '{expected_id}'")
        issue(f"id mismatch: field='{q_id}', file='{expected_id}'")
    else:
        print(f"    ✓ id: {q_id}")

    # -- type ---------------------------------------------------------------
    q_type = data.get("type", "")
    if q_type not in VALID_TYPES:
        print(f"    ❌ Invalid type '{q_type}' (must be one of {sorted(VALID_TYPES)})")
        issue(f"Invalid type '{q_type}'")
    else:
        print(f"    ✓ type: {q_type}")

    # -- body ---------------------------------------------------------------
    body = data.get("body", "")
    if not isinstance(body, str) or not body.strip():
        print(f"    ❌ 'body' is empty or not a string")
        issue("'body' is empty or not a string")
    else:
        print(f"    ✓ body: {len(body)} characters")
        # Warn if body mentions a database by name
        db_mentions = [db for db in VALID_DATABASES if db.lower() in body.lower()]
        if db_mentions:
            print(f"    ⚠  body mentions database name(s): {db_mentions}")
            warning(f"body mentions database name(s): {db_mentions}")

    # -- choices (required only for choice type) ----------------------------
    choices = data.get("choices")
    if q_type == "choice":
        if not isinstance(choices, list) or len(choices) < 2:
            print(f"    ❌ 'choices' must be a list of ≥2 items for type 'choice'")
            issue("'choices' must be a list of ≥2 items for type 'choice'")
        elif len(choices) > 10:
            print(f"    ⚠  'choices' has {len(choices)} items (max recommended: 10)")
            warning(f"'choices' has {len(choices)} items")
        else:
            print(f"    ✓ choices: {len(choices)} items")
    elif choices is not None:
        print(f"    ⚠  'choices' present but type is '{q_type}' (only needed for 'choice')")
        warning("'choices' present on non-choice question")

    # -- inspiration_keyword ------------------------------------------------
    kw = data.get("inspiration_keyword")
    if not isinstance(kw, dict):
        print(f"    ❌ 'inspiration_keyword' must be a mapping")
        issue("'inspiration_keyword' must be a mapping")
    else:
        kw_missing = [f for f in INSPIRATION_KEYWORD_FIELDS if f not in kw]
        if kw_missing:
            print(f"    ❌ inspiration_keyword missing: {kw_missing}")
            issue(f"inspiration_keyword missing fields: {kw_missing}")
        else:
            print(f"    ✓ inspiration_keyword: {kw.get('name')} ({kw.get('keyword_id')})")

    # -- togomcp_databases_used --------------------------------------------
    dbs_used = data.get("togomcp_databases_used", [])
    if not isinstance(dbs_used, list) or len(dbs_used) == 0:
        print(f"    ❌ 'togomcp_databases_used' must be a non-empty list")
        issue("'togomcp_databases_used' is empty or not a list")
        dbs_used = []
    else:
        invalid_dbs = [d for d in dbs_used if d not in VALID_DATABASES]
        if invalid_dbs:
            print(f"    ❌ Unknown database names: {invalid_dbs}")
            issue(f"Unknown database names: {invalid_dbs}")
        else:
            print(f"    ✓ databases used: {dbs_used}")

    # -- verification_score ------------------------------------------------
    vs = data.get("verification_score")
    if not isinstance(vs, dict):
        print(f"    ❌ 'verification_score' must be a mapping")
        issue("'verification_score' must be a mapping")
    else:
        vs_missing = [f for f in VERIFICATION_SCORE_FIELDS if f not in vs]
        if vs_missing:
            print(f"    ❌ verification_score missing fields: {vs_missing}")
            issue(f"verification_score missing fields: {vs_missing}")
        else:
            dims = ["biological_insight", "multi_database", "verifiability", "rdf_necessity"]
            dim_vals = {d: vs.get(d) for d in dims}

            # Each dimension must be 0-3
            for dim, val in dim_vals.items():
                if not isinstance(val, int) or val < 0 or val > 3:
                    print(f"    ❌ verification_score.{dim} = {val!r} (must be integer 0-3)")
                    issue(f"verification_score.{dim} = {val!r} (must be 0-3)")

            # Zero check (any dimension = 0 means fail)
            zeros = [d for d, v in dim_vals.items() if v == 0]
            if zeros:
                print(f"    ❌ Dimensions with 0 (not allowed): {zeros}")
                issue(f"Dimensions with 0: {zeros}")

            # Total must equal sum of dimensions
            expected_total = sum(v for v in dim_vals.values()
                                 if isinstance(v, int))
            actual_total   = vs.get("total")
            if actual_total != expected_total:
                print(f"    ❌ verification_score.total {actual_total} "
                      f"≠ sum of dimensions {expected_total}")
                issue(f"verification_score.total mismatch: "
                      f"stored={actual_total}, sum={expected_total}")

            # Must pass (total ≥9 and no zeros)
            passed = vs.get("passed")
            should_pass = (expected_total >= 9) and (not zeros)
            if passed is not True:
                print(f"    ❌ verification_score.passed = {passed!r} (must be true)")
                issue(f"verification_score.passed = {passed!r}")
            elif not should_pass:
                print(f"    ❌ passed=true but score {expected_total}<9 or has zeros")
                issue(f"passed=true but score {expected_total}<9 or has dimension=0")
            else:
                print(f"    ✓ verification_score: {actual_total}/12 — passed")

    # -- pubmed_test -------------------------------------------------------
    pt = data.get("pubmed_test")
    if not isinstance(pt, dict):
        print(f"    ❌ 'pubmed_test' must be a mapping")
        issue("'pubmed_test' must be a mapping")
    else:
        pt_missing = [f for f in PUBMED_TEST_FIELDS if f not in pt]
        if pt_missing:
            print(f"    ❌ pubmed_test missing fields: {pt_missing}")
            issue(f"pubmed_test missing fields: {pt_missing}")
        else:
            conclusion = str(pt.get("conclusion", "")).upper()
            if "PASS" not in conclusion:
                print(f"    ❌ pubmed_test.conclusion does not contain 'PASS': "
                      f"{pt.get('conclusion')!r}")
                issue(f"pubmed_test.conclusion does not contain PASS")
            else:
                print(f"    ✓ pubmed_test: {pt.get('conclusion')}")

    # -- sparql_queries ----------------------------------------------------
    sparql_qs = data.get("sparql_queries", [])
    if not isinstance(sparql_qs, list) or len(sparql_qs) == 0:
        print(f"    ❌ 'sparql_queries' must be a non-empty list")
        issue("'sparql_queries' is empty or not a list")
    else:
        sparql_dbs = set()
        for i, sq in enumerate(sparql_qs, start=1):
            if not isinstance(sq, dict):
                print(f"    ❌ sparql_queries[{i}] is not a mapping")
                issue(f"sparql_queries[{i}] not a mapping")
                continue
            sq_missing = [f for f in SPARQL_QUERY_FIELDS if f not in sq]
            if sq_missing:
                print(f"    ❌ sparql_queries[{i}] missing: {sq_missing}")
                issue(f"sparql_queries[{i}] missing fields: {sq_missing}")
            # query_number should match index
            qn = sq.get("query_number")
            if qn != i:
                print(f"    ⚠  sparql_queries[{i}].query_number = {qn} (expected {i})")
                warning(f"sparql_queries[{i}].query_number = {qn} (expected {i})")
            # collect databases used in queries
            db_val = sq.get("database", "")
            if db_val:
                sparql_dbs.add(db_val)
            # result_count should be integer >= 0
            rc = sq.get("result_count")
            if not isinstance(rc, int) or rc < 0:
                print(f"    ⚠  sparql_queries[{i}].result_count = {rc!r} (expected int ≥ 0)")
                warning(f"sparql_queries[{i}].result_count = {rc!r}")

        print(f"    ✓ sparql_queries: {len(sparql_qs)} quer(ies) found")

        # Check all declared databases appear in at least one SPARQL query
        declared_dbs = set(dbs_used)
        not_queried  = declared_dbs - sparql_dbs
        if not_queried:
            print(f"    ⚠  databases declared but not seen in sparql_queries: {not_queried}")
            warning(f"databases declared but absent from sparql_queries: {not_queried}")

    # -- rdf_triples -------------------------------------------------------
    rdf = data.get("rdf_triples", "")
    if not isinstance(rdf, str) or not rdf.strip():
        print(f"    ❌ 'rdf_triples' is empty or not a string")
        issue("'rdf_triples' is empty or not a string")
    else:
        lines = rdf.strip().splitlines()
        triple_lines = [l for l in lines
                        if l.strip() and not l.strip().startswith("#")
                        and not l.strip().startswith("@prefix")]
        comment_lines = [l for l in lines if l.strip().startswith("#")]

        # Every non-prefix, non-blank, non-comment line must be followed by a comment
        # Simple heuristic: count comment lines vs triple lines
        if triple_lines and len(comment_lines) < len(triple_lines):
            print(f"    ⚠  rdf_triples: {len(triple_lines)} triples but only "
                  f"{len(comment_lines)} comments (each triple needs a comment)")
            warning(f"rdf_triples: fewer comments ({len(comment_lines)}) "
                    f"than triples ({len(triple_lines)})")

        # Check comment format
        bad_comments = [l.strip() for l in comment_lines
                        if not RDF_COMMENT_RE.match(l.strip())]
        if bad_comments:
            sample = bad_comments[:3]
            print(f"    ⚠  rdf_triples: {len(bad_comments)} comment(s) with wrong format "
                  f"(need '# Database: X | Query: N | Comment: ...'): {sample}")
            warning(f"rdf_triples: {len(bad_comments)} mal-formatted comment(s)")
        else:
            print(f"    ✓ rdf_triples: {len(triple_lines)} triples, "
                  f"{len(comment_lines)} comments")

    # -- exact_answer ------------------------------------------------------
    ea = data.get("exact_answer")
    if q_type == "yes_no":
        if ea not in ("yes", "no"):
            print(f"    ❌ exact_answer for yes_no must be 'yes' or 'no', got {ea!r}")
            issue(f"exact_answer for yes_no = {ea!r} (must be 'yes' or 'no')")
        else:
            print(f"    ✓ exact_answer: {ea}")

    elif q_type == "factoid":
        if ea is None:
            print(f"    ❌ exact_answer for factoid must not be null")
            issue("exact_answer for factoid is null")
        elif not isinstance(ea, (str, int, float)):
            print(f"    ⚠  exact_answer for factoid is type {type(ea).__name__} "
                  f"(expected string or number)")
            warning(f"exact_answer for factoid is {type(ea).__name__}")
        else:
            print(f"    ✓ exact_answer: {ea}")

    elif q_type == "list":
        if not isinstance(ea, list):
            print(f"    ❌ exact_answer for list must be an array")
            issue("exact_answer for list is not an array")
        else:
            print(f"    ✓ exact_answer: {len(ea)} items")

    elif q_type == "choice":
        if not isinstance(ea, list):
            print(f"    ❌ exact_answer for choice must be an array (even for single answer)")
            issue("exact_answer for choice is not an array")
        else:
            if isinstance(choices, list):
                not_in_choices = [item for item in ea if item not in choices]
                if not_in_choices:
                    print(f"    ❌ exact_answer items not in choices: {not_in_choices}")
                    issue(f"exact_answer items not in choices: {not_in_choices}")
                else:
                    print(f"    ✓ exact_answer (choice): {ea}")
            else:
                print(f"    ✓ exact_answer (choice): {ea}")

    elif q_type == "summary":
        if ea not in (None, "", []):
            print(f"    ⚠  exact_answer for summary should be empty string or null, "
                  f"got {ea!r}")
            warning(f"exact_answer for summary = {ea!r} (should be empty)")
        else:
            print(f"    ✓ exact_answer: empty (summary type)")

    # -- ideal_answer -------------------------------------------------------
    ia = data.get("ideal_answer", "")
    if not isinstance(ia, str) or not ia.strip():
        print(f"    ❌ 'ideal_answer' is empty or not a string")
        issue("'ideal_answer' is empty or not a string")
    else:
        print(f"    ✓ ideal_answer: {len(ia)} characters")
        # For summary: must be a single paragraph (no blank lines between sentences)
        if q_type == "summary":
            paragraphs = [p.strip() for p in ia.split("\n\n") if p.strip()]
            if len(paragraphs) > 1:
                print(f"    ⚠  ideal_answer for summary has {len(paragraphs)} paragraphs "
                      f"(must be single paragraph)")
                warning("ideal_answer for summary has multiple paragraphs")
        # Warn about meta-references
        meta = ["according to uniprot", "according to pubmed", "research shows",
                "sparql", "the query", "the database shows"]
        found = [m for m in meta if m in ia.lower()]
        if found:
            print(f"    ⚠  ideal_answer contains meta-references: {found}")
            warning(f"ideal_answer contains meta-references: {found}")
        # For choice: should explain why correct and why others are wrong
        if q_type == "choice":
            if len(ia) < 100:
                print(f"    ⚠  ideal_answer for choice is very short ({len(ia)} chars); "
                      f"should explain correct and incorrect options")
                warning("ideal_answer for choice is very short")

    # -- question_template_used --------------------------------------------
    tmpl = data.get("question_template_used", "")
    if not isinstance(tmpl, str) or not tmpl.strip():
        print(f"    ❌ 'question_template_used' is empty or missing")
        issue("'question_template_used' is empty or missing")
    else:
        print(f"    ✓ question_template_used: {tmpl}")

    # -- time_spent --------------------------------------------------------
    ts = data.get("time_spent")
    if not isinstance(ts, dict):
        print(f"    ❌ 'time_spent' must be a mapping")
        issue("'time_spent' must be a mapping")
    else:
        ts_missing = [f for f in TIME_SPENT_FIELDS if f not in ts]
        if ts_missing:
            print(f"    ⚠  time_spent missing optional fields: {ts_missing}")
            # Non-fatal: just warn
            warning(f"time_spent missing fields: {ts_missing}")
        else:
            print(f"    ✓ time_spent: total = {ts.get('total')}")

    return True  # Always returns; caller checks issues_out length


# ---------------------------------------------------------------------------
# Coverage tracker validation
# ---------------------------------------------------------------------------

def verify_coverage_tracker(actual_counts: dict,
                             actual_db_counts: dict,
                             total: int,
                             issues_out: list,
                             warnings_out: list):
    """Validate coverage_tracker.yaml against observed question data."""
    tracker_path = BASE_PATH / "coverage_tracker.yaml"
    if not tracker_path.exists():
        print(f"\n  ⚠  coverage_tracker.yaml not found")
        warnings_out.append("coverage_tracker.yaml not found")
        return

    tracker, err = load_yaml(tracker_path)
    if err:
        print(f"\n  ❌ coverage_tracker.yaml: {err}")
        issues_out.append(f"coverage_tracker.yaml: {err}")
        return

    print(f"\n  ✓ coverage_tracker.yaml loaded")

    # -- total_questions ---------------------------------------------------
    ct_total = tracker.get("total_questions")
    if ct_total != total:
        print(f"  ❌ coverage_tracker.total_questions = {ct_total}, actual = {total}")
        issues_out.append(f"coverage_tracker total_questions mismatch: {ct_total} vs {total}")
    else:
        print(f"  ✓ total_questions: {ct_total}")

    # -- question_types ----------------------------------------------------
    ct_types = tracker.get("question_types", {})
    for qtype, actual_count in actual_counts.items():
        ct_entry = ct_types.get(qtype, {})
        ct_count  = ct_entry.get("count", 0) if isinstance(ct_entry, dict) else ct_entry
        if ct_count != actual_count:
            print(f"  ❌ type '{qtype}': tracker={ct_count}, actual={actual_count}")
            issues_out.append(
                f"coverage_tracker type '{qtype}' mismatch: {ct_count} vs {actual_count}")
        else:
            print(f"  ✓ type '{qtype}': {ct_count}")

    # -- databases ---------------------------------------------------------
    ct_dbs = tracker.get("databases", {})
    for db, actual_cnt in actual_db_counts.items():
        ct_entry = ct_dbs.get(db, {})
        ct_cnt   = ct_entry.get("count", 0) if isinstance(ct_entry, dict) else 0
        if ct_cnt != actual_cnt:
            print(f"  ⚠  database '{db}': tracker={ct_cnt}, actual={actual_cnt}")
            warnings_out.append(
                f"coverage_tracker db '{db}' mismatch: {ct_cnt} vs {actual_cnt}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def verify_questions():
    question_files = sorted(BASE_PATH.glob("question_*.yaml"))

    total_questions  = 0
    all_types        = []
    all_ids          = []
    db_question_map  = defaultdict(list)   # db -> [question numbers]
    multi_db_2plus   = 0
    multi_db_3plus   = 0
    uniprot_count    = 0

    all_issues   = []
    all_warnings = []

    print("=" * 70)
    print("TOGOMCP BENCHMARK QUESTIONS VERIFICATION")
    print("=" * 70)
    print(f"\nScanning {BASE_PATH} ...")

    # -- Per-question checks -----------------------------------------------
    print("\n--- Per-Question Checks ---")
    for filepath in question_files:
        q_issues   = []
        q_warnings = []

        data, err = load_yaml(filepath)
        if err:
            print(f"\n  {filepath.name}:")
            print(f"    ❌ {err}")
            all_issues.append(f"{filepath.name}: {err}")
            continue

        verify_question(filepath, q_issues, q_warnings)

        # Collect aggregate stats (only from valid data)
        q_id   = data.get("id", "")
        q_type = data.get("type", "")
        dbs    = data.get("togomcp_databases_used", []) or []

        if q_id:
            all_ids.append(q_id)
        if q_type in VALID_TYPES:
            all_types.append(q_type)
        if isinstance(dbs, list):
            if len(dbs) >= 2:
                multi_db_2plus += 1
            if len(dbs) >= 3:
                multi_db_3plus += 1
            if "uniprot" in dbs:
                uniprot_count += 1
            num = filepath.stem.replace("question_", "")
            for db in dbs:
                db_question_map[db].append(num)

        total_questions += 1

        all_issues.extend(q_issues)
        all_warnings.extend(q_warnings)

    # -- Summary -----------------------------------------------------------
    type_counts = Counter(all_types)
    db_counts   = {db: len(qs) for db, qs in db_question_map.items()}

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"\nTotal Questions: {total_questions}")

    if total_questions >= 50:
        print(f"  ✓ PASS: 50-question target met")
    else:
        pct = total_questions / 50 * 100
        print(f"  ⚠  PROGRESS: {total_questions}/50 ({pct:.0f}%)")

    # -- Type distribution -------------------------------------------------
    print(f"\nQuestion Type Distribution (target: 10 each, cap: 8-12):")
    for qtype in sorted(VALID_TYPES):
        cnt = type_counts.get(qtype, 0)
        if cnt == 10:
            sym = "✓"
        elif 8 <= cnt <= 12:
            sym = "~"
        else:
            sym = "❌"
        note = ""
        if cnt > 12:
            note = " ← OVER CAP!"
            all_issues.append(f"Type '{qtype}' has {cnt} uses (hard cap is 12)")
        elif cnt < 8 and total_questions >= 50:
            note = " ← UNDER MINIMUM!"
            all_issues.append(f"Type '{qtype}' has {cnt} uses (minimum is 8)")
        print(f"  {sym} {qtype:12s}: {cnt:3d}{note}")

    # -- Duplicate IDs -----------------------------------------------------
    print(f"\nID Uniqueness:")
    dup_ids = [i for i, c in Counter(all_ids).items() if c > 1]
    if dup_ids:
        print(f"  ❌ Duplicate IDs: {dup_ids}")
        all_issues.append(f"Duplicate IDs: {dup_ids}")
    else:
        print(f"  ✓ All {len(all_ids)} IDs are unique")

    # -- Database coverage -------------------------------------------------
    print(f"\nDatabase Coverage ({len(db_counts)}/{len(VALID_DATABASES)} databases used):")

    missing_dbs = sorted(VALID_DATABASES - set(db_counts.keys()))
    if missing_dbs:
        print(f"  ❌ Databases never used: {missing_dbs}")
        all_issues.append(f"Databases never used: {missing_dbs}")
    else:
        print(f"  ✓ All {len(VALID_DATABASES)} databases used at least once")

    for db in sorted(VALID_DATABASES):
        cnt = db_counts.get(db, 0)
        sym = "✓" if cnt > 0 else "❌"
        print(f"    {sym} {db:15s}: {cnt:3d} question(s)")

    # -- Multi-database stats ----------------------------------------------
    print(f"\nMulti-Database Metrics:")
    pct_2 = multi_db_2plus / total_questions * 100 if total_questions else 0
    pct_3 = multi_db_3plus / total_questions * 100 if total_questions else 0
    sym_2 = "✓" if pct_2 >= 60 else "❌"
    sym_3 = "✓" if pct_3 >= 20 else "❌"
    print(f"  {sym_2} 2+ databases: {multi_db_2plus}/{total_questions} "
          f"({pct_2:.1f}%, target ≥60%)")
    print(f"  {sym_3} 3+ databases: {multi_db_3plus}/{total_questions} "
          f"({pct_3:.1f}%, target ≥20%)")
    if pct_2 < 60:
        all_issues.append(f"2+ database coverage {pct_2:.1f}% < 60% target")
    if pct_3 < 20:
        all_issues.append(f"3+ database coverage {pct_3:.1f}% < 20% target")

    # -- UniProt cap -------------------------------------------------------
    pct_up = uniprot_count / total_questions * 100 if total_questions else 0
    sym_up = "✓" if pct_up <= 70 else "❌"
    print(f"\nUniProt Cap:")
    print(f"  {sym_up} UniProt used in {uniprot_count}/{total_questions} "
          f"questions ({pct_up:.1f}%, cap ≤70%)")
    if pct_up > 70:
        all_issues.append(f"UniProt usage {pct_up:.1f}% exceeds 70% cap")

    # -- Coverage tracker --------------------------------------------------
    print(f"\n--- Coverage Tracker Verification ---")
    verify_coverage_tracker(type_counts, db_counts, total_questions,
                            all_issues, all_warnings)

    # -- Warnings summary --------------------------------------------------
    if all_warnings:
        print(f"\n{'=' * 70}")
        print(f"WARNINGS ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  ⚠  {w}")

    # -- Issues summary ----------------------------------------------------
    if all_issues:
        print(f"\n{'=' * 70}")
        print(f"ERRORS ({len(all_issues)}):")
        for err in all_issues:
            print(f"  ❌ {err}")
    else:
        print(f"\n✓ No errors found!")

    print(f"\n{'=' * 70}")
    print(f"VERIFICATION COMPLETE  —  "
          f"{len(all_issues)} error(s), {len(all_warnings)} warning(s)")
    print(f"{'=' * 70}\n")

    return len(all_issues) == 0


if __name__ == "__main__":
    success = verify_questions()
    sys.exit(0 if success else 1)

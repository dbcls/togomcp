"""Classifier shared by audit_transcripts.py and the runner's strict-isolation hook."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark" / "scripts"))

import audit_transcripts  # noqa: E402
from audit_transcripts import classify  # noqa: E402

import pytest  # noqa: E402

SID = "aaaaaaaa-0000-0000-0000-000000000000"
OTHER = __file__                                        # a real file outside the session


@pytest.fixture(autouse=True)
def _folder(tmp_path, monkeypatch):
    """A transcript folder with this session's saved output on disk (paths must exist)."""
    global FOLDER, OWN
    # On Linux pytest's tmp_path lives under /tmp/, which the classifier ignores as scratch
    # space, so every path here would be dropped before it is judged (CI failed that way,
    # macOS did not). Keep only the /dev/ entries; a real transcript folder is never in /tmp.
    monkeypatch.setattr(audit_transcripts, "SAFE_PREFIXES", tuple(
        p for p in audit_transcripts.SAFE_PREFIXES if p.startswith("/dev/")))
    FOLDER = str(tmp_path)
    own = tmp_path / SID / "tool-results" / "out.txt"
    own.parent.mkdir(parents=True)
    own.write_text("{}")
    OWN = str(own)


def test_reading_own_saved_output_is_allowed():
    assert classify("Read", {"file_path": OWN}, SID, FOLDER, FOLDER) == "own-output"


def test_reading_another_file_is_a_violation():
    assert classify("Read", {"file_path": OTHER}, SID, FOLDER, FOLDER) == "VIOLATION"
    assert classify("Bash", {"command": f"grep -c MIE {OTHER}"}, SID, FOLDER, FOLDER) == "VIOLATION"


def test_network_command_is_a_violation_but_a_printed_url_is_not():
    assert classify("Bash", {"command": "curl -s https://example.org"}, SID, FOLDER, FOLDER) == "VIOLATION"
    assert classify("Bash", {"command": "echo 'PREFIX x: <http://example.org/>'"}, SID, FOLDER, FOLDER) == "compute"


def test_dev_null_and_grep_patterns_are_not_paths():
    assert classify("Bash", {"command": f"jq -r .result {OWN} 2>/dev/null"}, SID, FOLDER, FOLDER) == "own-output"
    assert classify("Bash", {"command": f"grep '/product=\"16S\"' {OWN}"}, SID, FOLDER, FOLDER) == "own-output"


def test_folder_listing_is_review_but_reading_through_it_is_not():
    assert classify("Bash", {"command": f"find {FOLDER} -name '*.txt' | head -5"}, SID, FOLDER, FOLDER) == "REVIEW"
    assert classify("Bash", {"command": f"find {FOLDER} -name '*.txt' -exec cat {{}} +"}, SID, FOLDER, FOLDER) == "VIOLATION"


def test_grep_without_path_searches_the_repo():
    assert classify("Grep", {"pattern": "exact_answer"}, SID, FOLDER, FOLDER) == "VIOLATION"


def test_sed_script_with_slashes_is_not_a_path():
    cmd = f"cat {OWN} | sed 's/.*\"name\": \"\\(.*\\)\".*/\\1/' | head"
    assert classify("Bash", {"command": cmd}, SID, FOLDER, FOLDER) == "own-output"


def test_inter_agent_tools():
    assert classify("Agent", {"description": "x", "prompt": "y"}, SID, FOLDER, FOLDER) == "SUBAGENT"
    assert classify("SendMessage", {"to": "main", "message": "m"}, SID, FOLDER, FOLDER) == "REVIEW"
    assert classify("SendMessage", {"to": "other-session", "message": "m"}, SID, FOLDER, FOLDER) == "VIOLATION"


def test_wildcard_path_resolving_to_own_folder_is_own_output():
    import os
    parent = os.path.dirname(FOLDER)
    name = os.path.basename(FOLDER)
    # (pytest gives sibling tests their own temp dirs holding the same SID, so the middle
    # wildcard must stay specific to this test's directory)
    own_glob = f"{parent}/{name[:-1]}?/{SID[:8]}*/tool-results/"
    assert classify("Bash", {"command": f"cd {own_glob}; jq -r .result out.txt | head"}, SID, FOLDER, FOLDER) == "own-output"
    # a wildcard that also reaches another session's folder is still a violation
    other = Path(FOLDER) / "bbbbbbbb-0000-0000-0000-000000000000" / "tool-results"
    other.mkdir(parents=True)
    (other / "x.txt").write_text("{}")
    assert classify("Bash", {"command": f"cat {parent}/{name}/*/tool-results/*.txt"}, SID, FOLDER, FOLDER) == "VIOLATION"

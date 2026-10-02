"""Classifier shared by audit_transcripts.py and the runner's strict-isolation hook."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark" / "scripts"))

from audit_transcripts import classify  # noqa: E402

import pytest  # noqa: E402

SID = "aaaaaaaa-0000-0000-0000-000000000000"
OTHER = __file__                                        # a real file outside the session


@pytest.fixture(autouse=True)
def _folder(tmp_path):
    """A transcript folder with this session's saved output on disk (paths must exist)."""
    global FOLDER, OWN
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

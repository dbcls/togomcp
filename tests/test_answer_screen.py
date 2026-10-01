"""The shared refusal/stub detector used by results_analyzer.py and benchmark-runner."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark" / "scripts"))

from answer_screen import classify  # noqa: E402

REFUSAL = (
    "API Error: Claude Code is unable to respond to this request, which appears to violate "
    "our Usage Policy (https://www.anthropic.com/legal/aup). Try rephrasing the request."
)


def test_refusal_text_is_a_refusal_even_when_marked_success():
    assert classify(REFUSAL, "True") == "refusal"


def test_login_stub_marked_success_is_a_stub():
    assert classify("Not logged in · Please run /login", "True") == "stub"


def test_error_placeholder_and_empty_are_stubs():
    assert classify("[ERROR: Empty response from claude-agent-sdk (baseline)]", "False") == "stub"
    assert classify("", "True") == "stub"
    assert classify(None) == "stub"


def test_failed_run_is_a_stub():
    assert classify("Partial text", "False") == "stub"


def test_short_real_answer_is_valid():
    # A real ~400-character answer must not be mistaken for a refusal by its length.
    answer = "Yes. The HSPB1 gene has 68 documented ClinVar variants for Charcot-Marie-Tooth disease."
    assert classify(answer, "True") == "valid"

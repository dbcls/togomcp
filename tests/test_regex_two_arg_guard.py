"""Drift guard: no shipped SPARQL may use the two-argument form of `REGEX()`.

On every SPARQL endpoint in `endpoints.csv` (all 10, verified 2026-08-14), the
two-argument `REGEX(?x, "pattern")` form silently mishandles at least two regex
constructs, returning **0 rows with no error**:

    VALUES ?s { "Fentanyl" "Sufentanil" }  FILTER(REGEX(?s, "Fentanyl|Sufentanil"))  -> 0, want 2
    VALUES ?s { "ab" "aab" "aaab" }        FILTER(REGEX(?s, "a{1,2}b"))              -> 0, want 3

Alternation fails in every shape tested (`A|B`, `A|B|C`, one-sided `A|`, even
`A|A`); brace quantifiers fail as `{n}`, `{n,}` and `{n,m}`. Passing any third
(flags) argument — `""` is enough — fixes both. Plain substrings, character
classes, `? + *`, anchors, `.`, escapes and `(?:...)` are unaffected.

That asymmetry is what makes this worth a test rather than a note. A single-term
`REGEX` example works, so it passes review and passes `check_mie_examples.py`;
it starts returning 0 only when someone later widens the pattern to a family or
adds a count, and the empty result reads as "the database doesn't have those."
A production session concluded MassBank had no fentanyls; it has 44.

Worse, `check_mie_examples.py` cannot catch the general case at all: it flags
zero-ROW results, but a broken `REGEX` inside an `OPTIONAL` or one `UNION` branch
still returns rows — just silently fewer. So the only reliable guard is static,
and it is a blanket ban on the two-argument form rather than a hunt for the
specific metacharacters, because the two known-broken constructs are what has
been *tested*, not a proof that nothing else is affected.

The rule itself lives in `usage_guide_v6/03_workflows.md` (SILENT-FAILURE TRAPS
#10) and in the mie-generator skill's `query-strategy.md`; this test enforces it
against the corpus that ships.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
MIE_DIR = REPO / "togo_mcp" / "data" / "mie"
GUIDE = REPO / "togo_mcp" / "data" / "resources" / "usage_guide_v6" / "03_workflows.md"

# Field names whose string values are executed as SPARQL (as opposed to prose that
# may legitimately quote a broken form as a counter-example).
EXECUTABLE_FIELD = re.compile(r"(^|\.)(sparql|query)(\[\d+\])?$", re.IGNORECASE)


def _split_top_level(text: str, sep: str) -> list[str]:
    """Split on `sep` at paren-depth 0, honouring quoted strings and backslash escapes."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    current = ""
    for ch in text:
        if escaped:
            current += ch
            escaped = False
            continue
        if ch == "\\":
            current += ch
            escaped = True
            continue
        if quote:
            current += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            current += ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return parts


def find_regex_calls(text: str) -> list[tuple[str, int]]:
    """Return (call_source, argument_count) for every REGEX(...) in `text`."""
    calls: list[tuple[str, int]] = []
    for match in re.finditer(r"\bREGEX\s*\(", text, re.IGNORECASE):
        i = match.end()
        depth = 1
        start = i
        while i < len(text) and depth:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        if depth:  # unbalanced — not a call we can judge
            continue
        inner = text[start : i - 1]
        calls.append(("REGEX(" + inner + ")", len(_split_top_level(inner, ","))))
    return calls


def walk_strings(node, path: str = ""):
    """Yield (dotted_path, string) for every string leaf in a parsed YAML document."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def mie_files() -> list[Path]:
    return sorted(MIE_DIR.glob("*.yaml"))


def test_mie_dir_is_populated():
    """Guard the guard: an empty glob would make every test below vacuously pass."""
    assert len(mie_files()) >= 30, f"expected the full MIE corpus, found {len(mie_files())}"


@pytest.mark.parametrize("mie_path", mie_files(), ids=lambda p: p.stem)
def test_no_two_arg_regex_in_executable_sparql(mie_path: Path):
    """Every REGEX() inside an executable `sparql` field must pass a flags argument."""
    document = yaml.safe_load(mie_path.read_text())
    offenders: list[str] = []
    for path, text in walk_strings(document):
        if not EXECUTABLE_FIELD.search(path):
            continue
        for call, n_args in find_regex_calls(text):
            if n_args < 3:
                offenders.append(f"{mie_path.name}{path}: {call}")
    assert not offenders, (
        "Two-argument REGEX() found in executable SPARQL. It silently returns 0 rows for "
        "alternation and brace quantifiers on every endpoint — pass a third argument "
        '(REGEX(?x, "pat", "")). See usage_guide_v6/03_workflows.md SILENT-FAILURE TRAPS #10.\n  '
        + "\n  ".join(offenders)
    )


def test_guide_documents_the_rule():
    """The corpus rule is only safe to enforce while the guide still explains it."""
    text = GUIDE.read_text()
    assert "SILENT-FAILURE TRAPS" in text
    # The prescription, and both verified-broken constructs, must survive edits.
    assert "REGEX" in text and 'REGEX(?label, "Fentanyl|Sufentanil", "")' in text, (
        "the guide must show the three-argument fix verbatim — it is what authors copy"
    )
    assert "a{1,2}b" in text, "the brace-quantifier case must stay documented alongside alternation"

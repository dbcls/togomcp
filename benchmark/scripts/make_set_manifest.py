#!/usr/bin/env python3
"""
Write or check the frozen-question-set manifest (benchmark/questions/SET_MANIFEST.json).

The manifest records the sha256 of every question_*.yaml plus one combined hash, so an
evaluation run can state exactly which question set it used. The combined hash is the
sha256 of the sha256sum-style listing ("<hash>  <filename>\n" per file, sorted by name),
so it can be reproduced without this script:

    cd benchmark/questions && sha256sum question_*.yaml | LC_ALL=C sort -k2 | sha256sum

Usage:
    python benchmark/scripts/make_set_manifest.py            # write the manifest
    python benchmark/scripts/make_set_manifest.py --check    # exit 1 if files differ from it
    python benchmark/scripts/make_set_manifest.py --hash     # print the current combined hash
"""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

QUESTIONS = Path(__file__).resolve().parents[1] / "questions"
MANIFEST = QUESTIONS / "SET_MANIFEST.json"


def file_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(QUESTIONS.glob("question_*.yaml"))}


def combined_hash(hashes):
    listing = "".join(f"{h}  {name}\n" for name, h in sorted(hashes.items()))
    return hashlib.sha256(listing.encode()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(QUESTIONS), *args], text=True).strip()


def build():
    dirty = git("status", "--porcelain", "--", "question_*.yaml")
    if dirty:
        sys.exit(f"ERROR: uncommitted question files; commit them first:\n{dirty}")
    hashes = file_hashes()
    held_out, by_type = [], {}
    for name in hashes:
        q = yaml.safe_load((QUESTIONS / name).read_text())
        by_type[q["type"]] = by_type.get(q["type"], 0) + 1
        if q.get("held_out") is True:
            held_out.append(q["id"])
    return {
        "set_hash": combined_hash(hashes),
        "created": datetime.date.today().isoformat(),
        "questions_commit": git("log", "-1", "--format=%H", "--", "question_*.yaml"),
        "question_count": len(hashes),
        "by_type": dict(sorted(by_type.items())),
        "held_out": held_out,
        "hash_method": "sha256 of sorted '<sha256>  <filename>\\n' lines (sha256sum format)",
        "files": hashes,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="verify files against the manifest")
    ap.add_argument("--hash", action="store_true", help="print the current combined hash")
    args = ap.parse_args()

    if args.hash:
        print(combined_hash(file_hashes()))
        return
    if args.check:
        m = json.loads(MANIFEST.read_text())
        cur = file_hashes()
        changed = sorted(n for n in set(cur) | set(m["files"]) if cur.get(n) != m["files"].get(n))
        if changed:
            print(f"MISMATCH vs manifest {m['set_hash'][:12]} ({len(changed)} file(s)):")
            for n in changed:
                print(f"  {n}")
            sys.exit(1)
        print(f"OK: {len(cur)} questions match set {m['set_hash']}")
        return

    m = build()
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n")
    print(f"Wrote {MANIFEST.relative_to(QUESTIONS.parents[1])}: "
          f"{m['question_count']} questions, set {m['set_hash']}")


if __name__ == "__main__":
    main()

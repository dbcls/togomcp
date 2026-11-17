#!/usr/bin/env python3
"""Probe a deployed TogoMCP's skills-over-MCP (SEP-2640) surface, as a client sees it.

The curl probe in CLAUDE.md sends `initialize` on protocol 2025-06-18, and
skills/list does not exist there: FastMCP binds skills/list and skills/get to the
2026-07-28 protocol only. This script connects on 2026-07-28 with the Skills
client extension and prints what a supporting host would see: the server
version, each skill with its metadata.version and file count, and one digest
per skill. The digest is a sha256 over the sorted per-file digests, so a
changed digest is what makes such a host ask its users to re-approve the skill.
With --verify it also downloads every file and checks each one against the
digest and size the server advertised (read_skill).

Usage:
    uv run python scripts/probe_skills.py                                    # production
    uv run python scripts/probe_skills.py --url https://test-togomcp.rdfportal.org/mcp
    uv run python scripts/probe_skills.py --url http://localhost:8000/mcp --verify

Exit status: 0 = skills/list answered; 1 = the server does not offer the Skills
extension (for example, a build older than 2.34.0) or the request failed.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys

DEFAULT_URL = "https://togomcp.rdfportal.org/mcp"
SKILLS_EXTENSION = "io.modelcontextprotocol/skills"


def _skill_digest(entry) -> str:
    h = hashlib.sha256()
    for r in sorted(entry.resources, key=lambda r: r.uri):
        h.update(f"{r.uri} {r.digest}\n".encode("utf-8"))
    return h.hexdigest()[:12]


async def probe(url: str, verify: bool) -> int:
    from fastmcp import Client
    from fastmcp.skills import SkillsClientExtension

    async with Client(url, extensions=[SkillsClientExtension()]) as client:
        version = getattr(client.server_info, "version", None)  # either protocol era
        print(f"server:   {url}")
        print(f"protocol: {client.protocol_version}")
        print(f"version:  {version or '?'}")
        caps = client.server_capabilities
        extensions = (caps.extensions if caps else None) or {}
        if SKILLS_EXTENSION not in extensions:
            print(f"\n{SKILLS_EXTENSION} is NOT advertised: this server has no skills/list.")
            return 1

        entries = await client.list_skills()
        print(f"\n{len(entries)} skills\n")
        print(f"{'name':28} {'version':8} {'files':>5} {'bytes':>8}  digest")
        for e in entries:
            fm = e.frontmatter.root
            meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
            files = e.resources if isinstance(e.resources, list) else []
            print(
                f"{fm.get('name', '?'):28} {str(meta.get('version', '-')):8} "
                f"{len(files):>5} {sum(r.size for r in files):>8}  {_skill_digest(e)}"
                + ("  (entry)" if meta.get("role") == "entry" else "")
            )

        if verify:
            print()
            for e in entries:
                skill = await client.read_skill(e.uri)  # raises on any mismatch
                print(f"verified  {e.uri}  ({len(skill.files)} files)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--url", default=DEFAULT_URL, help=f"MCP endpoint (default {DEFAULT_URL})")
    ap.add_argument("--verify", action="store_true", help="download every file and check its digest")
    args = ap.parse_args(argv)
    try:
        return asyncio.run(probe(args.url, args.verify))
    except Exception as exc:  # report, don't trace: this is an ops probe
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

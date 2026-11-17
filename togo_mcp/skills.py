"""Workflow (Agent Skill) registry: the ONE copy behind every skill route.

Three routes serve the same in-memory bytes: the `get_workflow` tool (hosts whose
models only call tools), `skill://<name>/...` resources (any resource-reading host),
and the SEP-2640 Skills extension's `skills/list` / `skills/get` (2026-07-28 protocol
only). The last two come from FastMCP's `SkillCatalogProvider`, fed by
`to_fastmcp_skill()` below, so the disk is read once and every route agrees.

A workflow is an Agent Skills directory — `SKILL.md` plus `references/` — that drives
the TogoMCP tools through a multi-step analysis. They are served from the server so
that there is ONE canonical copy: the skills carry fast-changing facts of the same kind
as MIE gotchas, and a fix to a server copy reaches every client at once, including hosts
whose models never read MCP resources on their own (Claude Desktop, claude.ai).

Only `data/skills/public/` is served. The developer skills (mie-generator, qa-generator,
intro-page-updater) stay in `.claude/skills/`, outside the package, so neither the tool
nor the resource route can reach them. `.claude/skills/<public name>` are symlinks INTO
`public/`, which keeps Claude Code's in-repo discovery working without a second copy.

This module is pure apart from `to_fastmcp_skill()`, the one function that imports
FastMCP (lazily); everything else has no FastMCP and no server state. The registry is built once at import
(a deploy restarts the server), and it fails LOUDLY on a malformed skill — a skill that
silently dropped out of the catalog would be indistinguishable from one never shipped.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

MAIN_FILE = "SKILL.md"
ALLOWED_SUFFIXES = frozenset({".md", ".yaml", ".yml", ".txt"})
_CATALOG_MAX = 120
# Agent Skills specification limits (agentskills.io/specification), which FastMCP
# also enforces when it builds a Skill. Checked here too, so the registry fails at
# load with a message naming the file rather than inside the provider.
NAME_MAX = 64
DESCRIPTION_MAX = 1024
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# `metadata.role` values. An entry skill is served only on the resource/SEP routes,
# never by get_workflow or in the Usage Guide's Workflows list (see rdf_portal.py).
ROLE_ENTRY = "entry"
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)


class SkillRegistryError(ValueError):
    """A skill directory is malformed. Raised at load time, never swallowed."""


@dataclass(frozen=True)
class SkillFile:
    path: str  # POSIX path relative to the skill root
    size: int
    content: str


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    catalog: str
    version: str | None
    # Aggregate digest: ONE sha256 over every file's path and content, used by
    # get_workflow's header. Not the SEP-2640 digest, which is per file (sha256 of
    # that file's bytes) and is computed by FastMCP for skills/list.
    digest: str
    root: Path
    files: dict[str, SkillFile] = field(default_factory=dict)
    role: str | None = None  # metadata.role, e.g. ROLE_ENTRY

    @property
    def short_digest(self) -> str:
        return self.digest[:12]

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files.values())

    @property
    def main(self) -> SkillFile:
        return self.files[MAIN_FILE]


def parse_frontmatter(text: str) -> dict:
    """Real YAML frontmatter parse (folded `>` descriptions, nested `metadata`)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    data = yaml.safe_load(m.group(1))
    return data if isinstance(data, dict) else {}


def _first_sentence(text: str, limit: int = _CATALOG_MAX) -> str:
    flat = " ".join(text.split())
    m = re.search(r"(?<=[.!?])\s", flat)
    sentence = flat[: m.start()] if m else flat
    if len(sentence) > limit:
        sentence = sentence[: limit - 1].rstrip() + "…"
    return sentence


def _scan_files(root: Path) -> dict[str, SkillFile]:
    """Every allowed, non-symlink regular file under `root`, not descending into
    symlinked directories. Disallowed suffixes are skipped (not served), not errors."""
    files: dict[str, SkillFile] = {}
    stack = [root]
    while stack:
        d = stack.pop()
        for entry in sorted(d.iterdir()):
            if entry.is_symlink():
                continue
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file() and entry.suffix.lower() in ALLOWED_SUFFIXES:
                rel = entry.relative_to(root).as_posix()
                data = entry.read_bytes()
                files[rel] = SkillFile(rel, len(data), data.decode("utf-8"))
    return dict(sorted(files.items()))


def _digest(files: dict[str, SkillFile]) -> str:
    h = hashlib.sha256()
    for rel, f in sorted(files.items()):
        h.update(rel.encode("utf-8") + b"\0")
        h.update(f.content.encode("utf-8") + b"\0")
    return h.hexdigest()


def load_skill(skill_dir: Path) -> Skill:
    main = skill_dir / MAIN_FILE
    if main.is_symlink() or not main.is_file():
        raise SkillRegistryError(f"{skill_dir}: {MAIN_FILE} missing or not a regular file")
    fm = parse_frontmatter(main.read_text(encoding="utf-8"))
    name = fm.get("name")
    if not name:
        raise SkillRegistryError(f"{main}: frontmatter has no `name`")
    if not isinstance(name, str) or len(name) > NAME_MAX or not _NAME_RE.match(name):
        raise SkillRegistryError(
            f"{main}: name {name!r} must be lowercase letters, digits and single "
            f"hyphens, at most {NAME_MAX} characters"
        )
    if name != skill_dir.name:
        raise SkillRegistryError(
            f"{main}: frontmatter name {name!r} does not match directory {skill_dir.name!r}"
        )
    description = fm.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SkillRegistryError(f"{main}: frontmatter has no `description`")
    if len(description) > DESCRIPTION_MAX:
        raise SkillRegistryError(
            f"{main}: description is {len(description)} characters "
            f"(Agent Skills limit {DESCRIPTION_MAX})"
        )
    description = " ".join(description.split())
    meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    catalog = meta.get("catalog")
    catalog = " ".join(str(catalog).split()) if catalog else _first_sentence(description)
    version = meta.get("version")
    role = meta.get("role")
    files = _scan_files(skill_dir)
    return Skill(
        name=name,
        description=description,
        catalog=catalog,
        version=str(version) if version is not None else None,
        digest=_digest(files),
        root=skill_dir.resolve(),
        files=files,
        role=str(role) if role is not None else None,
    )


def load_registry(root: Path) -> dict[str, Skill]:
    """Load every `<root>/<dir>/SKILL.md`. Raises SkillRegistryError on any bad skill."""
    registry: dict[str, Skill] = {}
    if not root.is_dir():
        raise SkillRegistryError(f"skills root not found: {root}")
    for d in sorted(root.iterdir()):
        if d.is_symlink() or not d.is_dir() or not (d / MAIN_FILE).exists():
            continue
        skill = load_skill(d)
        if skill.name in registry:
            raise SkillRegistryError(f"duplicate skill name {skill.name!r} under {root}")
        registry[skill.name] = skill
    return registry


def to_fastmcp_skill(skill: Skill) -> Any:
    """The registry snapshot as a FastMCP `Skill` (SEP-2640 resources + skills/list).

    Built from the registry's own file contents, not re-read from disk, so the
    resource route and get_workflow serve identical bytes. FastMCP parses the
    frontmatter itself (that verbatim copy is what skills/list returns), so check
    that its parse agrees with ours: a mismatch would make skills/list and
    get_workflow describe the same skill differently, and must stop the boot.
    """
    from fastmcp.skills import Skill as FastMCPSkill

    try:
        fm = FastMCPSkill.from_files(
            {path: f.content.encode("utf-8") for path, f in skill.files.items()}
        )
    except Exception as exc:  # FastMCP's own Agent Skills validation
        raise SkillRegistryError(f"{skill.root}: rejected by FastMCP: {exc}") from exc
    if fm.name != skill.name or " ".join(fm.description.split()) != skill.description:
        raise SkillRegistryError(
            f"{skill.root}: FastMCP parses the frontmatter differently from the "
            f"registry (name {fm.name!r} vs {skill.name!r}, or the description differs)"
        )
    return fm


def resolve_path(skill: Skill, path: str) -> SkillFile:
    """Validate a caller-supplied relative path. Raises SkillRegistryError with a
    caller-readable reason; the caller adds the retry guidance."""
    if not path or not path.strip():
        raise SkillRegistryError("`path` is empty")
    if "\\" in path or "\0" in path:
        raise SkillRegistryError(f"invalid path {path!r}: use forward slashes")
    p = PurePosixPath(path)
    if p.is_absolute() or re.match(r"^[A-Za-z]:", path):
        raise SkillRegistryError(f"invalid path {path!r}: must be relative to the workflow root")
    if ".." in p.parts:
        raise SkillRegistryError(f"invalid path {path!r}: `..` is not allowed")
    if p.suffix.lower() not in ALLOWED_SUFFIXES:
        raise SkillRegistryError(
            f"invalid path {path!r}: only {', '.join(sorted(ALLOWED_SUFFIXES))} files are served"
        )
    rel = p.as_posix()
    # Lookup is against the load-time snapshot, so a path can only ever name a file
    # that was a regular, non-symlink file inside the skill root when it was scanned.
    f = skill.files.get(rel)
    if f is None:
        raise SkillRegistryError(f"no file {path!r} in workflow {skill.name!r}")
    return f


def format_size(n: int) -> str:
    return f"{n / 1024:.1f} KB"

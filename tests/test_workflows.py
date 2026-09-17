"""Workflow (Agent Skill) delivery: the registry, `get_workflow`, the Usage Guide's
Workflows section, and the `skill://` resources.

The two properties that matter most are asserted against what a CLIENT receives
(in-memory `fastmcp.Client`), not against module internals:

* internal/dev skills (mie-generator, qa-generator, intro-page-updater) are reachable
  by NEITHER route, and an attempt does not reveal that they exist;
* the tool and the resource route serve the same bytes, from one copy.
"""

import asyncio
import json
import os
from pathlib import Path

import pytest

from togo_mcp import skills as sk

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "togo_mcp" / "data" / "skills" / "public"
EXPECTED = {"prism", "research-article-analysis", "disease-analysis"}
INTERNAL = ("mie-generator", "qa-generator", "intro-page-updater")


def _run(calls, *, local: bool = False):
    from fastmcp import Client

    from togo_mcp.main import mcp, setup

    async def go():
        await setup(local=local)
        async with Client(mcp) as client:
            return await calls(client)

    return asyncio.run(go())


def _call(args: dict, **kw) -> str:
    async def calls(client):
        res = await client.call_tool("get_workflow", args)
        return res.content[0].text

    return _run(calls, **kw)


def _write_skill(root: Path, dirname: str, frontmatter: str, files: dict | None = None) -> Path:
    d = root / dirname
    (d / "references").mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n# Body\n", encoding="utf-8")
    for rel, text in (files or {}).items():
        (d / rel).write_text(text, encoding="utf-8")
    return d


# --- Registry ---------------------------------------------------------------


class TestRegistry:
    def test_public_skills_load_with_matching_names(self) -> None:
        reg = sk.load_registry(PUBLIC)
        assert set(reg) == EXPECTED
        for name, skill in reg.items():
            assert skill.root.name == name
            assert skill.description and skill.catalog
            assert "SKILL.md" in skill.files

    def test_internal_skills_are_not_in_the_package_tree(self) -> None:
        pkg_skills = REPO / "togo_mcp" / "data" / "skills"
        found = {p.parent.name for p in pkg_skills.rglob("SKILL.md")}
        assert not found & set(INTERNAL)

    def test_folded_description_is_parsed_as_yaml(self) -> None:
        # prism uses `description: >` — a naive line parser yields ">".
        assert sk.load_registry(PUBLIC)["prism"].description.startswith("PRISM finds")

    def test_name_mismatch_raises(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha", "name: beta\ndescription: x")
        with pytest.raises(sk.SkillRegistryError, match="does not match"):
            sk.load_registry(tmp_path)

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha", "description: x")
        with pytest.raises(sk.SkillRegistryError, match="no `name`"):
            sk.load_registry(tmp_path)

    def test_missing_description_raises(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha", "name: alpha")
        with pytest.raises(sk.SkillRegistryError, match="no `description`"):
            sk.load_registry(tmp_path)

    def test_duplicate_name_raises(self, tmp_path: Path, monkeypatch) -> None:
        # name must equal the directory name, so two directories in one root cannot
        # collide on disk; stub load_skill to make them collide and prove the guard.
        _write_skill(tmp_path, "alpha", "name: alpha\ndescription: x")
        skill = sk.load_skill(tmp_path / "alpha")
        _write_skill(tmp_path, "beta", "name: beta\ndescription: y")
        monkeypatch.setattr(sk, "load_skill", lambda d: skill)
        with pytest.raises(sk.SkillRegistryError, match="duplicate"):
            sk.load_registry(tmp_path)

    def test_catalog_prefers_metadata_then_first_sentence(self, tmp_path: Path) -> None:
        _write_skill(
            tmp_path, "a",
            'name: a\ndescription: First one. Second.\nmetadata:\n  version: "1.0"\n  catalog: Short line',
        )
        _write_skill(tmp_path, "b", "name: b\ndescription: First one. Second.")
        reg = sk.load_registry(tmp_path)
        assert reg["a"].catalog == "Short line" and reg["a"].version == "1.0"
        assert reg["b"].catalog == "First one." and reg["b"].version is None

    def test_digest_tracks_content(self, tmp_path: Path) -> None:
        d = _write_skill(tmp_path, "a", "name: a\ndescription: x", {"references/r.md": "one"})
        first = sk.load_skill(d).digest
        assert sk.load_skill(d).digest == first
        (d / "references" / "r.md").write_text("two", encoding="utf-8")
        assert sk.load_skill(d).digest != first

    def test_symlinks_and_disallowed_suffixes_are_not_loaded(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("secret", encoding="utf-8")
        d = _write_skill(tmp_path / "root", "a", "name: a\ndescription: x", {"references/ok.md": "ok"})
        os.symlink(outside / "secret.md", d / "references" / "link.md")
        os.symlink(outside, d / "linkdir")
        (d / "references" / "script.py").write_text("print()", encoding="utf-8")
        files = sk.load_skill(d).files
        assert set(files) == {"SKILL.md", "references/ok.md"}


# --- get_workflow -----------------------------------------------------------


class TestGetWorkflow:
    def test_listing_has_public_and_no_internal(self) -> None:
        text = _call({})
        for name in EXPECTED:
            assert f"- {name}:" in text
        for name in INTERNAL:
            assert name not in text
        assert "digest:" in text

    def test_name_returns_header_and_raw_skill_md(self) -> None:
        from togo_mcp.rdf_portal import WORKFLOWS

        skill = WORKFLOWS["prism"]
        text = _call({"name": "prism"})
        header = text.partition("\n---\n")[0]
        assert text.endswith("\n" + skill.main.content)
        assert f"digest: {skill.short_digest}" in header
        for rel, f in skill.files.items():
            if rel == "SKILL.md":
                continue
            assert rel in header and sk.format_size(f.size) in header
            assert f.size == (PUBLIC / "prism" / rel).stat().st_size

    def test_path_returns_reference_body(self) -> None:
        expected = (PUBLIC / "prism" / "references" / "worked-example.md").read_text(encoding="utf-8")
        assert _call({"name": "prism", "path": "references/worked-example.md"}) == expected

    @pytest.mark.parametrize(
        "bad", ["../SKILL.md", "/etc/passwd", "references/../../x.md", "references/x.py", "C:\\x.md"]
    )
    def test_bad_paths_are_rejected(self, bad: str) -> None:
        text = _call({"name": "prism", "path": bad})
        assert text.startswith("Error:") and "Do not retry" in text

    def test_missing_path_lists_files(self) -> None:
        text = _call({"name": "prism", "path": "references/nope.md"})
        assert text.startswith("Error:") and "references/sparql-templates.md" in text

    def test_path_without_name_is_an_error(self) -> None:
        assert _call({"path": "SKILL.md"}).startswith("Error:")

    @pytest.mark.parametrize("name", ["no-such-workflow", *INTERNAL])
    def test_unknown_and_internal_names_list_valid_names(self, name: str) -> None:
        text = _call({"name": name})
        assert text.startswith("Error:")
        for valid in EXPECTED:
            assert valid in text

    def test_symlink_in_skill_is_rejected_by_tool(self, tmp_path: Path, monkeypatch) -> None:
        import togo_mcp.rdf_portal as rp

        outside = tmp_path / "secret.md"
        outside.write_text("secret", encoding="utf-8")
        d = _write_skill(tmp_path / "root", "a", "name: a\ndescription: x")
        os.symlink(outside, d / "references" / "link.md")
        monkeypatch.setattr(rp, "WORKFLOWS", sk.load_registry(tmp_path / "root"))
        text = _call({"name": "a", "path": "references/link.md"})
        assert text.startswith("Error:") and "secret" not in text

    @pytest.mark.parametrize("local", [False, True])
    def test_registered_on_http_and_stdio(self, local: bool) -> None:
        # run() (HTTP) and run_local() (stdio) serve the same root `mcp`; only
        # setup(local=...) differs, so check the tool list after each.
        async def calls(client):
            return {t.name for t in await client.list_tools()}

        assert "get_workflow" in _run(calls, local=local)


# --- Usage Guide ------------------------------------------------------------


def test_usage_guide_workflows_section_matches_registry() -> None:
    from togo_mcp.rdf_portal import WORKFLOWS

    guide = _call_guide()
    assert "## Workflows (fetch with get_workflow(name))" in guide
    for s in WORKFLOWS.values():
        assert f"- {s.name}: {s.catalog}" in guide
    # placed right after GATE 0's part, before the budgets part
    assert guide.index("GATE 0") < guide.index("## Workflows") < guide.index(
        (REPO / "togo_mcp/data/resources/usage_guide_v6/02_budgets_and_discovery.md")
        .read_text(encoding="utf-8").strip().splitlines()[0]
    )


def _call_guide() -> str:
    async def calls(client):
        return (await client.call_tool("TogoMCP_Usage_Guide", {})).content[0].text

    return _run(calls)


# --- Resources --------------------------------------------------------------


class TestResources:
    def test_list_has_public_skills_only(self) -> None:
        async def calls(client):
            return [str(r.uri) for r in await client.list_resources()]

        uris = _run(calls)
        for name in EXPECTED:
            assert f"skill://{name}/SKILL.md" in uris
        for name in INTERNAL:
            assert not any(name in u for u in uris)

    def test_resource_and_tool_serve_same_skill_md(self) -> None:
        async def calls(client):
            out = {}
            for name in EXPECTED:
                res = await client.read_resource(f"skill://{name}/SKILL.md")
                tool = (await client.call_tool("get_workflow", {"name": name})).content[0].text
                out[name] = (res[0].text, tool)
            return out

        for name, (resource_text, tool_text) in _run(calls).items():
            assert tool_text.endswith("\n" + resource_text), name

    def test_manifest_matches_registry_files(self) -> None:
        from togo_mcp.rdf_portal import WORKFLOWS

        async def calls(client):
            return {
                n: json.loads((await client.read_resource(f"skill://{n}/_manifest"))[0].text)
                for n in EXPECTED
            }

        for name, manifest in _run(calls).items():
            assert {f["path"] for f in manifest["files"]} == set(WORKFLOWS[name].files)

    def test_resource_description_is_real_description(self) -> None:
        async def calls(client):
            return {str(r.uri): r.description for r in await client.list_resources()}

        descs = _run(calls)
        assert descs["skill://prism/SKILL.md"].startswith("PRISM finds")

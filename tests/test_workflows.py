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
# The workflows: get_workflow and the Usage Guide serve exactly these.
EXPECTED = {"prism", "research-article-analysis", "disease-analysis", "query-provenance"}
# The entry skill: served on the resource / SEP-2640 routes only.
ENTRY = "togomcp-start"
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
        assert set(reg) == EXPECTED | {ENTRY}
        assert set(sk.workflows_of(reg)) == EXPECTED
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

    @pytest.mark.parametrize("bad", ["Prism", "pr_ism", "-prism", "a--b", "x" * 65])
    def test_invalid_name_raises(self, tmp_path: Path, bad: str) -> None:
        _write_skill(tmp_path, bad, f"name: {bad}\ndescription: x")
        with pytest.raises(sk.SkillRegistryError, match="lowercase"):
            sk.load_skill(tmp_path / bad)

    def test_overlong_description_raises(self, tmp_path: Path) -> None:
        d = _write_skill(tmp_path, "a", "name: a\ndescription: " + "x" * 1025)
        with pytest.raises(sk.SkillRegistryError, match="1025 characters"):
            sk.load_skill(d)

    def test_public_descriptions_fit_the_spec_limit(self) -> None:
        # prism is ~930 of 1024: the margin is small, so say which skill overflowed.
        for d in sorted(PUBLIC.iterdir()):
            fm = sk.parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
            assert len(fm["description"]) <= sk.DESCRIPTION_MAX, d.name

    def test_role_comes_from_metadata(self, tmp_path: Path) -> None:
        d = _write_skill(tmp_path, "a", "name: a\ndescription: x\nmetadata:\n  role: entry")
        assert sk.load_skill(d).role == sk.ROLE_ENTRY
        assert sk.load_registry(PUBLIC)["prism"].role is None

    def test_two_entry_skills_raise(self, tmp_path: Path) -> None:
        for n in ("a", "b"):
            _write_skill(tmp_path, n, f"name: {n}\ndescription: x\nmetadata:\n  role: entry")
        with pytest.raises(sk.SkillRegistryError, match="more than one entry skill"):
            sk.workflows_of(sk.load_registry(tmp_path))

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


# --- FastMCP adapter ---------------------------------------------------------


class TestToFastMCPSkill:
    def test_bytes_and_frontmatter_match_disk(self) -> None:
        for skill in sk.load_registry(PUBLIC).values():
            fm = sk.to_fastmcp_skill(skill)
            assert fm.name == skill.name
            assert set(fm.files) == set(skill.files), skill.name
            for rel, data in fm.files.items():
                assert data == (skill.root / rel).read_bytes(), (skill.name, rel)

    def test_parser_disagreement_raises(self, tmp_path: Path) -> None:
        import dataclasses

        skill = sk.load_skill(_write_skill(tmp_path, "a", "name: a\ndescription: real"))
        with pytest.raises(sk.SkillRegistryError, match="differently"):
            sk.to_fastmcp_skill(dataclasses.replace(skill, description="other"))


def test_no_deprecated_fastmcp_api_at_import() -> None:
    # FastMCP 4.3 removes what 4.2 deprecates (the old skills provider among them).
    # A fresh process, because a module an earlier test imported warns no more.
    # The filter is set AFTER importing fastmcp, whose __init__ installs a "default"
    # filter for its own category; matching on the category (not module=) because
    # FastMCP attributes the warning to the CALLER's module, i.e. togo_mcp.
    import subprocess
    import sys

    code = (
        "import warnings, fastmcp\n"
        "warnings.simplefilter('error', fastmcp.FastMCPDeprecationWarning)\n"
        "import togo_mcp.main\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO
    )
    assert proc.returncode == 0, proc.stderr[-2000:]


# --- get_workflow -----------------------------------------------------------


class TestGetWorkflow:
    def test_listing_has_public_and_no_internal(self) -> None:
        text = _call({})
        for name in EXPECTED:
            assert f"- {name}:" in text
        for name in (*INTERNAL, ENTRY):
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

    @pytest.mark.parametrize("name", ["no-such-workflow", *INTERNAL, ENTRY])
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

    def test_workflows_named_in_description_exist(self) -> None:
        # The description routes "save the queries for a paper" to query-provenance by
        # NAME, because it is the one text still in view when that request arrives (the
        # guide was read at the start). A fixed string cannot follow a rename, so pin it.
        import re

        from togo_mcp.rdf_portal import WORKFLOWS

        async def calls(client):
            tools = await client.list_tools()
            return next(t for t in tools if t.name == "get_workflow").description

        named = set(re.findall(r'name="([a-z0-9-]+)"', _run(calls))) - {"usage-guide"}
        assert named, "the description no longer routes to any workflow by name"
        assert named <= set(WORKFLOWS), named - set(WORKFLOWS)


# --- Usage Guide ------------------------------------------------------------


def test_usage_guide_workflows_section_matches_registry() -> None:
    from togo_mcp.rdf_portal import WORKFLOWS

    guide = _call_guide()
    assert "## Workflows (fetch with get_workflow(name))" in guide
    for s in WORKFLOWS.values():
        assert f"- {s.name}: {s.catalog}" in guide
    assert ENTRY not in guide
    # placed right after GATE 0's part, before the budgets part
    assert guide.index("GATE 0") < guide.index("## Workflows") < guide.index(
        (REPO / "togo_mcp/data/resources/usage_guide_v7/02_budgets_and_discovery.md")
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
        for name in (*EXPECTED, ENTRY):
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
        # FastMCP < 4.2 read a folded `description: >` as the literal ">", which
        # rdf_portal.py patched over. 4.2 parses real YAML, so no patch remains.
        async def calls(client):
            return {str(r.uri): r.description for r in await client.list_resources()}

        descs = _run(calls)
        assert descs["skill://prism/SKILL.md"].startswith("PRISM finds")


# --- Entry skill (togomcp-start) ---------------------------------------------
#
# Its only job is to route a SEP-2640 host's skill list to TogoMCP_Usage_Guide.
# Every edit changes its digest, which makes supporting hosts ask every user to
# re-approve it — so it must not carry facts that change with releases.


class TestEntrySkill:
    @staticmethod
    def _body() -> str:
        return (PUBLIC / ENTRY / "SKILL.md").read_text(encoding="utf-8")

    def test_is_small(self) -> None:
        assert len(self._body().encode("utf-8")) < 2048

    def test_is_the_entry_role(self) -> None:
        assert sk.load_registry(PUBLIC)[ENTRY].role == sk.ROLE_ENTRY

    def test_named_tools_exist(self) -> None:
        import re

        async def calls(client):
            return {t.name for t in await client.list_tools()}

        tools = _run(calls)
        named = set(re.findall(r"`([A-Za-z_]+)(?:\(\))?`", self._body()))
        assert {"TogoMCP_Usage_Guide", "get_workflow"} <= named
        assert named <= tools, named - tools

    def test_names_no_workflow(self) -> None:
        # A workflow named here would change this digest whenever workflows change.
        body = self._body()
        for name in EXPECTED:
            assert name not in body, name

    def test_has_no_references(self) -> None:
        assert set(sk.load_registry(PUBLIC)[ENTRY].files) == {"SKILL.md"}


# --- SEP-2640 (skills/list, skills/get) ----------------------------------------
#
# Asserted against what a skills-extension CLIENT receives. skills/* exist only on
# the 2026-07-28 protocol; a handshake-protocol client gets resources + _manifest.


def _run_sep(calls, *, local: bool = False, mode: str = "auto"):
    from fastmcp import Client
    from fastmcp.skills import SkillsClientExtension

    from togo_mcp.main import mcp, setup

    async def go():
        await setup(local=local)
        async with Client(mcp, mode=mode, extensions=[SkillsClientExtension()]) as client:
            return await calls(client)

    return asyncio.run(go())


def _sha(data: bytes) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(data).hexdigest()


class TestSkillsExtension:
    @staticmethod
    def _list(**kw):
        async def calls(client):
            return await client.list_skills()

        return _run_sep(calls, **kw)

    @pytest.mark.parametrize("local", [False, True])
    def test_list_is_public_skills_plus_entry_on_both_transports(self, local: bool) -> None:
        entries = self._list(local=local)
        assert {e.uri for e in entries} == {
            f"skill://{n}/SKILL.md" for n in (*EXPECTED, ENTRY)
        }

    def test_list_excludes_guide_and_internal(self) -> None:
        text = json.dumps([e.model_dump(mode="json", by_alias=True) for e in self._list()])
        for name in (*INTERNAL, "usage-guide"):
            assert name not in text, name

    def test_frontmatter_is_the_registry_yaml_parse(self) -> None:
        for e in self._list():
            name = e.uri.split("/")[2]
            disk = sk.parse_frontmatter((PUBLIC / name / "SKILL.md").read_text(encoding="utf-8"))
            assert e.frontmatter.root == disk, name
            assert "version" in disk["metadata"] and "catalog" in disk["metadata"], name

    def test_digests_match_what_get_workflow_serves(self) -> None:
        # The routes must serve identical bytes. get_workflow returns SKILL.md
        # after a header; references/ verbatim. The entry skill is not served by
        # get_workflow, so compare it with the file on disk.
        async def calls(client):
            out = {}
            for e in await client.list_skills():
                name = e.uri.split("/")[2]
                for r in e.resources:
                    rel = r.uri.split("/", 3)[3]
                    if name == ENTRY:
                        body = (PUBLIC / name / rel).read_bytes()
                    else:
                        args = {"name": name} if rel == "SKILL.md" else {"name": name, "path": rel}
                        text = (await client.call_tool("get_workflow", args)).content[0].text
                        if rel == "SKILL.md":  # drop get_workflow's header
                            text = text[text.index("\n---\nname: ") + 1:]
                        body = text.encode("utf-8")
                    out[r.uri] = (r.digest, r.size, _sha(body), len(body))
            return out

        got = _run_sep(calls)
        assert len(got) == sum(len(s.files) for s in sk.load_registry(PUBLIC).values())
        for uri, (digest, size, want_digest, want_size) in got.items():
            assert (digest, size) == (want_digest, want_size), uri

    def test_resources_list_every_registry_file(self) -> None:
        for e in self._list():
            name = e.uri.split("/")[2]
            assert {r.uri for r in e.resources} == {
                f"skill://{name}/{rel}" for rel in sk.load_registry(PUBLIC)[name].files
            }

    @pytest.mark.parametrize("mode", ["auto", "legacy"])
    def test_read_skill_verifies_end_to_end(self, mode: str) -> None:
        # auto: manifest from skills/get; legacy: from the _manifest resource.
        async def calls(client):
            return {
                n: await client.read_skill(f"skill://{n}/SKILL.md") for n in (*EXPECTED, ENTRY)
            }

        for name, skill in _run_sep(calls, mode=mode).items():
            for rel, data in skill.files.items():
                assert data == (PUBLIC / name / rel).read_bytes(), (name, rel)

    def test_get_known_uri(self) -> None:
        async def calls(client):
            return await client.get_skill("skill://prism/SKILL.md")

        assert _run_sep(calls).frontmatter.root["name"] == "prism"

    @pytest.mark.parametrize("name", ["no-such-skill", "usage-guide", *INTERNAL])
    def test_get_unknown_or_internal_uri_is_invalid_params(self, name: str) -> None:
        from mcp.shared.exceptions import MCPError

        async def calls(client):
            with pytest.raises(MCPError) as exc:
                await client.get_skill(f"skill://{name}/SKILL.md")
            return exc.value

        assert _run_sep(calls).error.code == -32602

    def test_handshake_protocol_has_resources_but_no_skills_methods(self) -> None:
        async def calls(client):
            uris = {str(r.uri) for r in await client.list_resources()}
            with pytest.raises(RuntimeError, match="modern MCP connection"):
                await client.list_skills()
            return uris

        uris = _run_sep(calls, mode="legacy")
        assert f"skill://{ENTRY}/SKILL.md" in uris and "skill://prism/_manifest" in uris

    def test_each_skill_is_far_below_sep_limits(self) -> None:
        # SEP-2640 / FastMCP cap a skill at 512 files and 16 MiB.
        for s in sk.load_registry(PUBLIC).values():
            assert len(s.files) < 512 and s.total_size < 16 * 1024 * 1024, s.name

    @pytest.mark.parametrize("local", [False, True])
    @pytest.mark.parametrize("mode", ["auto", "legacy"])
    def test_extension_is_advertised(self, local: bool, mode: str) -> None:
        async def calls(client):
            # server_capabilities covers both eras (initialize or server/discover).
            caps = client.server_capabilities
            return caps.model_dump(mode="json", by_alias=True) if caps else {}

        caps = _run_sep(calls, local=local, mode=mode)
        advertised = "io.modelcontextprotocol/skills" in (caps.get("extensions") or {})
        # Only where skills/* exist: a handshake client is not told about methods
        # it cannot call (it still reads the skill:// resources).
        assert advertised == (mode == "auto"), caps

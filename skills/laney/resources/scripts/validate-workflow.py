#!/usr/bin/env python3
"""Validate a laney workflow against manifest contract v1.

Ships inside the skill bundle (resources/scripts/) so the load flow can
invoke it wherever the skill is installed — the repo-level scripts/ dir
does not travel with the plugin.

Usage:
    python3 <install-root>/resources/scripts/validate-workflow.py <workflow-dir> [options]

Options:
    --origin {builtin,local}   Trust origin (default: local). Only `builtin`
                               gets install-anchored treatment; the builtin
                               set is empty in v1 but the mechanism ships.
    --builtin-root PATH        Directory holding builtin workflows
                               (default: the install's skills/laney/workflows)
    --hash                     Print the sha256 over every file in the folder
                               (framed by path + length) and exit

Exit codes: 0 = valid (warnings allowed), 1 = invalid.
Fail-closed: a crash or an unreadable declared file is invalid, never a pass.

Stdlib only (tomllib requires Python >= 3.11). Run standalone this is
advisory; invoked by the `load` flow it is authoritative.

Error catalog W01-W15: docs/workflow-contract.md in the laney repo.
Messages are literal and fix-forward.
"""

import argparse
import hashlib
import re
import sys
import tomllib
from pathlib import Path

CONTRACT_SUPPORTED = (1,)
# A workflow id is a bare slug — never a path. It becomes a path component
# (`.laney/workflows/<id>` materialization is reserved post-v1), so `..`,
# slashes, and absolute paths are rejected before anything uses the id.
WORKFLOW_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MODES = {"native", "invoke"}
CAPTURES = {"stdout", "files"}
RESERVED_OWNERS = {"human", "judge"}
PLACEHOLDER_VOCAB = {"prompt_file", "run_dir"}
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")
INJECTION_PATTERNS = ("ignore previous", "you must now", "disregard the above")
DEFAULT_TIMEOUT_SECONDS = 600

TOP_REQUIRED = ("id", "version", "contract", "description")
# Reserved for later contracts — declaring them today warns (W15), ignored.
RESERVED_KEYS = {"extends", "detect", "command", "identity"}
TOP_KNOWN = {"id", "version", "contract", "description", "body",
             "roles", "phase", "artifact", "judge"}
ROLE_KNOWN = {"mode", "command", "capture", "timeout_seconds", "description"}
PHASE_KNOWN = {"id", "title", "owner", "body", "reads", "writes"}
ARTIFACT_KNOWN = {"id", "file", "template", "versioned", "description"}
JUDGE_KNOWN = {"commands", "evidence", "max_fix_loops", "on_fail"}


def default_builtin_root() -> Path:
    # this script lives at <install-root>/resources/scripts/; builtin
    # workflows at <install-root>/workflows/
    return Path(__file__).resolve().parent.parent.parent / "workflows"


class Result:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, code: str, msg: str):
        self.errors.append(f"{code}: {msg}")

    def warn(self, code: str, msg: str):
        self.warnings.append(f"warning {code}: {msg}")


def load_manifest(root: Path, res: Result) -> dict | None:
    manifest = root / "workflow.toml"
    if not manifest.is_file():
        res.error("W01", f"workflow.toml: not found in {root}")
        return None
    try:
        with open(manifest, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        res.error("W01", f"workflow.toml: parse error: {e}")
    except OSError as e:
        res.error("W01", f"workflow.toml: unreadable: {e}")
    return None


def resolve_declared(path_str: str, root: Path, label: str, res: Result) -> Path | None:
    """Uniform folder confinement: every workflow's declared paths resolve
    inside its own folder, regardless of origin."""
    p = Path(path_str)
    if p.is_absolute() or ".." in p.parts:
        res.error("W04", f"{label}: declared path '{path_str}' escapes the workflow root; move the file inside the folder")
        return None
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root.resolve()):  # symlink escape
        res.error("W04", f"{label}: declared path '{path_str}' escapes the workflow root via a symlink; move the file inside the folder")
        return None
    if resolved.is_file():
        try:
            with open(resolved, "rb"):
                pass
        except OSError:
            res.error("W04", f"{label}: declared path '{path_str}' exists but is unreadable — fix its permissions")
            return None
        return resolved
    res.error("W04", f"{label}: declared path '{path_str}' does not exist")
    return None


def check_tree_confinement(root: Path, res: Result) -> None:
    """Reject symlinks, `.git/`, and non-regular files anywhere under the
    workflow folder (W04). A workflow must be self-contained plain files, and
    every file must be covered by the trust hash: a symlink's target mutates
    without changing the folder's bytes, `.git/` is skipped by the hash (so
    content under it would be a hash-blind channel), and a FIFO/socket/device
    is unhashable. Cheap top-level `.git` check first."""
    root_r = root.resolve()
    top_git = root_r / ".git"
    if top_git.exists() or top_git.is_symlink():
        res.error("W04", "'.git' present under the workflow root — a workflow must be a clean content folder, not a git working tree; load a copy without .git")
        return
    for f in root_r.rglob("*"):
        rel = f.relative_to(root_r)
        if ".git" in rel.parts:
            res.error("W04", f"'.git' path '{rel.as_posix()}' under the workflow root — VCS metadata is not workflow content and is hash-blind; remove it")
            return
        if f.is_symlink():
            res.error("W04", f"symlink '{rel.as_posix()}' under the workflow root — workflows must be self-contained plain files; replace it with the real file")
        elif not f.is_dir() and not f.is_file():
            res.error("W04", f"non-regular entry '{rel.as_posix()}' under the workflow root — only regular files and directories are allowed")


def check_top_level(data: dict, res: Result):
    for field in TOP_REQUIRED:
        if field not in data:
            res.error("W02", f"manifest: missing required field '{field}'")
    wid = data.get("id", "")
    if not isinstance(wid, str):
        res.error("W02", "manifest: 'id' must be a string")
    elif wid and not WORKFLOW_ID_RE.match(wid):
        res.error("W04", f"manifest: 'id' {wid!r} is not a valid workflow id — must be a slug (lowercase alphanumeric with single hyphens, e.g. 'my-workflow'); the id is used as a path component, so `..`, slashes, or absolute paths are rejected")
    if not isinstance(data.get("version", ""), str):
        res.error("W02", "manifest: 'version' must be a string")
    contract = data.get("contract")
    if contract is not None and not isinstance(contract, int):
        res.error("W02", "manifest: 'contract' must be an integer")
    elif isinstance(contract, int) and contract not in CONTRACT_SUPPORTED:
        supported = ", ".join(str(c) for c in CONTRACT_SUPPORTED)
        res.error("W03", f"manifest targets contract {contract}; this engine supports {supported} — upgrade laney or lower the manifest contract")
    desc = data.get("description")
    if desc is not None and (not isinstance(desc, str) or not desc.strip()):
        res.error("W02", "manifest: 'description' must be a non-empty string")
    body = data.get("body")
    if body is not None and not isinstance(body, str):
        res.error("W02", "manifest: 'body' must be a path string")
    for key in data:
        if key in RESERVED_KEYS:
            res.warn("W15", f"manifest: '{key}' is reserved for a later contract — ignored by this engine")
        elif key not in TOP_KNOWN:
            res.warn("W15", f"manifest: unknown key '{key}' — ignored by this engine")


def check_roles(data: dict, res: Result) -> dict[str, dict]:
    roles_tbl = data.get("roles")
    roles: dict[str, dict] = {}
    if roles_tbl is None:
        return roles
    if not isinstance(roles_tbl, dict):
        res.error("W02", "manifest: [roles] must be a table of role tables")
        return roles
    for name, role in roles_tbl.items():
        label = f"role '{name}'"
        if not WORKFLOW_ID_RE.match(name):
            res.error("W05", f"{label}: role names must be slugs (lowercase alphanumeric with single hyphens)")
        if name in RESERVED_OWNERS:
            res.error("W05", f"{label}: '{name}' is a reserved owner name — 'human' and 'judge' are never declared as roles ('judge' is configured by [judge])")
            continue
        if not isinstance(role, dict):
            res.error("W02", f"{label}: must be a table")
            continue
        mode = role.get("mode")
        if mode is None:
            res.error("W02", f"{label}: missing required field 'mode'")
        elif not isinstance(mode, str) or mode not in MODES:
            res.error("W05", f"{label}: mode '{mode}' is not one of native, invoke")
        command = role.get("command")
        capture = role.get("capture")
        if mode == "invoke":
            if not isinstance(command, str) or not command.strip():
                res.error("W05", f"{label}: mode 'invoke' requires a non-empty 'command' string (the tool binding)")
            else:
                for ph in PLACEHOLDER_RE.findall(command):
                    if ph not in PLACEHOLDER_VOCAB:
                        res.error("W12", f"{label}: command placeholder '{{{ph}}}' is not in the vocabulary — only {{prompt_file}} and {{run_dir}} are substituted")
            if not isinstance(capture, str) or capture not in CAPTURES:
                res.error("W05", f"{label}: mode 'invoke' requires capture = \"stdout\" or \"files\"")
        elif mode == "native":
            if command is not None:
                res.error("W05", f"{label}: mode 'native' takes no 'command' — the loaded session itself performs the phase")
            if capture is not None:
                res.error("W05", f"{label}: mode 'native' takes no 'capture'")
        ts = role.get("timeout_seconds")
        if ts is not None and (not isinstance(ts, int) or isinstance(ts, bool) or ts < 1):
            res.error("W02", f"{label}: 'timeout_seconds' must be a positive integer")
        rdesc = role.get("description")
        if rdesc is not None and not isinstance(rdesc, str):
            res.error("W02", f"{label}: 'description' must be a string")
        for key in role:
            if key not in ROLE_KNOWN:
                res.warn("W15", f"{label}: unknown key '{key}' — ignored by this engine")
        roles[name] = role
    return roles


def check_artifacts(data: dict, res: Result) -> dict[str, dict]:
    artifacts: dict[str, dict] = {}
    entries = data.get("artifact", [])
    if not isinstance(entries, list):
        res.error("W02", "manifest: [[artifact]] entries must be an array of tables")
        return artifacts
    for idx, art in enumerate(entries):
        label = f"artifact #{idx + 1}"
        if not isinstance(art, dict):
            res.error("W02", f"{label}: must be a table")
            continue
        aid = art.get("id")
        if not isinstance(aid, str) or not WORKFLOW_ID_RE.match(aid):
            res.error("W02", f"{label}: 'id' must be a slug string")
            continue
        label = f"artifact '{aid}'"
        if aid in artifacts:
            res.error("W07", f"duplicate artifact id '{aid}'; rename one")
            continue
        file = art.get("file")
        if not isinstance(file, str) or not file.strip():
            res.error("W02", f"{label}: missing required field 'file' (the filename inside the run directory)")
        elif Path(file).is_absolute() or len(Path(file).parts) != 1 or ".." in Path(file).parts:
            res.error("W04", f"{label}: 'file' {file!r} must be a bare filename — artifacts materialize inside the run directory, never outside it")
        versioned = art.get("versioned")
        if versioned is not None and not isinstance(versioned, bool):
            res.error("W02", f"{label}: 'versioned' must be a boolean (true/false), not {type(versioned).__name__}")
        adesc = art.get("description")
        if adesc is not None and not isinstance(adesc, str):
            res.error("W02", f"{label}: 'description' must be a string")
        for key in art:
            if key not in ARTIFACT_KNOWN:
                res.warn("W15", f"{label}: unknown key '{key}' — ignored by this engine")
        artifacts[aid] = art
    return artifacts


def check_phases(data: dict, roles: dict[str, dict], artifacts: dict[str, dict], res: Result) -> list[dict]:
    phases_raw = data.get("phase", [])
    if not isinstance(phases_raw, list):
        res.error("W02", "manifest: [[phase]] entries must be an array of tables")
        return []
    if not phases_raw:
        res.error("W02", "manifest: at least one [[phase]] is required — a workflow with no phases has nothing to run")
        return []
    phases: list[dict] = []
    seen: set[str] = set()
    for idx, phase in enumerate(phases_raw):
        label = f"phase #{idx + 1}"
        if not isinstance(phase, dict):
            res.error("W02", f"{label}: must be a table")
            continue
        pid = phase.get("id")
        if not isinstance(pid, str) or not WORKFLOW_ID_RE.match(pid):
            res.error("W02", f"{label}: 'id' must be a slug string")
            pid = f"<phase #{idx + 1}>"
        label = f"phase '{pid}'"
        if pid in seen:
            res.error("W07", f"duplicate phase id '{pid}'; rename one")
        seen.add(pid)
        owner = phase.get("owner")
        if not isinstance(owner, str):
            res.error("W02", f"{label}: missing required field 'owner'")
        elif owner not in RESERVED_OWNERS and owner not in roles:
            res.error("W05", f"{label}: owner '{owner}' is not 'human', 'judge', or a declared role ({sorted(roles) or 'none declared'})")
        body = phase.get("body")
        if owner == "judge":
            if body is not None:
                res.error("W06", f"{label}: a judge phase takes no 'body' — the judge is mechanical and follows [judge], not prose")
        else:
            if not isinstance(body, str):
                res.error("W02", f"{label}: missing required field 'body' (the prose the owner follows)")
        for field, required in (("reads", False), ("writes", True)):
            val = phase.get(field)
            if val is None:
                if required:
                    res.error("W02", f"{label}: missing required field 'writes' — artifact presence is the engine's only state, so every phase writes at least one artifact")
                continue
            if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
                res.error("W02", f"{label}: '{field}' must be an array of artifact-id strings")
                continue
            if required and not val:
                res.error("W08", f"{label}: 'writes' must be non-empty — artifact presence is the engine's only state")
            for aid in val:
                if aid not in artifacts:
                    res.error("W08", f"{label}: {field} '{aid}' does not name a declared artifact")
        title = phase.get("title")
        if title is not None and not isinstance(title, str):
            res.error("W02", f"{label}: 'title' must be a string")
        for key in phase:
            if key not in PHASE_KNOWN:
                res.warn("W15", f"{label}: unknown key '{key}' — ignored by this engine")
        phases.append(phase)
    return phases


def check_judge(data: dict, phases: list[dict], artifacts: dict[str, dict], res: Result) -> tuple[int, int] | None:
    """W06 judge coherence. Returns (on_fail_idx, judge_idx) — the inclusive
    loop-reachable range — when a coherent judge exists, else None."""
    judge = data.get("judge")
    judge_idxs = [i for i, p in enumerate(phases) if p.get("owner") == "judge"]
    if judge is None:
        if judge_idxs:
            res.error("W06", f"phase '{phases[judge_idxs[0]].get('id')}' has owner 'judge' but the manifest declares no [judge] table")
        return None
    if not isinstance(judge, dict):
        res.error("W02", "manifest: [judge] must be a table")
        return None
    if not judge_idxs:
        res.error("W06", "[judge] declared but no phase has owner 'judge' — declare exactly one judge phase")
        return None
    if len(judge_idxs) > 1:
        res.error("W06", "more than one phase has owner 'judge' — declare exactly one")
        return None
    judge_idx = judge_idxs[0]

    commands = judge.get("commands")
    if not isinstance(commands, list) or not commands or not all(isinstance(c, str) for c in commands):
        res.error("W02", "[judge]: 'commands' must be a non-empty array of command strings")
    else:
        for c in commands:
            if not c.strip():
                res.error("W14", "[judge]: commands must be non-empty strings")
            elif Path(c.split()[0]).is_absolute():
                res.warn("W14", f"[judge]: command '{c}' uses an absolute path — judge commands resolve against the consuming repo root, so absolute paths break on other machines")

    evidence = judge.get("evidence")
    if not isinstance(evidence, str):
        res.error("W02", "[judge]: missing required field 'evidence' (the artifact id the verdict is written to)")
    elif evidence not in artifacts:
        res.error("W06", f"[judge]: evidence '{evidence}' does not name a declared artifact")
    elif artifacts[evidence].get("versioned") is not True:
        res.error("W06", f"[judge]: evidence artifact '{evidence}' must declare versioned = true — the verdict filenames ({artifacts[evidence].get('file', '?')} → <stem>-<n>.pass/.fail<ext>) are the loop counter")
    judge_phase = phases[judge_idx]
    writes = judge_phase.get("writes")
    if isinstance(evidence, str) and isinstance(writes, list) and evidence not in writes:
        res.error("W06", f"[judge]: the judge phase '{judge_phase.get('id')}' must list the evidence artifact '{evidence}' in its 'writes'")

    mfl = judge.get("max_fix_loops")
    if not isinstance(mfl, int) or isinstance(mfl, bool) or mfl < 1:
        res.error("W02", "[judge]: 'max_fix_loops' must be an integer >= 1")

    on_fail = judge.get("on_fail")
    on_fail_idx = None
    if not isinstance(on_fail, str):
        res.error("W02", "[judge]: missing required field 'on_fail' (the phase re-entered on a failing verdict)")
    else:
        ids = [p.get("id") for p in phases]
        if on_fail not in ids:
            res.error("W06", f"[judge]: on_fail '{on_fail}' does not name a declared phase")
        else:
            on_fail_idx = ids.index(on_fail)
            if on_fail_idx >= judge_idx:
                res.error("W06", f"[judge]: on_fail '{on_fail}' must precede the judge phase — the fix loop runs earlier phases again")
                on_fail_idx = None
    for key in judge:
        if key not in JUDGE_KNOWN:
            res.warn("W15", f"[judge]: unknown key '{key}' — ignored by this engine")
    if on_fail_idx is None:
        return None
    return (on_fail_idx, judge_idx)


def check_dataflow(phases: list[dict], artifacts: dict[str, dict], loop_range: tuple[int, int] | None, res: Result) -> None:
    """W09 read-after-write, W10 single-writer, W13 versioning coherence.
    Loop-reachable = phase index within [on_fail_idx, judge_idx] inclusive."""
    def loop_reachable(i: int) -> bool:
        return loop_range is not None and loop_range[0] <= i <= loop_range[1]

    writers: dict[str, list[int]] = {}
    for i, p in enumerate(phases):
        for aid in p.get("writes") or []:
            if aid in artifacts:
                writers.setdefault(aid, []).append(i)

    for i, p in enumerate(phases):
        for aid in p.get("reads") or []:
            if aid not in artifacts:
                continue  # already W08
            ws = writers.get(aid, [])
            ok = any(w < i for w in ws) or (loop_reachable(i) and any(loop_reachable(w) for w in ws))
            if not ok:
                res.error("W09", f"phase '{p.get('id')}' reads '{aid}' but no earlier phase writes it (loop re-entry counted) — a run could never satisfy this phase's inputs")

    for aid, ws in writers.items():
        if len(ws) > 1:
            versioned = artifacts[aid].get("versioned") is True
            all_loop = all(loop_reachable(w) for w in ws)
            if not (versioned and all_loop):
                names = [phases[w].get("id") for w in ws]
                res.error("W10", f"artifact '{aid}' is written by multiple phases ({names}) — allowed only when the artifact is versioned and every writer is loop-reachable")

    for aid, art in artifacts.items():
        ws = writers.get(aid, [])
        loop_written = any(loop_reachable(w) for w in ws)
        versioned = art.get("versioned") is True
        if loop_written and not versioned:
            res.error("W13", f"artifact '{aid}' is written by a loop-reachable phase but is not versioned — loop iterations would overwrite each other and the loop count would be unrecoverable")
        if versioned and ws and not loop_written:
            res.warn("W13", f"artifact '{aid}' is versioned but not written by any loop-reachable phase — versioning it adds ordinal suffixes for no benefit")


def resolve_files(data: dict, phases: list[dict], artifacts: dict[str, dict], root: Path, res: Result) -> list[Path]:
    declared: list[Path] = []
    body = data.get("body")
    if isinstance(body, str):
        r = resolve_declared(body, root, "manifest 'body'", res)
        if r is not None:
            declared.append(r)
    for p in phases:
        b = p.get("body")
        if isinstance(b, str) and p.get("owner") != "judge":
            r = resolve_declared(b, root, f"phase '{p.get('id')}'", res)
            if r is not None:
                declared.append(r)
    for aid, art in artifacts.items():
        t = art.get("template")
        if t is not None:
            if not isinstance(t, str):
                res.error("W02", f"artifact '{aid}': 'template' must be a path string")
                continue
            r = resolve_declared(t, root, f"artifact '{aid}' template", res)
            if r is not None:
                declared.append(r)
    return declared


def lint_text(text: str, label: str, res: Result) -> None:
    low = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in low:
            res.warn("W11", f"{label}: contains an instruction-override pattern ('{pattern}'); review before trusting")


def lint_tree_prose(data: dict, phases: list[dict], root: Path, origin: str, res: Result) -> None:
    """W11-lint the union of (a) every declared prose file (manifest body,
    phase bodies, artifact templates — regardless of extension) and (b) every
    markdown/text file under a non-builtin workflow folder, deduped. The trust
    hash covers the whole folder, so the injection lint spans the same set.
    Builtins are repo-trusted, so this is skipped."""
    if origin == "builtin":
        return
    root_r = root.resolve()
    targets: dict[Path, str] = {}

    def add(decl, label: str) -> None:
        if not isinstance(decl, str):
            return
        p = (root_r / decl).resolve()
        if p.is_relative_to(root_r) and p.is_file() and not p.is_symlink():
            targets.setdefault(p, label)

    add(data.get("body"), "manifest 'body'")
    for p in phases:
        add(p.get("body"), f"phase '{p.get('id', '?')}' body")
    for art in data.get("artifact") or []:
        if isinstance(art, dict):
            add(art.get("template"), f"artifact '{art.get('id', '?')}' template")
    for f in root_r.rglob("*"):
        if (f.is_file() and not f.is_symlink()
                and f.suffix.lower() in (".md", ".markdown", ".txt")):
            targets.setdefault(f.resolve(), f"file '{f.relative_to(root_r).as_posix()}'")
    for p, label in targets.items():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            res.error("W04", f"{label}: prose file '{p.name}' is unreadable — fix its permissions")
            continue
        lint_text(text, label, res)


def lint_manifest_strings(data: dict, origin: str, res: Result) -> None:
    """W11-lint the free-text manifest fields the engine displays (workflow,
    role, phase-title, and artifact descriptions). Builtins are repo-trusted."""
    if origin == "builtin":
        return
    if isinstance(data.get("description"), str):
        lint_text(data["description"], "manifest 'description'", res)
    roles = data.get("roles")
    if isinstance(roles, dict):
        for name, role in roles.items():
            if isinstance(role, dict) and isinstance(role.get("description"), str):
                lint_text(role["description"], f"role '{name}' description", res)
    for p in data.get("phase") or []:
        if isinstance(p, dict) and isinstance(p.get("title"), str):
            lint_text(p["title"], f"phase '{p.get('id', '?')}' title", res)
    for a in data.get("artifact") or []:
        if isinstance(a, dict) and isinstance(a.get("description"), str):
            lint_text(a["description"], f"artifact '{a.get('id', '?')}' description", res)


def compute_hash(root: Path) -> str:
    """sha256 over **every file in the workflow folder**, each framed by its
    root-relative POSIX path and byte length, ordered by path. Whole-folder
    coverage (not just declared files) keeps undeclared-but-behavior-bearing
    files out of the mutable-after-approval channel; framing commits file
    boundaries so a cross-file byte move changes the digest. Symlinks and
    `.git/` are skipped defensively — validation already rejects both (W04)
    and --hash refuses to hash an invalid workflow."""
    root_r = root.resolve()
    entries: list[tuple[str, Path]] = []
    for f in root_r.rglob("*"):
        if f.is_symlink() or not f.is_file():
            continue
        rel = f.relative_to(root_r)
        if ".git" in rel.parts:
            continue
        entries.append((rel.as_posix(), f))
    h = hashlib.sha256()
    for key, fr in sorted(entries):
        data = fr.read_bytes()
        h.update(f"{key}\0{len(data)}\0".encode("utf-8"))
        h.update(data)
    return h.hexdigest()


def validate(root: Path, origin: str, builtin_root: Path) -> Result:
    res = Result()
    # `origin` is a trust CLAIM, not a fact. `builtin` grants install trust, so
    # a builtin must actually LIVE in the installed builtin root; otherwise a
    # lockfile could mark a workspace folder `builtin` and skip scrutiny.
    if origin == "builtin":
        if not root.resolve().is_relative_to(builtin_root.resolve()):
            res.error("W04", f"origin 'builtin' claimed for '{root}', which is not inside the installed builtin root '{builtin_root}' — builtins load only from the install, never a workspace path")
            return res
    check_tree_confinement(root, res)
    if res.errors:  # a symlink or `.git/` under the root is fail-closed
        return res
    data = load_manifest(root, res)
    if data is None:
        return res
    check_top_level(data, res)
    roles = check_roles(data, res)
    artifacts = check_artifacts(data, res)
    phases = check_phases(data, roles, artifacts, res)
    loop_range = check_judge(data, phases, artifacts, res)
    check_dataflow(phases, artifacts, loop_range, res)
    resolve_files(data, phases, artifacts, root, res)
    lint_tree_prose(data, phases, root, origin, res)
    lint_manifest_strings(data, origin, res)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workflow_dir", type=Path)
    ap.add_argument("--origin", choices=("builtin", "local"), default="local")
    ap.add_argument("--builtin-root", type=Path, default=None)
    ap.add_argument("--hash", action="store_true")
    args = ap.parse_args()

    root = args.workflow_dir
    builtin_root = args.builtin_root or default_builtin_root()

    res = validate(root, args.origin, builtin_root)

    if args.hash:
        if res.errors:
            for e in res.errors:
                print(e, file=sys.stderr)
            print("invalid: refusing to hash an invalid workflow (fail-closed)", file=sys.stderr)
            return 1
        print(compute_hash(root))
        return 0

    for w in res.warnings:
        print(w)
    if res.errors:
        for e in res.errors:
            print(e)
        print(f"invalid: {root} — {len(res.errors)} error(s), {len(res.warnings)} warning(s)")
        return 1
    print(f"ok: {root} — contract {CONTRACT_SUPPORTED[-1]}, {len(res.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail-closed: a validator crash is never a pass
        print(f"invalid: validator error (fail-closed): {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

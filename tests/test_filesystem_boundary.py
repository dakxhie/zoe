"""Phase B1 trust-boundary tests for Zoe filesystem tools.

Label: unit / fixture (temporary directories only; no network, no model).
Secret-shaped strings are assembled at runtime and are not real credentials.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

import tools.fs_policy as fs_policy
from tools.filesystem import FilesystemError, find_file, list_files, read_file, search_text

MARKER = "OUTSIDE_MARKER_" + "7f3c9a"


@pytest.fixture()
def layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """repo/ (workspace), repo_sibling/ (prefix sibling) and outside/ with a marker."""
    repo = tmp_path / "repo"
    sibling = tmp_path / "repo_sibling"
    outside = tmp_path / "outside"
    for d in (repo, sibling, outside):
        d.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("def main():\n    return 'inside'\n", encoding="utf-8")
    (repo / "README.md").write_text("# Demo\nhello workspace\n", encoding="utf-8")
    (sibling / "dummy.txt").write_text(f"sibling {MARKER}\n", encoding="utf-8")
    (outside / "marker.txt").write_text(f"secret {MARKER}\n", encoding="utf-8")
    monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, str(repo))
    fs_policy.clear_workspace_cache()
    yield {"repo": repo, "sibling": sibling, "outside": outside, "tmp": tmp_path}
    fs_policy.clear_workspace_cache()


@pytest.fixture()
def open_spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every os.open path so tests can prove outside files are never opened."""
    opened: list[str] = []
    real_open = os.open

    def spy(path, flags, *args, **kwargs):  # type: ignore[no-untyped-def]
        opened.append(os.path.realpath(path))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", spy)
    return opened


def _error_type(func, *args) -> str:  # type: ignore[no-untyped-def]
    with pytest.raises(FilesystemError) as info:
        func(*args)
    return info.value.error_type


# --- WORKSPACE_ROOT -------------------------------------------------------------


def test_workspace_root_is_canonical(layout: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    link = layout["tmp"] / "repo_link"
    link.symlink_to(layout["repo"], target_is_directory=True)
    monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, str(link))
    fs_policy.clear_workspace_cache()
    ws = fs_policy.get_workspace_root()
    assert ws.root == Path(os.path.realpath(layout["repo"]))
    assert ws.source == "env"


@pytest.mark.parametrize("value", ["relative/dir", "/definitely/not/here", "/"])
def test_workspace_root_rejects_bad_values(layout: dict[str, Path], monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, value)
    fs_policy.clear_workspace_cache()
    assert _error_type(fs_policy.get_workspace_root) == "workspace_misconfigured"
    assert _error_type(list_files, ".") == "workspace_misconfigured"


def test_workspace_root_rejects_file(layout: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, str(layout["repo"] / "README.md"))
    fs_policy.clear_workspace_cache()
    assert _error_type(fs_policy.get_workspace_root) == "workspace_misconfigured"


def test_workspace_root_rejects_home_and_its_parents(layout: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    home = layout["tmp"] / "home" / "user"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    for value in (home, home.parent):
        monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, str(value))
        fs_policy.clear_workspace_cache()
        assert _error_type(fs_policy.get_workspace_root) == "workspace_misconfigured"


def test_relative_paths_ignore_process_cwd(layout: dict[str, Path], monkeypatch: pytest.MonkeyPatch, open_spy: list[str]) -> None:
    monkeypatch.chdir(layout["outside"])
    assert _error_type(read_file, "marker.txt") == "not_found"
    assert "inside" in read_file("src/app.py")
    assert not any(str(layout["outside"]) in p for p in open_spy)


@pytest.mark.parametrize("path", ["~/notes.txt", "~", "$HOME/x", "${HOME}/x", "%USERPROFILE%/x", "a\x00b"])
def test_no_tilde_env_or_control_expansion(layout: dict[str, Path], path: str) -> None:
    assert _error_type(read_file, path) == "invalid_path"


# --- Containment ----------------------------------------------------------------


def test_within_is_component_based() -> None:
    root = Path("/workspace/zoe/repo")
    assert fs_policy._within(root, root)
    assert fs_policy._within(root / "a" / "b.txt", root)
    assert not fs_policy._within(Path("/workspace/zoe/repo_sibling/file.txt"), root)
    assert not fs_policy._within(Path("/workspace/zoe"), root)


@pytest.mark.parametrize(
    "rel",
    [
        "../outside/marker.txt",
        "src/../../outside/marker.txt",
        "src/a/../../../outside/marker.txt",
        "..\\outside\\marker.txt",
        "src\\..\\..\\outside/marker.txt",
        "../repo_sibling/dummy.txt",
        "../outside/does_not_exist.txt",
    ],
)
def test_traversal_rejected(layout: dict[str, Path], open_spy: list[str], rel: str) -> None:
    assert _error_type(read_file, rel) == "path_outside_workspace"
    assert not any(str(layout["outside"]) in p or str(layout["sibling"]) in p for p in open_spy)


def test_absolute_outside_and_sibling_prefix_rejected(layout: dict[str, Path]) -> None:
    assert _error_type(read_file, str(layout["outside"] / "marker.txt")) == "path_outside_workspace"
    assert _error_type(read_file, str(layout["sibling"] / "dummy.txt")) == "path_outside_workspace"
    assert _error_type(list_files, str(layout["sibling"])) == "path_outside_workspace"


def test_absolute_inside_allowed(layout: dict[str, Path]) -> None:
    assert "inside" in read_file(str(layout["repo"] / "src" / "app.py"))


def test_nonexistent_inside_and_root_and_kinds(layout: dict[str, Path]) -> None:
    assert _error_type(read_file, "src/missing.py") == "not_found"
    assert "README.md" in list_files(".")
    assert _error_type(read_file, ".") == "not_a_file"
    assert _error_type(list_files, "README.md") == "not_a_directory"
    assert "src/app.py" in list_files("src")


# --- Symlinks -------------------------------------------------------------------


@pytest.fixture()
def links(layout: dict[str, Path]) -> dict[str, Path]:
    repo = layout["repo"]
    (repo / "escape.txt").symlink_to(layout["outside"] / "marker.txt")
    (repo / "sib").symlink_to(layout["sibling"], target_is_directory=True)
    (repo / "alias.py").symlink_to(repo / "src" / "app.py")
    (repo / "srclink").symlink_to(repo / "src", target_is_directory=True)
    (repo / "src" / "deep_escape").symlink_to(layout["outside"], target_is_directory=True)
    return layout


def test_symlink_to_outside_file_rejected(links: dict[str, Path], open_spy: list[str]) -> None:
    assert _error_type(read_file, "escape.txt") == "symlink_escape"
    assert not any(str(links["outside"]) in p for p in open_spy)


def test_symlink_to_sibling_directory_rejected(links: dict[str, Path], open_spy: list[str]) -> None:
    assert _error_type(read_file, "sib/dummy.txt") == "symlink_escape"
    assert _error_type(list_files, "sib") == "symlink_escape"
    assert not any(str(links["sibling"]) in p for p in open_spy)


def test_symlink_to_inside_file_allowed(links: dict[str, Path]) -> None:
    assert "inside" in read_file("alias.py")


def test_symlinked_directory_not_followed_by_walks(links: dict[str, Path]) -> None:
    listing = list_files(".")
    assert "src/app.py" in listing
    assert "srclink/" not in listing
    assert "unsafe symlink" in listing
    # explicit access through an in-workspace directory link still resolves inside
    assert "inside" in read_file("srclink/app.py")


def test_recursive_search_through_malicious_symlink(links: dict[str, Path], open_spy: list[str]) -> None:
    result = search_text(MARKER)
    assert result.startswith("(no matches found")
    assert not any(str(links["outside"]) in p or str(links["sibling"]) in p for p in open_spy)


def test_recursive_listing_through_malicious_symlink(links: dict[str, Path], open_spy: list[str]) -> None:
    listing = list_files(".")
    found = find_file("marker")
    assert "escape.txt" not in listing
    assert "dummy.txt" not in listing and "marker.txt" not in listing
    assert found.startswith("(no files found")
    assert not any(str(links["outside"]) in p for p in open_spy)


def test_direct_read_of_malicious_symlink_never_reads_marker(links: dict[str, Path], open_spy: list[str]) -> None:
    for path in ("escape.txt", "src/deep_escape/marker.txt", "sib/dummy.txt"):
        with pytest.raises(FilesystemError) as info:
            read_file(path)
        assert MARKER not in str(info.value)
    assert not any(str(links["outside"]) in p or str(links["sibling"]) in p for p in open_spy)


def test_symlink_alias_to_sensitive_file_denied(layout: dict[str, Path]) -> None:
    repo = layout["repo"]
    (repo / ".env").write_text("API_KEY=" + "abcd" * 6 + "\n", encoding="utf-8")
    (repo / "notes.txt").symlink_to(repo / ".env")
    assert _error_type(read_file, "notes.txt") == "sensitive_path"
    assert "notes.txt" not in list_files(".")


# --- Hidden files ----------------------------------------------------------------


def test_hidden_policy(layout: dict[str, Path]) -> None:
    repo = layout["repo"]
    (repo / ".gitignore").write_text("build/\nHIDDEN_TOKEN_X\n", encoding="utf-8")
    (repo / ".editorconfig").write_text("root = true\n", encoding="utf-8")
    for d in (".git", ".venv", ".idea", ".cache", ".ssh", ".github"):
        (repo / d).mkdir()
        (repo / d / "inner.txt").write_text("HIDDEN_TOKEN_X\n", encoding="utf-8")
    for name in (".env", ".env.local", ".npmrc", ".netrc"):
        (repo / name).write_text("HIDDEN_TOKEN_X\n", encoding="utf-8")

    assert "build/" in read_file(".gitignore")
    assert "root = true" in read_file(".editorconfig")
    assert "HIDDEN_TOKEN_X" in read_file(".github/inner.txt")
    for name in (".env", ".env.local", ".npmrc", ".netrc", ".ssh/inner.txt"):
        assert _error_type(read_file, name) == "sensitive_path"
    assert _error_type(read_file, ".git/inner.txt") == "skipped_path"

    listing = list_files(".")
    assert ".gitignore" not in listing and ".github" not in listing and ".venv" not in listing
    assert search_text("HIDDEN_TOKEN_X").startswith("(no matches found")
    assert find_file("inner").startswith("(no files found")


# --- Sensitive files -------------------------------------------------------------

SENSITIVE = [
    ".env", ".env.production", "prod.env", ".envrc",
    "key.pem", "server.key", "cert.p12", "cert.pfx", "store.jks", "release.keystore", "putty.ppk",
    "id_rsa", "id_rsa.pub", "id_dsa", "id_ecdsa", "id_ed25519", "backup.gpg", "sig.asc", "secring.gpg",
    ".ssh/config", ".aws/credentials", ".azure/config", ".gcloud/creds", ".kube/config",
    ".docker/config.json", ".netrc", "_netrc", ".npmrc", ".pypirc", ".git-credentials", ".gitconfig",
    "credentials", "credentials.json", "credentials.yml", "service-account-prod.json", "deploy-sa.json",
    "client_secret_123.json", "token.json", "api.token", "my_token_list.txt", "secrets.yaml", "secret.txt",
    "db.secret", ".htpasswd", "auth.json", "keychain.db", "vault.kdbx",
    "app/keystore.properties", "app/signing.properties", "app/google-services.json",
    "ios/GoogleService-Info.plist",
]


@pytest.mark.parametrize("rel", SENSITIVE)
def test_sensitive_files_denied_and_unindexed(layout: dict[str, Path], rel: str) -> None:
    path = layout["repo"] / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("SENSITIVE_TOKEN_Q\n", encoding="utf-8")
    assert _error_type(read_file, rel) == "sensitive_path"
    assert rel not in list_files(".")
    assert search_text("SENSITIVE_TOKEN_Q").startswith("(no matches found")


def test_sensitive_denial_precedes_existence(layout: dict[str, Path]) -> None:
    assert _error_type(read_file, ".env") == "sensitive_path"
    assert _error_type(read_file, "nested/id_rsa") == "sensitive_path"


def test_env_template_placeholder_only(layout: dict[str, Path]) -> None:
    repo = layout["repo"]
    (repo / ".env.example").write_text("API_KEY=\nPORT=3000\nSECRET_KEY=changeme\n", encoding="utf-8")
    assert "PORT=3000" in read_file(".env.example")
    (repo / ".env.sample").write_text("API_KEY=" + "Zx9" * 8 + "\n", encoding="utf-8")
    assert _error_type(read_file, ".env.sample") == "sensitive_content"


def test_ordinary_names_not_overblocked(layout: dict[str, Path]) -> None:
    repo = layout["repo"]
    for name in ("tokenizer.py", "secret_scan.py", "keys.md", "environment.py", "credential_docs.md"):
        (repo / name).write_text("ok\n", encoding="utf-8")
        assert read_file(name) == "ok"


# --- Zoe internal state ----------------------------------------------------------


def test_internal_state_denied_when_workspace_is_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install = tmp_path / "zoe"
    files = [
        "data/history/s1.json", "data/telemetry/t.jsonl", "storage/chroma/c.txt",
        "training/data/held_out_eval/eval.jsonl", "training/adapters/run1/adapter_config.json",
        "models/w.safetensors", "other/chroma/x.txt",
    ]
    for rel in files:
        p = install / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("INTERNAL_TOKEN_Z\n", encoding="utf-8")
    (install / "README.md").write_text("INTERNAL_TOKEN_Z public\n", encoding="utf-8")
    monkeypatch.setattr(fs_policy, "ROOT", install)
    monkeypatch.delenv(fs_policy.WORKSPACE_ROOT_ENV, raising=False)
    monkeypatch.setattr(fs_policy, "_configured_value", lambda: (None, "install_root_fallback"))
    fs_policy.clear_workspace_cache()
    try:
        ws = fs_policy.get_workspace_root()
        assert ws.overlaps_install and ws.source == "install_root_fallback"
        for rel in files:
            err = _error_type(read_file, rel)
            assert err in {"internal_state", "skipped_path"}, (rel, err)
        listing = list_files(".")
        assert listing.splitlines()[0] == "README.md"
        assert not any(rel in listing for rel in files)
        hits = search_text("INTERNAL_TOKEN_Z")
        assert hits.splitlines()[0].startswith("README.md:1:")
        assert not any(rel in hits for rel in files)
    finally:
        fs_policy.clear_workspace_cache()


# --- Content secret scanning -------------------------------------------------------


def _secret_lines() -> dict[str, str]:
    return {
        "aws": "aws_id = " + "AKIA" + "ABCDEFGHIJKLMNOP",
        "github": "gh = " + "ghp_" + "a1B2" * 9,
        "slack": "slack = " + "xoxb-" + "1234567890-abcdefghij",
        "google": "maps = " + "AIza" + "Sy" + "A" * 33,
        "jwt": "auth = " + "eyJhbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcDEF123456ghi",
        "password": "password=" + "hunter2hunter2",
        "api_key": "api_key = '" + "Q7" * 10 + "'",
        "bearer": "Authorization: Bearer " + "x9" * 15,
    }


def test_content_secrets_redacted_with_count(layout: dict[str, Path], caplog: pytest.LogCaptureFixture) -> None:
    secrets = _secret_lines()
    benign = [
        "token = tokenizer(text)",
        "password: str",
        "api_key = os.environ['API_KEY']",
        "max_new_tokens=256",
        "print('hello')",
    ]
    (layout["repo"] / "config.py").write_text("\n".join(list(secrets.values()) + benign) + "\n", encoding="utf-8")
    caplog.set_level(logging.DEBUG)
    content = read_file("config.py")
    for value in secrets.values():
        assert value.split()[-1].strip("'") not in content
    for line in benign:
        assert line in content
    assert f"[redacted {len(secrets)} line(s) containing possible secrets]" in content
    for value in secrets.values():
        assert value.split()[-1].strip("'") not in caplog.text


def test_search_redacts_matching_secret_lines(layout: dict[str, Path]) -> None:
    value = "AKIA" + "ZYXWVUTSRQPONMLK"
    (layout["repo"] / "deploy.sh").write_text(f"export AWS_ID={value}  # NEEDLE_N\necho NEEDLE_N\n", encoding="utf-8")
    result = search_text("NEEDLE_N")
    assert value not in result
    assert "deploy.sh:2: echo NEEDLE_N" in result
    assert "[redacted 1 matching line(s) containing possible secrets]" in result


def test_private_key_blocks_whole_file(layout: dict[str, Path]) -> None:
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    (layout["repo"] / "notes.txt").write_text(f"NEEDLE_P\n{header}\nMIIabc\n-----END RSA PRIVATE KEY-----\n", encoding="utf-8")
    with pytest.raises(FilesystemError) as info:
        read_file("notes.txt")
    assert info.value.error_type == "sensitive_content"
    assert "MIIabc" not in str(info.value)
    result = search_text("NEEDLE_P")
    assert "notes.txt" not in result.splitlines()[0]
    assert "[skipped 1 file(s) containing private keys]" in result


# --- Limits ----------------------------------------------------------------------


def test_filesystem_limits(layout: dict[str, Path]) -> None:
    repo = layout["repo"]
    (repo / "big.txt").write_bytes(b"a" * (2 * 1024 * 1024 + 1))
    assert _error_type(read_file, "big.txt") == "file_too_large"
    (repo / "blob.dat").write_bytes(b"\x00\x01\x02")
    assert _error_type(read_file, "blob.dat") == "binary_file"
    (repo / "long.txt").write_text("\n".join(f"line {i}" for i in range(1000)), encoding="utf-8")
    assert "truncated to first 400 lines" in read_file("long.txt", max_lines=5000)
    many = repo / "many"
    many.mkdir()
    for i in range(250):
        (many / f"f{i:03}.txt").write_text("LIMIT_NEEDLE\n", encoding="utf-8")
    listing = list_files("many")
    assert "truncated to first 200 entries" in listing
    assert len([l for l in listing.splitlines() if l.startswith("many/")]) == 200
    hits = search_text("LIMIT_NEEDLE", "many")
    assert len([l for l in hits.splitlines() if l.startswith("many/")]) == 50
    assert "truncated to first 50 entries" in hits


# --- Spec §8 fixture (exact layout from the B1 brief) ------------------------------


@pytest.fixture()
def spec_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    base = tmp_path / "zoe-audit"
    ws = base / "workspace"
    (ws / "sub").mkdir(parents=True)
    (base / "outside").mkdir()
    (base / "repo_sibling").mkdir()
    (ws / "safe.txt").write_text("safe content\n", encoding="utf-8")
    (ws / "sub" / "nested.txt").write_text("nested content\n", encoding="utf-8")
    (base / "outside" / "marker.txt").write_text(f"outside {MARKER}\n", encoding="utf-8")
    (base / "repo_sibling" / "marker.txt").write_text(f"sibling {MARKER}\n", encoding="utf-8")
    (ws / "link-outside.txt").symlink_to(base / "outside" / "marker.txt")
    (ws / "link-sibling.txt").symlink_to(Path("..") / "repo_sibling" / "marker.txt")
    (ws / "link-safe.txt").symlink_to(Path("safe.txt"))
    (ws / "dirlink").symlink_to(base / "outside", target_is_directory=True)
    monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, str(ws))
    fs_policy.clear_workspace_cache()
    yield {"base": base, "ws": ws}
    fs_policy.clear_workspace_cache()


def test_spec_fixture_inside_paths_work(spec_fixture: dict[str, Path]) -> None:
    assert read_file("safe.txt") == "safe content"
    assert read_file("sub/nested.txt") == "nested content"
    assert read_file("link-safe.txt") == "safe content"


@pytest.mark.parametrize("rel", ["../outside.txt", "../../outside.txt", "sub/../../outside.txt"])
def test_spec_fixture_parent_escapes(spec_fixture: dict[str, Path], rel: str) -> None:
    assert _error_type(read_file, rel) == "path_outside_workspace"


def test_spec_fixture_symlinks(spec_fixture: dict[str, Path], open_spy: list[str]) -> None:
    base = spec_fixture["base"]
    assert _error_type(read_file, "link-outside.txt") == "symlink_escape"
    assert _error_type(read_file, "link-sibling.txt") == "symlink_escape"
    assert _error_type(read_file, "dirlink/marker.txt") == "symlink_escape"
    assert _error_type(list_files, "dirlink") == "symlink_escape"
    assert search_text(MARKER).startswith("(no matches found")
    listing = list_files(".")
    found = find_file("marker")
    for output in (listing, found):
        assert str(base) not in output
        assert "outside" not in output and "repo_sibling" not in output
    assert listing.splitlines()[:4] == ["link-safe.txt", "safe.txt", "sub/nested.txt", "[skipped: 3 unsafe symlink]"]
    assert found.startswith("(no files found")
    assert not any(str(base / "outside") in p or str(base / "repo_sibling") in p for p in open_spy)


# --- Resolver modes and input validation --------------------------------------------


def test_resolver_modes_and_empty(spec_fixture: dict[str, Path]) -> None:
    ws = spec_fixture["ws"]
    resolved = fs_policy.resolve_in_workspace("sub/nested.txt", fs_policy.AccessMode.READ)
    assert resolved.relative.as_posix() == "sub/nested.txt"
    assert fs_policy.resolve_in_workspace(".", fs_policy.AccessMode.LIST).canonical == Path(os.path.realpath(ws))
    assert fs_policy.resolve_in_workspace(str(ws), fs_policy.AccessMode.LIST).relative.as_posix() == "."
    with pytest.raises(FilesystemError) as info:
        fs_policy.resolve_in_workspace("sub", fs_policy.AccessMode.READ)
    assert info.value.error_type == "not_a_file"
    with pytest.raises(FilesystemError) as info:
        fs_policy.resolve_in_workspace("safe.txt", fs_policy.AccessMode.LIST)
    assert info.value.error_type == "not_a_directory"
    for bad in ("", "   "):
        assert _error_type(read_file, bad) == "invalid_path"
        assert _error_type(list_files, bad) == "invalid_path"
    with pytest.raises(FilesystemError) as info:
        fs_policy.resolve_in_workspace(None)  # type: ignore[arg-type]
    assert info.value.error_type == "invalid_path"


# --- Code index loader (recursive indexing honours the same policy) -----------------


def test_code_loader_skips_hidden_sensitive_and_escaping_files(layout: dict[str, Path]) -> None:
    from codebase.loader import load_code

    repo = layout["repo"]
    (repo / ".github").mkdir()
    (repo / ".github" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    (repo / "credentials.json").write_text('{"a": 1}\n', encoding="utf-8")
    (repo / "app").mkdir()
    (repo / "app" / "google-services.json").write_text('{"b": 2}\n', encoding="utf-8")
    (repo / "outside_link.py").symlink_to(layout["outside"] / "marker.txt")
    (repo / ".env.example").write_text("API_KEY=\nPORT=3000\n", encoding="utf-8")
    (repo / "key_notes.md").write_text("-----BEGIN " + "PRIVATE KEY-----\nabc\n", encoding="utf-8")
    secret = "ghp_" + "Zz09" * 9
    (repo / "cfg.py").write_text(f"GH = '{secret}'\nDEBUG = True\n", encoding="utf-8")

    docs = {d["path"]: d for d in load_code(repo)}
    assert "src/app.py" in docs and "README.md" in docs
    assert ".env.example" in docs
    for skipped in (".github/ci.yml", "credentials.json", "app/google-services.json", "outside_link.py", "key_notes.md"):
        assert skipped not in docs
    assert secret not in docs["cfg.py"]["content"]
    assert "DEBUG = True" in docs["cfg.py"]["content"]
    assert all(MARKER not in d["content"] for d in docs.values())

from pathlib import Path

import pytest

from virtuoso_bridge import env as env_mod


def _write_env(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_explicit_env_has_highest_priority(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    explicit = tmp_path / "custom.env"

    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)
    env_mod.set_runtime_env_file(None)

    _write_env(home / ".virtuoso-bridge" / ".env", "VB_REMOTE_HOST=user-host\n")
    _write_env(cwd / ".env", "VB_REMOTE_HOST=cwd-host\n")
    _write_env(explicit, "VB_REMOTE_HOST=explicit-host\n")

    loaded = env_mod.load_vb_env(explicit)

    assert loaded == explicit.resolve()
    assert env_mod.resolve_env_path(explicit) == explicit.resolve()


def test_cwd_env_beats_user_env(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"

    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)
    env_mod.set_runtime_env_file(None)

    _write_env(home / ".virtuoso-bridge" / ".env", "VB_REMOTE_HOST=user-host\n")
    _write_env(cwd / ".env", "VB_REMOTE_HOST=cwd-host\n")

    assert env_mod.resolve_env_path() == (cwd / ".env").resolve()


def test_user_env_is_fallback(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"

    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)
    env_mod.set_runtime_env_file(None)

    _write_env(home / ".virtuoso-bridge" / ".env", "VB_REMOTE_HOST=user-host\n")

    assert env_mod.resolve_env_path() == (home / ".virtuoso-bridge" / ".env").resolve()


def test_runtime_env_file_beats_cwd_and_user(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    runtime = tmp_path / "runtime.env"

    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)

    _write_env(home / ".virtuoso-bridge" / ".env", "VB_REMOTE_HOST=user-host\n")
    _write_env(cwd / ".env", "VB_REMOTE_HOST=cwd-host\n")
    _write_env(runtime, "VB_REMOTE_HOST=runtime-host\n")

    env_mod.set_runtime_env_file(runtime)
    try:
        assert env_mod.resolve_env_path() == runtime.resolve()
    finally:
        env_mod.set_runtime_env_file(None)


def test_missing_explicit_env_raises(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    env_mod.set_runtime_env_file(None)

    with pytest.raises(FileNotFoundError):
        env_mod.resolve_env_path(tmp_path / "missing.env")

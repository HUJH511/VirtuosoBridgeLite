from pathlib import Path

from virtuoso_bridge import cli
from virtuoso_bridge import env as env_mod


def test_cli_init_creates_user_env(monkeypatch, tmp_path, capsys):
    env_path = tmp_path / ".virtuoso-bridge" / ".env"
    monkeypatch.setattr(cli, "default_user_env_path", lambda: env_path)
    monkeypatch.setattr(cli, "_generate_env_template", lambda: "VB_REMOTE_HOST=test-host\n")

    rc = cli.cli_init()

    assert rc == 0
    assert env_path.read_text(encoding="utf-8") == "VB_REMOTE_HOST=test-host\n"
    assert f".env created at {env_path}" in capsys.readouterr().out


def test_main_sets_runtime_env_file_for_start(monkeypatch, tmp_path):
    explicit = tmp_path / "config.env"
    explicit.write_text("VB_REMOTE_HOST=test-host\n", encoding="utf-8")

    observed: dict[str, Path | None] = {}

    def fake_start() -> int:
        observed["env"] = env_mod.get_runtime_env_file()
        return 0

    monkeypatch.setattr(cli, "cli_start", fake_start)
    env_mod.set_runtime_env_file(None)
    try:
        rc = cli.main(["start", "--env", str(explicit)])
    finally:
        env_mod.set_runtime_env_file(None)

    assert rc == 0
    assert observed["env"] == explicit.resolve()


def test_main_sets_runtime_env_file_for_sim_jobs(monkeypatch, tmp_path):
    explicit = tmp_path / "config.env"
    explicit.write_text("VB_REMOTE_HOST=test-host\n", encoding="utf-8")

    observed: dict[str, Path | None] = {}

    def fake_sim_jobs() -> int:
        observed["env"] = env_mod.get_runtime_env_file()
        return 0

    monkeypatch.setattr(cli, "cli_sim_jobs", fake_sim_jobs)
    env_mod.set_runtime_env_file(None)
    try:
        rc = cli.main(["sim-jobs", "--env", str(explicit)])
    finally:
        env_mod.set_runtime_env_file(None)

    assert rc == 0
    assert observed["env"] == explicit.resolve()

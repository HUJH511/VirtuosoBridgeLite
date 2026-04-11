from virtuoso_bridge import env as env_mod
from virtuoso_bridge.transport import ssh as ssh_mod


def test_windows_no_window_kwargs_default_is_detached(monkeypatch):
    class FakeStartupInfo:
        def __init__(self):
            self.dwFlags = 0
            self.wShowWindow = 1

    monkeypatch.setattr(ssh_mod.os, "name", "nt", raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "STARTUPINFO", FakeStartupInfo, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "STARTF_USESHOWWINDOW", 0x00000001, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "DETACHED_PROCESS", 0x00000008, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200, raising=False)

    kwargs = ssh_mod._windows_no_window_kwargs()

    assert kwargs["close_fds"] is True
    assert kwargs["creationflags"] & ssh_mod.subprocess.CREATE_NO_WINDOW
    assert kwargs["creationflags"] & ssh_mod.subprocess.DETACHED_PROCESS
    assert not (kwargs["creationflags"] & ssh_mod.subprocess.CREATE_NEW_PROCESS_GROUP)
    assert kwargs["startupinfo"].dwFlags & ssh_mod.subprocess.STARTF_USESHOWWINDOW
    assert kwargs["startupinfo"].wShowWindow == 0


def test_windows_no_window_kwargs_can_request_new_process_group(monkeypatch):
    class FakeStartupInfo:
        def __init__(self):
            self.dwFlags = 0
            self.wShowWindow = 1

    monkeypatch.setattr(ssh_mod.os, "name", "nt", raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "STARTUPINFO", FakeStartupInfo, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "STARTF_USESHOWWINDOW", 0x00000001, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "DETACHED_PROCESS", 0x00000008, raising=False)
    monkeypatch.setattr(ssh_mod.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200, raising=False)

    kwargs = ssh_mod._windows_no_window_kwargs(new_process_group=True)

    assert kwargs["creationflags"] & ssh_mod.subprocess.CREATE_NEW_PROCESS_GROUP


def test_windows_disables_persistent_shell(monkeypatch):
    monkeypatch.setattr(ssh_mod.os, "name", "nt", raising=False)

    runner = ssh_mod.SSHRunner(host="example.com", user="tester", persistent_shell=True)

    assert runner.persistent_shell_enabled is False


def test_env_overrides_ssh_scp_and_tar(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("VB_SSH_CMD", r"C:\custom\ssh.exe")
    monkeypatch.setenv("VB_SCP_CMD", r"C:\custom\scp.exe")
    monkeypatch.setenv("VB_TAR_CMD", r"C:\custom\tar.exe")
    monkeypatch.setattr(ssh_mod.shutil, "which", lambda name: rf"C:\path\{name}.exe")

    runner = ssh_mod.SSHRunner(host="example.com", user="tester")

    assert runner._ssh_cmd == r"C:\custom\ssh.exe"
    assert runner._scp_cmd == r"C:\custom\scp.exe"
    assert runner._tar_cmd == r"C:\custom\tar.exe"


def test_default_windows_tools_come_from_path(monkeypatch, tmp_path):
    tools = {
        "ssh": r"C:\Windows\System32\OpenSSH\ssh.exe",
        "scp": r"C:\Windows\System32\OpenSSH\scp.exe",
        "tar": r"C:\Windows\System32\tar.exe",
    }

    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(ssh_mod.os, "name", "nt", raising=False)
    monkeypatch.delenv("VB_SSH_CMD", raising=False)
    monkeypatch.delenv("VB_SCP_CMD", raising=False)
    monkeypatch.delenv("VB_TAR_CMD", raising=False)
    monkeypatch.setattr(ssh_mod.shutil, "which", lambda name: tools.get(name))

    runner = ssh_mod.SSHRunner(host="example.com", user="tester")

    assert runner._ssh_cmd == tools["ssh"]
    assert runner._scp_cmd == tools["scp"]
    assert runner._tar_cmd == tools["tar"]


def test_ssh_runner_loads_tool_overrides_from_dotenv(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / ".env").write_text(
        "VB_SSH_CMD=C:\\custom\\ssh.exe\n"
        "VB_TAR_CMD=C:\\custom\\tar.exe\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(env_mod.Path, "home", lambda: home)
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("VB_SSH_CMD", raising=False)
    monkeypatch.delenv("VB_SCP_CMD", raising=False)
    monkeypatch.delenv("VB_TAR_CMD", raising=False)
    monkeypatch.setattr(ssh_mod.shutil, "which", lambda name: rf"C:\path\{name}.exe")

    runner = ssh_mod.SSHRunner(host="example.com", user="tester")

    assert runner._ssh_cmd == r"C:\custom\ssh.exe"
    assert runner._tar_cmd == r"C:\custom\tar.exe"

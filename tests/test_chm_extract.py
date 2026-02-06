from pathlib import Path

import src.chm_extract as chm_extract


def test_auto_install_apt_when_missing(monkeypatch, tmp_path: Path) -> None:
    calls = []
    state = {"extract_checks": 0}

    def fake_which(cmd: str):
        if cmd == "extract_chmLib":
            state["extract_checks"] += 1
            return None if state["extract_checks"] == 1 else "/usr/bin/extract_chmLib"
        if cmd == "apt-get":
            return "/usr/bin/apt-get"
        return None

    def fake_run(cmd, capture_output=True, text=True, check=False):
        calls.append(cmd)

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(chm_extract.shutil, "which", fake_which)
    monkeypatch.setattr(chm_extract.platform, "system", lambda: "Linux")
    monkeypatch.setattr(chm_extract.subprocess, "run", fake_run)

    chm_extract.extract_chm(tmp_path / "manual.chm", tmp_path / "out")

    assert calls[0][:3] == ["sudo", "apt-get", "-y"]
    assert calls[0][3:] == ["install", "chmlib-tools"]
    assert calls[1][0] == "extract_chmLib"
    assert calls[1][1] == str(tmp_path / "manual.chm")
    assert calls[1][2] == str(tmp_path / "out")


def test_no_auto_install_when_present(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_which(cmd: str):
        if cmd == "extract_chmLib":
            return "/usr/bin/extract_chmLib"
        return None

    def fake_run(cmd, capture_output=True, text=True, check=False):
        calls.append(cmd)

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(chm_extract.shutil, "which", fake_which)
    monkeypatch.setattr(chm_extract.subprocess, "run", fake_run)

    chm_extract.extract_chm(tmp_path / "manual.chm", tmp_path / "out")

    assert len(calls) == 1
    assert calls[0][0] == "extract_chmLib"
    assert calls[0][1] == str(tmp_path / "manual.chm")
    assert calls[0][2] == str(tmp_path / "out")

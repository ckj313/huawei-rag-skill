from pathlib import Path

import pytest

import src.chm_extract as chm_extract


def test_missing_extract_chmlib_raises(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_which(cmd: str):
        if cmd == "extract_chmLib":
            return None
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

    with pytest.raises(SystemExit, match="extract_chmLib not found"):
        chm_extract.extract_chm(tmp_path / "manual.chm", tmp_path / "out")

    assert not calls


def test_extract_chm_runs_when_present(monkeypatch, tmp_path: Path) -> None:
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

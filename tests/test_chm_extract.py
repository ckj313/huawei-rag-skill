from pathlib import Path

import scripts.chm_to_index as chm


def test_extract_chm_uses_chmlib(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, capture_output=True, text=True, check=False):
        calls.append(cmd)
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return Result()

    monkeypatch.setattr(chm.subprocess, "run", fake_run)

    chm.extract_chm(tmp_path / "manual.chm", tmp_path / "out")

    assert calls, "expected extract command to run"
    assert calls[0][0] == "extract_chmLib"
    assert calls[0][1] == str(tmp_path / "manual.chm")
    assert calls[0][2] == str(tmp_path / "out")

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from src.chm_extract import resolve_manual_input, resolve_tree_dir, source_cache_key


def test_source_cache_key_supports_stem_strategy() -> None:
    key = source_cache_key(Path("/tmp/HUAWEI_usg V8.5.chm"), strategy="stem")
    assert key == "huawei_usg-v8-5"


def test_source_cache_key_supports_hash_strategy(tmp_path: Path) -> None:
    chm_path = tmp_path / "HUAWEI_usg.chm"
    chm_path.write_bytes(b"test")
    key = source_cache_key(chm_path, strategy="hash")
    assert key.startswith("huawei_usg-")
    suffix = key.split("-", 1)[1]
    assert len(suffix) == 12


def test_resolve_manual_input_uses_manual_dir_directly(tmp_path: Path) -> None:
    manual_dir = tmp_path / "manuals" / "usg"
    manual_dir.mkdir(parents=True)

    resolved_dir, meta = resolve_manual_input(
        manual_dir=manual_dir,
        chm_file=None,
        extract_root=tmp_path / "manuals" / "chm",
        cache_strategy="stem",
        force_extract=False,
    )

    assert resolved_dir == manual_dir.resolve()
    assert meta["input_type"] == "manual_dir"
    assert meta["source_key"] == "usg"


def test_resolve_manual_input_uses_cached_extraction(tmp_path: Path) -> None:
    chm_file = tmp_path / "HUAWEI_usg.chm"
    chm_file.write_bytes(b"fake")
    extract_root = tmp_path / "manuals" / "chm"
    extracted_dir = extract_root / "huawei_usg"
    extracted_dir.mkdir(parents=True)
    (extracted_dir / "index.htm").write_text("<html>cached</html>", encoding="utf-8")

    resolved_dir, meta = resolve_manual_input(
        manual_dir=None,
        chm_file=chm_file,
        extract_root=extract_root,
        cache_strategy="stem",
        force_extract=False,
    )

    assert resolved_dir == extracted_dir.resolve()
    assert meta["input_type"] == "chm_file"
    assert meta["extract_status"] == "cached"


def test_resolve_manual_input_extracts_with_extract_chmlib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chm_file = tmp_path / "HUAWEI_usg.chm"
    chm_file.write_bytes(b"fake")
    extract_root = tmp_path / "manuals" / "chm"

    monkeypatch.setattr("src.chm_extract.shutil.which", lambda name: "/opt/homebrew/bin/extract_chmLib" if name == "extract_chmLib" else None)

    def fake_run(cmd: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        out_dir = Path(cmd[-1])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "topic.html").write_text("<html>new</html>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("src.chm_extract.subprocess.run", fake_run)

    resolved_dir, meta = resolve_manual_input(
        manual_dir=None,
        chm_file=chm_file,
        extract_root=extract_root,
        cache_strategy="stem",
        force_extract=False,
    )

    assert resolved_dir == (extract_root / "huawei_usg").resolve()
    assert meta["extract_status"] == "extracted"
    assert meta["extractor"] == "extract_chmLib"


def test_resolve_manual_input_errors_when_no_extractor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chm_file = tmp_path / "HUAWEI_usg.chm"
    chm_file.write_bytes(b"fake")
    extract_root = tmp_path / "manuals" / "chm"

    monkeypatch.setattr("src.chm_extract.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="No CHM extractor found"):
        resolve_manual_input(
            manual_dir=None,
            chm_file=chm_file,
            extract_root=extract_root,
            cache_strategy="stem",
            force_extract=False,
        )


def test_resolve_tree_dir_prefers_explicit_value(tmp_path: Path) -> None:
    explicit = tmp_path / "data" / "custom-tree"
    resolved = resolve_tree_dir(
        explicit_tree_dir=explicit,
        tree_root=tmp_path / "data" / "pageindex",
        source_key="huawei_usg",
    )
    assert resolved == explicit.resolve()


def test_resolve_tree_dir_uses_tree_root_when_not_explicit(tmp_path: Path) -> None:
    resolved = resolve_tree_dir(
        explicit_tree_dir=None,
        tree_root=tmp_path / "data" / "pageindex",
        source_key="huawei_usg",
    )
    assert resolved == (tmp_path / "data" / "pageindex" / "huawei_usg").resolve()

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "-", value.lower()).strip("-")
    return normalized or "manual"


def _hash_file(path: Path, chunk_size: int = 2 * 1024 * 1024) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def source_cache_key(chm_file: Path, strategy: str = "stem") -> str:
    source = Path(chm_file).expanduser().resolve()
    stem = _slug(source.stem)
    if strategy == "stem":
        return stem
    if strategy == "hash":
        return f"{stem}-{_hash_file(source)[:12]}"
    raise ValueError("strategy must be one of: stem, hash")


def _has_manual_files(directory: Path) -> bool:
    if not directory.exists():
        return False
    for pattern in ("*.md", "*.htm", "*.html"):
        if any(directory.rglob(pattern)):
            return True
    return False


def _resolve_extractor(preferred_extractor: str | None = None) -> str:
    if preferred_extractor:
        if shutil.which(preferred_extractor):
            return preferred_extractor
        raise RuntimeError(f"Configured extractor is unavailable: {preferred_extractor}")

    for name in ("extract_chmLib", "7z"):
        if shutil.which(name):
            return name
    raise RuntimeError(
        "No CHM extractor found. Install `extract_chmLib` (preferred) or `7z`."
    )


def _run_extractor(extractor: str, chm_file: Path, out_dir: Path) -> None:
    if extractor == "extract_chmLib":
        cmd = [extractor, str(chm_file), str(out_dir)]
    elif extractor == "7z":
        cmd = [extractor, "x", "-y", f"-o{out_dir}", str(chm_file)]
    else:
        raise RuntimeError(f"Unsupported CHM extractor: {extractor}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        raise RuntimeError(f"Failed to extract CHM using {extractor}: {details}")


def extract_chm(
    input_path: Path,
    out_dir: Path,
    *,
    force: bool = False,
    preferred_extractor: str | None = None,
) -> dict[str, object]:
    chm_file = Path(input_path).expanduser().resolve()
    target_dir = Path(out_dir).expanduser().resolve()

    if not chm_file.exists() or not chm_file.is_file():
        raise FileNotFoundError(f"CHM not found: {chm_file}")

    if target_dir.exists() and _has_manual_files(target_dir) and not force:
        return {
            "status": "cached",
            "extractor": None,
            "output_dir": str(target_dir),
        }

    if force and target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    extractor = _resolve_extractor(preferred_extractor)
    _run_extractor(extractor, chm_file, target_dir)
    if not _has_manual_files(target_dir):
        raise RuntimeError(
            f"CHM extraction finished but no html/markdown files found in {target_dir}"
        )

    file_count = 0
    for pattern in ("*.md", "*.htm", "*.html"):
        file_count += sum(1 for _ in target_dir.rglob(pattern))

    return {
        "status": "extracted",
        "extractor": extractor,
        "output_dir": str(target_dir),
        "file_count": file_count,
    }


def resolve_manual_input(
    *,
    manual_dir: Path | None,
    chm_file: Path | None,
    extract_root: Path,
    cache_strategy: str = "stem",
    force_extract: bool = False,
    preferred_extractor: str | None = None,
) -> tuple[Path, dict[str, object]]:
    if bool(manual_dir) == bool(chm_file):
        raise ValueError("Provide exactly one source: `manual_dir` or `chm_file`.")

    if manual_dir:
        source_dir = Path(manual_dir).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise FileNotFoundError(f"manual_dir not found: {source_dir}")
        return source_dir, {
            "input_type": "manual_dir",
            "manual_dir": str(source_dir),
            "source_key": _slug(source_dir.name),
        }

    chm_path = Path(chm_file).expanduser().resolve()
    if not chm_path.exists() or not chm_path.is_file():
        raise FileNotFoundError(f"chm_file not found: {chm_path}")

    source_key = source_cache_key(chm_path, strategy=cache_strategy)
    extract_dir = Path(extract_root).expanduser().resolve() / source_key
    extract_meta = extract_chm(
        chm_path,
        extract_dir,
        force=force_extract,
        preferred_extractor=preferred_extractor,
    )
    meta: dict[str, object] = {
        "input_type": "chm_file",
        "source_key": source_key,
        "chm_file": str(chm_path),
        "extract_dir": str(extract_dir.resolve()),
        "extract_status": extract_meta["status"],
    }
    if extract_meta.get("extractor"):
        meta["extractor"] = extract_meta["extractor"]
    if extract_meta.get("file_count") is not None:
        meta["extracted_file_count"] = int(extract_meta["file_count"])
    return extract_dir.resolve(), meta


def resolve_tree_dir(
    *,
    explicit_tree_dir: Path | None,
    tree_root: Path,
    source_key: str,
) -> Path:
    if explicit_tree_dir:
        return Path(explicit_tree_dir).expanduser().resolve()
    return (Path(tree_root).expanduser().resolve() / source_key).resolve()

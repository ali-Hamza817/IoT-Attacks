"""Download the datasets from their official repositories and verify integrity.

* NF-ToN-IoT V1  -> University of Queensland RDM (open access, BagIt zip)
* Downsampled V1 -> University of Burgos RIUBU (used only as a reference to
  check that our own downsampling reproduces the authors' published subset)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

from . import config

_UA = {"User-Agent": "nf-toniot-reproduction/1.0 (academic research)"}


def _http_get(url: str, dest: Path | None = None) -> bytes | None:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        if dest is None:
            return resp.read()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh, length=1 << 20)
        tmp.replace(dest)
    return None


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_original_csv() -> Path | None:
    hits = list(config.EXTRACT_DIR.glob("*/data/NF-ToN-IoT.csv"))
    return hits[0] if hits else None


def download_original(force: bool = False) -> Path:
    """Fetch the official NF-ToN-IoT V1 zip from UQ, extract, verify SHA-1."""
    config.ensure_dirs()
    csv = find_original_csv()
    if csv is not None and not force:
        print(f"[download] original CSV already present: {csv}")
    else:
        if force or not config.RAW_ZIP.exists():
            # The RDM API returns a short-lived pre-signed S3 URL.
            meta = json.loads(_http_get(config.UQ_DOWNLOAD_API))
            if not meta.get("canDownload") or not meta.get("url"):
                raise RuntimeError(f"UQ RDM refused the download: {meta}")
            print("[download] fetching NF-ToN-IoT V1 zip from UQ RDM ...")
            _http_get(meta["url"], config.RAW_ZIP)
        print("[download] extracting zip ...")
        with zipfile.ZipFile(config.RAW_ZIP) as zf:
            for member in zf.namelist():  # guard against path traversal
                target = (config.EXTRACT_DIR / member).resolve()
                if config.EXTRACT_DIR.resolve() not in target.parents:
                    raise RuntimeError(f"unsafe path in zip: {member}")
            zf.extractall(config.EXTRACT_DIR)
        csv = find_original_csv()
        if csv is None:
            raise FileNotFoundError("NF-ToN-IoT.csv not found inside the zip")

    digest = sha1_of(csv)
    if digest != config.UQ_CSV_SHA1:
        raise RuntimeError(f"SHA-1 mismatch: got {digest}, expected {config.UQ_CSV_SHA1}")
    print(f"[download] SHA-1 verified ({digest})")
    return csv


def download_reference(force: bool = False) -> Path:
    """Fetch the authors' published downsampled CSV (for verification only)."""
    config.ensure_dirs()
    if config.REFERENCE_CSV.exists() and not force:
        print(f"[download] reference CSV already present: {config.REFERENCE_CSV}")
    else:
        print("[download] fetching authors' downsampled CSV from UBU ...")
        _http_get(config.UBU_REFERENCE_URL, config.REFERENCE_CSV)
    return config.REFERENCE_CSV


if __name__ == "__main__":
    download_original()
    download_reference()

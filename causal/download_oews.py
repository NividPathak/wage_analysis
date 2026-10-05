"""Fallback downloader for OEWS state files from BLS into data_external/oews/.

The repo already ships raw state workbooks for 2005-2024 under data/, so the pipeline does not need
this script. It is kept so a missing or damaged year can be re-fetched reproducibly.

Usage: python -m causal.download_oews 2005 2022
"""

from __future__ import annotations

import subprocess
import sys
import time
import zipfile
from io import BytesIO

import requests

from causal.oews_io import EXTERNAL_OEWS_DIR

URL_PATTERNS = [
    "https://www.bls.gov/oes/special-requests/oesm{yy}st.zip",
    "https://www.bls.gov/oes/special.requests/oesm{yy}st.zip",
]


def user_agent() -> str:
    """BLS rejects anonymous requests, so identify with the git-configured email."""
    email = subprocess.run(["git", "config", "user.email"], capture_output=True,
                           text=True).stdout.strip()
    return f"Nivid Pathak research <{email}>"


def download_year(year: int) -> bool:
    """Download and unzip one year's state file. Returns True on success."""
    yy = f"{year % 100:02d}"
    headers = {"User-Agent": user_agent()}
    for pattern in URL_PATTERNS:
        url = pattern.format(yy=yy)
        r = requests.get(url, headers=headers, timeout=60)
        time.sleep(2)
        if r.ok and r.content[:2] == b"PK":
            target = EXTERNAL_OEWS_DIR / f"oesm{yy}st"
            target.mkdir(parents=True, exist_ok=True)
            zipfile.ZipFile(BytesIO(r.content)).extractall(target)
            print(f"{year}: downloaded from {url}")
            return True
    print(f"{year}: download failed")
    return False


if __name__ == "__main__":
    start, end = (int(a) for a in sys.argv[1:3])
    for y in range(start, end + 1):
        download_year(y)

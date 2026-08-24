"""Download CloakBrowser binary from cloakbrowser.dev.

Resolves the Chromium version from the PyPI wheel metadata (no pip
install needed), then downloads and extracts the binary tarball.
"""

import json
import os
import platform
import re
import sys
import tarfile
import urllib.request
import zipfile
from io import BytesIO

PYPI_JSON = "https://pypi.org/pypi/cloakbrowser/json"
GITHUB_BASE = "https://github.com/CloakHQ/cloakbrowser/releases/download"
MIRROR = os.environ.get("CLOAKBROWSER_MIRROR", "")
CACHE_DIR = os.environ.get(
    "CLOAKBROWSER_CACHE_DIR", os.path.expanduser("~/.cloakbrowser")
)


def _get_chromium_version(pip_version: str | None = None) -> str:
    """Get CloakBrowser's Chromium version from PyPI wheel metadata."""
    pypi = json.loads(urllib.request.urlopen(PYPI_JSON, timeout=30).read())
    whl_url = next(u["url"] for u in pypi["urls"] if u["filename"].endswith(".whl"))
    whl_data = urllib.request.urlopen(whl_url, timeout=60).read()
    with zipfile.ZipFile(BytesIO(whl_data)) as zf:
        for name in zf.namelist():
            if name.endswith("config.py"):
                content = zf.read(name).decode()
                m = re.search(r'CHROMIUM_VERSION\s*=\s*"([^"]+)"', content)
                if m:
                    return m.group(1)
    raise RuntimeError("Could not find CHROMIUM_VERSION in cloakbrowser wheel")


def _detect_platform() -> str:
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "linux":
        arch = "x64" if machine in ("x86_64", "amd64") else "arm64"
        return f"linux-{arch}"
    if system == "darwin":
        arch = "arm64" if machine == "arm64" else "x64"
        return f"mac-{arch}"
    raise RuntimeError(f"Unsupported platform: {system}-{machine}")


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else None
    if not version:
        print("Resolving CloakBrowser Chromium version from PyPI...")
        version = _get_chromium_version()

    plat = _detect_platform()
    dest = os.path.join(CACHE_DIR, f"chromium-{version}")
    binary = os.path.join(dest, "chrome")

    if os.path.isfile(binary):
        print(f"Already installed: {binary}")
        return

    gh_url = f"{GITHUB_BASE}/chromium-v{version}/cloakbrowser-{plat}.tar.gz"
    url = f"{MIRROR}/{gh_url}" if MIRROR else gh_url
    os.makedirs(dest, exist_ok=True)
    tmp = os.path.join(CACHE_DIR, "download.tar.gz")

    print(f"Downloading CloakBrowser {version} ({plat})...")
    print(f"  URL: {url}")
    urllib.request.urlretrieve(url, tmp)

    print("Extracting...")
    with tarfile.open(tmp, "r:gz") as tf:
        tf.extractall(dest)
    os.unlink(tmp)

    if os.path.isfile(binary):
        os.chmod(binary, 0o755)
    print(f"Installed: {binary}")


if __name__ == "__main__":
    main()

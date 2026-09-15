"""Download Obscura headless browser binary from GitHub releases.

Downloads the stealth variant (rendering + anti-detection) for the
current platform. No external dependencies required.
"""

import os
import platform
import sys
import tarfile
import urllib.request

DEFAULT_VERSION = "0.2.2"
GITHUB_BASE = "https://github.com/h4ckf0r0day/obscura/releases/download"
MIRROR = os.environ.get("OBSCURA_MIRROR", "")
CACHE_DIR = os.environ.get("OBSCURA_CACHE_DIR", os.path.expanduser("~/.obscura"))


def _detect_platform() -> str:
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "linux":
        arch = "x86_64" if machine in ("x86_64", "amd64") else "aarch64"
        return f"{arch}-linux"
    if system == "darwin":
        arch = "aarch64" if machine == "arm64" else "x86_64"
        return f"{arch}-macos"
    raise RuntimeError(f"Unsupported platform: {system}-{machine}")


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VERSION

    plat = _detect_platform()
    dest = os.path.join(CACHE_DIR, f"v{version}")
    binary = os.path.join(dest, "obscura")

    if os.path.isfile(binary):
        print(f"Already installed: {binary}")
        return

    gh_url = f"{GITHUB_BASE}/v{version}/obscura-{plat}-stealth.tar.gz"
    url = f"{MIRROR}/{gh_url}" if MIRROR else gh_url
    os.makedirs(dest, exist_ok=True)
    tmp = os.path.join(CACHE_DIR, "download.tar.gz")

    print(f"Downloading Obscura {version} ({plat})...")
    print(f"  URL: {url}")
    urllib.request.urlretrieve(url, tmp)

    print("Extracting...")
    with tarfile.open(tmp, "r:gz") as tf:
        tf.extractall(dest, filter="data")
    os.unlink(tmp)

    if os.path.isfile(binary):
        os.chmod(binary, 0o755)
    print(f"Installed: {binary}")


if __name__ == "__main__":
    main()

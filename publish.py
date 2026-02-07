"""
ESPU publish script.

Publishes all packages in ./packages to PyPI or TestPyPI.
"""

from pathlib import Path
import subprocess
import sys
import shutil

from secret import PYPI_USERNAME, PYPI_PASSWORD


ROOT = Path(__file__).parent
PACKAGES = ROOT / "packages"


def fail(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str], cwd: Path):
    print(f"> {' '.join(cmd)}   (cwd={cwd})")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        fail(f"Command failed: {' '.join(cmd)}")


def publish_package(pkg_dir: Path, repository: str | None):
    dist = pkg_dir / "dist"

    if dist.exists():
        shutil.rmtree(dist)

    # Build
    run([sys.executable, "-m", "build"], cwd=pkg_dir)

    # Upload
    cmd = [
        "twine",
        "upload",
        "--non-interactive",
        "-u", PYPI_USERNAME,
        "-p", PYPI_PASSWORD,
        "dist/*",
    ]

    if repository:
        cmd.extend(["--repository-url", repository])

    run(cmd, cwd=pkg_dir)

    print(f"Published {pkg_dir.name}")


def main():
    if not PACKAGES.exists():
        fail("packages/ directory does not exist. Run build.py first.")

    testpypi = "--testpypi" in sys.argv
    repository = (
        "https://test.pypi.org/legacy/"
        if testpypi
        else None
    )

    for pkg_dir in sorted(PACKAGES.iterdir()):
        if not pkg_dir.is_dir():
            continue

        print(f"\n=== Publishing {pkg_dir.name} ===")
        publish_package(pkg_dir, repository)

    print("\nAll packages published successfully.")


if __name__ == "__main__":
    main()
"""
ESPU Build Script to automatically turn the monorepo into chunks
"""

from __future__ import annotations
from pathlib import Path
import shutil
import json
import sys

# Paths / Constants
ROOT = Path(__file__).parent
SRC = ROOT / "monorepo" / "src" / "espu"
OUT = ROOT / "packages"

VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

TEMPLATES = ROOT / "pyproject.templates"
README_TEMPLATES = ROOT / "readme.templates"
README_ROOT = ROOT / "README.md"

DEPENDENCIES_FILE = ROOT / "dependencies.json"

# Dependency config
if DEPENDENCIES_FILE.exists():
    COMPONENT_DEPENDENCIES: dict[str, list[str]] = json.loads(
        DEPENDENCIES_FILE.read_text(encoding="utf-8")
    )
else:
    raise FileNotFoundError(f"DEPENDENCIES_FILE missing at {DEPENDENCIES_FILE}")

# Utils
def fail(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def clean_out():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

def copy_tree(src: Path, dst: Path):
    shutil.copytree(
        src,
        dst,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    )

def validate_namespace():
    forbidden = [
        SRC / "__init__.py",
        SRC / "lib" / "__init__.py"
    ]
    for p in forbidden:
        if p.exists():
            fail(f"Forbidden __init__.py found: {p}")

def validate_unique_component_names(libs: list[str], exts: list[str]):
    overlap = set(libs) & set(exts)
    if overlap:
        fail(
            "Duplicate component names detected: " + ", ".join(sorted(overlap))
        )

# Registry + dependency resolution
def scan_components() -> tuple[list[str], list[str]]:
    """Return (libs, exts) as component names (NOT PyPI names)"""
    libs: list[str] = []
    exts: list[str] = []

    lib_root = SRC / "lib"
    if lib_root.exists():
        libs = sorted(p.name for p in lib_root.iterdir() if p.is_dir())

    exts = sorted(
        p.name for p in SRC.iterdir()
        if p.is_dir() and p.name not in ["core", "lib", "__pycache__"]
    )
    return libs, exts

def build_registry(libs: list[str], exts: list[str]) -> dict[str, dict]:
    """
    Registry maps component-name -> {package, kind, requires?}
    Component names are:
    - "core"
    - ext names (e.g. "bezier")
    - lib names (e.g. "vector")
    """
    registry: dict[str, dict] = {
        "core": {"package": "espu", "kind": "core"}
    }

    # libs
    for name in libs:
        registry[name] = {
            "package": f"espu-lib-{name}",
            "kind": "lib",
            "requires": COMPONENT_DEPENDENCIES.get(name, [])
        }

    # exts
    for name in exts:
        registry[name] = {
            "package": f"espu-ext-{name}",
            "kind": "ext",
            "requires": COMPONENT_DEPENDENCIES.get(name, [])
        }
    
    return registry

def validate_dependency_graph(registry: dict[str, dict]):
    """
    - every dependency name must exist in registry
    - libs may only depend on libs
    - extensions may depend on libs and/or extension
    """
    for name, meta in registry.items():
        requires = meta.get("requires", [])
        if not requires:
            continue

        kind = meta["kind"]
        for dep in requires:
            if dep not in registry:
                fail(f"Unknown dependency '{dep}' referenced by '{name}'")

            dep_kind = registry[dep]["kind"]
            if kind == "lib" and dep_kind != "lib":
                fail(f"Lib '{name}' cannot depend on non-lib '{dep}' (kind={dep_kind})")

def generate_extras(registry: dict[str, dict]) -> str:
    """
    Core exposes:
    - extensions as espu[bezier]
    - libs as espu[lib-vector]
    """
    lines: list[str] = []

    for name, meta in sorted(registry.items()):
        kind = meta["kind"]
        if kind == "core":
            continue

        pkg = meta["package"]
        if kind == "ext":
            extra = name
        elif kind == "lib":
            extra = f"lib-{name}"
        else:
            continue

        lines.append(f'{extra} = ["{pkg}=={VERSION}"]')

    return "\n".join(lines)

def resolve_ext_dependencies(name: str, registry: dict[str, dict]) -> list[str]:
    deps = [f"espu=={VERSION}"]
    for dep_name in registry[name].get("requires", []):
        deps.append(f'{registry[dep_name]["package"]}=={VERSION}')
    return deps

def resolve_lib_dependencies(name: str, registry: dict[str, dict]) -> list[str]:
    deps = [f"espu=={VERSION}"]
    for dep_name in registry[name].get("requires", []):
        # validated already: dep is lib
        deps.append(f'{registry[dep_name]["package"]}=={VERSION}')
    return deps

# File writers
def write_core_pyproject(core_dst: Path, registry: dict[str, dict]):
    template = (TEMPLATES / "core.toml").read_text(encoding="utf-8")
    extras = generate_extras(registry)

    text = (
        template
        .replace("{name}", "espu")
        .replace("{version}", VERSION)
        .replace("{extras}", extras)
    )
    (core_dst / "pyproject.toml").write_text(text, encoding="utf-8")

def write_ext_pyproject(dst: Path, ext_name: str, registry: dict[str, dict]):
    template = (TEMPLATES / "ext.toml").read_text(encoding="utf-8")
    deps = resolve_ext_dependencies(ext_name, registry)
    deps_text = ",\n".join(f'"{d}"' for d in deps)

    text = (
        template
        .replace("{name}", f"espu-ext-{ext_name}")
        .replace("{version}", VERSION)
        .replace("{dependencies}", deps_text)
    )
    (dst / "pyproject.toml").write_text(text, encoding="utf-8")

def write_lib_pyproject(dst: Path, lib_name: str, registry: dict[str, dict]):
    template = (TEMPLATES / "lib.toml").read_text(encoding="utf-8")
    deps = resolve_lib_dependencies(lib_name, registry)
    deps_text = ",\n".join(f'"{d}"' for d in deps)

    text = (
        template
        .replace("{name}", f"espu-lib-{lib_name}")
        .replace("{version}", VERSION)
        .replace("{dependencies}", deps_text)
    )
    (dst / "pyproject.toml").write_text(text, encoding="utf-8")

def copy_core_readme(dst: Path):
    shutil.copy(README_ROOT, dst / "README.md")

def write_readme(dst: Path, kind: str):
    template = (README_TEMPLATES / f"{kind}.md").read_text(encoding="utf-8")
    (dst / "README.md").write_text(template, encoding="utf-8")

# Builders
def materialize_core() -> Path:
    dst = OUT / "espu"
    (dst / "src").mkdir(parents=True)

    copy_tree(SRC / "core", dst / "src" / "espu" / "core")
    copy_core_readme(dst)

    return dst

def materialize_lib(lib_name: str, registry: dict[str, dict]):
    pkg_dir = OUT / f"espu-lib-{lib_name}"
    (pkg_dir / "src").mkdir(parents=True)

    copy_tree(
        SRC / "lib" / lib_name,
        pkg_dir / "src" / "espu" / "lib" / lib_name
    )
    write_readme(pkg_dir, "lib")
    write_lib_pyproject(pkg_dir, lib_name, registry)

def materialize_ext(ext_name: str, registry: dict[str, dict]):
    pkg_dir = OUT / f"espu-ext-{ext_name}"
    (pkg_dir / "src").mkdir(parents=True)

    copy_tree(SRC / ext_name, pkg_dir / "src" / "espu" / ext_name)
    write_readme(pkg_dir, "ext")
    write_ext_pyproject(pkg_dir, ext_name, registry)

# Main
def main():
    validate_namespace()
    clean_out()

    libs, exts = scan_components()
    validate_unique_component_names(libs, exts)
    registry = build_registry(libs, exts)
    validate_dependency_graph(registry)

    # materialize packages
    core_dst = materialize_core()

    for lib_name in libs:
        materialize_lib(lib_name, registry)

    for ext_name in exts:
        materialize_ext(ext_name, registry)

    # write registry.json into core package
    core_registry = OUT / "espu" / "src" / "espu" / "core" / "registry.json"
    core_registry.parent.mkdir(parents=True, exist_ok=True)
    core_registry.write_text(
        json.dumps(registry, indent=4, sort_keys=True), encoding="utf-8"
    )

    # write core pyproject last (extras need full registry)
    write_core_pyproject(core_dst, registry)

    print("Build complete.")
    print("Components: ", ", ".join(sorted(registry)))

if __name__ == "__main__":
    main()
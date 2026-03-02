"""
ESPUnity Package Manager
========================

A coherent, ecosystem-aware CLI / CI tool for managing ESPU packages in the current Python environment.
This tool uses ONLY the Python standard library.
"""

# from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from importlib.metadata import distributions, requires
from typing import Any, Optional

# Types
Package = tuple[str, str]  # (distribution_name, version_string)
VersionTuple = tuple[int, int, int]  # major.minor.patch
DependencyGraphLC = dict[str, set[str]]  # src_name_lower -> deps_lower
PackageMap = dict[str, str]  # name -> version


# Version handling (strict x.y.z)
def parse_version(version_str: str) -> VersionTuple:
    """
    Parse a strict semantic version string "x.y.z" into a comparable tuple.

    This intentionally rejects any suffixes like:
    1.2.3rc1, 1.2.3.post1, 1.2.3+local, 1.2.3.dev1

    Raises:
        ValueError if the format is not exactly x.y.u with numeric parts.
    """
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format (expected: x.y.z): {version_str}")
    try:
        return tuple(int(p) for p in parts)
    except ValueError as e:
        raise ValueError(
            f"Invalid version format (non-numeric parts): {version_str}"
        ) from e


def detect_version_mismatch(packages: list[Package]) -> tuple[bool, Optional[str]]:
    """
    Determine whether installed ESPU packages have differing versions.

    Returns:
        (mismatch_detected, newest_installed_version_string)
    """
    if not packages:
        return False, None

    parsed = [parse_version(v) for _, v in packages]
    newest = max(parsed)
    mismatch = any(v != newest for v in parsed)
    return mismatch, ".".join(str(x) for x in newest)


# Package discovery / classification
def get_espu_packages(prefix: str = "espu") -> list[Package]:
    """
    Retrieve installed ESPU distribution packages (distribution names start with prefix).

    Returns:
        Sorted list of (name, version).
    """
    out: list[Package] = []

    for dist in distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue

        if name.lower().startswith(prefix.lower()):
            out.append((name, dist.version))

    return sorted(out, key=lambda x: x[0].lower())


def packages_to_map(packages: list[Package]) -> PackageMap:
    """Map installed ESPU package name -> version string."""
    return {n: v for n, v in packages}


def split_espu_roles(packages: list[Package]) -> tuple[set[str], set[str], set[str]]:
    """
    Split installed ESPU packages into:
    - extensions: espu-ext-*
    - libraries:  espu-lib-*
    - other:      everything else starting with espu

    Returns:
        (exts, libs, others) sets using canonical installed names.
    """
    exts: set[str] = set()
    libs: set[str] = set()
    other: set[str] = set()

    for name, _ in packages:
        nl = name.lower()
        if nl.startswith("espu-ext-"):
            exts.add(name)
        elif nl.startswith("espu-lib-"):
            libs.add(name)
        else:
            other.add(name)

    return exts, libs, other


# Dependency graph and reachability (stdlib only)
_REQ_NAME_RE = re.compile(r"^([A-Za-z0-9_.-]+)")


def parse_requirement_name(requirement: str) -> str:
    """
    Extract the distribution name from a PEP 508 requirement string.

    Example:
        "espu-lib-core (>1.2.0) ; extra == 'test'"
        -> "espu-lib-core"
    """
    req = requirement.split(";", 1)[0].strip()
    m = _REQ_NAME_RE.match(req)
    return m.group(1).lower() if m else req.lower()


def build_espu_dependency_graph_lower(installed_names: set[str]) -> DependencyGraphLC:
    """
    Build a dependency graph for installed ESPU packages, stored in lowercase.
    """
    installed_lc = {n.lower() for n in installed_names}
    graph: DependencyGraphLC = {n.lower(): set() for n in installed_names}

    for name in installed_names:
        src_lc = name.lower()

        try:
            reqs = requires(name)
        except Exception:
            reqs = None

        if not reqs:
            continue

        for r in reqs:
            dep_lc = parse_requirement_name(r)
            if dep_lc in installed_lc:
                graph[src_lc].add(dep_lc)

    return graph


def compute_reachable_libs(
    packages: list[Package], graph_lc: DependencyGraphLC
) -> set[str]:
    """
    Compute which espu-lib-* packages are reachable from any installed extension / library.
    """
    exts, libs, _ = split_espu_roles(packages)

    installed_names = [n for n, _ in packages]
    lc_to_name = {n.lower(): n for n in installed_names}

    stack: list[str] = [e.lower() for e in sorted(exts)]
    visited: set[str] = set()
    reachable_libs: set[str] = set()

    while stack:
        node_lc = stack.pop()
        if node_lc in visited:
            continue
        visited.add(node_lc)

        node_name = lc_to_name.get(node_lc)
        if node_name and node_name in libs:
            reachable_libs.add(node_name)

        for dep_lc in graph_lc.get(node_lc, set()):
            if dep_lc not in visited:
                stack.append(dep_lc)

    return reachable_libs


# pip execution helpers
def pip_install_update(
    package_specs: list[str], ignore_deps: bool, silent: bool, dry_run: bool
) -> list[str]:
    """
    Build and optionally execute: python -m pip install -U ...

    Returns
        The command list (useful for --dry-run and --json).
    """
    if not package_specs:
        return []

    cmd = [sys.executable, "-m", "pip", "install", "-U", *package_specs]
    if ignore_deps:
        cmd.append("--no-deps")

    if dry_run:
        return cmd

    if silent:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.check_call(cmd)

    return cmd


def pip_uninstall(package_names: list[str], silent: bool, dry_run: bool) -> list[str]:
    """
    Build and optionally execute: python -m pip uninstall -y ...

    Returns:
        The command list.
    """
    if not package_names:
        return []

    cmd = [sys.executable, "-m", "pip", "uninstall", "-y", *package_names]

    if dry_run:
        return cmd

    if silent:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.check_call(cmd)

    return cmd


# Output helpers


def emit_json(payload: dict[str, Any]) -> None:
    """Emit stable JSON for automation."""
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def print_packages(
    packages: list[Package], show_version: bool, use_color: bool
) -> None:
    """Print installed ESPU packages (human mode)."""
    header = f"Installed Components ({len(packages)})"
    if use_color:
        print(f"\033[1;33m{header}\033[0m\n")
    else:
        print(header + "\n")

    for i, (name, version) in enumerate(packages):
        if use_color:
            color = "\033[97m" if i % 2 == 0 else "\033[38;5;245m"
            reset = "\033[0m"
            if show_version:
                print(f"{color}{name}={version}{reset}")
            else:
                print(f"{color}{name}{reset}")
        else:
            if show_version:
                print(f"{name}={version}")
            else:
                print(name)


def confirm(prompt: str, auto_yes: bool) -> bool:
    """Prompt unless auto_yes is enabled."""
    if auto_yes:
        return True
    return input(prompt).strip().lower() == "y"


# Main
def main() -> None:
    """
    Main entry point.

    Argument layout is grouped by:
    - Output / UX
    - Safety
    - Operations
    - Checks
    - Cleanup
    """
    parser = argparse.ArgumentParser(description="ESPUnity Package Manager")

    # Output / UX
    out_grp = parser.add_argument_group("output")
    out_grp.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (disables colors).",
    )
    out_grp.add_argument(
        "--no-color", action="store_true", help="Disable ANSI colors for human output."
    )
    out_grp.add_argument(
        "--no-version",
        action="store_true",
        help="Do not print versions in the installed list.",
    )
    out_grp.add_argument("--silent", action="store_true", help="Suppress pip output.")

    # Safety / automation control
    safe_grp = parser.add_argument_group("safety")
    safe_grp.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions but do not change anything.",
    )
    safe_grp.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm prompts (does NOT imply --ignore-deps).",
    )
    safe_grp.add_argument(
        "--ignore-deps",
        action="store_true",
        help="Pass --no-deps to pip (dangerous; explicit).",
    )

    # Checks / mismatch behavior
    chk_grp = parser.add_argument_group("checks")
    chk_grp.add_argument(
        "--no-version-check",
        action="store_true",
        help="Disable version mismatch detection and warnings.",
    )
    chk_grp.add_argument(
        "--resolve-mismatch",
        action="store_true",
        help="Align all installed ESPU packages to newest installed version.",
    )

    # Operations
    op_grp = parser.add_argument_group("operations")
    op_grp.add_argument(
        "--update",
        action="store_true",
        help="Update all installed ESPU packages to latest available versions.",
    )
    op_grp.add_argument(
        "--set-version",
        metavar="X.Y.Z",
        type=str,
        help="Force all installed ESPU packages to exactly X.Y.Z.",
    )

    # Cleanup (libs only)
    clean_grp = parser.add_argument_group("cleanup")
    clean_grp.add_argument(
        "--auto-uninstall",
        action="store_true",
        help="Remove unused espu-lib-* packages (not reachable from any installed espu-ext-*).",
    )
    clean_grp.add_argument(
        "--protect",
        nargs="*",
        default=[],
        metavar="LIB",
        help=(
            "Protect specific espu-lib-* packages from auto-uninstall. "
            "Provide names like: espu-lib-core espu-lib-utils"
        ),
    )

    args = parser.parse_args()

    # Compatibility rules
    if args.resolve_mismatch and args.no_version_check:
        parser.error("--resolve-mismatch cannot be used with --no-version-check")

    use_color = (not args.no_color) and (not args.json)

    # Discover installed packages
    packages = get_espu_packages()
    installed_map = packages_to_map(packages)

    payload: dict[str, Any] = {
        "installed": [{"name": n, "version": v} for n, v in packages],
        "actions": [],
        "warnings": [],
        "notes": [],
    }

    if not packages:
        payload["notes"].append("No ESPU packages found.")
        if args.json:
            emit_json(payload)
        else:
            print("No ESPU packages found.")

    # Fail fast on strict version violations (x.y.z only).
    for _, v in packages:
        parse_version(v)

    if not args.json:
        print_packages(packages, show_version=not args.no_version, use_color=use_color)

    # Helper: post-action mismatch check
    def post_action_mismatch_check() -> None:
        if args.no_version_check:
            return

        refreshed = get_espu_packages()
        payload["installed"] = [{"name": n, "version": v} for n, v in refreshed]

        mismatch, newest = detect_version_mismatch(refreshed)
        payload["mismatch"] = mismatch
        payload["newest_installed_version"] = newest

        if mismatch:
            msg = (
                "Versions are still mismatched after the operation. "
                "This often means a release is currently propagating. "
                "Please wait a couple minutes and try again."
            )
            payload["warnings"].append(msg)
            if not args.json:
                print("\n" + msg)

        if not args.json:
            print_packages(
                refreshed, show_version=not args.no_version, use_color=use_color
            )

    # Operations are flag-driven:
    if args.set_version:
        parse_version(args.set_version)  # validate strict
        specs = [f"{name}=={args.set_version}" for name in installed_map.keys()]

        cmd = pip_install_update(specs, args.ignore_deps, args.silent, args.dry_run)
        payload["actions"].append(
            {"type": "set_version", "target": args.set_version, "pip_cmd": cmd}
        )

        if args.dry_run:
            payload["notes"].append("Dry-run enabled, no changes were made.")
            if args.json:
                emit_json(payload)
            return

        post_action_mismatch_check()

        # Check: mismatch detection + optional resolution
        if not args.no_version_check:
            mismatch, newest = detect_version_mismatch(get_espu_packages())
            payload["mismatch"] = mismatch
            payload["newest_installed_version"] = newest

            if mismatch and newest and args.resolve_mismatch:
                specs = [f"{name}=={newest}" for name, _ in get_espu_packages()]
                cmd = pip_install_update(
                    specs, args.ignore_deps, args.silent, args.dry_run
                )
                payload["actions"].append(
                    {"type": "resolve_mismatch", "target": newest, "pip_cmd": cmd}
                )

                if args.dry_run:
                    payload["notes"].append("Dry-run enabled: no changes were made.")
                    if args.json:
                        emit_json(payload)
                    return

                post_action_mismatch_check()

        #

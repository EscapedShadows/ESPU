from __future__ import annotations
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import PurePosixPath, Path
import json

# Data Model
@dataclass(frozen=True)
class ComponentInfo:
    # Metadata for an official espu component
    name: str
    package: str
    kind: str # core | ext | lib

# Load trusted registry from JSON (edited by build script)
_REGISTRY_PATH = Path(__file__).with_name("registry.json")

def _load_registry() -> dict[str, ComponentInfo]:
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Missing registry: {_REGISTRY_PATH}. Reinstall ESPU to fix")
    
    data: dict[str, dict] = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))

    out: dict[str, ComponentInfo] = {}
    for name, meta in data.items():
        out[name] = ComponentInfo(
            name=name,
            package=str(meta["package"]),   # This is meant to fail if its missing
            kind=str(meta["kind"])
        )

    return out

_AVAILABLE: dict[str, ComponentInfo] = _load_registry()

# Internal helpers
def _espu_contributors() -> dict[str, set[str]]:
    """
    distribution-name -> set of espu components it contributes.

    Rules:
    - espu/core/...         -> "core"
    - espu/<name>/...       -> "<name>"
    - espu/lib/...          -> ignored
    - espu/lib/<name>/...   -> "<name>"
    """
    result: dict[str, set[str]] = {}

    for dist in distributions():
        files = dist.files or []
        found: set[str] = set()

        for f in files:
            path = PurePosixPath(f)
            parts = path.parts

            if not parts or parts[0] != "espu":
                continue

            if len(parts) >= 2 and parts[1] == "core":
                found.add("core")
            elif len(parts) >= 3 and parts[1] == "lib":
                found.add(parts[2])
            elif len(parts) >= 2:
                found.add(parts[1])

        if found:
            result[dist.metadata.get("Name", "<unknown>")] = found

    return result

# Public API
def available() -> set[str]:
    return set(_AVAILABLE.keys())

def installed() -> set[str]:
    found: set[str] = set()
    for comps in _espu_contributors().values():
        found |= comps
    return found

def unknown() -> set[str]:
    return installed() - available()

def info(name: str) -> ComponentInfo:
    try:
        return _AVAILABLE[name]
    except KeyError:
        raise KeyError(f"Unknown espu component: {name}") from None
    
def contributors() -> dict[str, set[str]]:
    return _espu_contributors()
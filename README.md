# ESPU

**ESPU** (EscapedShadows Python Utils) is a modular Python utility ecosystem built around a small core and opt-in extensions and libraries.

The core package is intentionally minimal. Functionality is added via extensions (`espu-ext-*`) and internal libraries (`espu-lib-*`), all living under the shared `espu.*` namespace.

The goal is to provide a clean, extensible foundation without forcing users to install everything up front.

---

## Installation

Install the core package:

```bash
pip install espu
```

The core on its own provides only minimal functionality and acts primarily as an entry point and registry.

---

## Extensions and Extras

Most functionality is provided via **extensions**, which can be installed using extras:

```bash
pip install espu[bezier]
```

This will install:
- `espu` (core)
- `espu-ext-bezier`
- any required internal libraries (for example `espu-lib-vector`)

Extensions may depend on libraries and/or other extensions.
Libraries may **only** depend on other libraries and never on extensions.

Multiple extras can be combined:

```bash
pip install espu[bezier,logger,wol]
```

---

## Libraries

Internal libraries are reusable building blocks used by extensions or other libraries.
They can also be installed explicitly if needed:

```bash
pip install espu[lib-vector]
```

Libraries live under the following namespace:

`espu.lib.<name>`

---

## Inspecting Installed Components

The ESPU core module provides a small runtime API to inspect what components are known and which are currently installed.

```py
from espu import core

print(core.available())     # All known official components
print(core.installed())     # Components currently installed
print(core.unknown())       # Installed but unregistered components
```

If `core.unknown()` returns any entries, it is recommended to review them carefully.
Unrecognized packages inside the `espu` namespace may indicate unintended or potentially malicious code.

---

## Managing Installations

The ESPU GitHub repository contains a `management/` directory with helper scripts for maintaining an ESPU installation.

This folder includes:
- a `.sh` script (Unix / Linux / macOS)
- a `.bat` script (Windows)
- a `.py` script (cross-platform)

These scripts are capable of:
- detecting which ESPU components are currently installed
- cleanly uninstalling all ESPU-related packages
- upgrading to newer versions without manual package management pain

They are intended as convenience tools and are **not required** for normal usage although heavily recommended.

---

# Uninstalling Extensions or Libraries

Extras are **install-time only**. To remove functionality, uninstall the underlying package directly:

```bash
pip uninstall espu-ext-bezier
pip uninstall espu-lib-vector
```

Or use one of the managing scripts mentioned above.

The core package (`espu`) will remain installed unless explicitly removed.

---

## Versioning

All ESPU packages share the same version number.
While this may seem unusual, it is intentional.

Using a single version across the core, extensions and libraries:
- simplifies dependency management
- avoids compatibility mismatches
- allows predictable upgrades
- reduces long-term maintenance overhead

This trade-off favors clarity and stability over fine-grained versioning.

---
## Resources
[Changelog](./CHANGELOG.md)

~~[Documentation](./DOCUMENTATION.md)~~ Please be patient as i am working on the documentation.

---

## License

MIT License
© EscapedShadows
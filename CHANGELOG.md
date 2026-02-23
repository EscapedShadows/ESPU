## 0.1.2

Fixed:
- Minor bug in the logger module that required a logger to be initialized with a template. Now it works without one and defaults to just the message.
- Minor spelling mistakes in the changelog.
- Typos and grammar issues in docstrings and comments (logger).
- Corrected inconsistent parameter type documentation in handler docstrings (logger).

## 0.1.1

Changed:
- Removed a section of README.md because it is currently irrelevant.

Removed:
- Build and publish script.

## 0.1.0

Added:
- Custom exceptions.

Fixed:
- `QuadraticBezierCurve` did not have `_baked` set, causing an error when calling `resolve_uniform` before baking.

Changed:
- Now using custom exceptions.
- Renamed bezier helpers to utils.
- Renamed `Points` to `points` in the `bezier/curve.py` file.
- Added source reference to `bezier/curve.py`.
- Removed a small section of comment in `wol/win_adapters.py`.

Notes:
- First structured release.

## 0.0.2 & 0.0.3

Fixed:
- Registry JSON file missing in the wheel.
- Missing placeholders in pyproject templates.

Changed:
- Removed force TestPyPI upload.
- Updated README templates.

## 0.0.1

Initial monorepo.
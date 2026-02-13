## 0.1.1

Changed:
- Removed section of README.md because it currently is irrelevant

Removed:
- Build and Publish script

## 0.1.0

Added:
- Added custom exceptions

Fixed:
- QuadraticBezierCurve not having _baked set causing an error when calling resolve_uniform before baking

Changed:
- Now using custom Exceptions
- Renamed bezier helpers to utils
- Renamed `Points` to `points` in the `bezier/curve.py` file
- Added source reference to `bezier/curve.py`
- Removed a small section of comment in `wol/win_adapters.py`

Notes:
- First structured release

## 0.0.2 & 0.0.3

Fixed:
- Registry JSON file missing in wheel
- Missing placeholders in pyproject templates

Changed:
- Removed force TestPyPI upload
- Updated README templates

## 0.0.1

Initial Monorepo
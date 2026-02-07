# Formatter
#
# The Formatter class compiles a template into a sequence of callable
# functions and static strings. When called, it stitches together the
# static parts with the result of the dynamic parts. The Formatter
# never allocates per log call and only computes the data that the
# template requires.
#
# Each dynamic accessor is a small nested function that closes over
# exactly the variable it needs. These accessors are compiled once
# when the Formatter is created. On each log call the Formatter
# iterates through its static/dynamic parts and builds the final string.

import re
import datetime
from .config import LEVEL_MAPPINGS, LEVEL_NAMES
from .utils import basename

class Formatter:
    """Compile a logging template into a callable formatter.

    Parameters
    ----------
    template: str
        A string containing double-brace expressions to be replaced at
        runtime. Static text outside of braces is copied directly into
        the output. Expressions support dot access (e.g. "log_level.up")
        and optional format specifiers separated by a colon.
    start_time: float
        The time when the top-level Logger was created. This is used
        for computing elapsed time via "time_since_start".

    The compiled formatter can be reused safely across log calls and
    requires no per-call state beyond the frame and optional timestamp passed in.
    """

    # Precompiled regex to find all dynamic expressions within "{{...}}"
    _PATTERN = re.compile(r"\{\{(.*?)\}\}")

    __slots__ = (
        "template",
        "start_time",
        "requires_time",
        "requires_thread",
        "_static_parts",
        "_dyn_parts"
    )

    def __init__(self, template: str, start_time: float) -> None:
        self.template = template
        # The loggers start time is needed for time_since_start calculations
        self.start_time = start_time

        # These flags indicate whether the template uses certain values.
        # They allow the Logger to avoid computing data that is not used.
        self.requires_time: bool = False
        self.requires_thread: bool = False

        # Parsed output plan. "_static_parts" holds the literal strings and
        # "_dyn_parts" holds the callable accessors. The two lists have the
        # same length: static parts at index i correspond to dynamic parts
        # at index i
        self._static_parts: list[str] = []
        self._dyn_parts: list[callable | None] = []

        self._compile_template()

    def _compile_template(self) -> None:
        """Parse the template and produce lists of static and dynamic parts."""
        static_parts: list[str] = []
        dyn_parts: list[callable | None] = []
        last = 0
        for match in self._PATTERN.finditer(self.template):
            # Append any literal text before the expression.
            if match.start() > last:
                static_parts.append(self.template[last : match.start()])
                dyn_parts.append(None)
            # Extract the expression (strip whitespace to allow "{{ msg }}" etc.)
            expr = match.group(1).strip()
            static_parts.append("")
            dyn_parts.append(self._compile_expr(expr))
            last = match.end()
        # Append any trailing literal text
        if last < len(self.template):
            static_parts.append(self.template[last:])
            dyn_parts.append(None)
        self._static_parts = static_parts
        self._dyn_parts = dyn_parts

    def _compile_expr(self, expr: str) -> callable:
        """Compile a single dynamic expression into an accessor function."""
        # Special case: "ctime.format('%Y-%m-%d %H:%M:%S')"
        if expr.startswith("ctime.format(") and expr.endswith(")"):
            # Any template using ctime must compute a timestamp on log call
            self.requires_time = True
            # Extract the format string inside the parentheses and strip quotes
            fmt = expr[len("ctime.format(") : -1].strip().strip("'\"")

            def accessor(msg, level, levelname, frame, created, thread_name, _fmt=fmt):
                # Use created (passed in at call time) to format as a datetime
                return datetime.datetime.fromtimestamp(created).strftime(_fmt)
            
            return accessor
        
        # Special case: "time_since_start.format('.3f')"
        if expr.startswith("time_since_start.format(") and expr.endswith(")"):
            self.requires_time = True
            fmt_spec = expr[len("time_since_start.format(") : -1].strip().strip("'\"")
            # Build a format string for the elapsed time
            fmt = "{" + ":" + fmt_spec + "}" if fmt_spec else "{}"

            def accessor(msg, level, levelname, frame, created, thread_name, _fmt=fmt):
                return _fmt.format(created - self.start_time)
            
            return accessor
        
        # Split expression on colon to support format specs (e.g. "{{ lineno:04d }}")
        if ":" in expr:
            key_expr, fmt_spec = expr.split(":", 1)
            key_expr = key_expr.strip()
            fmt = "{" + ":" + fmt_spec.strip() + "}"
        else:
            key_expr = expr.strip()
            fmt = None

        # Expressions can contain dot notation (e.g. "log_level.up")
        # Split on periods and compile getters for each part
        parts = key_expr.split(".")
        root = parts[0]

        # Mark capability flags based on the root. This allows the
        # Logger to avoid computing thread or time if the template
        # doesnt need them.
        if root in ("ctime", "time_since_start"):
            self.requires_time = True
        if root == "threadName":
            self.requires_thread = True

        # Precompile a getter for the root. This closure returns the
        # base value before applying any dot path or formatting.
        root_getter = self._compile_root_getter(root)

        # If there are further parts after the root (dot notation)
        # compile a resolver for the tail. The resolver navigates
        # through attributes or dictionary keys as needed.
        if len(parts) > 1:
            tail = parts[1:]

            def resolve_tail(value):
                for part in tail:
                    if value is None:
                        return None
                    # Support dict lookup for dictionary values.
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = getattr(value, part, None)
                return value
            
            if fmt is None:
                def accessor(msg, level, levelname, frame, created, thread_name, _rg=root_getter, _rt=resolve_tail):
                    v = _rt(_rg(msg, level, levelname, frame, created, thread_name))
                    return "<invalid>" if v is None else str(v)
                return accessor
            else:
                def accessor(msg, level, levelname, frame, created, thread_name, _rg=root_getter, _rt=resolve_tail, _fmt=fmt):
                    v = _rt(_rg(msg, level, levelname, frame, created, thread_name))
                    if v is None:
                        return "<invalid>"
                    try:
                        return _fmt.format(v)
                    except Exception:
                        return "<format_error>"
                return accessor
            
        # No dot notation, just a simple root accessor
        if fmt is None:
            def accessor(msg, level, levelname, frame, created, thread_name, _rg=root_getter):
                v = _rg(msg, level, levelname, frame, created, thread_name)
                return "<invalid>" if v is None else str(v)
            return accessor
        else:
            def accessor(msg, level, levelname, frame, created, thread_name, _rg=root_getter, _fmt=fmt):
                v = _rg(msg, level, levelname, frame, created, thread_name)
                if v is None:
                    return "<invalid>"
                try:
                    return _fmt.format(v)
                except Exception:
                    return "<format_error>"
            return accessor
    
    def _compile_root_getter(self, key: str) -> callable:
        """Return a function that fetches the root value for a given key.
        
        This function does only the minimal work needed to get the value
        required by the template. More complicated resolution (dot navigation)
        happens in the caller if necessary.
        """
        if key == "msg":
            # Return the message passed to the log call
            def get(msg, level, levelname, frame, created, thread_name):
                return msg
            return get
        if key == "log_level":
            # Return the mapping for the level (low, up, case).
            # Look up the levelname in the precomputed dictionary.
            # If not found, fall back to computing on the fly.
            def get(msg, level, levelname, frame, created, thread_name):
                return LEVEL_MAPPINGS.get(
                    levelname,
                    {
                        "low": levelname.lower(),
                        "up": levelname.upper(),
                        "case": levelname.capitalize()
                    }
                )
            return get
        if key == "ctime":
            # Return a datetime object from the timestamp passed in.
            # Note that created may be None if requires_time was false,
            # but this should never be called in that case because the
            # accessor is only present when requires_time is True.
            def get(msg, level, levelname, frame, created, thread_name):
                return datetime.datetime.fromtimestamp(created)
            return get
        if key == "time_since_start":
            # Compute elapsed time relative to the loggers start time
            def get(msg, level, levelname, frame, created, thread_name):
                return created - self.start_time
            return get
        if key == "filename":
            # Extracts just the base name from the frames code file
            def get(msg, level, levelname, frame, created, thread_name):
                return basename(frame.f_code.co_filename)
            return get
        if key == "pathname":
            # Full path of the current source file
            def get(msg, level, levelname, frame, created, thread_name):
                return frame.f_code.co_filename
            return get
        if key == "lineno":
            # Current line number in the source
            def get(msg, level, levelname, frame, created, thread_name):
                return frame.f_lineno
            return get
        if key == "funcName":
            # Name of the current function
            def get(msg, level, levelname, frame, created, thread_name):
                return frame.f_code.co_name
            return get
        if key == "threadName":
            # Fetch thread name lazily in the caller and pass it as
            # thread_name argument, so the getter just returns that.
            def get(msg, level, levelname, frame, created, thread_name):
                return thread_name
            return get
        # Default: unknown key returns None which will be treated as invalid
        def get(msg, level, levelname, frame, created, thread_name):
            return None
        return get
    
    def format(self, msg: str, level: int, frame, created: float | None, thread_name: str | None) -> str:
        """Assemble the final log line from static parts and dynamic accessors.

        Parameters
        ----------
        msg: str
            The message passed to the log call.
        level: int
            Numeric log level (DEBUG, INFO, etc.).
        frame: types.FrameType
            The call site frame captured by the Logger.
        created: float or None
            Time timestamp (seconds since epoch) captured
            by the Logger if any handler requires time.
            Otherwise None.
        thread_name: str or None
            The name of the current thread if required.
            Otherwise None.

        Returns
        -------
        str
            The formatted log line ready to be used.
        """
        # Lookup the level name once. If the level isnt in the map,
        # fall back to INFO.
        levelname = LEVEL_NAMES.get(level, "INFO")

        # Build the output by interleaving static strings and dynamic values
        parts: list[str] = []
        for static, dyn in zip(self._static_parts, self._dyn_parts):
            if static:
                parts.append(static)
            if dyn is not None:
                # dynamic accessor returns a string (or placeholder if None)
                parts.append(dyn(msg, level, levelname, frame, created, thread_name))
        return "".join(parts)
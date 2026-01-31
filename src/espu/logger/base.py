# Base handler and concrete handlers
#
# A handler owns a Formatter and knows how to output the formatted
# string. The base handler enforces level filtering and stores the
# formatter. Concrete handlers implement the "emit" method for the
# actual I/O (terminal, file). Handlers expose two flags to indicate
# whether the template requires the current time or thread name.
# These flags allow the Logger to skip expensive calls when they
# are unnecessary.

from .formatter import Formatter

class BaseHandler:
    """Base class for all handlers.

    Parameters
    ----------
    level: int
        Minimum log level for this handler. Messages below this level
        are discarded early.
    formatter: Formatter
        The compiled formatter used to render log messages.
    """

    __slots__ = ("level", "formatter")

    def __init__(self, *, level: int, formatter: Formatter) -> None:
        self.level = level
        self.formatter = formatter

    @property
    def requires_time(self) -> bool:
        return self.formatter.requires_time
    
    @property
    def requires_thread(self) -> bool:
        return self.formatter.requires_thread
    
    def handle(self, msg: str, level: int, frame, created: float | None, thread_name: str | None) -> None:
        """Entry point for the Logger.

        The Logger calls this method once per attached handler on every
        log call. If the log level is below the handlers threshold
        nothing happens. Otherwise it delegates to "emit" which does
        the actual I/O
        """
        if level < self.level:
            # Fast path: ignore messages below this handlers level.
            return
        self.emit(msg, level, frame, created, thread_name)

    def emit(self, msg: str, level: int, frame, created: float | None, thread_name: str | None) -> None:
        """Emit a single formatted log line. Must be overwritten by subclasses."""
        raise NotImplementedError
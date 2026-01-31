from .base import BaseHandler
from .config import DEBUG, INFO, WARNING, ERROR, CRITICAL
from .formatter import Formatter
import sys
import time
import threading

class TerminalLogger(BaseHandler):
    """Handler that writes log messages to a text stream (stdout by default)
    
    Parameters
    ----------
    template: str
        Logging template for this handler. See Formatter for details.
    start_time: float
        The start time of the parent Logger. Passed into the Formatter.
    level: int, optional
        Minimum log level for this handler (default: INFO).
    stream: Text I/O, optional
        The output stream (defaults to sys.stdout). Any object with a
        "write(str)" method will work.
    flush: bool, optional
        Whether to flush the stream after each write. Flushing can
        reduce performance but is useful in REPLs or when logs must
        appear immediately (default: False).
    """

    __slots__ = ("stream", "flush")

    def __init__(self, *, template: str, level: int = INFO, stream=None, flush: bool = False, start_time: float | None = None) -> None:
        """Create a terminal handler.

        Parameters
        ----------
        template: str
            Logging template for this handler. See Formatter for details.
        start_time: float
            The start time of the parent Logger. Passed into the Formatter.
        level: int, optional
            Minimum log level for this handler (default: INFO).
        stream: Text I/O, optional
            The output stream (defaults to sys.stdout). Any object with a
            "write(str)" method will work.
        flush: bool, optional
            Whether to flush the stream after each write. Flushing can
            reduce performance but is useful in REPLs or when log must
            appear immediately (default: False).
        """
        if start_time is None:
            start_time = time.time()
        formatter = Formatter(template=template, start_time=start_time)
        super().__init__(level=level, formatter=formatter)
        self.stream = stream if stream is not None else sys.stdout
        self.flush = flush

    def emit(self, msg: str, level: int, frame, created: float | None, thread_name: str | None) -> None:
        line = self.formatter.format(msg, level, frame, created, thread_name)
        self.stream.write(line + "\n")
        if self.flush:
            self.stream.flush()

class FileLogger(BaseHandler):
    """Handler that writes log messages to a file with optional buffering.

    Parameters
    ----------
    filename: str, optional
        Path to the file to open. Defaults to "app.log". If the file
        does not exist it will be created. If the file exists and mode
        is "w" it will be truncated.
    template: str
        Logging template for this handler. See Formatter for details.
    start_time: float
        The start time of the parent Logger. Passed into the Formatter.
    level: int, optional
        Minimum log level for this handler (default: INFO).
    mode: str, optional
        File mode (default: "w"). Any valid Python file mode
        for text files can be used.
    encoding: str | None, optional
        Encoding used when opening file. Defaults to "utf-8".
    buffer_size: int, optional
        Number of log calls to buffer before writing to disk.
        A Value of 1 disables buffering (immediate write). Larger
        values improve I/O throughput at the cost of delaying logs (default: 5).
    """

    __slots__ = ("file", "buffer_size", "buffer", "closed")

    def __init__(self, *, filename: str = "app.log", template: str, level: int = INFO, mode: str = "w", encoding: str | None = "utf-8", buffer_size: int = 5, start_time: float | None = None) -> None:
        """Create a file handler.
        
        Parameters
        ----------
        filename: str, optional
            Path to the file to open. Defaults to "app.log". If the file
            does not exist it will be created. If the file exists and mode
            is "w" it will be truncated.
        template: str
            Logging template for this handler. See Formatter for details.
        start_time: float
            The start time of the parent Logger. Passed into the Formatter.
        level: int, optional
            Minimum log level for this handler (default: INFO).
        mode: str, optional
            File mode (default: "w"). Any valid Python file mode
            for text files can be used.
        encoding: str | None, optional
            Encoding used when opening file. Defaults to "utf-8".
        buffer_size: int, optional
            Number of log calls to buffer before writing to disk.
            A Value of 1 disables buffering (immediate write). Larger
            values improve I/O throughput at the cost of delaying logs (default: 5).
        """
        if start_time is None:
            start_time = time.time()
        formatter = Formatter(template=template, start_time=start_time)
        super().__init__(level=level, formatter=formatter)
        self.file = open(filename, mode, encoding=encoding)
        # Ensure buffer_size is at least 1. A buffer_size of 1 means
        # write after every log call. Larger values batch writes.
        self.buffer_size = 1 if buffer_size <= 1 else buffer_size
        self.buffer: list[str] = []
        self.closed: bool = False

    def emit(self, msg: str, level: int, frame, created: float | None, thread_name: str | None) -> None:
        if self.closed:
            return
        line = self.formatter.format(msg, level, frame, created, thread_name)
        self.buffer.append(line)
        # Flush to disk when the buffer reaches the configured size
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        """Write any buffered log lines to disk and clear the buffer."""
        if self.closed:
            return
        if not self.buffer:
            return
        # Joining with newline once per flush reduces the number of write calls
        self.file.write("\n".join(self.buffer) + "\n")
        self.file.flush()
        self.buffer.clear()

    def close(self) -> None:
        """Flush any pending logs and close the file."""
        if self.closed:
            return
        try:
            self.flush()
        finally:
            try:
                self.file.close()
            finally:
                self.closed = True

# Logger (top-level)
#
# The Logger coordinates log calls, level filtering and fan-out to
# handlers. The Logger itself performs no formatting and knows
# nothing about templates. It captures the call site frame and,
# if necessary, the current timestamp and thread name. It then
# passes these raw values to each attached handler to format and
# output.
#
# A Logger instance is intended to be reused for the lifetime of
# your application. Attaching or detaching handlers at runtime is
# inexpensive, but attachments should normally happen once during
# startup.

class Logger:
    """Simple logging coordinator with handler fan-out and level filtering.
    
    Parameters
    ----------
    level: int, optional
        Messages with a level below this threshold are ignored entirely by
        the logger. Default is INFO (20).
    """

    __slots__ = (
        "name",
        "level",
        "start_time",
        "_handlers",
        "_needs_time",
        "_needs_thread"
    )

    def __init__(self, level: int = INFO) -> None:
        self.level = level
        # Capture the creation time of the Logger for elapsed time templates
        self.start_time = time.time()
        # Handlers will be stored in a simple list. Order matters for
        # file/terminal ordering but has no functional effect.
        self._handlers: list[BaseHandler] = []
        # Internal flags to memoize whether any handler needs time or thread
        self._needs_time: bool = False
        self._needs_thread: bool = False

    def attach(self, handler: BaseHandler) -> None:
        """Add a handler to this logger.
        
        The logger will call the handler for every log message.
        If the same handler is attached multiple times it will
        receive duplicate log messages.
        """
        self._handlers.append(handler)
        try:
            handler.formatter.start_time = self.start_time
        except AttributeError:
            pass
        # Recalculate what data is needs to be captured on each log call
        self._recalc_needs()

    def detach(self, handler: BaseHandler) -> None:
        """Remove a handler from this logger if present."""
        try:
            self._handlers.remove(handler)
        except ValueError:
            return
        self._recalc_needs()

    def _recalc_needs(self) -> None:
        """Determine whether any attached handler requires time or thread."""
        needs_time = False
        needs_thread = False
        for h in self._handlers:
            # Simply OR together the flags from all handlers. If any
            # handler needs a value, compute it once per log call.
            needs_time |= h.requires_time
            needs_thread |= h.requires_thread
        self._needs_time = needs_time
        self._needs_thread = needs_thread

    def _log(self, level: int, msg: str) -> None:
        """Dispatch a log message to all attached handlers."""
        if level < self.level:
            # Skip messages below the logger threshold
            return
        if not self._handlers:
            # If there are no handlers, there is nothing to do.
            return
        frame = sys._getframe(2)
        created: float | None = time.time() if self._needs_time else None
        thread_name: str | None = (
            threading.current_thread().name if self._needs_thread else None
        )
        # Fan out to handlers. Each handler performs its own logic.
        for handler in self._handlers:
            handler.handle(msg, level, frame, created, thread_name)

    # Convenience methods for each log level. These simply call _log
    # with the appropriate level constant. The docstring on info() is
    # representative for all other level methods.
    def debug(self, msg: str) -> None:
        """Log a message with severity DEBUG."""
        self._log(DEBUG, msg)
    
    def info(self, msg: str) -> None:
        """Log a message with severity INFO."""
        self._log(INFO, msg)

    def warning(self, msg: str) -> None:
        """Log a message with severity WARNING."""
        self._log(WARNING, msg)

    def error(self, msg: str) -> None:
        """Log a message with severity ERROR."""
        self._log(ERROR, msg)

    def critical(self, msg: str) -> None:
        """Log a message with severity CRITICAL."""
        self._log(CRITICAL, msg)
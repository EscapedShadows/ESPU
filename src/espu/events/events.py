from contextlib import contextmanager

class Events:
    """
    Simple synchronous event dispatcher.
    """
    def __init__(self):
        # Dict structure:
        # {
        #   "event_name": [fn1, fn2, fn3, ...]
        # }
        self._handlers = {}

    def on(self, name, fn):
        """
        Registers a handler that is called every time the event is emitted.
        """
        self._handlers.setdefault(name, []).append(fn)
        return fn   # allows decorator usage
    
    def off(self, name, fn=None):
        """
        Removes handlers for an event.

        off(name, fn)   -> remove a specific handler
        off(name)       -> remove ALL handlers for that event
        """
        if fn is None:
            # Remove the entire event entry
            self._handlers.pop(name, None)
            return
        
        handlers = self._handlers.get(name)
        if not handlers:
            return
        
        try:
            handlers.remove(fn)
        except ValueError:
            pass

        # Clean up empty lists
        if not handlers:
            self._handlers.pop(name, None)
    
    def once(self, name, fn):
        """
        Register a handler that runs once,
        then unregisters itself.
        """

        # Register a wrapper NOT fn directly
        def wrapper(*args, **kwargs):
            # Remove the wrapper before calling fn
            self.off(name, wrapper)
            return fn(*args, **kwargs)
        
        self.on(name, wrapper)
        return fn
    
    def emit(self, name, *args, **kwargs):
        """
        Emit an event and call all registered handlers.
        """

        # Copy the list so handlers can modify registration safely
        for fn in list(self._handlers.get(name, [])):
            fn(*args, **kwargs)

    # Decorators
    def on_event(self, name):
        """
        Decorator version of .on()
        """
        def decorator(fn):
            self.on(name, fn)
            return fn
        return decorator
    
    def once_event(self, name):
        """
        Decorator version of .once()
        """
        def decorator(fn):
            self.once(name, fn)
            return fn
        return decorator
    
    # Scoped handlers
    @contextmanager
    def scope(self):
        """
        Temporarily register handlers inside a context.

        All handlers registered inside the scope
        are automatically removed when exiting.
        """
        snapshot = {
            name: list(handlers)
            for name, handlers in self._handlers.items()
        }

        try:
            yield
        finally:
            self._handlers = snapshot

    @contextmanager
    def isolated_scope(self):
        """
        Temporarily register handlers inside an empty context.

        All handlers registered inside the scope are automatically
        removed when exiting and the original is restored.
        """
        snapshot = {
            name: list(handlers)
            for name, handlers in self._handlers.items()
        }

        self._handlers = {}
        try:
            yield
        finally:
            self._handlers = snapshot
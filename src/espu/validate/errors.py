class ValidationError(Exception):
    def __init__(self, *, expected=None, actual=None, message=None):
        self.expected = expected
        self.actual = actual
        self.message = message

        super().__init__(self._format)

    def _format(self):
        parts = []

        if self.expected:
            parts.append(f"expected {self.expected}")
        
        if self.actual:
            parts.append(f"got {self.actual}")

        if self.message:
            parts.append(self.message)

        return ", ".join(parts) or "unknown error"
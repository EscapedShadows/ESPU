from .errors import ValidationError

class Check:
    def __init__(self, _value):
        self._value = _value

    def _require(self, condition, *, expected):
        if not condition:
            raise ValidationError(
                expected=expected,
                actual=self._value
            )
        return self

    # A lot of repetition
    def is_int(self):
        return self._require(
            isinstance(self._value, int) and not isinstance(self._value, bool),
            expected="int"
        )
    
    def is_float(self):
        return self._require(
            isinstance(self._value, float),
            expected="float"
        )
    
    def is_str(self):
        return self._require(
            isinstance(self._value, str),
            expected="str"
        )
    
    def is_bool(self):
        return self._require(
            isinstance(self._value, bool),
            expected="bool"
        )
    
    def is_list(self):
        return self._require(
            isinstance(self._value, list),
            expected="list"
        )
    
    def is_tuple(self):
        return self._require(
            isinstance(self._value, tuple),
            expected="tuple"
        )
    
    def is_dict(self):
        return self._require(
            isinstance(self._value, dict),
            expected="dict"
        )
    
    def is_callable(self):
        return self._require(
            callable(self._value),
            expected="callable"
        )
    
    def is_instance(self, cls):
        return self._require(
            isinstance(self._value, cls),
            expected=f"instance of {cls.__name__}"
        )
    
    # Safeguards
    def _require_number(self):
        return self._require(
            isinstance(self._value, (int, float)) and not isinstance(self._value, bool),
            expected="number"
        )
    
    def _require_len(self):
        return self._require(
            hasattr(self._value, "__len__"),
            expected="object with length"
        )
    
    # Checking
    def min(self, n):
        self._require_number()
        if self._value < n:
            raise ValidationError(
                expected=f">= {n}",
                actual=self._value
            )
        return self
    
    def max(self, n):
        self._require_number()
        if self._value > n:
            raise ValidationError(
                expected=f"<= {n}",
                actual=self._value
            )
        return self
    
    def between(self, a, b):
        self._require_number()
        if self._value < a or self._value > b:
            raise ValidationError(
                expected=f"between {a} and {b}",
                actual=self._value
            )
        return self

    def len_min(self, n):
        self._require_len()
        if len(self._value) < n:
            raise ValidationError(
                expected=f"length >= {n}",
                actual=len(self._value)
            )
        return self
    
    def len_max(self, n):
        self._require_len()
        if len(self._value) > n:
            raise ValidationError(
                expected=f"length <= {n}",
                actual=len(self._value)
            )
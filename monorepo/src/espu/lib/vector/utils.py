import math

DEFAULT_EPSILON = 1e-9

def almost_equal(a: float, b: float, eps: float = DEFAULT_EPSILON) -> bool:
    return abs(a - b) <= eps

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))

def safe_div(value: float, divisor: float, default: float = 0.0) -> float:
    if abs(divisor) < DEFAULT_EPSILON:
        return default
    return value / divisor
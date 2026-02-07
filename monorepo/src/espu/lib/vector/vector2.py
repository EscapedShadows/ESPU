from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable
from .utils import DEFAULT_EPSILON, almost_equal, safe_div

@dataclass(frozen=True, slots=True)
class Vec2:
    x: float
    y: float

    @staticmethod
    def from_tuple(v: Iterable[float]) -> Vec2:
        x, y = v
        return Vec2(float(x), float(y))
    
    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)
    
    ZERO = None
    ONE = None
    UP = None
    DOWN = None
    LEFT = None
    RIGHT = None

    def __add__(self, o: Vec2) -> Vec2:
        return Vec2(self.x + o.x, self.y + o.y)
    
    def __sub__(self, o: Vec2) -> Vec2:
        return Vec2(self.x - o.x, self.y - o.y)
    
    def __mul__(self, s: float) -> Vec2:
        return Vec2(self.x * s, self.y * s)
    
    def __rmul__(self, s: float) -> Vec2:
        return self * s
    
    def __truediv__(self, s: float) -> Vec2:
        return Vec2(
            safe_div(self.x, s),
            safe_div(self.y, s)
        )
    
    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)
    
    def __iter__(self):
        yield self.x
        yield self.y

    def almost_equal(self, o: Vec2, eps: float = DEFAULT_EPSILON) -> bool:
        return (
            almost_equal(self.x, o.x, eps)
            and almost_equal(self.y, o.y, eps)
        )
    
    # geometry
    def dot(self, o: Vec2) -> float:
        return self.x * o.x + self.y * o.y
    
    def length_sq(self) -> float:
        return self.dot(self)
    
    def length(self) -> float:
        return math.sqrt(self.length_sq())
    
    def distance_sq(self, o: Vec2) -> float:
        return (self - o).length_sq()
    
    def distance(self, o: Vec2) -> float:
        return math.sqrt(self.distance_sq(o))
    
    def normalize(self) -> Vec2:
        l = self.length()
        if l < DEFAULT_EPSILON:
            return Vec2.ZERO
        return self / l
    
    def clamp_length(self, max_len: float) -> Vec2:
        l = self.length()
        if l <= max_len:
            return self
        return self.normalize() * max_len
    
    def lerp(self, o: Vec2, t: float) -> Vec2:
        return Vec2(
            self.x + (o.x - self.x) * t,
            self.y + (o.y - self.y) * t
        )
    
    def perp(self) -> Vec2:
        return Vec2(-self.y, self.x)
    
    def angle(self) -> float:
        return math.atan2(self.y, self.x)
    
    def rotate(self, radians: float) -> Vec2:
        c = math.cos(radians)
        s = math.sin(radians)
        return Vec2(
            self.x * c - self.y * s,
            self.x * s + self.y * c
        )
    
Vec2.ZERO = Vec2(0.0, 0.0)
Vec2.ONE = Vec2(1.0, 1.0)
Vec2.UP = Vec2(0.0, 1.0)
Vec2.DOWN = Vec2(0.0, -1.0)
Vec2.LEFT = Vec2(-1.0, 0.0)
Vec2.RIGHT = Vec2(1.0, 0.0)
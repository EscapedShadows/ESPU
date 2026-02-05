from .base import Point
from .helpers import quadratic_roots, curvature_from_derivatives, lerp, t_at_arc_length, build_arc_table
from typing import Tuple

# According to the Bernstein Polynomial Form
# https://en.wikipedia.org/wiki/Bernstein_polynomial

class LinearBezierCurve:
    def __init__(self, P1: Point, P2: Point):
        self.P1 = P1
        self.P2 = P2

    def resolve(self, t: float) -> Point:
        return lerp(self.P1, self.P2, t)
    
    def derivative(self) -> Point:
        return self.P2 - self.P1
    
    def bounding_box(self) -> Tuple[float, float, float, float]:
        xs = [self.P1.x, self.P2.x]
        ys = [self.P1.y, self.P2.y]
        return min(xs), min(ys), max(xs), max(ys)

class QuadraticBezierCurve:
    def __init__(self, P1: Point, P2: Point, P3: Point):
        self.P1 = P1
        self.P2 = P2
        self.P3 = P3

    def resolve(self, t: float) -> Point:
        u = 1.0 - t
        return (
            self.P1 * (u * u)
            + self.P2 * (2 * u * t)
            + self.P3 * (t * t)
        )
    
    def derivative(self) -> LinearBezierCurve:
        return LinearBezierCurve(
            2 * (self.P2 - self.P1),
            2 * (self.P3 - self.P2)
        )
    
    def bounding_box(self) -> Tuple[float, float, float, float]:
        points = [
            self.resolve(0.0),
            self.resolve(1.0)
        ]

        # derivative is linear
        d = self.derivative()

        def axis_root(a, b):
            denom = a - b
            if abs(denom) < 1e-9:
                return None
            t = a / denom
            return t if 0.0 < t < 1.0 else None
        
        tx = axis_root(d.P1.x, d.P2.x)
        ty = axis_root(d.P1.y, d.P2.y)

        if tx is not None:
            points.append(self.resolve(tx))
        if ty is not None:
            points.append(self.resolve(ty))

        xs = [p.x for p in points]
        ys = [p.y for p in points]

        return min(xs), min(ys), max(xs), max(ys)
    
    def curvature(self, t: float, d1: LinearBezierCurve, d2: Point) -> float:
        v = d1.resolve(t)
        return curvature_from_derivatives(v, d2)
    
    def bake(self, steps: int = 32):
        self._arc_table = build_arc_table(self, steps)
        self._arc_length = self._arc_table[-1][1]
        self._baked = True

    def resolve_uniform(self, u: float) -> Point:
        if not self._baked:
            raise RuntimeError("Curve must be baked before uniform evaluation")
        s = u * self._arc_length
        t = t_at_arc_length(self, s)
        return self.resolve(t)

class CubicBezierCurve:
    def __init__(self, P1: Point, P2: Point, P3: Point, P4: Point):
        self.P1 = P1
        self.P2 = P2
        self.P3 = P3
        self.P4 = P4
        self._baked = False

    def resolve(self, t: float) -> Point:
        u = 1.0 - t
        return (
            self.P1 * (u*u*u)
            + self.P2 * (3*u*u*t)
            + self.P3 * (3*u*t*t)
            + self.P4 * (t*t*t)
        )
    
    def derivative(self) -> QuadraticBezierCurve:
        return QuadraticBezierCurve(
            3 * (self.P2 - self.P1),
            3 * (self.P3 - self.P2),
            3 * (self.P4 - self.P3)
        )
    
    def bounding_box(self) -> Tuple[float, float, float, float]:
        points = [
            self.resolve(0.0),
            self.resolve(1.0)
        ]

        d = self.derivative()

        # Convert quadratic Bezier to power basis
        a = d.P1 - 2*d.P2 + d.P3
        b = 2*(d.P2 - d.P1)
        c = d.P1

        for t in quadratic_roots(a.x, b.x, c.x):
            if 0.0 < t < 1.0:
                points.append(self.resolve(t))
            
        for t in quadratic_roots(a.y, b.y, c.y):
            if 0.0 < t < 1.0:
                points.append(self.resolve(t))

        xs = [p.x for p in points]
        ys = [p.y for p in points]

        return min(xs), min(ys), max(xs), max(ys)
    
    def curvature(self, t: float, d1: QuadraticBezierCurve, d2: LinearBezierCurve) -> float:
        v = d1.resolve(t)
        a = d2.resolve(t)
        return curvature_from_derivatives(v, a)

    def bake(self, steps: int = 32):
        self._arc_table = build_arc_table(self, steps)
        self._arc_length = self._arc_table[-1][1]
        self._baked = True

    def resolve_uniform(self, u: float) -> Point:
        if not self._baked:
            raise RuntimeError("Curve must be baked before uniform evaluation")
        s = u * self._arc_length
        t = t_at_arc_length(self, s)
        return self.resolve(t)
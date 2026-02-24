import math
from espu.lib.vector import Vec2

def quadratic_roots(a, b, c):
    if abs(a) < 1e-9:
        if abs(b) < 1e-9:
            return []
        return [-c / b]
    
    disc = b * b - 4 * a * c
    if disc < 0:
        return []
    
    s = math.sqrt(disc)
    return [
        (-b + s) / (2 * a),
        (-b - s) / (2 * a)
    ]

def det(a: Vec2, b: Vec2) -> float:
    return a.x * b.y - a.y * b.x

def curvature_from_derivatives(v: Vec2, a: Vec2) -> float:
    speed = v.length()
    if speed == 0:
        return 0.0
    return det(v, a) / (speed ** 3)

def lerp(a , b, t: float):
    return a + (b - a) * t

def build_arc_table(obj, steps: int):
    table = []

    prev_point = obj.resolve(0.0)
    length = 0.0

    table.append((0.0, 0.0))

    for i in range(1, steps + 1):
        t = i / steps
        point = obj.resolve(t)
        length += (point - prev_point).length()
        table.append((t, length))
        prev_point = point

    return table
    
def t_at_arc_length(obj, s: float) -> float:
    table = obj._arc_table
    
    if s <= 0.0:
        return 0.0
    if s >= obj._arc_length:
        return 1.0
        
    lo = 0
    hi = len(table) - 1

    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if table[mid][1] < s:
            lo = mid
        else:
            hi = mid

    t0, s0 = table[lo]
    t1, s1 = table[hi]

    return t0 + (s - s0) * (t1 - t0) / (s1 - s0)
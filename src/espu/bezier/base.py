from dataclasses import dataclass
import math

@dataclass
class Point:
    x: float
    y: float

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> "Point":
        return Point(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar: float) -> "Point":
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float) -> "Point":
        return Point(self.x / scalar, self.y / scalar)
    
    def length(self) -> float:
        return math.hypot(self.x, self.y)
    
    def normalized(self) -> "Point":
        l = self.length()
        if l == 0:
            raise ValueError("Cannot normalize zero-length vector")
        return self / l
    
    def perpendicular(self) -> "Point":
        # 90° rotation (counter-clockwise)
        return Point(-self.y, self.x)
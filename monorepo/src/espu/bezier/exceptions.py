from espu.core import CoreError

class CurveNotBakedError(CoreError):
    """Raised when attempting to resolve_uniform() a curve before it has been baked."""
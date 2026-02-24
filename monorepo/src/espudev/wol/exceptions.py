from espu.core import CoreError

class InvalidMACFormat(CoreError):
    """Raised when a MAC address has an invalid format."""
    def __init__(self, mac: str):
        super().__init__(f"Invalid MAC Address format: {mac}")
        self.mac = mac

class GetAdaptersAddressesError(CoreError):
    """Raised when GetAdaptersAddresses fails for any reason."""
    def __init__(self, code: int):
        super().__init__(f"GetAdaptersAddresses failed with error code {code}")
        self.code = code

class AdapterBufferOverflow(CoreError):
    """Raised when the set buffer size was insufficient to hold all adapter data."""

class DuplicateIPError(CoreError):
    """Raised when multiple interfaces have the same IP address"""
    def __init__(self, address: str, interfaces: list):
        super().__init__(f"IP Address: {address} used by multiple interfaces: {interfaces}")
        self.address = address
        self.interfaces = interfaces

class ResolveInterfaceError(CoreError):
    """Raised when interface fails to resolve into IP and index"""
    def __init__(self, iface: str):
        super().__init__(f"Failed to resolve interface '{iface}' to IP and index")
        self.iface = iface
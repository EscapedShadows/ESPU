import socket
import struct
import platform
from .win_adapters import get_windows_adapters

# Magic packet according to
# https://www.amd.com/content/dam/amd/en/documents/archived-tech-docs/white-papers/20213.pdf
# Made from the MAC broadcast address (FF:FF:FF:FF:FF:FF) and the target MAC repeated 16 times
def build_magic_packet(mac_address: str) -> bytes:
    mac = mac_address.replace(":", "").replace("-", "").strip()
    if len(mac) != 12 or any(c not in "0123456789abcdefABCDEF" for c in mac):
        raise ValueError("Invalid MAC address format")
    return b"\xff" * 6 + bytes.fromhex(mac) * 16

def set_windows_unicast_if(sock: socket.socket, ifindex: int):
    IP_UNICAST_IF = 31  # undocumented but stable socket option
    sock.setsockopt(
        socket.IPPROTO_IP,
        IP_UNICAST_IF,
        struct.pack("!I", ifindex)
    )

# Resolve an interface name (eth0, enp7s0, whatever) to its IPv4 address on Unix systems.
# Uses the SIOCGIFADDR ioctl which directly asks the kernel for the address.
#
# This is simple, fast and sane unlike Windows.
def get_iface_ipv4_unix(ifname: str) -> str:
    import fcntl

    SIOCGIFADDR = 0x8915    # Unix ioctl code to resolve interface name to IP
    ifreq = struct.pack("256s", ifname.encode()[:15])
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        res = fcntl.ioctl(s.fileno(), SIOCGIFADDR, ifreq)
        # IPv4 address is at bytes 20-24 of the returned struct
        return socket.inet_ntoa(res[20:24])
    finally:
        s.close()

# Returns all interfaces that own an IPv4. Used if there is a weird setup
# where a device has two or more NICs on different networks that share
# the same IPv4 Address. Unlikely but its the entire reason i put
# myself trough the pain of working with Win32 API.
def get_ip_owners():
    owners = {}
    system = platform.system().lower()

    if system == "windows":
        # Call that Win32 API monster
        for a in get_windows_adapters():
            for ip in a["ips"]:
                owners.setdefault(ip, []).append(a["friendly"] or a["name"])
    else:
        import psutil
        for ifname, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    owners.setdefault(addr.address, []).append(ifname)
    
    return owners

# Resolves an interface name to:
#   its IPv4 address
#   and (on Windows) its interface index
def resolve_iface(iface: str):
    system = platform.system().lower()

    if system == "windows":
        for a in get_windows_adapters():
            if iface.lower() in (a["friendly"] or "").lower() or iface == a["name"]:
                # 169.254.x.x is APIPA (Automatic Private IP Addressing).
                # Basically meaning that Windows screwed up to get an IP.
                ip = next((i for i in a["ips"] if not i.startswith("169.254.")), None)
                return ip, a["ifindex"]
        return None, None
    else:
        return get_iface_ipv4_unix(iface), None
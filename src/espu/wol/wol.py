from .helpers import build_magic_packet, resolve_iface, set_windows_unicast_if, get_ip_owners
import platform
import socket

# Sends a Wake-on-LAN (WoL) packet with optional control over
# source IP and network interface.
def wake_on_lan(mac, dest_ip="255.255.255.255", port=9, src_ip=None, iface=None):
    """
    Send a Wake-on-LAN (WoL) magic packet to a target device.

    This function builds and sends a WoL magic packet for the given MAC
    address using UDP. It supports optional control over the source IP
    address and/or network interface, with platform-specific handling
    for Linux and Windows.

    Parameters
    ----------
    mac : str
        Target MAC address to wake (e.g. "AA:BB:CC:DD:EE:FF").
    dest_ip : str, optional
        Destination IP address to send the packet to. Defaults to the
        broadcast address "255.255.255.255".
    port : int, optional
        UDP destination port. Defaults to 9 (the standard WoL port).
    src_ip : str, optional
        Source IP address to bind the socket to. If provided, it must
        belong to exactly one network interface, otherwise an error
        is raised.
    iface : str, optional
        Network interface name to send the packet through. If specified,
        it overrides src_ip and is resolved to the appropriate source
        address and (on Windows) interface index.

    Raises
    ------
    RuntimeError
        If the provided source IP exists on multiple interfaces, or if
        the specified interface cannot be resolved.

    Notes
    -----
    - On Linux, the socket is bound to the interface using SO_BINDTODEVICE.
    - On Windows, the interface is selected using the unicast interface index.
    - The socket is always configured to allow broadcast packets.
    """
    # Haha... magic
    magic = build_magic_packet(mac)
    system = platform.system().lower()

    # If a source IP is provided make sure it belongs to exactly one interface
    if src_ip:
        owners = get_ip_owners()
        if src_ip in owners and len(owners[src_ip]) > 1:
            raise RuntimeError(
                f"Source IP {src_ip} exsts on multiple interfaces: {owners[src_ip]}. Refusing to guess. Use --iface instead."
            )
        
    win_ifindex = None
    if iface:
        src_ip, win_ifindex = resolve_iface(iface)
        if not src_ip:
            raise RuntimeError(f"Could not resolve interface: {iface}")
        
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Bind source IP if explicitly requested
        if src_ip:
            sock.bind((src_ip, 0))
        
        # Unix-style interface binding
        if iface and system == "linux":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, iface.encode())

        # Windows-style interface binding
        if win_ifindex and system == "windows":
            set_windows_unicast_if(sock, win_ifindex)

        sock.sendto(magic, (dest_ip, port))
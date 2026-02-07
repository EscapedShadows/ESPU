import socket

# Use the horrific Win32 API to get a list of Windows network adapters.
# This function asks Windows for a snapshot of all IPv4 adapters,
# then manually walks several linked lists inside a raw memory blob.
# I have gone trough the pain of commenting almost every line in here
# just so anyone reading this code has a shot of understanding what is going on here.
#
# Just a funfact:
# This entire 100+ line Monster exists purely because Windows doesnt accept
# interface names into sock.bind() directly unlike Unix. Gotta love it.
def get_windows_adapters(win_buffer_size: int) -> list:
    import ctypes
    from ctypes import wintypes

    # Address family constant for IPv4
    # This filters results so Windows only returns IPv4 addresses.
    AF_INET = 2

    # Flag telling Windows to include prefix information (subnet data).
    GAA_FLAG_INCLUDE_PREFIX = 0x0010

    # --- Low-level struct definitions ---
    #
    # These structs do NOT store data themselves.
    # They only describe how to interpret memory that Windows writes.

    # Windows wraps a sockaddr pointer + its size in this struct.
    # lpSockaddr points to a sockaddr_in (IPv4) in memory.
    class SOCKET_ADDRESS(ctypes.Structure):
        _fields_ = [
            ("lpSockaddr", ctypes.c_void_p),    # void* -> raw sockaddr bytes
            ("iSockaddrLength", ctypes.c_int)   # size of sockaddr struct
        ]

    # Forward declaration because this struct contains a pointer to itself
    # because this is required by Windows.
    class IP_ADAPTER_UNICAST_ADDRESS(ctypes.Structure):
        pass

    # Represents ONE unicast IP address on an adapter.
    # Windows links these together into a linked list.
    IP_ADAPTER_UNICAST_ADDRESS._fields_ = [
        ("Length", wintypes.ULONG),     # struct size / ABI versioning
        ("Flags", wintypes.DWORD),
        ("Next", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),   # pointer to the struct that represents the next IP in the linked list
        ("Address", SOCKET_ADDRESS)     # pointer to sockaddr
    ]

    # Forward declaration for adapter linked list
    class IP_ADAPTER_ADDRESSES(ctypes.Structure):
        pass

    # Represents ONE network adapter.
    # Windows once again returns a linked list of these.
    IP_ADAPTER_ADDRESSES._fields_ = [
    ("Length", wintypes.ULONG),         # struct size / ABI versioning
    ("IfIndex", wintypes.DWORD),        # IPv4 interface index
    ("Next", ctypes.POINTER(IP_ADAPTER_ADDRESSES)),     # next adapter
    ("AdapterName", ctypes.c_char_p),   # internal name (GUID-like)

    # These are not really needed but without them Windows crappy layout breaks
    # and returns unusable gibberish.
    ("FirstUnicastAddress", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
    ("FirstAnycastAddress", ctypes.c_void_p),
    ("FirstMulticastAddress", ctypes.c_void_p),
    ("FirstDnsServerAddress", ctypes.c_void_p),
    ("DnsSuffix", wintypes.LPWSTR),
    ("Description", wintypes.LPWSTR),

    ("FriendlyName", wintypes.LPWSTR)   # human-readable name
    ]

    # --- Bind the Win32 API ---
    #
    # GetAdaptersAddresses lives in iphlpapi.dll and expects the caller
    # to manage memory, buffer size and pointer traversal.
    GetAdaptersAddresses = ctypes.windll.iphlpapi.GetAdaptersAddresses
    GetAdaptersAddresses.argtypes = [
        wintypes.ULONG,                         # Address family (AF_INET)
        wintypes.ULONG,                         # Flags (unused -> 0)
        ctypes.c_void_p,                        # Reserved (must be NULL)
        ctypes.POINTER(IP_ADAPTER_ADDRESSES),   # Output buffer
        ctypes.POINTER(wintypes.ULONG)          # In/out buffer size
    ]

    # Im going to be honest here. Allocating 1MB of buffer (the default setting) is not how
    # this API is supposed to be used. In normal setups, 16KB is enough.
    # However i just want to make sure that even if someone has 100 Virtual Adapters
    # the buffer wont overflow. Plus 1MB of RAM in 2026 is really nothing.
    # The reason for that is that its very possible for the enviroment to be a Hyper-V
    # or something else that just naturally adds a lot of Network Adapters.
    # Hate it all you want but performance wise its basically 0 overhead.
    buf_len = wintypes.ULONG(win_buffer_size)
    buf = ctypes.create_string_buffer(buf_len.value)

    # Ask Windows to fill the buffer with adapter data
    ret = GetAdaptersAddresses(
        AF_INET,
        GAA_FLAG_INCLUDE_PREFIX,
        None,   # reserved
        ctypes.cast(buf, ctypes.POINTER(IP_ADAPTER_ADDRESSES)),
        ctypes.byref(buf_len)
    )

    # ERROR_BUFFER_OVERFLOW means even 1MB wasnt enough.
    # At this point something is seriously wrong with the system.
    if ret == 111:
        raise RuntimeError("1 MB buffer was not enough. Please rethink how many of the dozen Network Adapters you are using are actually needed.")
    elif ret != 0:
        raise OSError(f"GetAdaptersAddresses failed ({ret})")
    
    adapters = []

    # p points to the FIRST adapter struct at the start of the buffer.
    # From here on, everything is pointer chasing.
    p = ctypes.cast(buf, ctypes.POINTER(IP_ADAPTER_ADDRESSES))

    # Walk the adapter linked list
    while p:
        a = p.contents
        ips = []

        # Each adapter has a linked list of unicast IP addresses
        u = a.FirstUnicastAddress
        while u:
            # Copy the raw sockaddr bytes into Python memory
            raw = ctypes.string_at(
                u.contents.Address.lpSockaddr,
                u.contents.Address.iSockaddrLength
            )

            # sockaddr_in layout (IPv4):
            #   bytes 0-1: sin_family (AF_INET = 2)
            #   bytes 2-3: port (ignored)
            #   bytes 4-7: IPv4 address
            #
            # On little-endian Windows, raw[0] == AF_INET works reliably.
            if raw and raw[0] == AF_INET:
                ips.append(socket.inet_ntoa(raw[4:8]))

            # Move to the next IP node
            u = u.contents.Next

        # Convert this adapter into a sane Python structure
        adapters.append({
            "friendly": a.FriendlyName,     # Ethernet, WLAN, whatever
            "name": a.AdapterName.decode() if a.AdapterName else "",
            "ifindex": int(a.IfIndex),     # interface index
            "ips": ips                      # list of IPv4 strings
        })

        # Move to next adapter node
        p = a.Next
    
    return adapters
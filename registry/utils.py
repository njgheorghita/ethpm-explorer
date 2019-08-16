from eth_utils import humanize_hash, to_bytes, to_canonical_address


def humanize_address(addr: str):
    bytes_addr = to_canonical_address(addr)
    human_hash = humanize_hash(bytes_addr)
    return f"0x{human_hash}"

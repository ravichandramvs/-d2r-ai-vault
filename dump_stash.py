"""Read-only dump of shared-stash contents using parser-walked iteration.
Walks items by parsing each and advancing by exact bits consumed —
authoritative, no regex false positives."""
import re, os, struct, math
from config import STASH_FILE, TAB_SIG
from d2r_item_parser import parse_item
from item_names import load_code_info, load_unique_names, load_set_names, get_item_label


def walk_tab_items(tab_block):
    """Iterate true item DNAs in a tab by parser-driven length."""
    jm = tab_block.find(b'\x4A\x4D')
    if jm == -1:
        return
    count = struct.unpack('<H', tab_block[jm+2:jm+4])[0]
    if count == 0:
        return
    region = tab_block[jm+4:]
    cursor = 0  # byte offset in `region`
    for i in range(count):
        if cursor >= len(region):
            return
        # Items should start with 0x10 0x00 0x?0 0x00 — sanity check
        if region[cursor] != 0x10 or region[cursor+1] != 0x00:
            # Try to find next item-start signature
            m = re.search(b'\x10\x00[\x80\xA0\xC0]\x00.', region[cursor:])
            if not m:
                return
            cursor += m.start()
        # Parse to determine how many bytes this item occupies
        sub = region[cursor:].hex()
        try:
            p = parse_item(sub)
            consumed_bits = p.get('_consumed_bits')
            if consumed_bits is None:
                return
            consumed_bytes = math.ceil(consumed_bits / 8)
        except Exception:
            return
        yield region[cursor:cursor+consumed_bytes].hex(), p
        cursor += consumed_bytes


def main():
    if not os.path.exists(STASH_FILE):
        print(f"NO STASH FILE at: {STASH_FILE}")
        return
    print(f"Stash : {STASH_FILE}")
    print(f"Size  : {os.path.getsize(STASH_FILE)} bytes")
    with open(STASH_FILE, 'rb') as f:
        data = f.read()
    tab_offsets = [i for i in range(len(data)) if data[i:i+4] == TAB_SIG]
    print(f"Tabs  : {len(tab_offsets)}\n")

    code_info = load_code_info()
    uniq = load_unique_names()
    sets = load_set_names()

    for ti, start in enumerate(tab_offsets):
        end = tab_offsets[ti+1] if ti+1 < len(tab_offsets) else len(data)
        block = data[start:end]
        jm = block.find(b'\x4A\x4D')
        count = struct.unpack('<H', block[jm+2:jm+4])[0] if jm != -1 else 0
        print(f"=== Tab {ti+1}: JM-count={count} ===")
        for dna, p in walk_tab_items(block):
            try:
                lbl = get_item_label(p, code_info, uniq, sets)
                print(f"  {lbl}")
            except Exception as ex:
                print(f"  [label fail: {ex}]")
        print()


if __name__ == '__main__':
    main()

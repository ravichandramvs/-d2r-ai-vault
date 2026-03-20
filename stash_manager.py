"""
D2R AI Vault - Stash Manager
Commands: scan, status, wipe, inject

scan   - Collect items from stash/character into vault, update chronicle
status - Show vault stats
wipe   - Clear stash tabs (default: tabs 1-5)
inject - Place vault items into stash tabs with grid placement
"""
import os, binascii, json, re, sys, shutil
from datetime import datetime
from config import STASH_FILE, CHAR_FILE, VAULT_FILE, TAB_SIG, CHRONICLE_SIG, ITEM_START_RE

# Item sizes (width x height) for grid placement
ITEM_SIZES = {
    'dgr':(1,3),'dir':(1,3),'kri':(1,3),'bld':(1,3),
    'axe':(2,3),'hax':(1,3),'2ax':(2,3),'mpi':(1,3),
    'wnd':(1,2),'ywn':(1,2),'bwn':(1,2),'gwn':(1,2),
    'scp':(1,3),'gsc':(2,3),'wsp':(2,3),
    'mac':(1,3),'spc':(1,3),'fla':(2,3),'mst':(1,3),
    'ssd':(1,3),'scm':(1,3),'sbr':(1,3),'flc':(1,3),
    'bsd':(1,3),'lsd':(1,3),'wsd':(1,3),
    'clb':(1,3),'whm':(2,3),
    '9wn':(1,2),'9cl':(1,3),'9di':(1,3),'9dg':(1,3),
    '9sr':(2,4),'9la':(2,3),'9ss':(1,3),'9sb':(1,3),
    'mau':(2,4),'gma':(2,4),'pik':(2,4),
    'gix':(2,3),'hal':(2,4),'pax':(2,4),
    'gsd':(1,4),'2hs':(1,4),'clm':(1,4),'bsw':(1,4),
    'bar':(2,4),'vou':(2,4),'wsc':(2,4),'scy':(2,4),
    'cap':(2,2),'skp':(2,2),'hlm':(2,2),'fhl':(2,2),
    'ghm':(2,2),'crn':(2,2),'msk':(2,2),'bhm':(2,2),
    'ci0':(2,2),'ci1':(2,2),'ci2':(2,2),'ci3':(2,2),
    'lgl':(2,2),'vgl':(2,2),'mgl':(2,2),'tgl':(2,2),'hgl':(2,2),
    'lbt':(2,2),'vbt':(2,2),'mbt':(2,2),'tbt':(2,2),'hbt':(2,2),
    'lbl':(2,1),'vbl':(2,1),'mbl':(2,1),'tbl':(2,1),'hbl':(2,1),
    'buc':(2,2),'sml':(2,2),'lrg':(2,3),'kit':(2,3),
    'tow':(2,3),'gts':(2,4),'spk':(2,3),
    'lea':(2,3),'hla':(2,3),'stu':(2,3),'rng':(2,3),
    'scl':(2,3),'chn':(2,3),'brs':(2,3),'spl':(2,3),
    'plt':(2,3),'fld':(2,3),'gth':(2,3),'ful':(2,3),
    'aar':(2,3),'ltp':(2,3),'qui':(2,3),
    'xrg':(2,3),'xpk':(2,4),'xlg':(2,2),'xlb':(2,2),
    'xmg':(2,2),'zvb':(2,2),
    'rin':(1,1),'amu':(1,1),'jew':(1,1),
    'cm1':(1,1),'cm2':(1,1),'cm3':(1,1),
}


def backup():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    for p in [STASH_FILE, CHAR_FILE]:
        if os.path.exists(p):
            shutil.copy2(p, f"{p}.{ts}.bak")
    return ts


def load_vault():
    if os.path.exists(VAULT_FILE):
        return json.load(open(VAULT_FILE, 'r'))
    return {'items': [], 'materials': [], 'chronicle': []}


def save_vault(v):
    with open(VAULT_FILE, 'w') as f:
        json.dump(v, f, indent=4)


def scan_items(path, source):
    if not os.path.exists(path): return []
    with open(path, 'rb') as f: data = f.read()
    items = []
    starts = [m.start() for m in re.finditer(ITEM_START_RE, data)]
    for i in range(len(starts)):
        start = starts[i]
        end = starts[i+1] if i+1 < len(starts) else len(data)
        chunk = data[start:end]
        h_match = re.search(b'(\x4A\x4D|\x55\xAA\x55\xAA|\xC0\xED\xEA\xC0)', chunk[1:])
        if h_match: end = start + 1 + h_match.start()
        dna = data[start:end].hex()
        if len(dna) // 2 >= 25 or dna.startswith("1000a0"):
            items.append({'source': source, 'dna': dna})
    return items


def set_item_position(dna_hex, col, row, panel):
    """Set position bits in item DNA. Layout after 32 flag bits:
    3 bits version, 3 bits location(=0), 4 bits body_pos(=0),
    4 bits col, 4 bits row, 3 bits panel
    """
    raw = bytearray(binascii.unhexlify(dna_hex))
    bits = []
    for byte in raw:
        for i in range(8):
            bits.append((byte >> i) & 1)

    for i in range(35, 42):  # location + body_position = 0
        bits[i] = 0
    for i in range(4):
        bits[42 + i] = (col >> i) & 1
    for i in range(4):
        bits[46 + i] = (row >> i) & 1
    for i in range(3):
        bits[50 + i] = (panel >> i) & 1

    result = bytearray(len(raw))
    for byte_idx in range(len(raw)):
        val = 0
        for bit_idx in range(8):
            if byte_idx * 8 + bit_idx < len(bits):
                val |= bits[byte_idx * 8 + bit_idx] << bit_idx
        result[byte_idx] = val
    return result


def place_items_on_grid(codes, grid_w=10, grid_h=10):
    """Place items on a grid avoiding overlaps, returns list of (col, row)."""
    grid = [[False]*grid_h for _ in range(grid_w)]
    positions = []
    for code in codes:
        w, h = ITEM_SIZES.get(code, (2, 3))
        placed = False
        for y in range(grid_h - h + 1):
            for x in range(grid_w - w + 1):
                can_place = all(
                    not grid[x+dx][y+dy]
                    for dx in range(w) for dy in range(h)
                )
                if can_place:
                    for dx in range(w):
                        for dy in range(h):
                            grid[x+dx][y+dy] = True
                    positions.append((x, y))
                    placed = True
                    break
            if placed:
                break
        if not placed:
            print(f"  WARNING: Could not place {code} (size {w}x{h})")
            positions.append((0, 0))
    return positions


def cmd_scan():
    v = load_vault()
    existing_dna = {it['dna'] for it in v['items']} | {it['dna'] for it in v['materials']}

    new_stash = scan_items(STASH_FILE, "SharedStash")
    new_char = scan_items(CHAR_FILE, "Character")

    added = 0
    for it in new_stash + new_char:
        if it['dna'] not in existing_dna:
            if it['dna'].startswith("1000a0"):
                v['materials'].append(it)
            else:
                v['items'].append(it)
            added += 1

    # Update chronicle
    if os.path.exists(STASH_FILE):
        with open(STASH_FILE, 'rb') as f: data = f.read()
        match = re.search(CHRONICLE_SIG, data)
        if match:
            start = match.start() + 24
            existing_chron = set(v['chronicle'])
            for i in range(start, len(data) - 10, 10):
                entry = data[i:i+10].hex()
                if entry == "00000000000000000000": break
                if entry not in existing_chron:
                    v['chronicle'].append(entry)

    save_vault(v)
    print(f"Scan complete. Added {added} new items to vault.")
    print(f"Vault: {len(v['items'])} items, {len(v['materials'])} materials, {len(v['chronicle'])} chronicle")


def cmd_status():
    v = load_vault()
    print(f"--- AI VAULT STATUS ---")
    print(f"Standard Gear: {len(v['items'])} items")
    print(f"Materials:     {len(v['materials'])} items")
    print(f"Chronicle:     {len(v['chronicle'])} entries")
    if os.path.exists(STASH_FILE):
        sz = os.path.getsize(STASH_FILE)
        print(f"\nGame Stash: {sz} bytes")


def cmd_wipe(target_tabs_str='all'):
    backup()
    with open(STASH_FILE, 'rb') as f: data = f.read()
    offsets = [i for i in range(len(data)) if data.startswith(TAB_SIG, i)]

    if target_tabs_str == 'all':
        targets = [0,1,2,3,4]
    else:
        targets = []
        for part in target_tabs_str.split(','):
            if '-' in part:
                s, e = map(int, part.split('-'))
                targets.extend(range(s-1, e))
            else:
                targets.append(int(part)-1)

    new_stash = bytearray()
    for i in range(len(offsets)):
        start = offsets[i]
        end = offsets[i+1] if i+1 < len(offsets) else len(data)
        if i in targets and i < 5:
            header = bytearray(data[start:start+64])
            content = b'\x4A\x4D\x00\x00'
            header[16:20] = (64 + len(content)).to_bytes(4, 'little')
            new_stash.extend(header + content)
            print(f"  Tab {i+1}: Wiped.")
        else:
            new_stash.extend(data[start:end])

    with open(STASH_FILE, 'wb') as f: f.write(new_stash)
    print("Wipe complete.")


def cmd_inject(indices, tab_assignments=None):
    """Inject items by vault index into stash tabs.
    indices: list of vault item indices
    tab_assignments: dict mapping index -> tab number (0-4), or None for auto
    """
    from d2r_item_parser import parse_item
    v = load_vault()

    if tab_assignments is None:
        tab_assignments = {idx: i // 6 for i, idx in enumerate(indices)}

    # Group by tab
    tab_items = [[] for _ in range(5)]
    for idx in indices:
        tab = tab_assignments.get(idx, 0)
        dna = v['items'][idx]['dna']
        try:
            p = parse_item(dna)
            code = p.get('code', '???')
        except:
            code = '???'
        tab_items[tab].append((idx, code, dna))

    backup()
    with open(STASH_FILE, 'rb') as f: stash_data = f.read()
    tab_offsets = [i for i in range(len(stash_data)) if stash_data[i:i+4] == TAB_SIG]

    if len(tab_offsets) < 7:
        print("ERROR: Expected at least 7 tabs")
        return

    new_stash = bytearray()
    for ti in range(len(tab_offsets)):
        tab_start = tab_offsets[ti]
        tab_end = tab_offsets[ti+1] if ti+1 < len(tab_offsets) else len(stash_data)
        original_tab = stash_data[tab_start:tab_end]

        if ti < 5:
            header = bytearray(original_tab[:64])
            items_for_tab = tab_items[ti] if ti < len(tab_items) else []

            if items_for_tab:
                codes = [item[1] for item in items_for_tab]
                positions = place_items_on_grid(codes)
                items_bin = bytearray()
                for j, (idx, code, dna) in enumerate(items_for_tab):
                    col, row = positions[j]
                    modified = set_item_position(dna, col, row, 5)
                    items_bin.extend(modified)
                    print(f"  Tab {ti}: IDX {idx} ({code}) -> pos ({col},{row})")
                content = b'\x4A\x4D' + len(items_for_tab).to_bytes(2, 'little') + bytes(items_bin)
            else:
                content = b'\x4A\x4D\x00\x00'

            header[16:20] = (64 + len(content)).to_bytes(4, 'little')
            new_stash.extend(header + content)
        else:
            new_stash.extend(original_tab)

    with open(STASH_FILE, 'wb') as f: f.write(bytes(new_stash))
    print(f"\nDone! {len(indices)} items injected.")
    print(f"Stash size: {len(stash_data)} -> {len(new_stash)} bytes")


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print("Usage: scan | status | wipe [tabs] | inject <indices...>")
    elif args[0] == 'scan':
        cmd_scan()
    elif args[0] == 'status':
        cmd_status()
    elif args[0] == 'wipe':
        cmd_wipe(args[1] if len(args) > 1 else 'all')
    elif args[0] == 'inject':
        indices = [int(x) for x in args[1:]]
        cmd_inject(indices)

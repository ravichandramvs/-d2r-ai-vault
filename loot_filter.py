"""
D2R AI Vault - Loot Filter Manager
Generates optimized loot filter based on vault holy grail progress.

Usage:
    python loot_filter.py status     - Show grail progress
    python loot_filter.py generate   - Generate optimized filter from vault
    python loot_filter.py apply      - Apply generated filter to game
    python loot_filter.py reset      - Reset to default starter filter
"""
import json, csv, os, sys, shutil
from datetime import datetime
from config import (VAULT_FILE, STASH_FILE, UNIQUE_TXT, SET_TXT,
                    ARMOR_TXT, WEAPONS_TXT, MISC_TXT)
from d2r_item_parser import parse_item

# --- Paths ---
SAVE_DIR = os.path.dirname(STASH_FILE)
LOOT_JSON = os.path.join(SAVE_DIR, 'lootfilter.json')
FILTER_DIR = SAVE_DIR  # .fltr files live alongside saves

# Character name from lootfilter.json profile mapping
def _get_profile():
    if os.path.exists(LOOT_JSON):
        d = json.load(open(LOOT_JSON, 'r', encoding='utf-8-sig'))
        profiles = d.get('Profiles', {})
        if profiles:
            char_name = list(profiles.keys())[0]
            filter_name = profiles[char_name]
            return char_name, filter_name
    return None, None

def _get_filter_path(filter_name=None):
    if filter_name is None:
        _, filter_name = _get_profile()
    if filter_name:
        return os.path.join(FILTER_DIR, f'{filter_name}.fltr')
    return None


# --- Holy Grail Analysis ---
def _read_chronicle_from_stash():
    """Read chronicle (holy grail) IDs directly from the game stash file.

    Chronicle structure (after C0EDEAC0 signature):
      Header (20 bytes): version(2), set_count(2), unique_count_or_total(2), sections(2), padding(12)
      Section 1: set_count entries (10 bytes each) — set item IDs
      Section 2: remaining entries — unique item IDs

    Each 10-byte entry: bytes 0-5 = metadata, bytes 6-7 = item ID (16-bit LE), bytes 8-9 = padding.

    Returns (found_set_ids, found_unique_ids) as two separate sets.
    """
    import re
    from config import STASH_FILE, CHRONICLE_SIG
    set_ids = set()
    unique_ids = set()
    if not os.path.exists(STASH_FILE):
        return set_ids, unique_ids
    with open(STASH_FILE, 'rb') as f:
        data = f.read()
    match = re.search(CHRONICLE_SIG, data)
    if not match:
        return set_ids, unique_ids

    # Parse header
    hdr_start = match.start() + 4
    set_count = int.from_bytes(data[hdr_start+2:hdr_start+4], 'little')

    entries_start = match.start() + 24

    # Read all entries
    entries = []
    for i in range(entries_start, len(data) - 10, 10):
        entry = data[i:i+10]
        if entry == b'\x00' * 10:
            entries.append(None)
        else:
            entries.append(entry)

    # Section 1: set IDs (first set_count entries)
    for entry in entries[:set_count]:
        if entry is not None:
            item_id = entry[6] + entry[7] * 256
            if item_id < 500:  # sanity check
                set_ids.add(item_id)

    # Section 2: unique IDs (remaining entries)
    for entry in entries[set_count:]:
        if entry is not None:
            item_id = entry[6] + entry[7] * 256
            if item_id < 500:  # sanity check — filter garbage entries
                unique_ids.add(item_id)

    return set_ids, unique_ids


def grail_status():
    """Build grail status with two views:
    - chronicle-based: what the game tracks as found (for status display)
    - vault-based: what's actually backed up in vault (for filter generation)

    The filter uses vault IDs so items found (in chronicle) but not backed up
    to vault still show in-game, letting the user re-collect them.
    """
    found_uids = set()
    found_sids = set()
    vault_uids = set()
    vault_sids = set()

    # Load tables
    unique_table = _load_table(UNIQUE_TXT, 'index', 'code', 'lvl')
    set_table = _load_table(SET_TXT, 'index', 'item', 'lvl')

    # 1. Chronicle IDs (game's holy grail tracker)
    chronicle_sids, chronicle_uids = _read_chronicle_from_stash()
    found_sids.update(chronicle_sids)
    found_uids.update(chronicle_uids)

    # 2. Current stash + character items (items physically present now)
    import re
    from config import STASH_FILE, CHAR_FILE, ITEM_START_RE
    for path in [STASH_FILE, CHAR_FILE]:
        if not os.path.exists(path):
            continue
        with open(path, 'rb') as f:
            data = f.read()
        starts = [m.start() for m in re.finditer(ITEM_START_RE, data)]
        for idx in range(len(starts)):
            start = starts[idx]
            end = starts[idx + 1] if idx + 1 < len(starts) else len(data)
            chunk = data[start:end]
            h_match = re.search(b'(\x4A\x4D|\x55\xAA\x55\xAA|\xC0\xED\xEA\xC0)', chunk[1:])
            if h_match:
                end = start + 1 + h_match.start()
            dna = data[start:end].hex()
            try:
                p = parse_item(dna)
                if p.get('unique_id') is not None:
                    found_uids.add(p['unique_id'])
                if p.get('set_id') is not None:
                    found_sids.add(p['set_id'])
            except:
                pass

    # 3. Vault items — what's actually backed up
    if os.path.exists(VAULT_FILE):
        vault = json.load(open(VAULT_FILE, 'r'))
        for it in vault.get('items', []):
            try:
                p = parse_item(it['dna'])
                if p.get('unique_id') is not None:
                    vault_uids.add(p['unique_id'])
                if p.get('set_id') is not None:
                    vault_sids.add(p['set_id'])
            except:
                pass

    quest_codes = QUEST_CODES
    unique_playable = [(i,n,c,l) for i,n,c,l in unique_table if c not in quest_codes]
    set_playable = set_table

    missing_u = [(i,n,c,l) for i,n,c,l in unique_playable if i not in found_uids]
    missing_s = [(i,n,c,l) for i,n,c,l in set_playable if i not in found_sids]
    found_u = [(i,n,c,l) for i,n,c,l in unique_playable if i in found_uids]
    found_s = [(i,n,c,l) for i,n,c,l in set_playable if i in found_sids]

    return {
        'found_uids': found_uids,
        'found_sids': found_sids,
        'vault_uids': vault_uids,
        'vault_sids': vault_sids,
        'chronicle_set_ids': chronicle_sids,
        'chronicle_unique_ids': chronicle_uids,
        'missing_uniques': missing_u,
        'found_uniques': found_u,
        'missing_sets': missing_s,
        'found_sets': found_s,
        'total_uniques': len(unique_playable),
        'total_sets': len(set_playable),
        'unique_table': unique_playable,
        'set_table': set_playable,
    }


def _load_table(path, name_col, code_col, lvl_col):
    rows = []
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        for i, row in enumerate(csv.DictReader(f, delimiter='\t')):
            name = row.get(name_col, '').strip()
            code = row.get(code_col, '').strip()
            lvl = row.get(lvl_col, '').strip()
            # Skip disabled or chronicle-disabled items
            if row.get('disabled', '').strip():
                continue
            if row.get('disableChronicle', '').strip():
                continue
            if not name or not code:
                continue
            # Use *ID column if available (RotW), else row index
            item_id = int(row['*ID']) if '*ID' in row and row['*ID'].strip() else i
            rows.append((item_id, name, code, lvl))
    return rows


def _load_code_names():
    code_to_name = {}
    for path in [ARMOR_TXT, WEAPONS_TXT, MISC_TXT]:
        with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                c = row.get('code', '').strip()
                n = row.get('name', '').strip()
                if c: code_to_name[c] = n
    return code_to_name


# --- Filter Generation ---
QUEST_CODES = {'qf1', 'qf2', 'msf', 'hst', 'hfh', 'vip', 'leg', 'hdm', 'g33', 'd33'}


def _get_unique_code_flags(grail):
    """Return {code: [in_vault_bool, ...]} for uniques."""
    vault_uids = grail.get('vault_uids', grail['found_uids'])
    u_by_code = {}
    for i, n, c, l in grail['unique_table']:
        if c in QUEST_CODES:
            continue
        u_by_code.setdefault(c, []).append(i in vault_uids)
    return u_by_code


def _get_set_code_flags(grail):
    """Return {code: [in_vault_bool, ...]} for sets."""
    vault_sids = grail.get('vault_sids', grail['found_sids'])
    s_by_code = {}
    for i, n, c, l in grail['set_table']:
        if c in QUEST_CODES:
            continue
        s_by_code.setdefault(c, []).append(i in vault_sids)
    return s_by_code


def generate_filter():
    """Generate filter using correct D2R filter semantics:

    - SHOW always beats HIDE (if both match, item is shown)
    - Unmatched items are SHOWN by default
    - Fields within a rule are AND'd; values within a field are OR'd
    - Rule order does NOT matter — SHOW always wins over HIDE

    IMPORTANT: D2R filter engine treats ALL items (including rings, amulets,
    jewels, charms) as "equipment" for filtering purposes. Use equipmentRarity
    and equipmentItemCode for these — NOT itemCode. The itemCode field is only
    for consumables (potions, scrolls, keys).

    Grail logic: separate SHOW rules for uniques vs sets so that e.g.
    set rings can be hidden (all found) while unique rings still show.
    """
    grail = grail_status()

    # Best elite bases for runewords (worth keeping as white/eth/socketed)
    ELITE_BASES = [
        # Body armor
        "utp",  # Archon Plate — best all-around (Enigma, Fortitude, CoH)
        "uui",  # Dusk Shroud — low str, caster favorite
        "uea",  # Wyrmhide — low str alternative
        "ula",  # Scarab Husk
        "utu",  # Wire Fleece
        "urs",  # Great Hauberk
        "uar",  # Sacred Armor — highest def, merc Fortitude
        # Helms
        "uh9",  # Bone Visage — Dream, Delirium
        "usk",  # Demonhead
        "ci3",  # Diadem — zero str req Dream
        "uhm",  # Spired Helm
        "urn",  # Corona
        # Druid pelts
        "drf",  # Dream Spirit
        "dre",  # Sky Spirit
        # Barb helms
        "baf",  # Guardian Crown
        "bae",  # Conquerer Crown
        # Shields
        "uit",  # Monarch — only 4os non-pally Spirit base
        "uts",  # Ward
        "ush",  # Troll Nest
        # Paladin shields (can roll +all res)
        "pab",  # Sacred Targe — best pally base
        "paf",  # Vortex Shield — max def pally
        "pae",  # Zakarum Shield
        "pac",  # Sacred Rondache
        "pad",  # Ancient Shield
        # Weapons — melee
        "7cr",  # Phase Blade — Grief, indestructible
        "7wa",  # Berserker Axe — Grief, Beast, Death
        "72a",  # Ettin Axe
        "7ls",  # Cryptic Sword — Spirit weapon
        "7fl",  # Scourge
        "7ws",  # Caduceus — CTA
        "7gd",  # Colossus Blade — BotD
        "7b7",  # Champion Sword
        # Weapons — polearms (merc Infinity, Insight)
        "7s8",  # Thresher — fastest, #1 merc base
        "7wc",  # Giant Thresher — 6os BotD
        "7pa",  # Cryptic Axe — more dmg per hit
        "7h7",  # Great Poleaxe
        "7vo",  # Colossus Voulge
        # Weapons — spears
        "7br",  # Mancatcher — fastest spear
        "7st",  # Ghost Spear
        # Assassin claws
        "7tw",  # Runic Talons — Chaos
        "7lw",  # Feral Claws
        # Staves
        "6ws",  # Archon Staff
    ]

    rules = []

    # === HIDE RULES ===
    # Strategy: hide broad categories, then SHOW specific valuable items.
    # D2R rule: SHOW always beats HIDE. Unmatched items shown by default.

    # 1. HIDE found uniques (codes where ALL uniques for that base are in vault)
    found_unique_codes = sorted(
        c for c, flags in _get_unique_code_flags(grail).items() if all(flags)
    )
    if found_unique_codes:
        rules.append({
            "name": "HIDE Found Uniques",
            "enabled": True,
            "ruleType": "hide",
            "filterEtherealSocketed": False,
            "equipmentRarity": ["unique"],
            "equipmentItemCode": found_unique_codes,
        })

    # 2. HIDE found sets (codes where ALL sets for that base are in vault)
    found_set_codes = sorted(
        c for c, flags in _get_set_code_flags(grail).items() if all(flags)
    )
    if found_set_codes:
        rules.append({
            "name": "HIDE Found Sets",
            "enabled": True,
            "ruleType": "hide",
            "filterEtherealSocketed": False,
            "equipmentRarity": ["set"],
            "equipmentItemCode": found_set_codes,
        })

    # 3. HIDE inferior gear
    rules.append({
        "name": "HIDE Inferior Gear",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["lowQuality"],
    })

    # 4. HIDE white/superior items (SHOW rules bring back elite bases)
    rules.append({
        "name": "HIDE White Items",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["normal", "hiQuality"],
    })

    # 5. HIDE magic items (SHOW brings back charms)
    rules.append({
        "name": "HIDE Magic Items",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["magic"],
    })

    # 6. HIDE rare items (SHOW brings back boots/gloves/circlets/jewelry)
    rules.append({
        "name": "HIDE Rare Items",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["rare"],
    })

    # 7. HIDE gold
    rules.append({
        "name": "HIDE Gold",
        "enabled": True,
        "ruleType": "hide",
        "goldFilterValue": 1,
    })

    # 8. HIDE misc junk (gems, runes, ammo, scrolls, keys)
    rules.append({
        "name": "HIDE Misc Categories",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": False,
        "itemCategory": ["gems", "runes", "ammo", "scrlt", "keysr"],
    })

    # 9. HIDE weak potions/books/keys
    rules.append({
        "name": "HIDE Weak Potions/Books",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": False,
        "itemCode": [
            "tsc", "isc", "tbk", "ibk", "key", "luv",
            "hp1", "hp2", "hp3", "hp4",
            "mp1", "mp2", "mp3", "mp4",
            "vps", "yps", "wms",
        ],
    })

    # === SHOW RULES (punch through HIDE rules) ===

    # 10. SHOW elite bases (white/superior, specific valuable codes only)
    rules.append({
        "name": "SHOW Elite Bases",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["normal", "hiQuality"],
        "equipmentItemCode": ELITE_BASES,
    })

    # 11. SHOW elite socketed/ethereal (specific valuable codes only)
    rules.append({
        "name": "SHOW Elite Socketed/Ethereal",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": True,
        "equipmentItemCode": ELITE_BASES,
    })

    # 12. SHOW rare gloves, boots, circlets
    rules.append({
        "name": "SHOW Rare Gear (gloves/boots/circlets)",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["rare"],
        "equipmentItemCode": [
            "ci0", "ci1", "ci2", "ci3",
            "lbt", "vbt", "mbt", "tbt", "hbt",
            "xlb", "xmb", "xtb", "xhb", "xvb",
            "ulb", "umb", "utb", "uhb", "uvb",
            "lgl", "vgl", "mgl", "tgl", "hgl",
            "xlg", "xmg", "xtg", "xhg", "xvg",
            "ulg", "umg", "utg", "uhg", "uvg",
        ],
    })

    # 13. SHOW rare jewelry (rings, amulets, jewels)
    rules.append({
        "name": "SHOW Rare Jewelry",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["rare"],
        "equipmentItemCode": ["rin", "amu", "jew"],
    })

    # 14. SHOW magic/rare jewels (all jewels are worth checking)
    rules.append({
        "name": "SHOW Jewels",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["magic", "rare"],
        "equipmentItemCode": ["jew"],
    })

    # 15. SHOW magic charms
    rules.append({
        "name": "SHOW Magic Charms",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["magic"],
        "equipmentItemCode": ["cm1", "cm2", "cm3"],
    })

    # 16. SHOW good potions
    rules.append({
        "name": "SHOW Good Potions",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "itemCode": ["hp5", "mp5", "rvl"],
    })

    # 17. SHOW quest items
    rules.append({
        "name": "SHOW Quest Items",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentItemCode": [
            "hst", "msf", "qf1", "qf2",
            "hdm", "hfh", "leg",
            "g33", "d33",
        ],
    })

    char_name, old_filter_name = _get_profile()
    filter_name = "AI Vault - War"
    fltr = {"name": filter_name, "rules": rules}

    return fltr, char_name, filter_name


# --- Commands ---
def cmd_status():
    grail = grail_status()
    pct_u = len(grail['found_uniques']) / grail['total_uniques'] * 100
    pct_s = len(grail['found_sets']) / grail['total_sets'] * 100

    vault_u = len([1 for i,n,c,l in grail['unique_table'] if i in grail.get('vault_uids', set())])
    vault_s = len([1 for i,n,c,l in grail['set_table'] if i in grail.get('vault_sids', set())])

    print(f"=== HOLY GRAIL STATUS ===")
    print(f"Uniques: {len(grail['found_uniques'])}/{grail['total_uniques']} ({pct_u:.1f}%) found | {vault_u} in vault")
    print(f"Sets:    {len(grail['found_sets'])}/{grail['total_sets']} ({pct_s:.1f}%) found | {vault_s} in vault")
    print(f"  (Filter uses vault — {len(grail['found_uniques'])-vault_u} uniques, {len(grail['found_sets'])-vault_s} sets found but not in vault will still show)")

    code_names = _load_code_names()

    for tier, lo, hi in [("Normal (1-30)", 0, 30), ("Exceptional (31-50)", 31, 50), ("Elite (51+)", 51, 999)]:
        tier_u = [(i,n,c,l) for i,n,c,l in grail['missing_uniques'] if l.isdigit() and lo <= int(l) <= hi]
        tier_s = [(i,n,c,l) for i,n,c,l in grail['missing_sets'] if l.isdigit() and lo <= int(l) <= hi]
        print(f"\n--- {tier} ---")
        print(f"  Missing uniques: {len(tier_u)}")
        for i, n, c, l in tier_u[:10]:
            base = code_names.get(c, c)
            print(f"    {n:30s} ({base}) lvl {l}")
        if len(tier_u) > 10:
            print(f"    ... +{len(tier_u)-10} more")
        print(f"  Missing sets: {len(tier_s)}")
        for i, n, c, l in tier_s[:10]:
            base = code_names.get(c, c)
            print(f"    {n:30s} ({base}) lvl {l}")
        if len(tier_s) > 10:
            print(f"    ... +{len(tier_s)-10} more")


def cmd_generate():
    fltr, char_name, filter_name = generate_filter()
    out_path = os.path.join(os.path.dirname(__file__), f'{filter_name}.fltr')
    with open(out_path, 'w') as f:
        json.dump(fltr, f, indent=4)
    print(f"Generated filter: {out_path}")
    print(f"  {len(fltr['rules'])} rules")
    for r in fltr['rules']:
        status = "ON" if r['enabled'] else "--"
        print(f"  [{status}] {r['ruleType']:4s} | {r['name']}")
    print(f"\nRun 'python loot_filter.py apply' to install to game.")


def cmd_apply():
    fltr, char_name, filter_name = generate_filter()
    if not char_name:
        print("ERROR: No character profile found in lootfilter.json")
        return

    # Backup existing
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    existing_filter_path = _get_filter_path()
    if existing_filter_path and os.path.exists(existing_filter_path):
        shutil.copy2(existing_filter_path, f"{existing_filter_path}.{ts}.bak")

    # Write filter file
    dest = os.path.join(FILTER_DIR, f'{filter_name}.fltr')
    with open(dest, 'w') as f:
        json.dump(fltr, f, indent=4)

    # Update lootfilter.json to point to new filter
    loot_cfg = {"Version": 1, "Presets Loaded": True, "Profiles": {char_name: filter_name}}
    with open(LOOT_JSON, 'w') as f:
        json.dump(loot_cfg, f, indent=4)

    print(f"Applied filter '{filter_name}' for character '{char_name}'")
    print(f"  Filter: {dest}")
    print(f"  Config: {LOOT_JSON}")
    print(f"  Backup: {existing_filter_path}.{ts}.bak")
    print(f"\nRestart D2R to activate the new filter.")


def cmd_reset():
    char_name, _ = _get_profile()
    if not char_name:
        print("ERROR: No character profile found")
        return

    default_name = "Starter - War"
    loot_cfg = {"Version": 1, "Presets Loaded": True, "Profiles": {char_name: default_name}}
    with open(LOOT_JSON, 'w') as f:
        json.dump(loot_cfg, f, indent=4)
    print(f"Reset to default filter '{default_name}' for '{char_name}'")


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print("Usage: status | generate | apply | reset")
    elif args[0] == 'status':
        cmd_status()
    elif args[0] == 'generate':
        cmd_generate()
    elif args[0] == 'apply':
        cmd_apply()
    elif args[0] == 'reset':
        cmd_reset()

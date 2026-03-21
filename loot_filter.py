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
def grail_status():
    vault = json.load(open(VAULT_FILE, 'r'))
    found_uids = set()
    found_sids = set()
    for it in vault['items']:
        try:
            p = parse_item(it['dna'])
            if p.get('unique_id') is not None: found_uids.add(p['unique_id'])
            if p.get('set_id') is not None: found_sids.add(p['set_id'])
        except:
            pass

    # Also count chronicle entries (items found then deleted)
    chronicle_ids = set()
    for entry_hex in vault.get('chronicle', []):
        if len(entry_hex) >= 14:
            chronicle_ids.add(int(entry_hex[12:14], 16))

    unique_table = _load_table(UNIQUE_TXT, 'index', 'code', 'lvl')
    set_table = _load_table(SET_TXT, 'index', 'item', 'lvl')

    quest_codes = {'qf1', 'qf2', 'msf', 'hst', 'hfh', 'vip', 'leg', 'hdm', 'g33', 'd33'}
    unique_playable = [(i,n,c,l) for i,n,c,l in unique_table if c not in quest_codes]
    set_playable = set_table

    missing_u = [(i,n,c,l) for i,n,c,l in unique_playable if i not in found_uids]
    missing_s = [(i,n,c,l) for i,n,c,l in set_playable if i not in found_sids]
    found_u = [(i,n,c,l) for i,n,c,l in unique_playable if i in found_uids]
    found_s = [(i,n,c,l) for i,n,c,l in set_playable if i in found_sids]

    return {
        'found_uids': found_uids,
        'found_sids': found_sids,
        'chronicle_ids': chronicle_ids,
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
            if name and code:
                rows.append((i, name, code, lvl))
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
def _build_grail_codes(grail):
    """Determine which base codes are fully completed (all uniques AND sets found).
    A code is 'complete' only if every unique and every set using that base code
    has been found. If even one is missing, keep showing that code.
    """
    quest_codes = {'qf1', 'qf2', 'msf', 'hst', 'hfh', 'vip', 'leg', 'hdm', 'g33', 'd33'}

    # code -> list of (id, found?) for uniques
    code_unique_status = {}
    for i, n, c, l in grail['unique_table']:
        if c in quest_codes: continue
        code_unique_status.setdefault(c, []).append(i in grail['found_uids'])
    for i, n, c, l in grail['missing_uniques']:
        if c in quest_codes: continue
        code_unique_status.setdefault(c, [])  # ensure entry exists

    # code -> list of (id, found?) for sets
    code_set_status = {}
    for i, n, c, l in grail['set_table']:
        code_set_status.setdefault(c, []).append(i in grail['found_sids'])
    for i, n, c, l in grail['missing_sets']:
        code_set_status.setdefault(c, [])

    # A code is fully complete if ALL uniques for it are found AND all sets for it
    completed_codes = set()
    all_codes = set(code_unique_status.keys()) | set(code_set_status.keys())
    for code in all_codes:
        if code in quest_codes:
            continue
        u_list = code_unique_status.get(code, [])
        s_list = code_set_status.get(code, [])
        # Must have found at least one item from this code
        if not u_list and not s_list:
            continue
        all_u_found = all(u_list) if u_list else True
        all_s_found = all(s_list) if s_list else True
        if all_u_found and all_s_found and (u_list or s_list):
            # Only mark complete if we actually found something
            has_any_found = any(u_list) or any(s_list)
            if has_any_found:
                completed_codes.add(code)

    return completed_codes


def generate_filter():
    """Generate filter using correct D2R filter semantics:

    - SHOW always beats HIDE (if both match, item is shown)
    - Unmatched items are SHOWN by default
    - Fields within a rule are AND'd; values within a field are OR'd
    - Correct pattern: HIDE ALL catch-all + targeted SHOW whitelist rules
    - No practical rule count limit (community filters use 20-30+)

    For grail: only SHOW uniques/sets from base codes with missing items.
    Completed base codes simply aren't in any SHOW rule → hidden by catch-all.
    """
    grail = grail_status()
    completed_codes = _build_grail_codes(grail)

    # Base codes that still have missing uniques or sets → must SHOW
    quest_codes = {'qf1','qf2','msf','hst','hfh','vip','leg','hdm','g33','d33'}
    all_grail_codes = set()
    for i, n, c, l in grail['unique_table']:
        if c not in quest_codes: all_grail_codes.add(c)
    for i, n, c, l in grail['set_table']:
        if c not in quest_codes: all_grail_codes.add(c)

    # Only show uniques/sets from incomplete base codes
    incomplete_codes = sorted(all_grail_codes - completed_codes)

    rules = []

    # === RULE 1: HIDE ALL (catch-all, matches everything) ===
    # This is the foundation — everything is hidden unless a SHOW rule saves it
    # Fields are OR'd at the category level: matches equipment OR misc OR gold
    rules.append({
        "name": "HIDE ALL",
        "enabled": True,
        "ruleType": "hide",
        "filterEtherealSocketed": True,
        "equipmentRarity": ["rare", "lowQuality", "magic", "unique", "set", "hiQuality", "normal"],
        "equipmentQuality": ["normal", "exceptional", "elite"],
        "equipmentCategory": ["acce", "armo", "weap"],
        "itemCategory": ["misc"],
        "goldFilterValue": 1
    })

    # === SHOW RULES (whitelist — punch holes through HIDE ALL) ===

    # 2. SHOW uniques/sets ONLY for incomplete grail base codes
    if incomplete_codes:
        rules.append({
            "name": "SHOW Unfound Uniques/Sets",
            "enabled": True,
            "ruleType": "show",
            "filterEtherealSocketed": False,
            "equipmentRarity": ["unique", "set"],
            "equipmentItemCode": incomplete_codes
        })

    # 3. SHOW socketed + ethereal (runeword bases — covers exc/elite socketed)
    rules.append({
        "name": "SHOW Socketed/Ethereal",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": True
    })

    # (removed "SHOW Exc/Elite Bases" — was showing ALL white exceptional items
    #  like Hatchet, Poignard, Gladius etc. Socketed/eth exc/elite items are
    #  already covered by the socketed/ethereal rule above)

    # 5. SHOW rare rings/amu/circlets/boots/jewels
    rules.append({
        "name": "SHOW Rare Ring/Amu/Circ/Boot/Jewel",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "equipmentRarity": ["rare"],
        "equipmentItemCode": [
            "rin", "amu", "jew",
            "ci0", "ci1", "ci2", "ci3",
            "lbt", "vbt", "mbt", "tbt", "hbt",
            "xlb", "xmb", "xtb", "xhb", "xvb",
            "ulb", "umb", "utb", "uhb", "uvb",
        ]
    })

    # 6. SHOW magic charms
    rules.append({
        "name": "SHOW Magic Charms",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "itemCode": ["cm1", "cm2", "cm3"]
    })

    # 7. SHOW good potions only (hp5, mp5, rejuv small, rejuv large)
    rules.append({
        "name": "SHOW Good Potions",
        "enabled": True,
        "ruleType": "show",
        "filterEtherealSocketed": False,
        "itemCode": ["hp5", "mp5", "rvs", "rvl"]
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

    print(f"=== HOLY GRAIL STATUS ===")
    print(f"Uniques: {len(grail['found_uniques'])}/{grail['total_uniques']} ({pct_u:.1f}%)")
    print(f"Sets:    {len(grail['found_sets'])}/{grail['total_sets']} ({pct_s:.1f}%)")

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

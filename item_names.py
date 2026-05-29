"""
Lookup tables for D2R item names, slots, uniques, and sets.
Reads from GoMule D2 data tables.
"""
import csv
from config import ARMOR_TXT, WEAPONS_TXT, MISC_TXT, UNIQUE_TXT, SET_TXT

# Armor sub-type classification
_HELM_TYPES   = {'helm','circ','phlm','elht','hlm3'}
_BELT_TYPES   = {'belt','zbel','lbl2','mbl2','hbl2'}
_BOOT_TYPES   = {'boot','mbt2','hbt2'}
_GLOVE_TYPES  = {'glov','lgv2','mgv2','hgv2'}
_SHIELD_TYPES = {'shie','ashd','spsh','head','pelt'}
_BODY_TYPES   = {'tors','cloa'}


def load_code_info():
    """Returns dict: code -> (base_name, slot)"""
    code_info = {}

    with open(ARMOR_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            code = row.get('code','').strip()
            name = row.get('name','').strip()
            t1 = row.get('type','').strip().lower()
            t2 = row.get('type2','').strip().lower()
            if   t1 in _HELM_TYPES   or t2 in _HELM_TYPES:   slot = 'helm'
            elif t1 in _BELT_TYPES   or t2 in _BELT_TYPES:   slot = 'belt'
            elif t1 in _BOOT_TYPES   or t2 in _BOOT_TYPES:   slot = 'boots'
            elif t1 in _GLOVE_TYPES  or t2 in _GLOVE_TYPES:  slot = 'gloves'
            elif t1 in _SHIELD_TYPES or t2 in _SHIELD_TYPES: slot = 'shield'
            elif t1 in _BODY_TYPES   or t2 in _BODY_TYPES:   slot = 'body'
            else: slot = 'armor_other'
            if code: code_info[code] = (name, slot)

    with open(WEAPONS_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            code = row.get('code','').strip()
            name = row.get('name','').strip()
            t1 = row.get('type','').strip().lower()
            if t1 in ('bow','xbow','orb','staf','wand','rod'):
                slot = 'weapon_ranged'
            else:
                slot = 'weapon'
            if code: code_info[code] = (name, slot)

    with open(MISC_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            code = row.get('code','').strip()
            name = row.get('name','').strip()
            t1 = row.get('type','').strip().lower()
            if   t1 == 'ring': slot = 'ring'
            elif t1 == 'amul': slot = 'amulet'
            else:              slot = 'misc'
            if code: code_info[code] = (name, slot)

    return code_info


def load_unique_names():
    """Returns dict: row_index -> {'name': str, 'code': str}.
    Stores the base code per row so lookup can verify uid against item code
    (RotW inserted a row mid-file ~uid=126, causing off-by-one for ~58% of items)."""
    rows = {}
    with open(UNIQUE_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for i, row in enumerate(csv.DictReader(f, delimiter='\t')):
            n = row.get('index','').strip()
            c = row.get('code','').strip()
            if n: rows[i] = {'name': n, 'code': c}
    return rows


def load_set_names():
    """Returns dict: row_index -> {'name': str, 'code': str}."""
    rows = {}
    with open(SET_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for i, row in enumerate(csv.DictReader(f, delimiter='\t')):
            n = row.get('index','').strip()
            c = (row.get('item','').strip() or row.get('code','').strip())
            if n: rows[i] = {'name': n, 'code': c}
    return rows


def _resolve_unique(uid, code, unique_rows):
    """Return the correct unique name by matching uid's code against item's code.
    Tries uid first, then uid+1 (handles the row-insertion off-by-one)."""
    if uid is None or not unique_rows:
        return None
    r = unique_rows.get(uid)
    if r and r['code'] == code:
        return r['name']
    r1 = unique_rows.get(uid + 1)
    if r1 and r1['code'] == code:
        return r1['name']
    # Fallback: try -1 too
    rm = unique_rows.get(uid - 1)
    if rm and rm['code'] == code:
        return rm['name']
    # Last resort: just return the uid-row name (may be wrong but at least
    # not silently empty)
    return r['name'] if r else None


def _resolve_set(sid, code, set_rows):
    if sid is None or not set_rows:
        return None
    r = set_rows.get(sid)
    if r and r['code'] == code:
        return r['name']
    r1 = set_rows.get(sid + 1)
    if r1 and r1['code'] == code:
        return r1['name']
    rm = set_rows.get(sid - 1)
    if rm and rm['code'] == code:
        return rm['name']
    return r['name'] if r else None


def resolve_unique_name(parsed, unique_rows):
    """Public helper: get the correct unique name from a parsed item dict."""
    return _resolve_unique(parsed.get('unique_id'), parsed.get('code'), unique_rows)


def resolve_set_name(parsed, set_rows):
    """Public helper: get the correct set name from a parsed item dict."""
    return _resolve_set(parsed.get('set_id'), parsed.get('code'), set_rows)


def get_item_label(parsed, code_info=None, unique_names=None, set_names=None):
    """Build a human-readable label for a parsed item."""
    code = parsed.get('code', '???')
    quality = parsed.get('quality', '')
    eth = '[ETH] ' if parsed.get('ethereal') else ''

    base = code
    if code_info and code in code_info:
        base = code_info[code][0]

    if quality == 'Unique' and parsed.get('unique_id') is not None:
        name = _resolve_unique(parsed['unique_id'], code, unique_names or {}) \
               or f'UID{parsed["unique_id"]}'
        return f'{eth}{name} ({base})'
    elif quality == 'Set' and parsed.get('set_id') is not None:
        name = _resolve_set(parsed['set_id'], code, set_names or {}) \
               or f'SID{parsed["set_id"]}'
        return f'{eth}{name} ({base})'
    else:
        return f'{eth}{quality} {base}'

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
    """Returns dict: row_index -> unique item name"""
    names = {}
    with open(UNIQUE_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for i, row in enumerate(csv.DictReader(f, delimiter='\t')):
            n = row.get('index','').strip()
            if n: names[i] = n
    return names


def load_set_names():
    """Returns dict: row_index -> set item name"""
    names = {}
    with open(SET_TXT, 'r', encoding='utf-8-sig', errors='replace') as f:
        for i, row in enumerate(csv.DictReader(f, delimiter='\t')):
            n = row.get('index','').strip()
            if n: names[i] = n
    return names


def get_item_label(parsed, code_info=None, unique_names=None, set_names=None):
    """Build a human-readable label for a parsed item."""
    code = parsed.get('code', '???')
    quality = parsed.get('quality', '')
    eth = '[ETH] ' if parsed.get('ethereal') else ''

    base = code
    if code_info and code in code_info:
        base = code_info[code][0]

    if quality == 'Unique' and parsed.get('unique_id') is not None:
        name = (unique_names or {}).get(parsed['unique_id'], f'UID{parsed["unique_id"]}')
        return f'{eth}{name} ({base})'
    elif quality == 'Set' and parsed.get('set_id') is not None:
        name = (set_names or {}).get(parsed['set_id'], f'SID{parsed["set_id"]}')
        return f'{eth}{name} ({base})'
    else:
        return f'{eth}{quality} {base}'

"""Quick dump of all named uniques/sets in the vault, grouped by slot, with counts."""
import json
from collections import defaultdict
from config import VAULT_FILE
from d2r_item_parser import parse_item
from item_names import load_code_info, load_unique_names, load_set_names, resolve_unique_name, resolve_set_name

with open(VAULT_FILE, 'r') as f:
    bank = json.load(f)

code_info = load_code_info()
uniq_names = load_unique_names()
set_names = load_set_names()

by_slot_uniq = defaultdict(lambda: defaultdict(list))   # slot -> name -> [idx]
by_slot_set  = defaultdict(lambda: defaultdict(list))

unknown_uid = defaultdict(list)
unknown_sid = defaultdict(list)

for idx, item_entry in enumerate(bank['items']):
    try:
        item = parse_item(item_entry['dna'])
    except Exception:
        continue
    code = item.get('code')
    quality = item.get('quality')
    eth = item.get('ethereal', False)
    if not code or code not in code_info:
        continue
    base_name, slot = code_info[code]

    if quality == 'Unique':
        name = resolve_unique_name(item, uniq_names)
        if name:
            label = f'{"[eth] " if eth else ""}{name}  ({base_name})'
            by_slot_uniq[slot][name].append((idx, label))
        else:
            unknown_uid[item.get('unique_id')].append((idx, base_name))
    elif quality == 'Set':
        name = resolve_set_name(item, set_names)
        if name:
            label = f'{"[eth] " if eth else ""}{name}  ({base_name})'
            by_slot_set[slot][name].append((idx, label))
        else:
            unknown_sid[item.get('set_id')].append((idx, base_name))

slot_order = ['helm','body','shield','weapon','weapon_ranged','gloves','boots','belt','ring','amulet','misc','armor_other']

print('========== UNIQUES ==========')
for slot in slot_order:
    items = by_slot_uniq.get(slot)
    if not items:
        continue
    print(f'\n--- {slot.upper()} ({sum(len(v) for v in items.values())} total) ---')
    for name in sorted(items.keys()):
        entries = items[name]
        cnt = len(entries)
        base = entries[0][1].split('  (')[1].rstrip(')')
        eth_count = sum(1 for _, lbl in entries if lbl.startswith('[eth]'))
        suffix = f' x{cnt}' if cnt > 1 else ''
        eth_suffix = f' [{eth_count} eth]' if eth_count else ''
        print(f'  {name}  ({base}){suffix}{eth_suffix}')

print('\n\n========== SETS ==========')
for slot in slot_order:
    items = by_slot_set.get(slot)
    if not items:
        continue
    print(f'\n--- {slot.upper()} ({sum(len(v) for v in items.values())} total) ---')
    for name in sorted(items.keys()):
        entries = items[name]
        cnt = len(entries)
        base = entries[0][1].split('  (')[1].rstrip(')')
        suffix = f' x{cnt}' if cnt > 1 else ''
        print(f'  {name}  ({base}){suffix}')

if unknown_uid:
    print(f'\n\n========== UNKNOWN UNIQUE IDs ({sum(len(v) for v in unknown_uid.values())} items) ==========')
    for uid in sorted(unknown_uid):
        print(f'  UID {uid}: {len(unknown_uid[uid])} item(s), bases: {set(b for _,b in unknown_uid[uid])}')

if unknown_sid:
    print(f'\n\n========== UNKNOWN SET IDs ({sum(len(v) for v in unknown_sid.values())} items) ==========')
    for sid in sorted(unknown_sid):
        print(f'  SID {sid}: {len(unknown_sid[sid])} item(s), bases: {set(b for _,b in unknown_sid[sid])}')

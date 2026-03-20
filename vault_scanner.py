"""
D2R AI Vault - Full vault scanner.
Parses all items and shows quality distribution + top items.
"""
import json
from config import VAULT_FILE
from d2r_item_parser import parse_item
from item_names import load_code_info, load_unique_names, load_set_names, get_item_label


def main():
    with open(VAULT_FILE, 'r') as f:
        bank = json.load(f)

    code_info = load_code_info()
    unique_names = load_unique_names()
    set_names = load_set_names()

    total = len(bank['items'])
    success = partial = failed = simple = 0
    quality_counts = {}

    results = []
    for idx in range(total):
        dna = bank['items'][idx]['dna']
        try:
            item = parse_item(dna)
        except Exception as e:
            failed += 1
            continue

        if item.get('simple'):
            simple += 1
            continue
        if item.get('error'):
            failed += 1
            continue

        q = item.get('quality', '?')
        quality_counts[q] = quality_counts.get(q, 0) + 1

        real_stats = [s for s in item.get('stats', []) if not s.get('marker') and s.get('val') is not None]
        if len(real_stats) > 0:
            success += 1
        else:
            partial += 1

        label = get_item_label(item, code_info, unique_names, set_names)
        results.append((idx, item, label, len(real_stats)))

    print(f"=== Vault Scan Summary ===")
    print(f"Total items: {total}")
    print(f"Simple items: {simple}")
    print(f"Successfully decoded: {success}")
    print(f"Partial (no real stats): {partial}")
    print(f"Failed: {failed}")
    print(f"\nQuality distribution:")
    for q, c in sorted(quality_counts.items()):
        print(f"  {q}: {c}")

    print(f"\n=== Top Items by Stat Count ===")
    results.sort(key=lambda x: -x[3])
    for idx, item, label, n in results[:15]:
        stats_str = ", ".join(f"{s['name']}={s['val']}" for s in item['stats'] if not s.get('marker') and s.get('val') is not None)
        print(f"  IDX {idx:3d}: {label} ({n} stats)")
        print(f"    {stats_str}")


if __name__ == '__main__':
    main()

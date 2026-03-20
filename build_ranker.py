"""
D2R AI Vault - Build Ranker
Ranks vault items for a specific build. Default: Echo Warlock.

Scoring weights are tuned for Echoing Strike (cast anim = FCR, SrcDam 96%,
Warlock can 1H any 2H weapon). Adjust weights for other builds.
"""
import json, sys
from config import VAULT_FILE
from d2r_item_parser import parse_item
from item_names import load_code_info, load_unique_names, load_set_names, get_item_label

# Warlock skill IDs (RotW)
WAR_SKILL_IDS = set(range(373, 403))


def get_all(stats, name):
    return sum(s['val'] for s in stats if s.get('name') == name and s.get('val') is not None)


def score_item(parsed, slot):
    stats = parsed.get('stats', []) or []
    score = 0
    notes = []

    # +All skills (only universal +skills helps Warlock)
    v = get_all(stats, 'item_allskills')
    if v > 0:
        score += v * 15; notes.append(f"+{v} all skills")

    # +Warlock class skills
    v = get_all(stats, 'item_addclassskills')
    if v > 0:
        score += v * 12; notes.append(f"+{v} war skills")

    # +Skill tab
    v = get_all(stats, 'item_addskill_tab')
    if v > 0:
        score += v * 6; notes.append(f"+{v} skill tab")

    # +Single Warlock skill
    for s in stats:
        if s.get('name') == 'item_singleskill' and s.get('val', 0) > 0:
            if s.get('param') in WAR_SKILL_IDS:
                score += s['val'] * 8; notes.append(f"+{s['val']} to war skill {s['param']}")

    # FCR
    v = get_all(stats, 'item_fastercastrate')
    if v > 0:
        score += v * 1.0; notes.append(f"{v}% FCR")

    # FHR
    v = get_all(stats, 'item_fastergethitrate')
    if v > 0:
        score += v * 0.5; notes.append(f"{v}% FHR")

    # Life
    v = get_all(stats, 'maxhp')
    if v > 0:
        score += v * 0.3; notes.append(f"+{v} life")

    # Mana
    v = get_all(stats, 'maxmana')
    if v > 0:
        score += v * 0.2; notes.append(f"+{v} mana")

    # Mana regen
    v = get_all(stats, 'manarecovery') + get_all(stats, 'manarecoverybonus')
    if v > 0:
        score += v * 0.35; notes.append(f"{v}% mana regen")

    # Mana after kill
    v = get_all(stats, 'item_manaafterkill')
    if v > 0:
        score += v * 3; notes.append(f"+{v} mana/kill")

    # Life steal
    v = get_all(stats, 'lifedrainmindam')
    if v > 0:
        score += v * 0.4; notes.append(f"{v}% life steal")

    # Mana steal
    v = get_all(stats, 'manadrainmindam')
    if v > 0:
        score += v * 0.5; notes.append(f"{v}% mana steal")

    # Resistances
    fr = get_all(stats, 'fireresist')
    lr = get_all(stats, 'lightresist')
    cr = get_all(stats, 'coldresist')
    pr = get_all(stats, 'poisonresist')
    if fr > 0 or lr > 0 or cr > 0 or pr > 0:
        score += (fr+lr+cr+pr) * 0.25
        if fr == lr == cr == pr and fr > 0:
            notes.append(f"+{fr} all res")
        else:
            parts = []
            if fr: parts.append(f"f{fr}")
            if lr: parts.append(f"l{lr}")
            if cr: parts.append(f"c{cr}")
            if pr: parts.append(f"p{pr}")
            notes.append("res:" + "/".join(parts))

    # Max res
    mfr = get_all(stats, 'maxfireresist')
    mlr = get_all(stats, 'maxlightresist')
    mcr = get_all(stats, 'maxcoldresist')
    mpr = get_all(stats, 'maxpoisonresist')
    if mfr+mlr+mcr+mpr > 0:
        score += (mfr+mlr+mcr+mpr) * 1.5
        notes.append(f"maxres +{mfr}/{mlr}/{mcr}/{mpr}")

    # Crushing blow
    v = get_all(stats, 'item_crushingblow')
    if v > 0:
        score += v * 1.0; notes.append(f"{v}% CB")

    # Str / Dex
    v = get_all(stats, 'strength')
    if v > 0:
        score += v * 0.15; notes.append(f"+{v} str")
    v = get_all(stats, 'dexterity')
    if v > 0:
        score += v * 0.1; notes.append(f"+{v} dex")

    # FRW
    v = get_all(stats, 'item_fastermovevelocity')
    if v > 0:
        score += v * 0.2; notes.append(f"{v}% FRW")

    # DR
    v = get_all(stats, 'normal_damage_reduction') + get_all(stats, 'damageresist')
    if v > 0:
        score += v * 0.5; notes.append(f"{v} DR")

    # MDR
    v = get_all(stats, 'magic_damage_reduction')
    if v > 0:
        score += v * 0.4; notes.append(f"{v} MDR")

    # WEAPON-SPECIFIC
    if slot == 'weapon':
        ed = (get_all(stats, 'damagepercent') + get_all(stats, 'item_maxdamage_percent') +
              get_all(stats, 'melee_mindamage_percent') + get_all(stats, 'item_mindamage_percent'))
        if ed > 0:
            score += ed * 0.6; notes.append(f"{ed}% ED")
        mn = get_all(stats, 'mindamage')
        mx = get_all(stats, 'maxdamage')
        if mx > 0:
            score += (mn+mx) * 0.5; notes.append(f"+{mn}-{mx} dmg")
        v = get_all(stats, 'item_tohit_percent') + get_all(stats, 'tohit')
        if v > 0:
            score += v * 0.1; notes.append(f"+{v} AR")
        v = get_all(stats, 'item_crushingblow')
        if v > 0:
            score += v * 0.5
        v = get_all(stats, 'item_damagetargetac')
        if v < 0:
            score += abs(v) * 0.2; notes.append(f"ITD {v}")

    return score, notes


def main():
    with open(VAULT_FILE, 'r') as f:
        bank = json.load(f)

    code_info = load_code_info()
    unique_names = load_unique_names()
    set_names = load_set_names()

    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    by_slot = {}
    for idx, it in enumerate(bank['items']):
        try:
            parsed = parse_item(it['dna'])
            code = parsed.get('code', '')
            info = code_info.get(code)
            if not info: continue
            base_name, slot = info
            if slot in ('misc', 'armor_other', 'weapon_ranged'): continue

            label = get_item_label(parsed, code_info, unique_names, set_names)
            sc, notes = score_item(parsed, slot)
            by_slot.setdefault(slot, []).append((sc, idx, label, notes))
        except:
            pass

    slot_order = ['weapon', 'helm', 'body', 'gloves', 'boots', 'belt', 'shield', 'ring', 'amulet']
    slot_labels = {
        'weapon': 'WEAPON', 'helm': 'HELM', 'body': 'BODY ARMOR',
        'gloves': 'GLOVES', 'boots': 'BOOTS', 'belt': 'BELT',
        'shield': 'SHIELD', 'ring': 'RING', 'amulet': 'AMULET'
    }

    for slot in slot_order:
        items = sorted(by_slot.get(slot, []), reverse=True)
        print(f"\n=== {slot_labels.get(slot, slot)} ===")
        for rank, (sc, idx, name, notes) in enumerate(items[:top_n], 1):
            print(f"  #{rank} IDX {idx:3d}  {name}  [score={sc:.0f}]")
            print(f"         {', '.join(notes) if notes else '(no scored stats)'}")


if __name__ == '__main__':
    main()

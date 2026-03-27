"""
D2R AI Vault - Build Ranker
Ranks vault items for a specific build.

Usage:
    python build_ranker.py [top_n] [profile]

Profiles:
    warlock  - Echo Warlock (default). FCR-based caster using Echoing Strike.
    merc     - Act 2 Might merc. Polearms/spears, life leech, CB, IAS.

Examples:
    python build_ranker.py 5          # Top 5 per slot for warlock
    python build_ranker.py 5 merc     # Top 5 per slot for merc
"""
import json, sys
from config import VAULT_FILE
from d2r_item_parser import parse_item
from item_names import load_code_info, load_unique_names, load_set_names, get_item_label

# Warlock skill IDs (RotW)
WAR_SKILL_IDS = set(range(373, 403))

# --- Merc-usable item codes ---
MERC_POLEARM_SPEAR = {
    # Polearms (normal / exceptional / elite)
    'hal','vou','scy','pax','bec','bar','wsc',
    '7ha','7vo','7s8','7pa','7bt','7ba','7wc',
    'o7h','o7v','o7s','o7p','o7b','o7a','o7w',
    # Spears (normal / exceptional / elite)
    'spr','tsp','spt','pik','bsd','ssp',
    '7sr','7tr','7sp','7p7','7bk','7ss',
    'o7r','o7t','o7i','o7k','o7l','o7m',
}


def get_all(stats, name):
    return sum(s['val'] for s in stats if s.get('name') == name and s.get('val') is not None)


def score_item(parsed, slot):
    """Score items for Echo Strike Warlock.

    Echo Strike mechanics:
    - Uses FCR (not IAS) — breakpoints: 9/18/30/48/75/125
    - DOES work with: Deadly Strike, Critical Strike, life/mana leech, ED%
    - Does NOT work with: Crushing Blow, Open Wounds, Grief flat damage
    - Priority: FCR > +Skills > ED% > Deadly Strike > Leech > Res > Utility
    """
    stats = parsed.get('stats', []) or []
    score = 0
    notes = []

    # --- TOP TIER: +Skills & FCR ---

    # +All skills — highest priority for Echo Strike damage scaling
    v = get_all(stats, 'item_allskills')
    if v > 0:
        score += v * 30; notes.append(f"+{v} all skills")

    # +Warlock class skills
    v = get_all(stats, 'item_addclassskills')
    if v > 0:
        score += v * 25; notes.append(f"+{v} war skills")

    # +Skill tab
    v = get_all(stats, 'item_addskill_tab')
    if v > 0:
        score += v * 10; notes.append(f"+{v} skill tab")

    # +Single Warlock skill
    for s in stats:
        if s.get('name') == 'item_singleskill' and s.get('val', 0) > 0:
            if s.get('param') in WAR_SKILL_IDS:
                score += s['val'] * 12; notes.append(f"+{s['val']} to war skill {s['param']}")

    # FCR — Echo Strike uses cast rate, not attack speed. 75/125 breakpoints.
    v = get_all(stats, 'item_fastercastrate')
    if v > 0:
        score += v * 4.0; notes.append(f"{v}% FCR")

    # --- HIGH TIER: Damage & Survival ---

    # Deadly Strike — works with Echo Strike, doubles physical hit damage
    v = get_all(stats, 'item_deadlystrike')
    if v > 0:
        score += v * 2.5; notes.append(f"{v}% DS")

    # Life steal — works with Echo Strike, essential for sustain
    v = get_all(stats, 'lifedrainmindam')
    if v > 0:
        score += v * 3.0; notes.append(f"{v}% life steal")

    # Mana steal — works with Echo Strike
    v = get_all(stats, 'manadrainmindam')
    if v > 0:
        score += v * 2.5; notes.append(f"{v}% mana steal")

    # Cannot Be Frozen — essential (Raven Frost), big bonus
    v = get_all(stats, 'item_nofreeze')
    if v > 0:
        score += 25; notes.append("CBF")

    # --- MID TIER: Defense & Utility ---

    # FHR
    v = get_all(stats, 'item_fastergethitrate')
    if v > 0:
        score += v * 0.8; notes.append(f"{v}% FHR")

    # Life
    v = get_all(stats, 'maxhp')
    if v > 0:
        score += v * 0.3; notes.append(f"+{v} life")

    # Mana — less important than life for Echo Strike
    v = get_all(stats, 'maxmana')
    if v > 0:
        score += v * 0.15; notes.append(f"+{v} mana")

    # Mana regen — minor, leech is better
    v = get_all(stats, 'manarecovery') + get_all(stats, 'manarecoverybonus')
    if v > 0:
        score += v * 0.1; notes.append(f"{v}% mana regen")

    # Mana after kill — minor
    v = get_all(stats, 'item_manaafterkill')
    if v > 0:
        score += v * 0.5; notes.append(f"+{v} mana/kill")

    # Resistances
    fr = get_all(stats, 'fireresist')
    lr = get_all(stats, 'lightresist')
    cr = get_all(stats, 'coldresist')
    pr = get_all(stats, 'poisonresist')
    if fr > 0 or lr > 0 or cr > 0 or pr > 0:
        score += (fr+lr+cr+pr) * 0.3
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
        score += (mfr+mlr+mcr+mpr) * 2.0
        notes.append(f"maxres +{mfr}/{mlr}/{mcr}/{mpr}")

    # Crushing Blow — DOES NOT WORK with Echo Strike, score = 0
    v = get_all(stats, 'item_crushingblow')
    if v > 0:
        notes.append(f"{v}% CB (no effect)")

    # Open Wounds — DOES NOT WORK with Echo Strike, score = 0
    v = get_all(stats, 'item_openwounds')
    if v > 0:
        notes.append(f"{v}% OW (no effect)")

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
        score += v * 0.8; notes.append(f"{v} DR")

    # MDR
    v = get_all(stats, 'magic_damage_reduction')
    if v > 0:
        score += v * 0.5; notes.append(f"{v} MDR")

    # --- WEAPON-SPECIFIC ---
    if slot == 'weapon':
        # ED% — scales Echo Strike damage directly
        ed = (get_all(stats, 'damagepercent') + get_all(stats, 'item_maxdamage_percent') +
              get_all(stats, 'melee_mindamage_percent') + get_all(stats, 'item_mindamage_percent'))
        if ed > 0:
            score += ed * 1.2; notes.append(f"{ed}% ED")
        # Flat damage — base weapon damage matters for Echo Strike
        mn = get_all(stats, 'mindamage')
        mx = get_all(stats, 'maxdamage')
        if mx > 0:
            score += (mn+mx) * 0.8; notes.append(f"+{mn}-{mx} dmg")
        # AR
        v = get_all(stats, 'item_tohit_percent') + get_all(stats, 'tohit')
        if v > 0:
            score += v * 0.1; notes.append(f"+{v} AR")

    return score, notes


# --- Act 2 Merc Scoring ---
def _fmt_res(fr, lr, cr, pr):
    """Format resistances: show 'all res' when equal, individual otherwise."""
    if fr == lr == cr == pr and fr > 0:
        return f"+{fr} all res"
    parts = []
    if fr: parts.append(f"f{fr}")
    if lr: parts.append(f"l{lr}")
    if cr: parts.append(f"c{cr}")
    if pr: parts.append(f"p{pr}")
    return "res:" + "/".join(parts) if parts else ""


def score_merc(parsed, slot):
    """Score items for Act 2 Might merc.
    Priorities: life leech > ED/IAS/CB > resistances > defense > utility.
    Ethereal is a bonus (mercs don't lose durability).
    """
    stats = parsed.get('stats', []) or []
    score = 0
    notes = []

    # Life leech — #1 merc survival stat
    v = get_all(stats, 'lifedrainmindam')
    if v > 0:
        score += v * 10; notes.append(f"{v}% LL")

    # Enhanced damage
    ed = (get_all(stats, 'item_maxdamage_percent') +
          get_all(stats, 'secondary_maxdamage_percent') +
          get_all(stats, 'maxdamage_percent') +
          get_all(stats, 'damagepercent'))
    if ed > 0:
        score += ed * 0.5; notes.append(f"{ed}% ED")

    # IAS
    v = get_all(stats, 'item_fasterattackrate')
    if v > 0:
        score += v * 2; notes.append(f"{v}% IAS")

    # Crushing Blow — huge for boss killing with Might aura
    v = get_all(stats, 'item_crushingblow')
    if v > 0:
        score += v * 3; notes.append(f"{v}% CB")

    # Resistances — broken out individually
    fr = get_all(stats, 'fireresist')
    lr = get_all(stats, 'lightresist')
    cr = get_all(stats, 'coldresist')
    pr = get_all(stats, 'poisonresist')
    total_res = fr + lr + cr + pr
    if total_res > 0:
        score += total_res * 0.3
        notes.append(_fmt_res(fr, lr, cr, pr))

    # Life
    v = get_all(stats, 'maxhp')
    if v > 0:
        score += v * 0.2; notes.append(f"+{v} life")

    # +All skills
    v = get_all(stats, 'item_allskills')
    if v > 0:
        score += v * 5; notes.append(f"+{v} all skills")

    # FHR
    v = get_all(stats, 'item_fastergethitrate')
    if v > 0:
        score += v * 0.5; notes.append(f"{v}% FHR")

    # Ethereal — mercs don't lose durability, free 50% ED on weapons / +50% def on armor
    if parsed.get('is_ethereal'):
        score += 15; notes.append("ETH")

    # Defense (for helm/armor)
    if slot != 'weapon':
        defense = parsed.get('defense') or 0
        if defense > 0:
            score += defense * 0.02

    # Open Wounds
    v = get_all(stats, 'item_openwounds')
    if v > 0:
        score += v * 1.5; notes.append(f"{v}% OW")

    # Deadly Strike
    v = get_all(stats, 'item_deadlystrike')
    if v > 0:
        score += v * 1.5; notes.append(f"{v}% DS")

    # Strength (helps equip better gear)
    v = get_all(stats, 'strength')
    if v > 0:
        score += v * 0.3; notes.append(f"+{v} str")

    # Flat damage (weapon only)
    if slot == 'weapon':
        mn = get_all(stats, 'mindamage')
        mx = get_all(stats, 'maxdamage')
        if mx > 0:
            score += (mn + mx) * 0.5; notes.append(f"+{mn}-{mx} dmg")

    # Half freeze duration
    v = get_all(stats, 'item_halffreezeduration')
    if v > 0:
        score += 3; notes.append("half freeze")

    return score, notes


# --- Main ---
PROFILES = {
    'warlock': {
        'name': 'Echo Warlock',
        'scorer': score_item,
        'slots': ['weapon', 'helm', 'body', 'gloves', 'boots', 'belt', 'shield', 'ring', 'amulet'],
        'slot_filter': None,  # all slots
    },
    'merc': {
        'name': 'Act 2 Might Merc',
        'scorer': score_merc,
        'slots': ['weapon', 'helm', 'body'],
        'slot_filter': lambda code, slot: (
            slot == 'helm' or slot == 'body' or
            (slot == 'weapon' and code in MERC_POLEARM_SPEAR)
        ),
    },
}

SLOT_LABELS = {
    'weapon': 'WEAPON', 'helm': 'HELM', 'body': 'BODY ARMOR',
    'gloves': 'GLOVES', 'boots': 'BOOTS', 'belt': 'BELT',
    'shield': 'SHIELD', 'ring': 'RING', 'amulet': 'AMULET',
}


def main():
    # Parse args
    top_n = 3
    profile_name = 'warlock'
    for arg in sys.argv[1:]:
        if arg.isdigit():
            top_n = int(arg)
        elif arg in PROFILES:
            profile_name = arg
        else:
            print(f"Unknown argument: {arg}")
            print(f"Usage: python build_ranker.py [top_n] [{'/'.join(PROFILES)}]")
            return

    profile = PROFILES[profile_name]
    scorer = profile['scorer']
    slot_filter = profile['slot_filter']

    with open(VAULT_FILE, 'r') as f:
        bank = json.load(f)

    code_info = load_code_info()
    unique_names = load_unique_names()
    set_names = load_set_names()

    print(f"=== {profile['name']} — Top {top_n} per slot ===")

    by_slot = {}
    for idx, it in enumerate(bank['items']):
        try:
            parsed = parse_item(it['dna'])
            code = parsed.get('code', '')
            info = code_info.get(code)
            if not info: continue
            base_name, slot = info
            if slot in ('misc', 'armor_other', 'weapon_ranged'): continue

            # Apply slot filter (e.g. merc can only use polearms/spears)
            if slot_filter and not slot_filter(code, slot):
                continue

            label = get_item_label(parsed, code_info, unique_names, set_names)
            sc, notes = scorer(parsed, slot)
            by_slot.setdefault(slot, []).append((sc, idx, label, notes))
        except:
            pass

    for slot in profile['slots']:
        items = sorted(by_slot.get(slot, []), reverse=True)
        print(f"\n--- {SLOT_LABELS.get(slot, slot)} ---")
        if not items:
            print("  (none in vault)")
            continue
        for rank, (sc, idx, name, notes) in enumerate(items[:top_n], 1):
            note_str = ', '.join(notes) if notes else '(no scored stats)'
            print(f"  #{rank} [{idx:3d}] {name}  [score={sc:.0f}]")
            print(f"         {note_str}")


if __name__ == '__main__':
    main()

"""
D2R Reign of the Warlock (RotW) Item Parser
Parses items from the AI vault (D2R_AI_Bank.json).

Key RotW differences from standard D2R:
- Unique/Set IDs use 13 bits (not 12)
- Custom stat IDs in ItemStatCost with 0 SaveBits (markers)
- Stat chaining for damage pairs (fire/light/cold/poison)
"""
import json, binascii, os

# --- Load mod data ---
_dir = os.path.dirname(os.path.abspath(__file__))
_map_path = os.path.join(_dir, 'PreciseModMap_v3.json')
with open(_map_path, 'r') as f:
    MOD_MAP = json.load(f)

# --- Huffman table (from dschu012/d2s) ---
HUFFMAN_CHARS = {
    " ": (1, 2), "b": (10, 4), "s": (4, 4), "c": (2, 5), "a": (15, 5),
    "g": (11, 5), "h": (24, 5), "l": (23, 5), "m": (22, 5), "p": (19, 5),
    "r": (7, 5), "t": (6, 5), "u": (16, 5), "w": (0, 5), "x": (28, 5),
    "7": (30, 5), "9": (14, 5), "2": (12, 6), "8": (8, 6), "d": (35, 6),
    "e": (3, 6), "f": (50, 6), "k": (18, 6), "n": (44, 6), "1": (31, 7),
    "3": (91, 7), "6": (123, 7), "i": (63, 7), "o": (127, 7), "v": (59, 7),
    "y": (40, 7), "0": (223, 8), "4": (95, 8), "5": (104, 8), "q": (155, 8),
    "z": (27, 8), "j": (232, 9),
}

def _build_decode_tree():
    root = {}
    for char, (value, length) in HUFFMAN_CHARS.items():
        bits_str = ""
        for i in range(length):
            bits_str += str((value >> i) & 1)
        node = root
        for i, bit in enumerate(bits_str):
            if i == len(bits_str) - 1:
                node[bit] = char
            else:
                if bit not in node:
                    node[bit] = {}
                node = node[bit]
    return root

DECODE_TREE = _build_decode_tree()

# --- Item type classification ---
WEAPON_CODES = {
    "hax","axe","2ax","mpi","wax","lax","bax","btx","gax","gix",
    "ssd","scm","sbr","flc","crs","bsd","lsd","wsd","2hs","clm","gis","bsw","flb","gsd",
    "dgr","dir","kri","bld","tkf","tax","bkf",
    "clb","spc","mac","mst","fla","wha","mau","gma",
    "sst","lst","cst","bst","wst",
    "pik","hal","pol","scy","pax","bar","vou","wsc",
    "sbb","lbb","swb","lwb","lxb","mxb","hxb","rxb",
    "jav","pil","ssp","gps","tsp","tri",
    "wnd","ywn","bwn","gwn",
    "scp","wsp","gsc",
    "ktr","wrb","axf","ces","clw","btl","skr",
    "ob1","ob2","ob3","ob4","ob5","ob6","ob7","ob8","ob9","oba","obb","obc","obd","obe","obf",
    "am1","am2","am3","am4","am5","am6","am7","am8","am9","ama","amb","amc","amd","ame","amf",
    "spr","brn","cbw","hbw","lbw","sbw","spt","whm","bal","d33","g33","glv","gpl","gpm",
    "hdm","hfh","hst","leg","msf","opl","opm","ops",
    "92a","92h","9ar","9ax","9b7","9b8","9b9","9ba","9bk","9bl","9br","9bs","9bt","9bw",
    "9cl","9cm","9cr","9cs","9dg","9di","9fb","9fc","9fl","9ga","9gd","9gi","9gl","9gm","9gs",
    "9gw","9h9","9ha","9ja","9kr","9la","9ls","9lw","9m9","9ma","9mp","9mt","9p9","9pa","9pi",
    "9qr","9qs","9s8","9s9","9sb","9sc","9sm","9sp","9sr","9ss","9st","9ta","9tk","9tr","9ts",
    "9tw","9vo","9wa","9wb","9wc","9wd","9wh","9wn","9ws","9xf","9yw",
    "6bs","6cb","6cs","6hb","6hx","6l7","6lb","6ls","6lw","6lx","6mx","6rx","6s7","6sb","6ss","6sw","6ws",
    "72a","72h","7ar","7ax","7b7","7b8","7ba","7bk","7bl","7br","7bs","7bt","7bw","7cl","7cm",
    "7cr","7cs","7dg","7di","7fb","7fc","7fl","7ga","7gd","7gi","7gl","7gm","7gs","7gw","7h7",
    "7ha","7ja","7kr","7la","7ls","7lw","7m7","7ma","7mp","7mt","7o7","7p7","7pa","7pi","7qr",
    "7qs","7s7","7s8","7sb","7sc","7sm","7sp","7sr","7ss","7st","7ta","7tk","7tr","7ts","7tw",
    "7vo","7wa","7wb","7wc","7wd","7wh","7wn","7ws","7xf","7yw",
    "8bs","8cb","8cs","8hb","8hx","8l8","8lb","8ls","8lw","8lx","8mx","8rx","8s8","8sb","8ss","8sw","8ws",
    "qf1","qf2",
}

ARMOR_CODES = {
    "cap","skp","hlm","fhl","ghm","crn","msk","bhm",
    "buc","sml","lrg","kit","tow","gts","bsh","spk",
    "qui","lea","hla","stu","rng","scl","chn","brs","spl","plt","fld","gth","ful","aar","ltp",
    "lgl","vgl","mgl","tgl","hgl",
    "lbt","vbt","mbt","tbt","hbt",
    "lbl","vbl","mbl","tbl","hbl",
    "ci0","ci1","ci2","ci3",
    "dr1","dr2","dr3","dr4","dr5","dr6","dr7","dr8","dr9","dra","drb","drc","drd","dre","drf",
    "ba1","ba2","ba3","ba4","ba5","ba6","ba7","ba8","ba9","baa","bab","bac","bad","bae","baf",
    "pa1","pa2","pa3","pa4","pa5","pa6","pa7","pa8","pa9","paa","pab","pac","pad","pae","paf",
    "ne1","ne2","ne3","ne4","ne5","ne6","ne7","ne8","ne9","nea","neb","ned","nee","nef","neg",
    "xap","xar","xcl","xea","xh9","xhb","xhg","xhl","xhm","xhn","xit","xkp","xla","xlb",
    "xld","xlg","xlm","xlt","xmb","xmg","xml","xng","xow","xpk","xpl","xrg","xrn","xrs",
    "xsh","xsk","xtb","xtg","xth","xtp","xts","xtu","xuc","xui","xul","xvb","xvg",
    "uap","uar","ucl","uea","uh9","uhb","uhc","uhg","uhl","uhm","uhn","uit","ukp","ula","ulb",
    "ulc","uld","ulg","ulm","ult","umb","umc","umg","uml","ung","uow","upk","upl","urg","urn",
    "urs","ush","usk","utb","utc","utg","uth","utp","uts","utu","uuc","uui","uul","uvb","uvc","uvg",
    "zhb","zlb","zmb","ztb","zvb",
}

STACKABLE_CODES = {
    "hp1","hp2","hp3","hp4","hp5","mp1","mp2","mp3","mp4","mp5",
    "rvs","rvl","yps","vps","wms","tsc","isc","key","aqv","cqv",
    "gpl","opl","gpm","opm","gps","ops","gld",
    "rps","rpl","bps","bpl",
    "tkf","tax","bkf","bal","jav","pil","ssp","glv","tsp",
    "9tk","9ta","9bk","9b8","9ja","9pi","9s9","9gl","9ts",
    "7tk","7ta","7bk","7b8","7ja","7pi","7s7","7gl","7ts",
    "am5","ama","amf",
}

QUALITY_NAMES = {
    1: "Low", 2: "Normal", 3: "Superior", 4: "Magic",
    5: "Set", 6: "Rare", 7: "Unique", 8: "Crafted"
}


class BitReader:
    def __init__(self, hex_dna):
        data = binascii.unhexlify(hex_dna)
        self.bits = "".join([bin(b)[2:].zfill(8)[::-1] for b in data])
        self.pos = 0

    def read(self, n):
        if self.pos + n > len(self.bits):
            return None
        chunk = self.bits[self.pos:self.pos + n]
        self.pos += n
        return int(chunk[::-1], 2)

    def read_huffman_char(self):
        node = DECODE_TREE
        while isinstance(node, dict):
            if self.pos >= len(self.bits):
                return None
            node = node.get(self.bits[self.pos])
            self.pos += 1
            if node is None:
                return None
        return node

    def read_item_code(self):
        code = ""
        for _ in range(4):
            ch = self.read_huffman_char()
            if ch is None: return None
            code += ch
        return code.rstrip()

    def remaining(self):
        return len(self.bits) - self.pos


# D2 hardcoded stat chains
STAT_CHAINS = {
    48: [49],       # firemindam -> firemaxdam
    50: [51],       # lightmindam -> lightmaxdam
    52: [53],       # magicmindam -> magicmaxdam
    54: [55, 56],   # coldmindam -> coldmaxdam + coldlength
    57: [58, 59],   # poisonmindam -> poisonmaxdam + poisonlength
}


def _read_stat_value(r, stat_id):
    sid_str = str(stat_id)
    if sid_str in MOD_MAP["stats"]:
        cfg = MOD_MAP["stats"][sid_str]
        param_bits = cfg.get("param", 0)
        param = None
        if param_bits > 0:
            param = r.read(param_bits)
        val_raw = r.read(cfg["bits"])
        if val_raw is not None:
            val = val_raw - cfg["add"]
        else:
            val = None
        return {
            "id": stat_id,
            "name": cfg["name"],
            "val": val,
            "param": param,
        }
    return None


def _read_properties(r):
    stats = []
    while r.remaining() >= 9:
        stat_id = r.read(9)
        if stat_id is None or stat_id == 511:
            break
        result = _read_stat_value(r, stat_id)
        if result is not None:
            stats.append(result)
            if stat_id in STAT_CHAINS:
                for chain_id in STAT_CHAINS[stat_id]:
                    chain_result = _read_stat_value(r, chain_id)
                    if chain_result is not None:
                        stats.append(chain_result)
        else:
            stats.append({
                "id": stat_id,
                "name": f"rotw_marker_{stat_id}",
                "val": None,
                "marker": True,
            })
    return stats


def parse_item(hex_dna):
    r = BitReader(hex_dna)

    flags_raw = r.read(32)
    flags = {}
    flag_bits = r.bits[:32]
    flags['identified'] = flag_bits[4] == '1'
    flags['socketed'] = flag_bits[11] == '1'
    flags['simple'] = flag_bits[21] == '1'
    flags['ethereal'] = flag_bits[22] == '1'
    flags['personalized'] = flag_bits[24] == '1'
    flags['runeword'] = flag_bits[26] == '1'

    version = r.read(3)
    location = r.read(3)
    equipped = r.read(4)
    col = r.read(4)
    row = r.read(4)
    container = r.read(3)

    item_code = r.read_item_code()
    if item_code is None:
        return {"error": "Failed to decode item code"}

    if flags['simple']:
        r.read(1)
        return {"code": item_code, "simple": True}

    filled_sockets = r.read(3)
    fingerprint = r.read(32)
    level = r.read(7)
    quality = r.read(4)

    has_pic = r.read(1)
    if has_pic:
        r.read(3)

    has_class = r.read(1)
    if has_class:
        r.read(11)

    unique_id = None
    set_id = None

    if quality == 1:
        r.read(3)
    elif quality == 3:
        r.read(3)
    elif quality == 4:
        r.read(11)  # prefix
        r.read(11)  # suffix
    elif quality == 5:
        set_id = r.read(13)
    elif quality in (6, 8):
        r.read(8)
        r.read(8)
        for _ in range(3):
            if r.read(1): r.read(11)
            if r.read(1): r.read(11)
    elif quality == 7:
        unique_id = r.read(13)

    if flags['runeword']:
        r.read(12)
        r.read(4)

    if flags['personalized']:
        for _ in range(16):
            if r.read(8) == 0:
                break

    if item_code in ("tbk", "ibk"):
        r.read(5)

    r.read(1)  # timestamp

    is_armor = item_code in ARMOR_CODES
    is_weapon = item_code in WEAPON_CODES

    defense = None
    max_durability = None
    current_durability = None
    quantity = None

    if is_armor:
        defense_raw = r.read(11)
        defense = defense_raw - 10 if defense_raw is not None else None

    if is_armor or is_weapon:
        max_durability = r.read(8)
        if max_durability and max_durability > 0:
            current_durability = r.read(9)

    if item_code in STACKABLE_CODES:
        quantity = r.read(9)

    total_sockets = None
    if flags['socketed']:
        total_sockets = r.read(4)

    plist_flag = 0
    if quality == 5:
        plist_flag = r.read(5)

    stats = _read_properties(r)

    set_bonuses = []
    if quality == 5 and plist_flag:
        for i in range(5):
            if plist_flag & (1 << i):
                set_bonuses.append(_read_properties(r))

    result = {
        "code": item_code,
        "simple": False,
        "level": level,
        "quality": QUALITY_NAMES.get(quality, f"q{quality}"),
        "quality_id": quality,
        "flags": flags,
        "unique_id": unique_id,
        "set_id": set_id,
        "defense": defense,
        "max_durability": max_durability,
        "current_durability": current_durability,
        "quantity": quantity,
        "total_sockets": total_sockets,
        "ethereal": flags['ethereal'],
        "stats": stats,
    }
    if set_bonuses:
        result["set_bonuses"] = set_bonuses
    return result


if __name__ == "__main__":
    from config import VAULT_FILE
    with open(VAULT_FILE, 'r') as f:
        bank = json.load(f)

    print(f"D2R RotW Item Parser - Testing first 30 of {len(bank['items'])} items")
    print("=" * 70)

    for idx in range(min(30, len(bank['items']))):
        dna = bank['items'][idx]['dna']
        try:
            item = parse_item(dna)
        except Exception as e:
            print(f"\nIDX {idx}: ERROR - {e}")
            continue

        if item.get('simple'):
            print(f"\nIDX {idx}: {item['code']} (simple)")
            continue

        qual = item['quality']
        uid_info = f" UID={item['unique_id']}" if item['unique_id'] is not None else ""
        if item.get('set_id') is not None:
            uid_info = f" SetID={item['set_id']}"
        eth = " [ETH]" if item['ethereal'] else ""
        def_info = f" Def={item['defense']}" if item['defense'] is not None else ""

        print(f"\nIDX {idx}: {item['code']} - {qual}{uid_info}{eth}{def_info} (Lvl {item['level']})")
        for s in item['stats']:
            if s.get('marker'): continue
            p = f" (param={s['param']})" if s.get('param') is not None else ""
            print(f"  {s['name']}: {s['val']}{p}")

#!/usr/bin/env python3
"""Builds data.js for the guide from a WoWSims Forever checkout and the sim runs.

    python3 tools/build_data.py --forever ~/forever --runs RUNS_DIR --out data.js

RUNS_DIR holds, per loadout (weave-, nweave-, turret-, bmturret- and melee- max, max-av and cheap):
  <id>.gear.json   the loadout's gear: {"head": [id, enchant, suffix], ...}
  <id>.guide.json  the per-slot runs: {group: {"base": dps, "rows": [{"move": {...}, "d": .., "m": ..}]}}
  <id>.cond.json   optional, the flipped-condition runs: {group: {"best": {"cond", "d"}, "rows": [{"move", "cond", "d", "m"}]}}
  <id>.scenario.json  optional, the best moves under a raid condition the set does not assume:
                   {group: [{"when", "detail", "rows": [{"move", "d", "m", "note"?}]}]}, Δ against the set under the same condition
  <id>.long.json   optional, the long fight toggle: {"label", "pieces": {slot: spec}, "at": [{"t", "d", "m"}], "note"}
and meta.json: {"loadouts": {id: {"build", "talents", "rotation", "hit"}}, "ep": {...}, "dw": [...], ...}.
"""
import argparse, json, os, re, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument('--forever', required=True)
ap.add_argument('--runs', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

db = json.load(open(os.path.join(a.forever, 'assets/database/db.json')))
items = {it['id']: it for it in db['items']}


def side_of(it):
    """1 Alliance, 2 Horde, 0 both: the item's faction, or else the one faction all its sources name. A source that
    names no faction is open to both."""
    if it.get('factionRestriction'):
        return it['factionRestriction']
    fs = {v.get('faction') or v.get('factionId') or 0 for src in it.get('sources') or [] for v in src.values() if v}
    return fs.pop() if len(fs) == 1 else 0


def twin_sig(it):
    return (it.get('type'), it.get('armorType'), it.get('weaponType'), it.get('rangedWeaponType'), it.get('handType'),
            it.get('weaponSpeed'), it.get('quality'), json.dumps(it.get('scalingOptions'), sort_keys=True))


# The Alliance copy of a Horde item has the same stats, slot and quality under another name (Darkspear and Theramore,
# Defiler's and Highlander's, Scout's and Sentinel's). Cleansed Vilebranch Medallion names no faction and no source.
ALLIANCE_BY_HAND = {19120: 270275}
_by_sig = {}
for _it in db['items']:
    _by_sig.setdefault(twin_sig(_it), []).append(_it)


def alliance_twin(it):
    if it['id'] in ALLIANCE_BY_HAND:
        return items[ALLIANCE_BY_HAND[it['id']]]
    if side_of(it) != 2:
        return None
    twins = [o for o in _by_sig[twin_sig(it)] if side_of(o) == 1]
    return twins[0] if len(twins) == 1 else None
zones = {z['id']: z['name'] for z in db['zones']}
npcs = {n['id']: n for n in db['npcs']}
facs = {f['id']: f['name'] for f in db['factions']}
suffixes = {s['id']: s for s in db['randomSuffixes']}
meta = json.load(open(os.path.join(a.runs, 'meta.json')))

PROF = {1: 'Alchemy', 2: 'Blacksmithing', 3: 'Enchanting', 4: 'Engineering', 8: 'Leatherworking', 11: 'Tailoring'}
REP = {4: 'Neutral', 5: 'Friendly', 6: 'Honored', 7: 'Revered', 8: 'Exalted'}
DUNGEONS = {1584, 1583, 2017, 2057, 2557, 2100, 1477, 1176, 1337, 722, 491, 796, 209, 719, 721, 1581, 717, 2437, 718,
            16620, 16554, 16842, 17191, 16550, 16919, 16651}
BG_VENDORS = {'Samuel Hawke', 'Rutherford Twing', 'Kelm Hargunth', 'Illiyana Moonblaze', 'Grunnda Wolfheart',
              'Jekyll Flandring', 'Gaelden Hammersmith', 'Thanthaldis Snowgleam'}
BG_REP = {509, 510}
BG_QUESTS = ('Korrak', 'Hero of the Frostwolf', 'Hero of the Stormpike')
# The tier rules the presets were built with (see the guide's Method page).
CHEAP_CRAFTS = {15062, 15063, 250619}  # Black Dragonscale Helm 252605 is a crafted epic: Max (2026-11-20)
MAX_CRAFTS = {252483, 279253, 252484, 12784, 12798, 12783}
MAX_SOURCELESS = {1728}
CHEAP_SOURCELESS = {6622, 13023}  # Sword of Zeal, Eaglehorn Long Bow
STAT = ['Strength', 'Agility', 'Stamina', 'Intellect']
TYPE = {1: 'Head', 2: 'Neck', 3: 'Shoulder', 4: 'Back', 5: 'Chest', 6: 'Wrist', 7: 'Hands', 8: 'Waist', 9: 'Legs',
        10: 'Feet', 11: 'Finger', 12: 'Trinket', 13: 'Weapon', 14: 'Ranged'}
ARMOR = {1: 'Cloth', 2: 'Leather', 3: 'Mail', 4: 'Plate'}
WEAPON = {1: 'Axe', 2: 'Dagger', 3: 'Fist Weapon', 4: 'Mace', 6: 'Polearm', 7: 'Shield', 8: 'Staff', 9: 'Sword'}
HAND = {1: 'Main Hand', 2: 'One-Hand', 3: 'Off Hand', 4: 'Two-Hand'}
RANGED = {1: 'Bow', 2: 'Crossbow', 3: 'Gun', 4: 'Thrown'}
SLOT_TYPE = {'head': 1, 'neck': 2, 'shoulder': 3, 'back': 4, 'chest': 5, 'wrist': 6, 'hands': 7, 'waist': 8, 'legs': 9,
             'feet': 10, 'finger1': 11, 'finger2': 11, 'trinket1': 12, 'trinket2': 12, 'main_hand': 13, 'off_hand': 13,
             'ranged': 14}

MOB = {1: 'Beasts', 2: 'Demons', 3: 'Dragonkin', 4: 'Elementals', 5: 'Giants', 6: 'Humanoids', 7: 'Mechanicals', 8: 'Undead'}
# The biomes and creature types the cards can be ranked for: (axis, picker label, figure label with it, without it).
# <id>.cond.json holds, per condition, every item with a bonus there run against the set under that condition, and
# under 'none' all of them on the sets' own boss (no creature type, no biome).
MOB_ID = {1: 'beast', 2: 'demon', 3: 'dragonkin', 4: 'elemental', 5: 'giant', 6: 'humanoid', 7: 'mechanical', 8: 'undead'}
AREA_ID = {1: 'forestgrassland', 2: 'mountainous', 3: 'snowy', 4: 'desert', 5: 'swamp', 6: 'wasteland', 7: 'haunted',
           8: 'cavernous', 9: 'volcanic', 10: 'strongholdscities'}
AREA_NAME = {'forestgrassland': 'Forest/Grassland', 'mountainous': 'Mountainous', 'snowy': 'Snowy', 'desert': 'Desert',
             'swamp': 'Swamp', 'wasteland': 'Wasteland', 'haunted': 'Haunted', 'cavernous': 'Cavernous',
             'volcanic': 'Volcanic', 'strongholdscities': 'Strongholds and cities'}
CONDS = {**{MOB_ID[k]: ('mob', MOB[k] if k in (3, 8) else MOB[k][:-1], f'Against {MOB[k]}', f'Not against {MOB[k]}') for k in MOB_ID},
         **{c: ('biome', n, f'In {n}', f'Outside {n}') for c, n in AREA_NAME.items()}}


def item_conds(iid):
    it = items.get(iid, {})
    return {MOB_ID[t] for t in it.get('mobTypes') or [] if t in MOB_ID} | {AREA_ID[x] for x in it.get('areaTypes') or [] if x in AREA_ID}


# The tier of every item as the runs' pools had it (pools.py dumps, folded: cheap if the Cheap pool allows it, else
# max), and the Premier pieces, of which a Cheap set wears two at most. Without them the rules below apply.
TIERS = {int(k): v for k, v in json.load(open(os.path.join(a.runs, 'tiers.json'))).items()} if os.path.exists(os.path.join(a.runs, 'tiers.json')) else {}
PREMIER = set(json.load(open(os.path.join(a.runs, 'cap.json')))['ids']) if os.path.exists(os.path.join(a.runs, 'cap.json')) else set()
PREMIER_CAP = json.load(open(os.path.join(a.runs, 'cap.json')))['max'] if PREMIER else 0

# Reputation a vendor asks for that the game files do not carry (the Wowhead tooltip names it).
VENDOR_REP = {19325: 'Reputation: Frostwolf Clan Exalted'}


def sources(it):
    out, kinds = [], set()
    for s in it.get('sources', []):
        k, v = next(iter(s.items()))
        if k == 'drop':
            n = npcs.get(v.get('npcId'), {})
            zid = v.get('zoneId') or n.get('zoneId')
            who = n.get('name') or v.get('otherName') or ''
            if any(c in who for c in '"[]()%'):
                who = ''  # a few database names are template text, not an NPC
            if v.get('otherName') == 'World Drop':
                out.append('World drop'); kinds.add('world')
            else:
                where = f" ({zones[zid]})" if zid in zones else ''
                out.append(f"Drop: {who.strip()}{where}" if who.strip() else f"Drop{where}")
                kinds.add('dungeon' if zid in DUNGEONS else 'world')
        elif k == 'quest':
            if v.get('faction') == 1:
                continue
            out.append(f"Quest: {v.get('name')}")
            kinds.add('bg' if any(q in v.get('name', '') for q in BG_QUESTS) else 'quest')
        elif k == 'soldBy':
            if v.get('faction') == 1:
                continue
            out.append(f"Vendor: {v.get('npcName')}" + (f" ({zones[v['zoneId']]})" if v.get('zoneId') in zones else ''))
            kinds.add('bg' if v.get('npcName') in BG_VENDORS else 'vendor')
        elif k == 'rep':
            out.append(f"Reputation: {facs.get(v.get('repFactionId'), v.get('repFactionId'))} {REP.get(v.get('repLevel'), '')}".strip())
            kinds.add('bg' if v.get('repFactionId') in BG_REP else 'rep')
        elif k == 'crafted':
            out.append(f"Crafted: {PROF.get(v.get('profession'), 'Profession')}")
            kinds.add('craft')
        elif k == 'pvp':
            kinds.add('bg')
            if it['id'] in PREMIER:
                out.append('PvP: Premier gear')
    if it['id'] in VENDOR_REP:
        out.insert(1, VENDOR_REP[it['id']])  # second, so the card's two source lines show it
    out = list(dict.fromkeys(out))
    if not out:
        if it.get('randomSuffixOptions'):
            out, kinds = ['World drop (random suffix, Auction House)'], {'world'}
        elif it['id'] < 200000:  # a classic item the game files give no source for, as the tier rules read it
            out, kinds = ['World drop (Auction House)'], {'world'}
        else:
            out, kinds = ['New Forever item: no source in the game files yet'], {'unknown'}
    return out[:4], sorted(kinds)


def tier(it):
    if it['id'] in TIERS:
        return TIERS[it['id']]
    srcs = it.get('sources', [])
    kinds = set()
    for s in srcs:
        k, v = next(iter(s.items()))
        if k == 'quest':
            kinds.add('quest')
        elif k == 'rep':
            kinds.add('bg' if v.get('repFactionId') in BG_REP else ('rep-high' if v.get('repLevel', 0) >= 7 else 'rep'))
        elif k == 'soldBy':
            kinds.add('bg' if v.get('npcName') in BG_VENDORS else 'vendor')
        elif k == 'crafted':
            kinds.add('craft')
        elif k == 'pvp':
            kinds.add('bg')
        else:
            kinds.add(k)
    if kinds & {'bg'} and not any(q in json.dumps(srcs) for q in BG_QUESTS):
        return 'max'
    if it.get('setName') == 'Beastmaster Armor':
        return 'max'
    if not srcs:
        if it.get('randomSuffixOptions'):
            return 'cheap'
        if it['id'] in CHEAP_SOURCELESS:
            return 'cheap'
        return 'max' if (it['id'] in MAX_SOURCELESS or it['id'] < 200000) else 'cheap'
    if 'rep-high' in kinds and not kinds & {'drop', 'quest', 'rep'}:
        return 'max'
    if kinds == {'craft'}:
        if it['id'] in CHEAP_CRAFTS:
            return 'cheap'
        return 'max' if (it['id'] in MAX_CRAFTS or it.get('quality', 0) >= 4) else 'cheap'
    return 'cheap'


icon_cache_path = os.path.join(os.path.dirname(__file__), 'icons.json')
icon_cache = json.load(open(icon_cache_path)) if os.path.exists(icon_cache_path) else {}


def icon(it):
    if it.get('icon'):
        return it['icon']
    key = str(it['id'])
    if key not in icon_cache:
        try:
            url = f"https://nether.wowhead.com/forever/tooltip/item/{it['id']}?lvl=60&dataEnv=16"
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'hunter-guide-build'}), timeout=15) as r:
                icon_cache[key] = json.load(r).get('icon', '')
        except Exception:
            icon_cache[key] = ''
    return icon_cache[key]


def pct(v, per):
    x = v / per
    return f"{x:g}%"


def item_data(iid, used_suffixes):
    it = items[iid]
    so = it.get('scalingOptions', {}).get('0', {})
    st = {int(k): v for k, v in so.get('stats', {}).items()}
    white = [[STAT[k], st[k]] for k in range(4) if st.get(k)]
    green = []
    if st.get(14) or st.get(15):
        ap = st.get(14, 0)
        green.append(f"Equip: +{ap} Attack Power." if st.get(14) == st.get(15) else f"Equip: +{st.get(15, 0)} ranged Attack Power.")
    if st.get(17):
        green.append(f"Equip: Improves your chance to hit by {pct(st[17], 10)}.")
    if st.get(18):
        green.append(f"Equip: Improves your chance to get a critical strike by {pct(st[18], 14)}.")
    if st.get(19):
        green.append(f"Equip: Improves your attack speed by {pct(st[19], 10)}.")
    AREA = {1: 'Forest/Grassland', 2: 'Mountainous', 3: 'Snowy', 4: 'Desert', 5: 'Swamp', 6: 'Wasteland', 7: 'Haunted',
            8: 'Cavernous', 9: 'Volcanic', 10: 'Stronghold and city'}
    for area in so.get('areaStats', []):
        ast = {int(k): v for k, v in area.get('stats', {}).items()}
        if ast.get(14):
            green.append(f"In {AREA.get(area.get('areaType'), 'some')} areas: +{ast[14]} Attack Power.")
    for mob in so.get('mobTypeStats', []):
        mst = {int(k): v for k, v in mob.get('stats', {}).items()}
        if mst.get(14):
            names = ' and '.join(MOB.get(t, 'some creatures') for t in mob.get('mobTypes', []))
            green.append(f"Equip: +{mst[14]} Attack Power when fighting {names}.")
    if it.get('itemEffects'):
        green.append('Has an equip, proc or use effect (see Wowhead).')
    t = it.get('type')
    slot = TYPE.get(t, '')
    kind = ''
    if t == 13:
        slot = HAND.get(it.get('handType'), 'Weapon')
        kind = WEAPON.get(it.get('weaponType'), '')
    elif t == 14:
        slot, kind = 'Ranged', RANGED.get(it.get('rangedWeaponType'), '')
    elif it.get('armorType') and t not in (2, 11, 12):
        kind = ARMOR.get(it['armorType'], '')
    weapon = None
    if so.get('unroundedDps'):
        weapon = {'min': so.get('weaponDamageMin', 0), 'max': so.get('weaponDamageMax', 0), 'speed': it.get('weaponSpeed', 0),
                  'dps': so.get('unroundedDps', 0)}
    srcs, kinds = sources(it)
    sfx = {}
    for sid in used_suffixes:
        s = suffixes[sid]
        sfx[sid] = [[(STAT + ['?'] * 40)[i] if i < 4 else {14: 'Attack Power', 15: 'Ranged Attack Power'}.get(i, f'stat {i}'),
                     round(a_ * so.get('randPropPoints', 0) / 10000)] for i, a_ in enumerate(s['stats']) if a_]
    return {'name': it['name'], 'q': it.get('quality', 1), 'ilvl': so.get('ilvl', 0), 'icon': icon(it), 'slot': slot,
            'kind': kind, 'armor': st.get(27, 0), 'white': white, 'green': green, 'weapon': weapon,
            'set': it.get('setName', ''), 'unique': bool(it.get('unique')),
            'side': {1: 'Alliance', 2: 'Horde'}.get(side_of(it), ''), 'sources': srcs, 'kinds': kinds,
            'alliance': {'id': tw['id'], 'name': tw['name']} if (tw := alliance_twin(it)) else None,
            'tier': tier(it), 'suffixStats': sfx, **({'premier': True} if it['id'] in PREMIER else {})}


def enchant_label(eid, slot):
    rows = [e for e in db['enchants'] if e['effectId'] == eid]
    t = SLOT_TYPE.get(slot)
    pick = next((e for e in rows if e.get('type') == t), None) or next((e for e in rows if t in e.get('extraTypes', [])), None) or (rows[0] if rows else None)
    if not pick:
        return f'Enchant {eid}'
    name = re.sub(r'^Enchant [^-]+ - ', '', pick['name'])
    st = pick.get('stats', [])
    parts = [f"+{v} {n}" for n, v in zip(['Str', 'Agi', 'Sta', 'Int'], st[:4]) if v]
    if len(parts) == 4:
        parts = [f"+{st[1]} all stats"]
    if pick.get('weaponDamage'):
        parts.append(f"+{pick['weaponDamage']} damage")
    return name + (f" ({', '.join(parts)})" if parts and not name.startswith('+') else '')


def spec_with_label(slot, v):
    v = list(v) + [0, 0, 0]
    return [v[0], v[1], v[2], enchant_label(v[1], slot) if v[1] else '']


# nweave-* are the normal weave sets, picked under Weave beside the max weave ones (weave-*); bmturret-* the Beast
# Mastery turret sets, picked under Turret beside the Marksmanship ones (turret-*).
IDS = ['weave-max', 'weave-max-av', 'weave-cheap', 'nweave-max', 'nweave-max-av', 'nweave-cheap', 'turret-max', 'turret-max-av', 'turret-cheap', 'bmturret-max',
       'bmturret-max-av', 'bmturret-cheap', 'melee-max', 'melee-max-av', 'melee-cheap']
IDS = [i for i in IDS if os.path.exists(os.path.join(a.runs, f'{i}.guide.json'))]
GROUP_ORDER = ['weapons_ranged', 'weapons', 'main_hand', 'off_hand', 'two_hand', 'ranged', 'head', 'neck', 'shoulder', 'back', 'chest', 'wrist', 'hands', 'waist',
               'legs', 'feet', 'finger1', 'finger2', 'trinket1', 'trinket2']
NOTES = {'weapons_ranged': 'Weave: the two-hander and the bow are picked together',
         'weapons': 'With the set\'s ranged weapon', 'ranged': 'With the set\'s melee weapons',
         'main_hand': 'One-handers beside the set\'s off hand', 'off_hand': 'Beside the set\'s main hand',
         'two_hand': 'With the set\'s ranged weapon',
         'finger1': 'Unique rings cannot be worn twice', 'trinket1': 'Effects the sim does not model count as their stats only'}
# Items worn by choice where the 3 minute boss sim picks another (owner ruling, 2026-11-17): Bloodseeker on every turret
# set. Eaglehorn Long Bow is about 16 DPS (1.5%) ahead on the lone boss, but Bloodseeker is a free quest reward and ends within
# 1% of it over a raid night, ahead once Volleyed trash is a third of the combat time. Keep it worn when the sets are
# rerun: the build stops if a set's gear wears anything else there. The card shows WHY as a hover on its title.
BIS_OVERRIDE = {('turret', 'ranged'): {'item': 19107, 'label': 'Why Bloodseeker?', 'why': [
    "A free quest reward that is practically the same as Eaglehorn Long Bow.",
    "Lone boss: 1.1% behind on this 3 minute fight, practically the same. Only long single-target fights lean toward a "
    "fast bow (about 6% at 5 minutes).",
    "Trash you Volley: Bloodseeker pulls ahead, about +75 DPS on a pack of four. Volley pauses Auto Shot, so its bigger "
    "shots and Multi-Shots (13% harder) count for more.",
    "Cleave: a tie while you stay on the boss, about 2% behind when you swap to kill adds.",
    "A 30 minute run of bosses, cleave and packs: within 1% either way, and ahead once Volleyed trash is a third of your "
    "combat time.",
    "Rather spend gold? Dwarven Hand Cannon was ahead of both in every mix."]}}
# Beast Mastery turret keeps Bloodseeker too (the ruling covers every turret set); its gap was measured on its own sets.
BIS_OVERRIDE[('bmturret', 'ranged')] = {'item': 19107, 'label': 'Why Bloodseeker?', 'why': [
    "A free quest reward. Every turret set wears it.",
    "Lone boss on Beast Mastery: Eaglehorn Long Bow is about 2% ahead on this 3 minute fight (+19 on Max, +18 on Cheap).",
    "The trash, cleave and raid night comparisons were run on Marksmanship, where Bloodseeker pulls ahead on trash you "
    "Volley and ends within 1% over a night.",
    "Rather spend gold? Eaglehorn Long Bow or a Hawkeye Bow of Agility."]}
used_items, used_suffixes = set(), {}
loadouts = {}
for lid in IDS:
    gear = json.load(open(os.path.join(a.runs, f'{lid}.gear.json')))
    runs = json.load(open(os.path.join(a.runs, f'{lid}.guide.json')))
    cond_path = os.path.join(a.runs, f'{lid}.cond.json')
    cond = json.load(open(cond_path)) if os.path.exists(cond_path) else {}
    maxonly_path = os.path.join(a.runs, f'{lid}.maxonly.json')
    maxonly = json.load(open(maxonly_path)) if lid.endswith('-cheap') and os.path.exists(maxonly_path) else {}
    scen_path = os.path.join(a.runs, f'{lid}.scenario.json')
    scen = json.load(open(scen_path)) if os.path.exists(scen_path) else {}
    m = meta['loadouts'][lid]
    groups = []
    for g in GROUP_ORDER:
        if g not in runs:
            continue
        slots = [s for s in {'weapons_ranged': ['main_hand', 'off_hand', 'ranged'], 'weapons': ['main_hand', 'off_hand'],
                             'two_hand': ['main_hand', 'off_hand']}.get(g, [g])]
        best = {s: spec_with_label(s, gear.get(s, [0, 0, 0])) for s in slots if gear.get(s, [0])[0]}
        note = NOTES.get(g, '')
        # A one-hand list on a set that wears a two-hander runs each one beside the same partner in the other hand: the
        # card shows the listed hand alone, has no BiS row, and every Δ is against the set's two-hander.
        if g in ('main_hand', 'off_hand') and not gear.get('off_hand', [0])[0]:
            other = 'off_hand' if g == 'main_hand' else 'main_hand'
            partner = items[runs[g]['rows'][0]['move'][other][0]]['name']
            best = {}
            note = f"Beside {partner} in the {other.replace('_', ' ')} · Δ against the set's two-hander"
        rows, by = [], {}

        def add_row(r, **flags):
            move = {s: spec_with_label(s, v) for s, v in r['move'].items() if v and v[0] and s in slots}
            if not move:
                return None
            row = {'move': move, 'd': round(r['d'], 2), 'm': round(r['m'], 2), **flags}
            rows.append(row)
            by[json.dumps(r['move'], sort_keys=True)] = row
            return row

        def max_only(move):
            """On a Cheap card: the move needs a Max item, or makes a third Premier piece."""
            worn = {**gear, **move}
            return (any(tier(items[v[0]]) == 'max' for v in move.values() if v and v[0])
                    or sum(1 for v in worn.values() if v and v[0] in PREMIER) > PREMIER_CAP)

        for r in runs[g]['rows'] or []:
            add_row(r)
        # A Cheap card also lists every Max option above the Cheap pick (<id>.maxonly.json, run against the Cheap set).
        for r in maxonly.get(g, {}).get('rows') or []:
            if r['d'] > 0 and json.dumps(r['move'], sort_keys=True) not in by and max_only(r['move']):
                add_row(r, max=1)
        # Biome and creature type: each row whose item has a bonus there gets its Δ there; an item with a bonus that
        # makes no card on the sets' own boss joins as a row shown only under its condition (x), with its Δ on that
        # boss from the 'none' run. Plain rows run under a condition only where the set wears an item with a bonus
        # there: their drop is that worn item's own gain, which moves the card's other plain rows (shift).
        none = {json.dumps(r['move'], sort_keys=True): r for r in cond.get('none', {}).get(g, {}).get('rows') or []}
        shift = {}
        worn_conds = {c for s in slots for c in item_conds((gear.get(s) or [0])[0])}
        for c, crun in sorted(cond.items()):
            if c == 'none' or c not in CONDS:
                continue
            plain = []
            for r in crun.get(g, {}).get('rows') or []:
                k = json.dumps(r['move'], sort_keys=True)
                if c not in {x for v in r['move'].values() if v and v[0] for x in item_conds(v[0])}:
                    if k in by and not by[k].get('c'):
                        plain.append(by[k]['d'] - r['d'])
                    continue
                if k not in by:
                    if k not in none:
                        continue
                    flags = {'x': 1}
                    if lid.endswith('-cheap') and max_only(r['move']):
                        flags['max'] = 1
                    if not add_row(none[k], **flags):
                        continue
                by[k].setdefault('c', {})[c] = [round(r['d'], 2), round(r['m'], 2)]
            if c in worn_conds and plain:
                shift[c] = round(sum(plain) / len(plain), 2)
        # A bonus the sim does not move (under 1 DPS against the same item on the None boss, same seed) is no bonus: the
        # row stays plain, and a row that was only there for it goes.
        for k, row in list(by.items()):
            ref = none[k]['d'] if k in none else row['d']
            for c, (d, _) in list(row.get('c', {}).items()):
                if abs(d - ref) < 1:
                    del row['c'][c]
            if 'c' in row and not row['c']:
                del row['c']
                if row.get('x'):
                    rows.remove(row)
        # Two items with the same stats, slot and quality under two names (the Premier Chain and Chainmail pieces) run
        # the same: the card lists the first.
        sig_of = lambda move: tuple(sorted((s, twin_sig(items[v[0]]), v[1], v[2]) for s, v in move.items()))
        twins_seen, kept = {sig_of(best)} if best else set(), []
        for row in sorted(rows, key=lambda r: -r['d']):
            sig = sig_of(row['move'])
            if sig not in twins_seen:
                twins_seen.add(sig)
                kept.append(row)
        rows = kept
        override = BIS_OVERRIDE.get((lid.split('-')[0], g))
        if override and override['item'] not in {spec[0] for spec in best.values()}:
            raise SystemExit(f"{lid} {g}: the set must wear {items[override['item']]['name']} (BIS_OVERRIDE); put it back in "
                             f"{lid}.gear.json and rerun the card against it")
        for spec in list(best.values()) + [v for r in rows for v in r['move'].values()]:
            used_items.add(spec[0])
            if spec[2]:
                used_suffixes.setdefault(spec[0], set()).add(spec[2])
        rows.sort(key=lambda r: -r['d'])
        group = {'id': g, 'best': best, 'rows': rows, 'note': note}
        if override:
            group['why'] = {'label': override['label'], 'lines': override['why']}
        if shift:
            group['shift'] = shift
        if g in scen:
            group['scenarios'] = [dict(sc, rows=[dict(r, move={s: spec_with_label(s, v) for s, v in r['move'].items() if v and v[0]})
                                                 for r in sc['rows']]) for sc in scen[g]]
            for sc in group['scenarios']:
                for r in sc['rows']:
                    used_items.update(v[0] for v in r['move'].values())
        groups.append(group)
    full = {s: spec_with_label(s, v) for s, v in gear.items() if v and v[0]}
    for s, spec in full.items():
        used_items.add(spec[0])
        if spec[2]:
            used_suffixes.setdefault(spec[0], set()).add(spec[2])
    loadouts[lid] = {'title': m['title'], 'build': m['build'], 'talents': m['talents'], 'rotation': m['rotation'],
                     'dps': m['dps'], 'hit': m['hit'], 'vsOther': m['vsOther'], 'talentLink': m['talentLink'], 'simLink': m['simLink'], 'gear': full, 'groups': groups}
    # <id>.long.json, when measured: the pieces a long fight swaps in and their gain at each length, against this set.
    long_path = os.path.join(a.runs, f'{lid}.long.json')
    if os.path.exists(long_path):
        lf = json.load(open(long_path))
        lf['pieces'] = {s: spec_with_label(s, v) for s, v in lf['pieces'].items()}
        for spec in lf['pieces'].values():
            used_items.add(spec[0])
        loadouts[lid]['long'] = lf

# The pickers list the biomes and creature types some card has a bonus row for, in CONDS order.
present = {c for L in loadouts.values() for g in L['groups'] for r in g['rows'] for c in r.get('c', {})}
data = {
    'meta': meta['meta'],
    'playstyles': meta['playstyles'],
    'conds': [{'id': c, 'axis': v[0], 'label': v[1], 'on': v[2], 'off': v[3]} for c, v in CONDS.items() if c in present],
    'loadouts': loadouts,
    'items': {i: item_data(i, used_suffixes.get(i, set())) for i in sorted(used_items)},
    'suffixes': {sid: s['name'] for sid, s in suffixes.items()},
    'enchants': {},
    'howto': meta['howto'],
    'method': meta['method'],
}
json.dump(icon_cache, open(icon_cache_path, 'w'), indent=1, sort_keys=True)
with open(a.out, 'w') as f:
    f.write('// Generated by tools/build_data.py. Do not edit by hand.\nwindow.GUIDE = ')
    json.dump(data, f, separators=(',', ':'))
    f.write(';\n')
# index.html loads the data with its content hash, so a browser never keeps an older copy after an update.
import hashlib, re
index = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'index.html')
if os.path.exists(index):
    digest = hashlib.sha256(open(a.out, 'rb').read()).hexdigest()[:10]
    html = open(index).read()
    html = re.sub(r'<script src="data\.js(\?v=[0-9a-f]*)?"></script>', f'<script src="data.js?v={digest}"></script>', html)
    open(index, 'w').write(html)
# The other pages that read the data (prebis-new/, the class guide) are stamped by tools/stamp_guide.py: run it too,
# so a rebuild never leaves one of them on a cached copy.
stamp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stamp_guide.py')
if os.path.exists(stamp):
    import runpy
    runpy.run_path(stamp, run_name='__main__')
print(f"wrote {a.out}: {len(used_items)} items, {len(loadouts)} loadouts")

#!/usr/bin/env python3
"""Builds data.js for the guide from a WoWSims Forever checkout and the sim runs.

    python3 tools/build_data.py --forever ~/forever --runs RUNS_DIR --out data.js

RUNS_DIR holds, per loadout (weave-max, weave-cheap, turret-max, turret-cheap, melee-max, melee-cheap):
  <id>.gear.json   the loadout's gear: {"head": [id, enchant, suffix], ...}
  <id>.guide.json  the per-slot runs: {group: {"base": dps, "rows": [{"move": {...}, "d": .., "m": ..}]}}
  <id>.cond.json   optional, the flipped-condition runs: {group: {"best": {"cond", "d"}, "rows": [{"move", "cond", "d", "m"}]}}
  <id>.scenario.json  optional, the best moves under a raid condition the set does not assume:
                   {group: [{"when", "detail", "rows": [{"move", "d", "m", "note"?}]}]}, Δ against the set under the same condition
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
CHEAP_CRAFTS = {252605, 15062, 15063, 250619, 279273}
MAX_CRAFTS = {252483, 279253, 252484, 12784, 12798, 12783}
MAX_SOURCELESS = {1728, 13023}
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
# <id>.cond.json holds, for the items whose bonus needs an area or a creature type, their Δ DPS with that condition
# flipped against the same set: a row's item with it, or the worn item's own loss without it.
COND_LABEL = {'forest': 'Outside Forest/Grassland', 'dragonkin': 'Not against Dragonkin', 'demon': 'Against Demons',
              'beast': 'Against Beasts', 'elemental': 'Against Elementals'}

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
    if it['id'] in VENDOR_REP:
        out.insert(1, VENDOR_REP[it['id']])  # second, so the card's two source lines show it
    out = list(dict.fromkeys(out))
    if not out:
        if it.get('randomSuffixOptions'):
            out, kinds = ['World drop (random suffix, Auction House)'], {'world'}
        else:
            out, kinds = ['New Forever item: no source in the game files yet'], {'unknown'}
    return out[:4], sorted(kinds)


def tier(it):
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
            'tier': tier(it), 'suffixStats': sfx}


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


IDS = ['weave-max', 'weave-max-av', 'weave-cheap', 'turret-max', 'turret-max-av', 'turret-cheap', 'melee-max', 'melee-max-av',
       'melee-cheap']
IDS = [i for i in IDS if os.path.exists(os.path.join(a.runs, f'{i}.guide.json'))]
GROUP_ORDER = ['weapons_ranged', 'weapons', 'ranged', 'head', 'neck', 'shoulder', 'back', 'chest', 'wrist', 'hands', 'waist',
               'legs', 'feet', 'finger1', 'finger2', 'trinket1', 'trinket2']
NOTES = {'weapons_ranged': 'Weave: the two-hander and the bow are picked together',
         'weapons': 'With the set\'s ranged weapon', 'ranged': 'With the set\'s melee weapons',
         'finger1': 'Unique rings cannot be worn twice', 'trinket1': 'Effects the sim does not model count as their stats only'}
used_items, used_suffixes = set(), {}
loadouts = {}
for lid in IDS:
    gear = json.load(open(os.path.join(a.runs, f'{lid}.gear.json')))
    runs = json.load(open(os.path.join(a.runs, f'{lid}.guide.json')))
    cond_path = os.path.join(a.runs, f'{lid}.cond.json')
    cond = json.load(open(cond_path)) if os.path.exists(cond_path) else {}
    scen_path = os.path.join(a.runs, f'{lid}.scenario.json')
    scen = json.load(open(scen_path)) if os.path.exists(scen_path) else {}
    m = meta['loadouts'][lid]
    groups = []
    for g in GROUP_ORDER:
        if g not in runs:
            continue
        slots = [s for s in {'weapons_ranged': ['main_hand', 'off_hand', 'ranged'], 'weapons': ['main_hand', 'off_hand']}.get(g, [g])]
        best = {s: spec_with_label(s, gear.get(s, [0, 0, 0])) for s in slots if gear.get(s, [0])[0]}
        flipped = {json.dumps(c['move'], sort_keys=True): c for c in cond.get(g, {}).get('rows', [])}
        rows = []
        for r in runs[g]['rows']:
            move = {s: spec_with_label(s, v) for s, v in r['move'].items() if v and v[0]}
            if not move:
                continue
            row = {'move': move, 'd': round(r['d'], 2), 'm': round(r['m'], 2)}
            if (c := flipped.get(json.dumps(r['move'], sort_keys=True))):
                row['alt'] = {'when': COND_LABEL[c['cond']], 'd': c['d'], 'm': c['m']}
            rows.append(row)
        for spec in list(best.values()) + [v for r in rows for v in r['move'].values()]:
            used_items.add(spec[0])
            if spec[2]:
                used_suffixes.setdefault(spec[0], set()).add(spec[2])
        rows.sort(key=lambda r: -r['d'])
        group = {'id': g, 'best': best, 'rows': rows, 'note': NOTES.get(g, '')}
        if (c := cond.get(g, {}).get('best')):
            group['bestAlt'] = {'when': COND_LABEL[c['cond']], 'd': c['d']}
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

data = {
    'meta': meta['meta'],
    'playstyles': meta['playstyles'],
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
print(f"wrote {a.out}: {len(used_items)} items, {len(loadouts)} loadouts")

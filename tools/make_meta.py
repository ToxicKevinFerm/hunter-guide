#!/usr/bin/env python3
"""Writes RUNS_DIR/meta.json: the loadouts' facts and the guide's prose, from the runs in RUNS_DIR.

    python3 tools/make_meta.py RUNS_DIR FOREVER_CHECKOUT

RUNS_DIR holds <id>.guide.json per loadout, hit.json ({id: [melee %, ranged %]}) and, when measured, ep.json
({playstyle: {stat: value}}).
"""
import json, os, statistics, sys

R = sys.argv[1]
db = json.load(open(os.path.join(sys.argv[2], 'assets/database/db.json')))
NAME = {it['id']: it['name'] for it in db['items']}
SPEED = {it['id']: it.get('weaponSpeed', 0) for it in db['items']}
# <playstyle>-max is the Max set for a player exalted with Darkspear Raiders (Theramore), <playstyle>-max-av the one for a
# player exalted with Frostwolf Clan (Stormpike Guard) in Alterac Valley.
IDS = ['weave-max', 'weave-max-av', 'weave-cheap', 'nweave-max', 'nweave-max-av', 'nweave-cheap', 'turret-max', 'turret-max-av', 'turret-cheap', 'bmturret-max',
       'bmturret-max-av', 'bmturret-cheap', 'melee-max', 'melee-max-av', 'melee-cheap']
IDS = [i for i in IDS if os.path.exists(os.path.join(R, f'{i}.guide.json'))]
runs = {i: json.load(open(os.path.join(R, f'{i}.guide.json'))) for i in IDS}
hit = json.load(open(os.path.join(R, 'hit.json')))
ep = json.load(open(os.path.join(R, 'ep.json'))) if os.path.exists(os.path.join(R, 'ep.json')) else {}
dps = {i: statistics.median(g['base'] for g in runs[i].values()) for i in IDS}

# Build name and rotation per playstyle. The talents are the ones the sets were simmed with, read from the run's setup
# (RUNS_DIR/<playstyle>.json), so they follow the sim's presets.
BUILDS = {
    'weave': ('SV Weave', 'Melee Weave (Max)'),
    'nweave': ('SV Weave', 'Melee Weave (Normal)'),
    'turret': ('MM', 'Turret'),
    'bmturret': ('BM', 'Turret (Hawks)'),
    'melee': ('SV Melee', 'Melee'),
}
TALENTS = {ps: json.load(open(os.path.join(R, f'{ps}.json')))['player']['talentsString'] for ps in BUILDS
           if os.path.exists(os.path.join(R, f'{ps}.json'))}
TITLES = {'weave': 'Weave', 'nweave': 'Weave · Normal', 'turret': 'Turret · MM', 'bmturret': 'Turret · BM', 'melee': 'Melee'}
# Wowhead's Forever talent calculator reads a build as its hash version followed by the points per talent, trees in
# row and column order like the sim's. The version is "hashVersion" in nether.wowhead.com/forever/data/talents-classic;
# Wowhead converts links stamped with an older version when its trees change.
WOWHEAD_HASH_VERSION = 'vkndmh'
# WoWSims share links per loadout (aplkit link on each set's setup), when RUNS_DIR/links.txt has them: "<id> <url>".
LINKS = {}
if os.path.exists(os.path.join(R, 'links.txt')):
    LINKS = dict(line.split(None, 1) for line in open(os.path.join(R, 'links.txt')).read().split('\n') if line.strip())
loadouts = {}
for i in IDS:
    ps, tier, *av = i.split('-')
    other = f"{ps}-{'cheap' if tier == 'max' else 'max'}"
    diff = dps[i] - dps.get(other, dps[i])
    b = BUILDS[ps]
    loadouts[i] = {
        'title': f"{TITLES[ps]} · {('Max · AV' if av else 'Max · Darkspear') if tier == 'max' else 'Cheap'}", 'build': b[0], 'talents': TALENTS[ps], 'rotation': b[1], 'dps': round(dps[i], 1),
        'hit': f"{hit[i][0]:g}% melee, {hit[i][1]:g}% ranged (cap 8%)",
        'vsOther': f"{'Cheap' if tier == 'max' else 'Max'} {dps.get(other, 0):.0f} ({diff:+.0f})",
        'talentLink': f"https://www.wowhead.com/forever/talent-calc/hunter/{WOWHEAD_HASH_VERSION}{TALENTS[ps]}",
        'simLink': LINKS.get(i, '').strip(),
    }

def swapped(base, other):
    """The items set `other` wears that set `base` does not, in slot order."""
    a = json.load(open(os.path.join(R, f'{base}.gear.json'))); b = json.load(open(os.path.join(R, f'{other}.gear.json')))
    worn = {v[0] for v in a.values() if v and v[0]}
    names = [NAME[v[0]] for v in b.values() if v and v[0] and v[0] not in worn]
    return ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else ''.join(names)


NWEAVE_BLURB = ('Survival with Marksmanship, no pet (Lone Wolf), played with the Melee Weave (Normal) rotation: the shots '
                'come first, you walk in only once Aimed Shot and Arcane Shot are both cooling and Auto Shot has just gone '
                'off, and you stay while a melee cooldown comes up soon. Fewer trips than the max weave, and easier to play.')
nweave_html = ''
if 'nweave-max-av' in dps:
    def replaced(t):
        """'X for Y' per slot where the normal weave set `t` wears another item than the max weave one."""
        a = json.load(open(os.path.join(R, f'weave-{t}.gear.json'))); b = json.load(open(os.path.join(R, f'nweave-{t}.gear.json')))
        worn = {v[0] for v in a.values() if v and v[0]}
        out = [f"{NAME[v[0]]} for {NAME[a[s][0]]}" for s, v in b.items() if v and v[0] and v[0] not in worn]
        return ', '.join(out[:-1]) + ' and ' + out[-1] if len(out) > 1 else ''.join(out)
    by = {t: replaced(t) for t in ('max', 'max-av', 'cheap')}
    nw_swaps = (f"on both Max sets {by['max']}" if by['max'] == by['max-av'] else
                f"on Max · Darkspear {by['max']}, on Max · AV {by['max-av']}")
    nw_swaps += f"; on Cheap {by['cheap']}" if by['cheap'] else '. Cheap wears the same set for both'
    nweave_html = f"""<h3>Weave: max or normal</h3>
<p>Weave comes in two rotations, each with its own sets: pick Max weave or Normal weave under Rotation. The max weave
walks in after every Auto Shot and is the stronger, {dps['weave-max-av'] - dps['nweave-max-av']:.0f} DPS ahead on the AV
set ({dps['weave-max-av']:.0f} against {dps['nweave-max-av']:.0f}). The normal weave walks in only once Aimed Shot and
Arcane Shot are both cooling, and stays while a melee cooldown comes up soon. Its sets were searched on its own
rotation from the max weave sets, with every two-hander and bow pair in the pool. They swap a few pieces:
{nw_swaps}. A two-hander still beats dual wield on the normal weave, by about 47 on Max.</p>"""


playstyles = [
    {'id': 'weave', 'short': 'Weave', 'name': 'Melee Weave',
     'blurb': 'Survival with Marksmanship, no pet (Lone Wolf). A slow two-hander and a slow bow: each weave lasts as long '
              'as the slower swing, so the two are picked as a pair.',
     # Weave comes as two rotations with their own sets: max weave (weave-*) and normal weave (nweave-*).
     'specLabel': 'Rotation',
     'specs': [{'id': 'max', 'short': 'Max weave', 'name': 'Melee Weave (Max): walk in after every Auto Shot',
                'title': 'Melee Weave', 'prefix': 'weave'},
               {'id': 'normal', 'short': 'Normal weave', 'title': 'Melee Weave · Normal', 'prefix': 'nweave',
                'name': 'Melee Weave (Normal): walk in only while the shots are cooling, stay for the melee cooldowns',
                'blurb': NWEAVE_BLURB}]},
    {'id': 'turret', 'short': 'Turret', 'name': 'Turret',
     'blurb': 'Marksmanship from range. The two-hander is only a stat stick. Bloodseeker is the bow: a free quest reward, '
              'practically the same as Eaglehorn Long Bow, and ahead on trash you Volley. Pick a turret rotation: the Auto '
              'rotation weaves whenever a two-hander is equipped.',
     # Turret comes as two specs with their own sets: Marksmanship (turret-*) and Beast Mastery (bmturret-*).
     'specLabel': 'Spec',
     'specs': [{'id': 'mm', 'short': 'MM', 'name': 'Marksmanship', 'title': 'Turret · MM', 'prefix': 'turret'},
               {'id': 'bm', 'short': 'BM', 'name': 'Beast Mastery', 'title': 'Turret · BM', 'prefix': 'bmturret',
                'blurb': 'Beast Mastery from range with a Raptor and Summon Hawk (Turret (Hawks) rotation). The two-hander '
                         'is only a stat stick and Bloodseeker is the bow, as on Marksmanship.'}]},
    {'id': 'melee', 'short': 'Melee', 'name': 'Survival Melee',
     'blurb': 'Dual wield in melee with hawks (Beast Mastery 16 / Survival 31). Crusader on the main hand; run out for '
              'Serpent Sting while Strider Kick speeds you up.'},
]

pairs = runs['weave-max'].get('weapons_ranged', {}).get('rows', [])
# The long fight toggles (<id>.long.json): the Beastmaster Armor pieces a 4-5 minute fight swaps in, and their gain.
LONG = {i: json.load(open(os.path.join(R, f'{i}.long.json'))) for i in IDS if os.path.exists(os.path.join(R, f'{i}.long.json'))}
def at(lf, t):
    return next(x['d'] for x in lf['at'] if x['t'] == t)
long_list = '; '.join(f"{loadouts[i]['title']}: {at(lf, '3 min'):+.0f} at 3 min, {at(lf, '4 min'):+.0f} at 4, {at(lf, '5 min'):+.0f} at 5"
                      for i, lf in LONG.items())
BM_WORN = {i: sum(1 for s, v in json.load(open(os.path.join(R, f'{i}.gear.json'))).items() if NAME.get(v[0], '').startswith('Beastmaster'))
           for i in IDS if i.startswith('bmturret')}
def swaps(t):
    mm = json.load(open(os.path.join(R, f'turret-{t}.gear.json'))); bm = json.load(open(os.path.join(R, f'bmturret-{t}.gear.json')))
    names = [NAME[bm[s][0]] for s in bm if bm[s][0] and bm[s][0] != mm.get(s, [0])[0]]
    return ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else ''.join(names)
bm_html = ''
if 'bmturret-max' in dps:
    bm_swaps = f"{swaps('max-av')} on Max; {swaps('cheap')} on Cheap"
    # The best Beastmaster four-piece on the BM turret AV set at each length (bm/long.py, not a toggle: it never gains).
    bm_long = {x['t']: x['d'] for x in json.load(open(os.path.join(R, 'bm', 'bmturret-max-av.long.draft.json')))['at']}
    bm_html = (f"""<h3>Turret: Marksmanship or Beast Mastery</h3>
<p>Turret comes in two specs, each with its own sets: pick MM or BM under Spec. Marksmanship is the stronger turret,
{dps['turret-max-av'] - dps['bmturret-max-av']:.0f} DPS ahead on the AV set ({dps['turret-max-av']:.0f} against {dps['bmturret-max-av']:.0f}).
Beast Mastery plays the Turret (Hawks) rotation with a Raptor. Its sets were searched on its own build, with every
Beastmaster Armor combination in the pool, and differ from the Marksmanship ones in a few slots: {bm_swaps}. Four
Beastmaster pieces never pay on Beast Mastery, whose turret does not run dry: the best four-piece is still
{-bm_long['3 min']:.0f} behind at 3 minutes, {-bm_long['4 min']:.0f} at 4 and {-bm_long['5 min']:.0f} at 5 (Max · AV).</p>""")
long_html = ''
if LONG:
    long_html = f"""<h3>Long fights: Beastmaster Armor</h3>
<p>Beastmaster Armor, the hunter vendor set, gives +8 mana per 5 sec at three pieces and Sudden Insight, a mana proc on
5% of Auto Shots and white swings, at four. On a 3 minute boss no set runs dry, so the pieces cost more than their mana
is worth. Marksmanship turret runs low on mana past about three and a half minutes and Survival melee toward five, and
there four pieces pay; Beast Mastery turret never does. Those sets carry a Long fight (4–5 min) toggle in the character
window, which swaps the four pieces in: {long_list}. Weave
never gets there: its best four-piece is still 12–15 behind at 5 minutes.</p>"""


def tr(cells):
    return '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'


best_pair = json.load(open(os.path.join(R, 'weave-max.gear.json')))


def wname(i):
    return f"{NAME.get(i, i)} ({SPEED.get(i, 0):g} s)"


pair_rows = tr([wname(best_pair['main_hand'][0]), wname(best_pair['ranged'][0]), 'best']) + ''.join(
    tr([wname(r['move']['main_hand'][0]), wname(r['move']['ranged'][0]), f"{r['d']:.1f} ± {r['m']:.1f}"])
    for r in pairs if r['move'].get('main_hand') and r['move'].get('ranged'))


ep_html = ''
if ep:
    # ep.json: the sim's own stat weights (gearkit epsim, core.StatWeights) in Agility, as the site's hunter EP is.
    stats = ['Agility', 'Strength', 'Intellect', 'Attack Power', 'Ranged Attack Power', 'Crit rating', 'Hit rating (under the cap)',
             'Haste rating', 'MP5', 'Main hand weapon DPS', 'Off hand weapon DPS', 'Ranged weapon DPS']
    cols = [('weave', 'Weave'), ('nweave', 'Normal weave'), ('turret', 'MM Turret'), ('bmturret', 'BM Turret'), ('melee', 'Melee')]
    ep_html = ('<h3>What a point of each stat is worth</h3><p>The sim\'s own EP, its stat weights as the site runs them, on '
               'each playstyle\'s Max set, in Agility: Agility is 1. Hit is weighed under the cap. Item crit rating is 14 per '
               '1%, hit and haste rating 10 per 1%. Intellect counts twice: Careful Aim, which every build takes, turns each '
               'point into Attack Power and Ranged Attack Power, and it is mana. The MM Turret set runs short of mana, so '
               'Intellect and MP5 count more there.</p><p>These numbers hold for these sets only. EP changes with gear, '
               'talents, buffs and consumables, so for your own character run the stat weights in '
               '<a href="https://www.wowsims.com/forever/hunter/dps/" target="_blank" rel="noopener">the sim</a>.</p>'
               '<table><thead><tr><th>Stat</th>'
               + ''.join(f'<th>{n}</th>' for _, n in cols) + '</tr></thead><tbody>'
               + ''.join(tr([s] + [f"{ep.get(p, {}).get(s, 0):.2f}" for p, _ in cols]) for s in stats)
               + '</tbody></table>')

howto = f"""
<div class="kpis">
  <div class="kpi"><b>8% hit</b><span>The cap against a level 63 boss, melee and ranged. Surefooted counts.</span></div>
  <div class="kpi"><b>Agility</b><span>The best stat for every playstyle; weave values it most.</span></div>
  <div class="kpi"><b>Slow + slow</b><span>Weave: a slow two-hander wants a slow bow (The Blackrock Slicer + Deep Jungle Rifle or Bloodseeker).</span></div>
  <div class="kpi"><b>Bloodseeker</b><span>Turret: a free quest reward, practically the same as Eaglehorn. Pick a turret rotation.</span></div>
</div>

<h2>Hit first</h2>
<p>Against a level 63 boss you miss 8% of your attacks, melee and ranged, until hit takes it away; past that hit is
worth nothing. Surefooted gives 3% and the Devilsaur two-piece another 2%, so the Survival sets need only about 3–5%
from gear. Every set here lands between {min(min(v) for v in hit.values()):g}% and {max(max(v) for v in hit.values()):g}%; the dual wield sets keep a little extra, since white swings with two weapons miss far more often.</p>
{ep_html}

<h2>Weapons decide the playstyle</h2>
<h3>Weave: pick the two-hander and the bow together</h3>
<p>A melee swing resets Auto Shot, so after each weave the next shot waits a full swing of the bow. Each weave
therefore takes as long as the slower of your two weapons. A fast bow wastes a slow two-hander and the other way
around. These are the best pairs on the Max weave set:</p>
<table><thead><tr><th>Two-hander</th><th>Ranged</th><th>Δ DPS</th></tr></thead><tbody>
{pair_rows}
</tbody></table>
<p>A faster two-hander wants a faster bow: Legionite Glaive (3.2 s) does best with Riphook (2.2 s), and that pair
still loses to the slow pair above.</p>

<h3>Turret: Bloodseeker</h3>
<p>Bloodseeker (3.3 s) is a free quest reward and practically the same as Eaglehorn Long Bow (1.8 s): 1.1% behind on the
3 minute boss here, within 1% over a raid night of bosses, cleave and packs, and ahead on trash you Volley. Only long
single-target fights lean toward the fast bow (about 6% at 5 minutes). Why Bloodseeker? next to the ranged slot has the
numbers. The melee weapon is only a stat stick, since turret never swings it: Legionite Glaive is the best on Max, with
Beastslayer's Trident about 6–7 behind and a pair of one-handers (Shadowblade with Tooth of the Matriarch or
Heartseeker) about 7. Cheap wears the Trident, since the Glaive is a Max craft: its 1.6% hit lets the rest of the set
shed hit, so the Glaive is only 1–2 ahead there. Against Beasts the Trident passes the Glaive. The Weapons, Main hand, Off hand and Two-hander cards
list them all. The Auto rotation weaves with any two-hander, and in a weave a slow bow wins by 30 to 90,
so with the turret sets choose the Turret rotation or the MM, BM or SV preset build.</p>

{nweave_html}
{bm_html}
{long_html}

<h3>Melee: dual wield, Crusader on the main hand</h3>
<p>Survival melee dual wields: Teebu's Blazing Longsword (Max) or Sword of Zeal (Cheap) in the main hand, with
Distracting Dagger in the off hand. Sword of Zeal is about 5–7 behind Teebu's on Max, and on Cheap Dal'Rend's Sacred
Charge is about 6 behind Sword of Zeal. Teebu's Firebolt is not simmed, so Teebu's does a little more in game. Crusader
on the main hand edges out Agility by about 2; the off hand keeps +15 Agility. SV Melee takes Careful Aim, so
Intellect pays here too: Ranger's Belt over Marksman's Girdle, and the Elixir of Greater Intellect.</p>
<p>Annihilator and Rivenspike are bait. Their armor procs (Armor Shatter, Puncture Armor) share one slot with Faerie
Fire and Curse of Recklessness, and only the strongest in it counts. Faerie Fire and the curse are both stronger, so with
either on the boss the proc adds nothing. Left as stat sticks, neither makes the best six one-handers.</p>

<h3>Dual wield while weaving</h3>
<p>If you weave with two one-handers, play Melee Weave (Normal): it walks in only when your shots are on cooldown and
stays for the melee cooldowns, which lets the off hand swing. Teebu's Blazing Longsword (or Dal'Rend's Sacred Charge)
with Bagh Nakh and Bloodseeker gives about 59 more than the best dual wield on the max weave. A two-hander on the max
weave is still about 68 higher.</p>

<h2>Enchants</h2>
<table><thead><tr><th>Slot</th><th>Enchant</th><th>Where</th></tr></thead><tbody>
{tr(['Head, legs', 'Lesser Arcane Amalgamation (+8 Agility); Arcanum of Rapidity (+1% haste) on melee', 'Libram of Voracity, Libram of Rapidity (Dire Maul)'])}
{tr(['Neck', '+5 Agility', 'Enchanter'])}
{tr(['Back', '+5 Agility', 'Enchanter'])}
{tr(['Chest', 'Greater Stats (+4 all stats)', 'Enchanter'])}
{tr(['Wrist', '+9 Agility', 'Enchanter'])}
{tr(['Hands', 'Greater Agility (+10 Agility); Minor Haste (+1% attack speed) on melee', 'Enchanter'])}
{tr(['Feet', 'Greater Agility (+7 Agility)', 'Enchanter'])}
{tr(['Two-hander', '+25 Agility', 'Enchanter'])}
{tr(['Melee main hand / off hand', 'Crusader / +15 Agility', 'Enchanter'])}
{tr(['Ranged', 'SAF-T Ultra Precision Scope (+2% ranged crit)', 'Engineering'])}
</tbody></table>
<p>Every slot was checked against its other enchants. Superior Agility on gloves (+15) is from Ahn'Qiraj, so it is not
in these sets: Greater Agility is about 4–5 behind it on weave and turret. On melee, Minor Haste edges out Greater Agility
by 2–3. Minor Speed on boots loses to Agility, because Strider Kick's
speed already covers it and only the highest speed effect counts. Sniper Scope loses to SAF-T by about 8 on weave, 15 on turret and 3 on melee.</p>

<h2>Trinkets</h2>
<p>Every set wears Heart of Wyrmthalak: its Flame Lash procs about twice a minute from melee and ranged hits. Weave and
turret pair it with Blackhand's Breadth, melee with Darkmoon Card: Maelstrom. Rune of the Guard Captain (Cleansed
Vilebranch Medallion on Alliance) gains +28 Attack Power in Forest/Grassland areas such as Mount Hyjal. On the sets'
boss it keeps only its 14 Attack Power and 0.7% hit, and even in Forest/Grassland it stays 1–7 DPS behind those two;
pick Forest/Grassland under Biome to see it. Against Undead, Seal of the Dawn passes them on weave; against Demons,
Royal Seal of Eldre'Thalas does. Hand of Justice is about 9–12 DPS behind the melee picks. Some trinkets do more in game than here, because the sim does not model their effect and counts only their
stats: Arcanite Dragonling, Scented Runewood Brooch, the Defender of the Timbermaw and Barkskin
pair (Teachings of the Furbolgs), Devilsaur Eye's use, and Scalding Flamehoof's run speed.</p>
"""

gap = {ps: dps[f"{ps}-max"] - dps[f"{ps}-max-av"] for ps in TITLES if f"{ps}-max-av" in dps}
method = f"""
<h2>How these were found</h2>
<p>Every number comes from WoWSims Forever: a 180 s fight against one level 63 boss with no creature type (None in the
sim) and no biome, so no bonus that needs a biome or a creature type counts; an Orc hunter with the full raid buffs and
consumables of the sim's hunter defaults; and a 150–350 ms reaction time. Improved Tracking counts on that boss: the sim
counts the talent only against a creature type a Track spell names, and for these runs it also counts on None, since
you track whatever the boss is. Each loadout uses the
sim's preset build for its playstyle: SV Weave for weave, MM or BM for turret, SV Melee for melee. The BM turret sets
were searched from the MM ones on the BM build, slot by slot with a pair check, Beastmaster Armor combinations
included, then run through the same cards. The normal weave sets were searched the same way from the max weave ones,
on the SV Weave build with the Melee Weave (Normal) rotation. The long fight figures run the same set and the four pieces at 240 and 300 s.</p>
<p>Every set was searched again and every card run again on 2026-11-20 on the sim's master (38786d6412), from the
2026-11-19 sets: each slot's candidates against the set, a swap kept only when it gains more than its margin, until
nothing moves, then every two-slot combination of each slot's three best. Each set's cards share one run against the
finished set, so every gap on a page is against the same base. Weapon pairs come from a screen: each two-hander and
each bow (each main hand and each off hand on melee) is run beside the set's own partner and beside a partner of the
other speed, and the best eight of each side are paired, so a slow two-hander that only pays with a slow bow still
makes it. The Main hand and Off hand cards run every one-hander on its own beside the set's other hand, so each weapon
shows once. The turret sets wear a two-hander, so their one-hand
lists run each one beside Tooth of the Matriarch and take Δ against the set; their Two-hander card runs every
two-hander, all against the Bloodseeker set. Every row wears the set's enchant in its slot.</p>
<p>Some items have a bonus that needs a biome or a creature type: Rune of the Guard Captain in Forest/Grassland,
Wyrmhide Spaulders against Dragonkin, Seal of the Dawn and the Argent Dawn pieces against Undead, King Mosh's Tooth
against Beasts, and more. None of them counts on the sets' boss. Pick a Biome or a Creature type above the cards and
they rerank: every such item a hunter can wear (whatever its stats, so ones that never make a card on the None boss
too) was run against each set under its condition. The sets stay as they are; only the cards move. With a biome and a
creature type both picked, an item with a bonus in both adds the two. Each of these rows shows its figure with its
condition the other way round under its source.</p>
<ul>
<li>Every Phase 1 item a hunter can wear was a candidate, except raid loot, raid reputation (The Watchers) and honor
rank gear. Items are Horde; Alliance mirrors (Theramore for Darkspear, Cleansed Vilebranch Medallion for Rune of the
Guard Captain) have the same stats.</li>
<li>Each slot's candidates were screened at 3,000 iterations (groups of more than 200 first at 1,000, keeping
everything within 25 DPS of the best) and the best six confirmed at 3,000 against the finished set on another seed,
on the sim's presets (SV Melee on Careful Aim, the Elixir of Greater Intellect in every build and Brilliant Mana Oil on
the turret). A row above the worn item ties on the search's own seeds (Arcanite Reaper on the normal weave Max sets).
Bloodseeker is worn on every turret set by choice: Eaglehorn Long Bow is about 13 DPS ahead on this boss (about 1.1%,
practically the same) and Bloodseeker is a free quest reward. Δ DPS is the confirmed gap, ± its 95% margin.</li>
<li>When the sets were first built, set bonuses were tried as whole sets, the weave's two-hander and bow as one pair,
and every two-slot combination of each slot's best alternatives was checked at the end. Every enchant was simmed
against the others.</li>
<li>The Two-piece sets card swaps two set pieces into each set together: the PvP set (Champion's Pursuit, the Premier
Chain pieces, +20 Agility at two) in its best two of all fifteen pairs, and the Devilsaur pair (+2% hit) where the set
does not wear it. Nothing else in the set changes, so a set already at the hit cap gets little from Devilsaur. The
PvP pair pays only on the AV weave sets, which now wear it: Premier Chain Shoulders with the Boots (max weave) or the
Gauntlets (normal weave), about +3. On BM Turret Cheap the Breastplate and Shoulders tie (+0.7 ±0.6), and the
set wears them.</li>
</ul>
<h3>Max and Cheap</h3>
<p><b>Max</b> is everything outside raids, with Exalted reputation from the one faction you pick: <b>Darkspear</b>
(Darkspear Raiders, Theramore for the Alliance) or <b>AV</b> (Frostwolf Clan, Stormpike Guard for the Alliance). The
Darkspear sets wear Darkspear Epaulets, and the weave set Raider Gloves too. The AV sets wear Don Julio's Band in their
place and lose {min(gap.values()):.0f}–{max(gap.values()):.0f} DPS. Items that need Exalted with any other faction (The Defilers, Timbermaw Hold, the other
Warsong Gulch and Alterac Valley rewards) are in neither. <b>Cheap</b> leaves out exalted reputation, battleground
quartermaster gear, the 0.5 set (the Beastmaster vendor pieces), crafted epics (Black Dragonscale Helm, Dawn Armor,
Timbermaw Tunic), epics that bind on equip (Lady Maye's Pendant, The Lion Horn of Stormwind, Ankle Slicers), Arcanite
Reaper, Annihilator, Heartseeker, Legionite Glaive, and world drops other than random-suffix ones, Sword of Zeal and Eaglehorn Long Bow.
The Devilsaur set counts as a cheap craft, and the Korrak quest weapons (Bloodseeker, Ice Barbed
Spear) as cheap. The Premier blues (the item level 60 PvP pieces) are in both: a Cheap set wears two at most, Max any
number. The item level 65 Premier epics are honor rank gear and in neither. Crafts that need a material from Mount
Hyjal (Outlaw's Collar, Mourning Handguards, Ironwood Blade) and items sold there (Bear Poking Stick) are in no set, nor
is Hyper Deluxe Sniper Rifle Mk XVII, which cannot be crafted yet. Max is a superset: every cheap item was simmed in it
too. A Cheap card also lists every Max option above the Cheap pick (a third Premier piece counts as Max), run against
the Cheap set, so you see what each upgrade is worth.</p>
<h3>Limits</h3>
<p>The sim models what the game files and combat logs show; a few trinket effects are missing (see How to gear). New
Forever items without a source in the game files are listed as such.</p>
"""

meta = {
    'meta': {'lede': 'WoW Forever · Phase 1 · simmed pre-raid gear for weave, turret and melee hunters',
             # Under the set's name in the character window: the boss every number is simmed on.
             'target': 'Simmed on a boss with no creature type (None) and no biome. Improved Tracking counts.',
             'footer': 'Simmed with WoWSims Forever on 2026-11-20 (master 38786d6412 with The Blackrock Slicer at 1.9 PPM from a4121e129c, Improved Tracking also on a boss with no creature type). Item data from the game files; links go to Wowhead.'},
    'playstyles': playstyles, 'loadouts': loadouts, 'howto': howto, 'method': method,
}
json.dump(meta, open(os.path.join(R, 'meta.json'), 'w'), indent=1)
print('meta for', ', '.join(f"{i} {dps[i]:.0f}" for i in IDS))

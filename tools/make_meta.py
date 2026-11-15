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
IDS = ['weave-max', 'weave-cheap', 'turret-max', 'turret-cheap', 'melee-max', 'melee-cheap']
IDS = [i for i in IDS if os.path.exists(os.path.join(R, f'{i}.guide.json'))]
runs = {i: json.load(open(os.path.join(R, f'{i}.guide.json'))) for i in IDS}
hit = json.load(open(os.path.join(R, 'hit.json')))
ep = json.load(open(os.path.join(R, 'ep.json'))) if os.path.exists(os.path.join(R, 'ep.json')) else {}
dps = {i: statistics.median(g['base'] for g in runs[i].values()) for i in IDS}

BUILDS = {
    'weave': ('SV Weave', '-00530501114-530200230050220151', 'Melee Weave (Max)'),
    'turret': ('MM', '5-0053452511522051-5', 'Turret'),
    'melee': ('SV Melee', '53200005001-004-530200230050022151', 'Melee'),
}
TITLES = {'weave': 'Weave', 'turret': 'Turret', 'melee': 'Melee'}
loadouts = {}
for i in IDS:
    ps, tier = i.split('-')
    other = f"{ps}-{'cheap' if tier == 'max' else 'max'}"
    diff = dps[i] - dps.get(other, dps[i])
    b = BUILDS[ps]
    loadouts[i] = {
        'title': f"{TITLES[ps]} · {tier.title()}", 'build': b[0], 'talents': b[1], 'rotation': b[2], 'dps': round(dps[i], 1),
        'hit': f"{hit[i][0]:g}% melee, {hit[i][1]:g}% ranged (cap 8%)",
        'vsOther': f"{'Cheap' if tier == 'max' else 'Max'} {dps.get(other, 0):.0f} ({diff:+.0f})",
    }

playstyles = [
    {'id': 'weave', 'short': 'Weave', 'name': 'Melee Weave',
     'blurb': 'Survival with Marksmanship, no pet (Lone Wolf). A slow two-hander and a slow bow: each weave lasts as long '
              'as the slower swing, so the two are picked as a pair.'},
    {'id': 'turret', 'short': 'Turret', 'name': 'Turret',
     'blurb': 'Marksmanship from range. The two-hander is only a stat stick, and a fast bow fires the most Auto Shots. '
              'Pick a turret rotation: the Auto rotation weaves whenever a two-hander is equipped.'},
    {'id': 'melee', 'short': 'Melee', 'name': 'Survival Melee',
     'blurb': 'Dual wield in melee with hawks (Beast Mastery 16 / Survival 31). Crusader on the main hand; run out for '
              'Serpent Sting while Strider Kick speeds you up.'},
]

pairs = runs['weave-max'].get('weapons_ranged', {}).get('rows', [])


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
    stats = ['Agility', 'Strength', 'Attack Power', 'Ranged Attack Power', 'Crit rating', 'Hit rating (under the cap)', 'Haste rating']
    ep_html = ('<h3>What a point of each stat is worth</h3><p>Paired sims on each playstyle\'s Max set, in Ranged Attack '
               'Power for weave and turret and in Attack Power for melee. Item crit rating is 14 per 1%, hit and haste '
               'rating 10 per 1%.</p><table><thead><tr><th>Stat</th><th>Weave</th><th>Turret</th><th>Melee</th></tr></thead><tbody>'
               + ''.join(tr([s] + [f"{ep.get(p, {}).get(s, 0):.2f}" for p in ('weave', 'turret', 'melee')]) for s in stats)
               + '</tbody></table>')

howto = f"""
<div class="kpis">
  <div class="kpi"><b>8% hit</b><span>The cap against a level 63 boss, melee and ranged. Surefooted counts.</span></div>
  <div class="kpi"><b>Agility</b><span>The best stat for every playstyle; weave values it most.</span></div>
  <div class="kpi"><b>Slow + slow</b><span>Weave: a slow two-hander wants a slow bow (Arcanite Reaper + Bloodseeker).</span></div>
  <div class="kpi"><b>Fast bow</b><span>Turret: Eaglehorn or a fast Agility bow. Pick a turret rotation.</span></div>
</div>

<h2>Hit first</h2>
<p>Against a level 63 boss you miss 8% of your attacks, melee and ranged, until hit takes it away; past that hit is
worth nothing. Surefooted gives 3% and the Devilsaur two-piece another 2%, so the Survival sets need only about 3–5%
from gear. Every set here lands between {min(min(v) for v in hit.values()):g}% and {max(max(v) for v in hit.values()):g}%; the dual wield sets keep a little extra, since white swings with two weapons miss far more often. An Orc swinging an axe (Arcanite Reaper, Annihilator) needs only
6% in melee, but the bow still needs 8%.</p>
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

<h3>Turret: a fast bow</h3>
<p>Standing at range, more Auto Shots win: Eaglehorn Long Bow (1.8 s) on Max, a Hawkeye Bow of Agility on Cheap. The
two-hander is only a stat stick. The Auto rotation weaves with any two-hander, and in a weave a slow bow wins by 30 to 90,
so with the turret sets choose the Turret rotation or the MM, BM or SV preset build.</p>

<h3>Melee: dual wield, Crusader on the main hand</h3>
<p>Survival melee dual wields: Annihilator (Max) or Dal'Rend's Sacred Charge (Cheap) in the main hand, with Bonescraper. Crusader on the main hand beats
Agility by about 3; the off hand keeps +15 Agility.</p>

<h3>Dual wield while weaving</h3>
<p>If you weave with two one-handers, play Melee Weave (Normal): it walks in only when your shots are on cooldown and
stays for the melee cooldowns, which lets the off hand swing. Teebu's Blazing Longsword (or Dal'Rend's Sacred Charge)
with Bagh Nakh and Bloodseeker gives 1172 (1169), against 1114 for the best dual wield on the max weave. A two-hander
on the max weave is still 68 higher.</p>

<h2>Enchants</h2>
<table><thead><tr><th>Slot</th><th>Enchant</th><th>Where</th></tr></thead><tbody>
{tr(['Head, legs', 'Lesser Arcane Amalgamation (+8 Agility)', 'Libram of Voracity (Dire Maul)'])}
{tr(['Neck', '+5 Agility', 'Enchanter'])}
{tr(['Back', '+5 Agility', 'Enchanter'])}
{tr(['Chest', 'Greater Stats (+4 all stats)', 'Enchanter'])}
{tr(['Wrist', '+9 Agility', 'Enchanter'])}
{tr(['Hands', 'Superior Agility (+15 Agility)', 'Enchanter'])}
{tr(['Feet', 'Greater Agility (+7 Agility)', 'Enchanter'])}
{tr(['Two-hander', '+25 Agility', 'Enchanter'])}
{tr(['Melee main hand / off hand', 'Crusader / +15 Agility', 'Enchanter'])}
{tr(['Ranged', 'SAF-T Ultra Precision Scope (+2% ranged crit)', 'Engineering'])}
</tbody></table>
<p>Every slot was checked against its other enchants. Minor Speed on boots loses to Agility, because Strider Kick's
speed already covers it and only the highest speed effect counts. Sniper Scope loses to SAF-T by 8–11.</p>

<h2>Trinkets</h2>
<p>Blackhand's Breadth and Highborne Research Tablet top almost every list. Rune of the Guard Captain (Cleansed
Vilebranch Medallion on Alliance) gains +28 Attack Power in Forest/Grassland areas such as Mount Hyjal, where it takes
the second slot for turret, melee and Weave Max (a tie with Highborne Research Tablet there, so the Rune) and falls
2 DPS behind on Weave Cheap; in Onyxia's Lair, a cavern, it keeps only its 14 Attack Power
and 0.7% hit and falls 5–12 DPS behind. Hand of Justice is within a few DPS of the melee picks. Some trinkets do more in game than here, because the sim does not model their effect and counts only their
stats: Arcanite Dragonling, Heart of Wyrmthalak, Scented Runewood Brooch, the Defender of the Timbermaw and Barkskin
pair (Teachings of the Furbolgs), Devilsaur Eye's use, and Scalding Flamehoof's run speed.</p>
"""

method = """
<h2>How these were found</h2>
<p>Every number comes from WoWSims Forever: a 180 s fight against one level 63 dragonkin boss in a Forest/Grassland area, as in Mount
Hyjal, so area-bound bonuses count; an Orc hunter with the full raid buffs and consumables of the sim's hunter
defaults; and a 150–350 ms reaction time. Each loadout uses the
sim's preset build for its playstyle: SV Weave for weave, MM for turret, SV Melee for melee.</p>
<ul>
<li>Every Phase 1 item a hunter can wear was a candidate, except raid loot, raid reputation (The Watchers) and honor
rank gear. Items are Horde; Alliance mirrors (Theramore for Darkspear, Cleansed Vilebranch Medallion for Rune of the
Guard Captain) have the same stats.</li>
<li>Each slot's candidates were screened at 3,000 iterations and the best confirmed at 20,000 against the finished set
on another seed. Δ DPS is that confirmed gap, ± its 95% margin.</li>
<li>Set bonuses were tried as whole sets, the weave's two-hander and bow as one pair, and every two-slot combination of
each slot's best alternatives was checked at the end. Every enchant was simmed against the others.</li>
</ul>
<h3>Max and Cheap</h3>
<p><b>Max</b> is everything outside raids. <b>Cheap</b> leaves out exalted reputation (Darkspear Raiders, Theramore),
battleground quartermaster gear, epic crafts (Dawn Armor, Outlaw's Collar, Timbermaw Tunic), Arcanite Reaper,
Annihilator, Heartseeker, the Beastmaster vendor pieces and world drops other than random-suffix ones. Black
Dragonscale Helm, the Devilsaur set, Legionite Glaive and the Hyper Deluxe Sniper Rifle count as cheap crafts, and the
Korrak quest weapons (Bloodseeker, Ice Barbed Spear) as cheap. Neither tier takes Warsong Gulch or Alterac Valley gear
that needs Exalted. Max is a superset: every cheap item was simmed in it too.</p>
<h3>Limits</h3>
<p>The sim models what the game files and combat logs show; a few trinket effects are missing (see How to gear). New
Forever items without a source in the game files are listed as such.</p>
"""

meta = {
    'meta': {'lede': 'WoW Forever · Phase 1 · simmed pre-raid gear for weave, turret and melee hunters',
             'footer': 'Simmed with WoWSims Forever on 2026-11-15. Item data from the game files; links go to Wowhead.'},
    'playstyles': playstyles, 'loadouts': loadouts, 'howto': howto, 'method': method,
}
json.dump(meta, open(os.path.join(R, 'meta.json'), 'w'), indent=1)
print('meta for', ', '.join(f"{i} {dps[i]:.0f}" for i in IDS))

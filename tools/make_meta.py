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
IDS = ['weave-max', 'weave-max-av', 'weave-cheap', 'turret-max', 'turret-max-av', 'turret-cheap', 'melee-max', 'melee-max-av',
       'melee-cheap']
IDS = [i for i in IDS if os.path.exists(os.path.join(R, f'{i}.guide.json'))]
runs = {i: json.load(open(os.path.join(R, f'{i}.guide.json'))) for i in IDS}
hit = json.load(open(os.path.join(R, 'hit.json')))
ep = json.load(open(os.path.join(R, 'ep.json'))) if os.path.exists(os.path.join(R, 'ep.json')) else {}
dps = {i: statistics.median(g['base'] for g in runs[i].values()) for i in IDS}
cond = {i: json.load(open(os.path.join(R, f'{i}.cond.json'))) for i in IDS if os.path.exists(os.path.join(R, f'{i}.cond.json'))}
# Rune of the Guard Captain outside Forest/Grassland: each set's loss, and the best other trinket 2's gap to it there.
rune_out = {i: c['trinket2']['best']['d'] for i, c in cond.items() if c.get('trinket2', {}).get('best')}
rune_next = {i: max(r['d'] for r in runs[i]['trinket2']['rows']) - rune_out[i] for i in rune_out}
assert all(v > 2 for v in rune_next.values()), rune_next

BUILDS = {
    'weave': ('SV Weave', '-00530501114-530200230050220151', 'Melee Weave (Max)'),
    'turret': ('MM', '5-0053452511522051-5', 'Turret'),
    'melee': ('SV Melee', '53200005001-004-530200230050022151', 'Melee'),
}
TITLES = {'weave': 'Weave', 'turret': 'Turret', 'melee': 'Melee'}
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
        'title': f"{TITLES[ps]} · {('Max · AV' if av else 'Max · Darkspear') if tier == 'max' else 'Cheap'}", 'build': b[0], 'talents': b[1], 'rotation': b[2], 'dps': round(dps[i], 1),
        'hit': f"{hit[i][0]:g}% melee, {hit[i][1]:g}% ranged (cap 8%)",
        'vsOther': f"{'Cheap' if tier == 'max' else 'Max'} {dps.get(other, 0):.0f} ({diff:+.0f})",
        'talentLink': f"https://www.wowhead.com/forever/talent-calc/hunter/{WOWHEAD_HASH_VERSION}{b[1]}",
        'simLink': LINKS.get(i, '').strip(),
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
    stats = ['Agility', 'Strength', 'Intellect', 'Attack Power', 'Ranged Attack Power', 'Crit rating', 'Hit rating (under the cap)', 'Haste rating', 'MP5']
    ep_html = ('<h3>What a point of each stat is worth</h3><p>Paired sims on each playstyle\'s Max set, in Ranged Attack '
               'Power for weave and turret and in Attack Power for melee. Item crit rating is 14 per 1%, hit and haste '
               'rating 10 per 1%. Intellect counts twice: Careful Aim turns each point into Attack Power and Ranged '
               'Attack Power, and it is mana. MP5 is worth little in a three minute fight with full consumables and '
               'more in a long one: about 2.5 Ranged Attack Power a point on the turret at five minutes.</p><table><thead><tr><th>Stat</th><th>Weave</th><th>Turret</th><th>Melee</th></tr></thead><tbody>'
               + ''.join(tr([s] + [f"{ep.get(p, {}).get(s, 0):.2f}" for p in ('weave', 'turret', 'melee')]) for s in stats)
               + '</tbody></table>')

howto = f"""
<div class="kpis">
  <div class="kpi"><b>8% hit</b><span>The cap against a level 63 boss, melee and ranged. Surefooted counts.</span></div>
  <div class="kpi"><b>Agility</b><span>The best stat for every playstyle; weave values it most.</span></div>
  <div class="kpi"><b>Slow + slow</b><span>Weave: a slow two-hander wants a slow bow (Arcanite Reaper + Deep Jungle Rifle or Bloodseeker).</span></div>
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
<p>Survival melee dual wields: Annihilator (Max) or Dal'Rend's Sacred Charge (Cheap) in the main hand, with Bonescraper. Crusader on the main hand edges
out Agility (about 2 on Max, a tie on Cheap); the off hand keeps +15 Agility.</p>

<h3>Dual wield while weaving</h3>
<p>If you weave with two one-handers, play Melee Weave (Normal): it walks in only when your shots are on cooldown and
stays for the melee cooldowns, which lets the off hand swing. Teebu's Blazing Longsword (or Dal'Rend's Sacred Charge)
with Bagh Nakh and Bloodseeker gives about 59 more than the best dual wield on the max weave. A two-hander on the max
weave is still about 68 higher.</p>

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
<p>Heart of Wyrmthalak tops the weave and melee lists: its Flame Lash procs about twice a minute from melee and ranged
hits. Blackhand's Breadth is next on weave and the best on turret, and Highborne Research Tablet is next on melee. Rune of the Guard Captain (Cleansed
Vilebranch Medallion on Alliance) gains +28 Attack Power in Forest/Grassland areas such as Mount Hyjal, and there it
takes a trinket slot in every set but Weave Cheap, where it ties with Blackhand's Breadth and Blackhand's wins the
tie (see Method). Anywhere else, in Onyxia's Lair for example, it keeps only its 14 Attack Power and 0.7% hit, and the
sets that wear it lose {-max(rune_out.values()):.0f}–{-min(rune_out.values()):.0f} DPS. Every one of them then does
{min(rune_next.values()):.0f}–{max(rune_next.values()):.0f} DPS more with its next trinket (Heart of Wyrmthalak on turret).
Each trinket card shows the Rune's figure outside the area. Hand of Justice is within a few DPS of the melee picks. Some trinkets do more in game than here, because the sim does not model their effect and counts only their
stats: Arcanite Dragonling, Scented Runewood Brooch, the Defender of the Timbermaw and Barkskin
pair (Teachings of the Furbolgs), Devilsaur Eye's use, and Scalding Flamehoof's run speed.</p>
"""

gap = {ps: dps[f"{ps}-max"] - dps[f"{ps}-max-av"] for ps in TITLES if f"{ps}-max-av" in dps}
method = f"""
<h2>How these were found</h2>
<p>Every number comes from WoWSims Forever: a 180 s fight against one level 63 dragonkin boss in a Forest/Grassland area, as in Mount
Hyjal, so area-bound bonuses count; an Orc hunter with the full raid buffs and consumables of the sim's hunter
defaults; and a 150–350 ms reaction time. Each loadout uses the
sim's preset build for its playstyle: SV Weave for weave, MM for turret, SV Melee for melee.</p>
<p>A few items have a bonus that needs an area or a creature type. Rune of the Guard Captain's counts only in
Forest/Grassland and Wyrmhide Spaulders' only against Dragonkin, so both count in these numbers; those of Royal Seal of
Eldre'Thalas (Demons), King Mosh's Tooth and Huntsman's Harpoon (Beasts) and Satyr's Bow (Elementals) do not. Each of these items shows a
second figure under its Δ DPS: the same comparison against the same set, with its condition the other way round. When
one of them ties with an item whose bonus always counts, the set wears the other item: Blackhand's Breadth over
the Rune on Weave Cheap, and Shadowcraft Spaulders or Stratholme Militia Shoulderguard over Wyrmhide Spaulders. Turret
Cheap wears Truestrike Shoulders: Wyrmhide is 1.7 DPS ahead of it against Dragonkin and 3.7 behind against anything
else, and Truestrike ties with the other shoulders while keeping Wyrmhide's 1.5% hit, so the set stays at the hit
cap.</p>
<ul>
<li>Every Phase 1 item a hunter can wear was a candidate, except raid loot, raid reputation (The Watchers) and honor
rank gear. Huntsman's Harpoon, Belt of the Trickster and Pendant of Celerity are in the game's own hotfix cache but
not in the copy the sim's item database was built from, so they were simmed afterwards against the finished sets, on
the same seed as the other rows. Items are Horde; Alliance mirrors (Theramore for Darkspear, Cleansed Vilebranch Medallion for Rune of the
Guard Captain) have the same stats.</li>
<li>Each slot's candidates were screened at 3,000 iterations and the best six confirmed at 3,000 against the finished
set on another seed. Where that run found a better item (Heart of Wyrmthalak in the weave and melee sets, Bracers of
the Eclipse on AV weave), the trinkets were simmed as pairs, and the changed slots were rerun the same way on the new
set; the other slots of those sets keep their gaps from before the change. Δ DPS is the confirmed gap, ± its 95%
margin.</li>
<li>When the sets were first built, set bonuses were tried as whole sets, the weave's two-hander and bow as one pair,
and every two-slot combination of each slot's best alternatives was checked at the end. Every enchant was simmed
against the others.</li>
</ul>
<h3>Max and Cheap</h3>
<p><b>Max</b> is everything outside raids, with Exalted reputation from the one faction you pick: <b>Darkspear</b>
(Darkspear Raiders, Theramore for the Alliance) or <b>AV</b> (Frostwolf Clan, Stormpike Guard for the Alliance). The
Darkspear sets wear Darkspear Epaulets, and the weave set Raider Gloves too. The AV sets wear Don Julio's Band in their
place and lose {min(gap.values()):.0f}–{max(gap.values()):.0f} DPS. Items that need Exalted with any other faction (The Defilers, Timbermaw Hold, the other
Warsong Gulch and Alterac Valley rewards) are in neither. <b>Cheap</b> leaves out exalted reputation, battleground
quartermaster gear, epic crafts (Dawn Armor, Timbermaw Tunic), Arcanite Reaper,
Annihilator, Heartseeker, the Beastmaster vendor pieces and world drops other than random-suffix ones. Black
Dragonscale Helm, the Devilsaur set, Legionite Glaive and the Hyper Deluxe Sniper Rifle count as cheap crafts, and the
Korrak quest weapons (Bloodseeker, Ice Barbed Spear) as cheap. Crafts that need a material from Mount Hyjal
(Outlaw's Collar, Mourning Handguards) are in no set. Max is a superset: every cheap item was simmed in it too.</p>
<h3>Limits</h3>
<p>The sim models what the game files and combat logs show; a few trinket effects are missing (see How to gear). New
Forever items without a source in the game files are listed as such.</p>
"""

meta = {
    'meta': {'lede': 'WoW Forever · Phase 1 · simmed pre-raid gear for weave, turret and melee hunters',
             'footer': 'Simmed with WoWSims Forever on 2026-11-16. Item data from the game files; links go to Wowhead.'},
    'playstyles': playstyles, 'loadouts': loadouts, 'howto': howto, 'method': method,
}
json.dump(meta, open(os.path.join(R, 'meta.json'), 'w'), indent=1)
print('meta for', ', '.join(f"{i} {dps[i]:.0f}" for i in IDS))

# Forever Hunter Guide

A hunter guide for WoW Forever, starting with pre-raid best in slot: for each playstyle (melee weave, turret,
Survival melee) and budget (Max, Cheap), every slot's best item and the next options, with their DPS gap to the best,
where to get each item, and how to gear around the hit cap and weapon speeds.

Open `index.html` in a browser, or serve the folder (`python3 -m http.server`) and open the printed address. The page
reads `data.js` and loads icons and links from Wowhead.

## Where the numbers come from

Every number is a WoWSims Forever sim (180 s, one level 63 boss, an Orc with full raid buffs and consumables, a
150–350 ms reaction time), run on the sim's preset builds: SV Weave, MM and SV Melee. The guide's Method page lists the
search and the Max/Cheap rules.

## Rebuilding the data

`data.js` is generated; do not edit it by hand.

1. In a WoWSims Forever checkout, run the per-slot search for each loadout into a runs folder (`<id>.gear.json`,
   `<id>.guide.json`, `hit.json`, optionally `ep.json`).
2. `python3 tools/make_meta.py RUNS_DIR FOREVER_CHECKOUT` writes the loadouts' facts and the prose to `RUNS_DIR/meta.json`.
3. `python3 tools/build_data.py --forever FOREVER_CHECKOUT --runs RUNS_DIR --out data.js` joins the runs with the item
   database (names, stats, icons, sources, tiers). Icons missing from the database are fetched once from Wowhead and
   kept in `tools/icons.json`.

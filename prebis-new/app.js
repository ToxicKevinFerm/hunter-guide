// Pre-raid best in slot: the gear page's layout in the class guide's colours. Same data (../data.js, window.GUIDE).
const G = window.GUIDE;
const ICON = (n, size = 'medium') => `https://wow.zamimg.com/images/wow/icons/${size}/${n || 'inv_misc_questionmark'}.jpg`;
const WH = id => `https://www.wowhead.com/forever/item=${id}`;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const $ = id => document.getElementById(id);
const SLOT_LABEL = { head: 'Head', neck: 'Neck', shoulder: 'Shoulder', back: 'Back', chest: 'Chest', wrist: 'Wrist', hands: 'Hands',
  waist: 'Waist', legs: 'Legs', feet: 'Feet', finger1: 'Ring 1', finger2: 'Ring 2', trinket1: 'Trinket 1', trinket2: 'Trinket 2',
  main_hand: 'Main hand', off_hand: 'Off hand', ranged: 'Ranged', weapons: 'Weapons', weapons_ranged: 'Weapons + ranged (as a pair)', two_hand: 'Two-hander', sets: 'Two-piece sets' };
const LEFT = ['head', 'neck', 'shoulder', 'back', 'chest', 'wrist'];
const RIGHT = ['hands', 'waist', 'legs', 'feet', 'finger1', 'finger2', 'trinket1', 'trinket2'];
const WEAPONS = ['main_hand', 'off_hand', 'ranged'];
const ORDER = [...LEFT, ...RIGHT, ...WEAPONS];
const SOURCE_KINDS = [['dungeon', 'Dungeon'], ['quest', 'Quest'], ['craft', 'Crafted'], ['vendor', 'Vendor'], ['rep', 'Reputation'],
  ['bg', 'Battleground'], ['world', 'World drop'], ['unknown', 'Unknown']];

// spec: the pick per playstyle that has one (Weave: max or normal rotation; Turret: MM or BM).
// biome, mob: the biome and creature type the cards are ranked for ('' = none, the sets' own boss).
const state = { ps: 'weave', spec: { weave: 'max', turret: 'mm' }, long: false, tier: 'max', rep: 'av', topn: 4, q: '', srcs: new Set(SOURCE_KINDS.map(s => s[0])), tab: 'gear', biome: '', mob: '' };
const CONDS = G.conds || [];
const condOf = id => CONDS.find(c => c.id === id);
const fromHash = () => {
  const p = new URLSearchParams(location.hash.slice(1));
  if (G.playstyles.some(x => x.id === p.get('ps'))) state.ps = p.get('ps');
  if (['max', 'cheap'].includes(p.get('tier'))) state.tier = p.get('tier');
  if (['darkspear', 'av'].includes(p.get('rep'))) state.rep = p.get('rep');
  if (['gear', 'all', 'howto', 'method'].includes(p.get('tab'))) state.tab = p.get('tab');
  if ((curPS().specs || []).some(x => x.id === p.get('spec'))) state.spec[state.ps] = p.get('spec');
  state.long = p.get('long') === '1';
  for (const axis of ['biome', 'mob']) if (CONDS.some(c => c.axis === axis && c.id === p.get(axis))) state[axis] = p.get(axis);
};
const toHash = () => history.replaceState(null, '', `#tab=${state.tab}&ps=${state.ps}${state.ps in state.spec ? `&spec=${state.spec[state.ps]}` : ''}&tier=${state.tier}&rep=${state.rep}${state.long ? '&long=1' : ''}${state.biome ? `&biome=${state.biome}` : ''}${state.mob ? `&mob=${state.mob}` : ''}`);

const item = id => G.items[id];
const qc = it => `color:var(--q${it ? it.q : 1})`;
// Max comes in two sets, one per exalted reputation: Darkspear Raiders (<prefix>-max) or Alterac Valley (<prefix>-max-av).
// A playstyle with specs has a set per spec and budget under the spec's prefix.
const curPS = () => G.playstyles.find(p => p.id === state.ps);
const specOf = P => (P.specs || []).find(x => x.id === state.spec[P.id]);
const loadout = () => G.loadouts[`${(specOf(curPS()) || { prefix: state.ps }).prefix}-${state.tier}${state.tier === 'max' && state.rep === 'av' ? '-av' : ''}`];
const tierLabel = () => state.tier === 'cheap' ? 'Cheap' : `Max · ${state.rep === 'av' ? 'Alterac Valley' : 'Darkspear'}`;
const itemName = spec => { const it = item(spec[0]); return it ? it.name + (spec[2] ? ' ' + (G.suffixes[spec[2]] || '') : '') : '—'; };
const enchantName = spec => spec[3] || (spec[1] ? 'Enchant ' + spec[1] : '');
const fmt = v => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}`;
const moveSpecs = move => Object.entries(move).filter(([, v]) => v && v[0]).sort((a, b) => ORDER.indexOf(a[0]) - ORDER.indexOf(b[0]));

// A Cheap card's Max rows (r.max) are the Max items above the Cheap pick; the Cheap filter keeps them.
function rowPasses(specs, r) {
  const q = state.q.trim().toLowerCase();
  return specs.every(([, spec]) => {
    const it = item(spec[0]);
    if (!it) return true;
    if (!it.kinds.some(k => state.srcs.has(k))) return false;
    return state.tier !== 'cheap' || it.tier === 'cheap' || (r && r.max);
  }) && (!q || specs.some(([, spec]) => {
    const it = item(spec[0]);
    return it && (itemName(spec).toLowerCase().includes(q) || (it.alliance && it.alliance.name.toLowerCase().includes(q)) ||
      it.sources.join(' ').toLowerCase().includes(q));
  }));
}

// ---------- The character window ----------
function renderDoll() {
  const L = loadout();
  // The long fight toggle shows the set with the pieces a 4-5 minute fight swaps in, outlined.
  const LF = state.long && L.long;
  const gear = LF ? { ...L.gear, ...L.long.pieces } : L.gear;
  const why = s => { const g = L.groups.find(g => g.id === s && g.why); return g ? ` <button class="why" type="button" data-why="${s}">${esc(g.why.label)}</button>` : ''; };
  const slot = s => {
    const spec = gear[s];
    if (!spec || !spec[0]) return `<div class="slot empty" data-go="${s}"><span class="icon"></span><span class="meta"><span class="lbl">${SLOT_LABEL[s]}</span><span class="nm">Empty</span></span></div>`;
    const it = item(spec[0]);
    return `<div class="slot${LF && L.long.pieces[s] ? ' lf' : ''}" data-go="${s}" data-tip="${spec[0]}" data-sfx="${spec[2] || 0}">
      <img class="icon" src="${ICON(it.icon, 'large')}" alt=""><span class="meta"><span class="lbl">${SLOT_LABEL[s]}${why(s)}</span>
      <span class="nm" style="${qc(it)}">${esc(itemName(spec))}${it.alliance ? `<span class="ally"> / ${esc(it.alliance.name)}</span>` : ''}</span>
      <span class="en">${esc(enchantName(spec)) || '&nbsp;'}</span></span></div>`;
  };
  const P = curPS(), sp = specOf(P);
  const lf = L.long ? `<div class="lfbox"><span class="small">Fight length</span>
      <div class="seg" role="group" aria-label="Fight length"><button data-long="0" aria-pressed="${!LF}">3 min</button><button data-long="1" aria-pressed="${!!LF}">4–5 min</button></div>
      ${LF ? `<p class="small"><b>${esc(L.long.label)}</b> (outlined): ${L.long.at.map(a => `${fmt(a.d)} ±${a.m.toFixed(1)} at ${esc(a.t)}`).join(', ')}, against this set at the same length. ${esc(L.long.note || '')}</p>` : ''}</div>` : '';
  $('doll').innerHTML = `
    <div class="col">${LEFT.map(slot).join('')}</div>
    <div class="center">
      <div><span class="small">${esc(tierLabel())}</span><h2>${esc(sp ? sp.title : P.name)}</h2>
        <p class="target">${esc(G.meta.target || '')}</p></div>
      <div class="dps"><b>${L.dps.toFixed(0)}</b><span>DPS in the sim</span></div>
      <dl class="facts">
        <dt>Build</dt><dd>${esc(L.build)}</dd>
        <dt>Talents</dt><dd><a href="${esc(L.talentLink)}" target="_blank" rel="noopener" title="Open in the Wowhead talent calculator"><code>${esc(L.talents)}</code></a></dd>
        <dt>Rotation</dt><dd>${esc(L.rotation)}</dd>
        <dt>Hit</dt><dd>${esc(L.hit)}</dd>
        <dt>vs other budget</dt><dd>${esc(L.vsOther)}</dd>
      </dl>
      ${L.simLink ? `<a class="btn primary" href="${esc(L.simLink)}" target="_blank" rel="noopener">Open this set in WoWSims ↗</a>` : ''}
      ${lf}
      <p class="blurb">${esc((sp && sp.blurb) || P.blurb)}</p>
    </div>
    <div class="col right">${RIGHT.map(slot).join('')}</div>
    <div class="weapons">${WEAPONS.map(slot).join('')}</div>`;
}

// ---------- Biome and creature type ----------
// A row whose item has a bonus in a biome or against a creature type carries its Δ there (r.c[cond] = [d, m]), against
// the same set under the same condition. Rows that only make a card under their condition carry r.x. With a biome and
// a creature type both picked, an item's two bonuses add up. A worn item with a bonus there moves the card's rows
// without one by its own gain (g.shift[cond]).
const picked = () => [state.biome, state.mob].filter(Boolean);
function ranked(g) {
  const on = picked();
  const out = [];
  for (const r of g.rows) {
    const hit = on.filter(c => r.c && r.c[c]);
    if (r.x && !hit.length) continue;
    let d = r.d, m = r.m;
    for (const c of on) {
      if (hit.includes(c)) { d += r.c[c][0] - r.d; m = Math.max(m, r.c[c][1]); }
      else d -= (g.shift && g.shift[c]) || 0;
    }
    out.push({ ...r, d, m, on: hit, base: [r.d, r.m] });
  }
  return out.sort((a, b) => b.d - a.d);
}
// Under the row: the item's figure with each of its conditions the other way round from the current pick.
function condLine(r) {
  if (!r.c) return '';
  const on = r.on || [];
  const parts = Object.entries(r.c).filter(([c]) => condOf(c)).map(([c, [d, m]]) => on.includes(c)
    ? `${condOf(c).off}: ${fmt(r.base[0])} ±${r.base[1].toFixed(1)}`
    : `${condOf(c).on}: ${fmt(d)} ±${m.toFixed(1)}`);
  return parts.length ? `<small>${esc([...new Set(parts)].join(' · '))}</small>` : '';
}

// ---------- The slot table: one table, a heading row per slot, one line per option ----------
// withEnchant: shown where a slot's options differ in enchant, so two rows of the same item don't look identical.
function itemHTML(spec, withEnchant) {
  const it = item(spec[0]);
  if (!it) return '<span class="small">empty</span>';
  const en = withEnchant && enchantName(spec);
  return `<span class="it" data-tip="${spec[0]}" data-sfx="${spec[2] || 0}"><img class="icon xs" loading="lazy" src="${ICON(it.icon)}" alt=""><a class="n" style="${qc(it)}" href="${WH(spec[0])}" target="_blank" rel="noopener">${esc(itemName(spec))}${it.alliance ? `<span class="ally"> / ${esc(it.alliance.name)}</span>` : ''}</a>${en ? `<span class="en" title="${esc(en)}">${esc(en)}</span>` : ''}</span>`;
}

// The gap chart: one scale per slot, the best item on a line, each row's bar from that line to its gap and a whisker
// for the sim's margin. A whisker that reaches the line is the same DPS as the best.
function scaleFor(rows) {
  let lo = Math.min(0, ...rows.map(r => r.d - r.m)), hi = Math.max(0, ...rows.map(r => r.d + r.m));
  if (hi - lo < 2) lo = hi - 2;
  const pad = (hi - lo) * 0.05;
  lo -= pad; hi += pad;
  return v => (v - lo) / (hi - lo) * 100;
}
const kindOf = r => r.best ? 'best' : r.d - r.m <= 0 && r.d + r.m >= 0 ? 'same' : r.d > 0 ? 'up' : 'down';
function gapChart(r, x) {
  const z = x(0);
  if (r.best) return `<span class="gap best"><i class="dot best" style="left:${z.toFixed(2)}%"></i></span>`;
  const a = x(r.d - r.m), b = x(r.d + r.m), p = x(r.d);
  return `<span class="gap ${kindOf(r)}"><i class="fill" style="left:${Math.min(p, z).toFixed(2)}%;width:${Math.abs(p - z).toFixed(2)}%"></i>
    <i class="err" style="left:${a.toFixed(2)}%;width:${Math.max(0.5, b - a).toFixed(2)}%"></i><i class="dot" style="left:${p.toFixed(2)}%"></i></span>`;
}
// Columns: phones get Item, Δ DPS and vs best, with the source under the name; wider screens add Where and Budget.
// Main hand and off hand sit side by side on wider screens, as two half tables with the phone's columns plus Budget.
const narrow = matchMedia('(max-width: 720px)');
const wide = matchMedia('(min-width: 1101px)');
const colsFor = half => ({ where: !narrow.matches && !half, tier: !narrow.matches });
const ncol = c => 3 + c.where + c.tier;
const colgroup = c => `<colgroup><col>${c.where ? '<col class="w-where">' : ''}<col class="w-d"><col class="w-chart">${c.tier ? '<col class="w-tier">' : ''}</colgroup>`;
function rowHTML(r, L, x, bestMove, c, enSlots) {
  const specs = moveSpecs(r.move);
  const k = kindOf(r);
  const its = specs.map(([, spec]) => item(spec[0])).filter(Boolean);
  const pct = L.dps ? r.d / L.dps * 100 : 0;
  // On a pair row, where to get the piece that differs from the best row (the shared piece is the same on every row).
  const differs = specs.filter(([s, spec]) => !bestMove || !bestMove[s] || bestMove[s][0] !== spec[0]).map(([, spec]) => item(spec[0])).filter(Boolean);
  const srcs = (differs.length ? differs : its).map(it => it.sources[0] || 'No source in the game files');
  const allSrcs = its.flatMap(it => it.sources).join('\n');
  // The item's figure with its biome or creature bonus the other way round, against the same set; or a scenario
  // row's note.
  const alt = condLine(r) || (r.note ? `<small>${esc(r.note)}</small>` : '');
  const d = r.best ? '<b>Best</b>' : `<b>${fmt(r.d)}</b> <small>±${r.m.toFixed(1)}</small>`;
  const maxRow = r.max || its.some(it => it.tier === 'max');
  // Phones have no Budget column: a Max row on a Cheap card says so before its source.
  const where = `<span class="w1">${!c.tier && state.tier === 'cheap' && r.max ? 'Max · ' : ''}${esc([...new Set(srcs)].join(' + '))}</span>${alt}`;
  return `<tr class="${k}"><td class="c-item"><span class="items">${specs.map(([s, spec]) => itemHTML(spec, enSlots && enSlots.has(s))).join('<span class="plus">+</span>')}</span>${c.where ? '' : `<span class="c-where" title="${esc(allSrcs)}">${where}</span>`}</td>
    ${c.where ? `<td class="c-where" title="${esc(allSrcs)}">${where}</td>` : ''}
    <td class="c-d" title="${r.best ? 'The best item in this set' : `${fmt(pct)}% of the set's DPS${k === 'same' ? ': within the margin, the same DPS' : ''}`}">${d}</td>
    <td class="c-chart">${gapChart(r, x)}</td>${c.tier ? `<td class="c-tier"${r.max && !its.some(it => it.tier === 'max') ? ' title="A third Premier piece: Cheap wears two at most"' : ''}>${maxRow ? 'Max' : state.tier === 'cheap' ? '' : 'Cheap'}</td>` : ''}</tr>`;
}
// One slot: its heading row, its options, and any raid-condition lists under it.
function groupHTML(g, L, c) {
  const n = ncol(c);
  // A list with nothing worn in its slot (one-handers on a two-hander set) has no best row; its gaps are against the set.
  const hasBest = Object.keys(g.best).length > 0;
  const rows = [...(hasBest ? [{ move: g.best, d: 0, m: 0, best: true }] : []), ...ranked(g)].sort((a, b) => b.d - a.d);
  // The card's best options, plus on a Cheap card every Max option above the Cheap pick, all in Δ order.
  const passing = rows.filter(r => rowPasses(moveSpecs(r.move), r));
  const shown = [...passing.filter(r => r.max && r.d > 0), ...passing.filter(r => !r.max).slice(0, state.topn)].sort((a, b) => b.d - a.d);
  const x = scaleFor(shown.length ? shown : rows.slice(0, 1));
  const hiddenBest = hasBest && shown.length && !rowPasses(moveSpecs(g.best));
  const head = `<tr class="gh"><th colspan="${n}" scope="rowgroup"><span class="ghn">${esc(SLOT_LABEL[g.id] || g.id)}</span>${g.why ? `<button class="why" type="button" data-why="${g.id}">${esc(g.why.label)}</button>` : ''}${g.note ? `<span class="ghnote">${esc(g.note)}</span>` : ''}</th></tr>`;
  // Slots whose shown options carry more than one enchant: name the enchant on every row of that slot.
  const en = {};
  shown.forEach(r => moveSpecs(r.move).forEach(([s, spec]) => (en[s] = en[s] || new Set()).add(enchantName(spec))));
  const enSlots = new Set(Object.keys(en).filter(s => en[s].size > 1));
  const body = shown.length ? shown.map(r => rowHTML(r, L, x, hasBest && g.best, c, enSlots)).join('') : `<tr><td colspan="${n}" class="empty">Nothing in this slot passes your filters.</td></tr>`;
  const hid = hiddenBest ? `<tr><td colspan="${n}" class="empty">The best item for this slot is hidden by your filters.</td></tr>` : '';
  // The best moves under a raid condition the set does not assume, against the set under the same condition.
  const scen = (g.scenarios || []).map(sc => {
    const rs = sc.rows.filter(r => rowPasses(moveSpecs(r.move)));
    if (!rs.length) return '';
    const sx = scaleFor(rs);
    return `<tbody class="scen" style="${bandVars(sx, rs)}"><tr class="sh"><th colspan="${n}">${esc(sc.when)}<span class="ghnote">${esc(sc.detail)}</span></th></tr>${rs.map(r => rowHTML(r, L, sx, null, c)).join('')}</tbody>`;
  }).join('');
  return `<tbody class="grp" id="card-${g.id}" style="${bandVars(x, shown)}">${head}${body}${hid}</tbody>${scen}`;
}
// The best line and, shaded around it, the slot's typical margin: a dot inside the shading is the same DPS as the best.
const median = a => { const s = a.slice().sort((p, q) => p - q); return s.length ? s[s.length >> 1] : 0; };
function bandVars(x, rows) {
  const m = median(rows.filter(r => !r.best).map(r => r.m));
  return `--z:${x(0).toFixed(2)}%;--b0:${x(-m).toFixed(2)}%;--b1:${x(m).toFixed(2)}%`;
}

// ---------- How much each slot matters: every option of every slot on one shared axis ----------
const OV_LABEL = { weapons_ranged: 'Two-hander + bow', weapons: 'Weapons', two_hand: 'Two-hander', main_hand: 'Main hand', off_hand: 'Off hand', sets: 'Two-piece sets' };
function renderOverview() {
  const L = loadout();
  const lines = L.groups.map(g => {
    const hasBest = Object.keys(g.best).length > 0;
    const rs = ranked(g).filter(r => rowPasses(moveSpecs(r.move), r));
    return { g, hasBest, rows: [...rs.filter(r => r.max && r.d > 0), ...rs.filter(r => !r.max).slice(0, 6)] };
  }).filter(o => o.rows.length || o.hasBest);
  // One axis for every slot, so a wide spread reads as a slot that matters. Very large gaps are pinned to the edge.
  const ds = lines.flatMap(o => o.rows.map(r => r.d));
  const lo = Math.max(-30, Math.min(-10, ...ds)), hi = Math.max(2, Math.min(20, Math.max(...ds, 0)));
  const pad = (hi - lo) * 0.03;
  const x = v => (Math.min(hi, Math.max(lo, v)) - lo + pad) / (hi - lo + 2 * pad) * 100;
  const ticks = [];
  for (let t = Math.ceil(lo / 10) * 10; t <= hi; t += 10) ticks.push(t);
  const tickHTML = ticks.map(t => `<i class="tk" style="left:${x(t).toFixed(2)}%"></i>`).join('');
  const rows = lines.map(({ g, hasBest, rows }) => {
    const m = median(rows.map(r => r.m));
    const same = rows.filter(r => kindOf(r) === 'same').length;
    const dots = rows.slice().sort((a, b) => a.d - b.d).map(r => {
      // The piece that differs from the best row is the one the dot stands for.
      const specs = moveSpecs(r.move);
      const [, spec] = specs.find(([s, sp]) => !hasBest || !g.best[s] || g.best[s][0] !== sp[0]) || specs[0];
      const clip = r.d < lo || r.d > hi;
      return `<i class="od ${kindOf(r)}${clip ? ' clip' : ''}" style="left:${x(r.d).toFixed(2)}%" data-tip="${spec[0]}" data-sfx="${spec[2] || 0}" data-d="${r.d}" data-m="${r.m}"></i>`;
    }).join('');
    const best = hasBest ? `<i class="od best" style="left:${x(0).toFixed(2)}%" data-tip="${moveSpecs(g.best)[0][1][0]}" data-d="0" data-m="0"></i>` : '';
    return `<button class="ov-row" type="button" data-grp="${g.id}"><span class="ov-l">${esc(OV_LABEL[g.id] || SLOT_LABEL[g.id] || g.id)}</span>
      <span class="ov-s" style="--z:${x(0).toFixed(2)}%;--b0:${x(-m).toFixed(2)}%;--b1:${x(m).toFixed(2)}%">${tickHTML}${dots}${best}</span>
      <span class="ov-n" title="Options whose margin reaches the best: the same DPS">${same ? `${same} tied` : ''}</span></button>`;
  }).join('');
  const axis = `<div class="ov-row ov-axis" aria-hidden="true"><span></span><span class="ov-s">${ticks.map(t => `<span class="tl" style="left:${x(t).toFixed(2)}%">${t ? `${t > 0 ? '+' : '−'}${Math.abs(t)}` : 'best'}</span>`).join('')}</span><span></span></div>`;
  // Folded by default; the summary line says what's inside.
  const tied = lines.reduce((n, o) => n + o.rows.filter(r => kindOf(r) === 'same').length, 0);
  const tiedSlots = lines.filter(o => o.rows.some(r => kindOf(r) === 'same')).length;
  $('ovteaser').textContent = tied ? `${tied} option${tied > 1 ? 's' : ''} tied with the best, in ${tiedSlots} slot${tiedSlots > 1 ? 's' : ''}` : 'No option ties the best in this set';
  $('overview').innerHTML = `<p class="small ov-p">Every simmed option (the best six per slot) against the slot's best, on one scale. Dots bunched in the shading are the same DPS: wear what you have. Spread out: the slot is worth chasing.</p>${axis}${rows}`;
}
function renderCards() {
  const L = loadout();
  const c = colsFor(false), h = colsFor(true);
  const out = [];
  for (let i = 0; i < L.groups.length; i++) {
    const g = L.groups[i], next = L.groups[i + 1];
    if (g.id === 'main_hand' && next && next.id === 'off_hand' && wide.matches) {
      const half = x => `<table class="bt half">${colgroup(h)}${groupHTML(x, L, h)}</table>`;
      out.push(`<tbody class="halves"><tr><td colspan="${ncol(c)}"><div class="halves-in">${half(g)}${half(next)}</div></td></tr></tbody>`);
      i++;
    } else out.push(groupHTML(g, L, c));
  }
  renderOverview();
  $('cards').innerHTML = `<table class="bt">${colgroup(c)}<thead><tr><th class="c-item">Item</th>${c.where ? '<th class="c-where">Where</th>' : ''}<th class="c-d">Δ DPS</th><th class="c-chart">vs best</th>${c.tier ? '<th class="c-tier">Budget</th>' : ''}</tr></thead>${out.join('')}</table>`;
}

// ---------- All loadouts ----------
// Rings and trinkets have no order: each loadout's pair is listed with the item more loadouts wear first.
function pairedGear(ids) {
  const out = Object.fromEntries(ids.map(id => [id, { ...G.loadouts[id].gear }]));
  for (const [a, b] of [['finger1', 'finger2'], ['trinket1', 'trinket2']]) {
    const count = {};
    ids.forEach(id => [a, b].forEach(s => { const v = out[id][s]; if (v && v[0]) count[v[0]] = (count[v[0]] || 0) + 1; }));
    ids.forEach(id => {
      const x = out[id][a], y = out[id][b];
      if (x && y && (count[y[0]] || 0) > (count[x[0]] || 0)) { out[id][a] = y; out[id][b] = x; }
    });
  }
  return out;
}
function renderMatrix() {
  const ids = Object.keys(G.loadouts), cur = ids.find(id => G.loadouts[id] === loadout());
  const gear = pairedGear(ids);
  const head = ids.map(id => `<th class="${id === cur ? 'on' : ''}">${esc(G.loadouts[id].title)}<small>${G.loadouts[id].dps.toFixed(0)} DPS</small></th>`).join('');
  const rows = ORDER.map(s => {
    const cells = ids.map(id => gear[id][s] || [0, 0, 0]);
    if (cells.every(c => !c[0])) return '';
    const keys = cells.map(c => c[0] + ':' + c[2]);
    const counts = {};
    keys.forEach(k => counts[k] = (counts[k] || 0) + 1);
    const common = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
    const same = keys.every(k => k === keys[0]);
    return `<tr class="${same ? 'same' : ''}"><td class="sl">${SLOT_LABEL[s]}</td>${cells.map((c, i) =>
      `<td class="${!same && keys[i] !== common ? 'odd' : ''}">${c[0] ? itemHTML(c, true) : '<span class="small">—</span>'}</td>`).join('')}</tr>`;
  }).join('');
  $('matrix').innerHTML = `<table><thead><tr><th class="sl">Slot</th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

// ---------- The game's item tooltip ----------
function tipHTML(id, sfx) {
  const it = item(id);
  if (!it) return '';
  const sx = sfx && it.suffixStats && it.suffixStats[sfx];
  const L = [];
  if (it.weapon) {
    L.push(`<div class="row"><span class="w">${it.weapon.min}–${it.weapon.max} Damage</span><span class="w">Speed ${it.weapon.speed.toFixed(2)}</span></div>`);
    L.push(`<div class="w">(${it.weapon.dps.toFixed(1)} damage per second)</div>`);
  }
  if (it.armor) L.push(`<div class="w">${it.armor} Armor</div>`);
  for (const [k, v] of it.white) L.push(`<div class="w">+${v} ${k}</div>`);
  if (sx) for (const [k, v] of sx) L.push(`<div class="w">+${v} ${k}</div>`);
  for (const line of it.green) L.push(`<div class="g">${esc(line)}</div>`);
  return `<div class="t" style="${qc(it)}">${esc(it.name)}${sfx ? ' ' + esc(G.suffixes[sfx] || '') : ''}</div>
    ${it.unique ? '<div class="w">Unique</div>' : ''}
    <div class="row"><span class="w">${esc(it.slot)}</span><span class="w">${esc(it.kind || '')}</span></div>
    ${L.join('')}${it.set ? `<div class="y">${esc(it.set)}</div>` : ''}
    <div class="m">Item level ${it.ilvl}${it.side ? ' · ' + it.side + ' only' : ''}</div>
    ${it.alliance ? `<div class="m">Alliance: ${esc(it.alliance.name)}, identical</div>` : ''}
    <div class="src">${it.sources.map(s => `<div class="y">${esc(s)}</div>`).join('') || '<div class="m">No source in the game files</div>'}</div>
    <div class="m">${it.premier ? 'Premier: Cheap sets wear two at most' : it.tier === 'cheap' ? 'In the Cheap sets' : 'Max sets only'}</div>`;
}
const whyOf = s => loadout().groups.find(g => g.id === s).why;
const tip = $('tip');
document.addEventListener('mousemove', e => {
  const t = e.target.closest('[data-tip], [data-why]');
  if (!t || !matchMedia('(hover: hover)').matches) { tip.hidden = true; return; }
  const why = t.dataset.why && whyOf(t.dataset.why);
  tip.classList.toggle('wide', !!why);
  // A dot in the overview says its gap first.
  const gapLine = t.dataset.d == null ? '' : +t.dataset.d === 0 && +t.dataset.m === 0 ? '<div class="tipd best">The best in this slot</div>'
    : `<div class="tipd">${fmt(+t.dataset.d)} ±${(+t.dataset.m).toFixed(1)} DPS against the best${Math.abs(+t.dataset.d) <= +t.dataset.m ? ': the same DPS' : ''}</div>`;
  tip.innerHTML = why ? `<div class="t y">${esc(why.label)}</div>${why.lines.map(l => `<p class="why-l">${esc(l)}</p>`).join('')}` : gapLine + tipHTML(+t.dataset.tip, +t.dataset.sfx);
  tip.hidden = false;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = e.clientX + 16, y = e.clientY + 16;
  if (x + w > innerWidth - 8) x = e.clientX - w - 16;
  if (y + h > innerHeight - 8) y = Math.max(8, innerHeight - h - 8);
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
});

function openInfo(title, body) {
  tip.hidden = true;
  $('infotitle').textContent = title;
  $('infobody').innerHTML = body;
  $('infomodal').hidden = false;
  document.body.classList.add('modal-open');
  $('infomodal').querySelector('.modal-close').focus();
}
function closeModals() { $('infomodal').hidden = true; document.body.classList.remove('modal-open'); }

// ---------- Controls ----------
function renderStatic() {
  // The key draws its three examples with the same chart as the tables, on one small scale.
  const kx = v => (v + 9) / 18 * 100;
  $('key').innerHTML = [[{ best: true, d: 0, m: 0 }, 'Best item'], [{ d: -1.5, m: 2.5 }, 'Same DPS: the margin reaches the best'], [{ d: -6, m: 1.5 }, 'Lower'],
    [{ d: 6, m: 1.5 }, 'Higher than the set’s pick']]
    .map(([r, l]) => `<span class="k"><span class="kchart" style="--z:${kx(0).toFixed(2)}%;--b0:${kx(-2).toFixed(2)}%;--b1:${kx(2).toFixed(2)}%">${gapChart(r, kx)}</span>${l}</span>`).join('')
    + `<span class="ktext">The bar is the DPS an item loses against the best and the whisker the sim's ± margin. The shading around the best line is the slot's typical margin: anything inside it is the same DPS.</span>`;
  $('lede').textContent = G.meta.lede;
  $('howto').innerHTML = G.howto;
  $('method').innerHTML = G.method;
  $('foot').innerHTML = `${esc(G.meta.footer)} · <a href="../guide/">Class guide</a>`;
  $('ps').innerHTML = G.playstyles.map(p => `<button data-ps="${p.id}">${esc(p.short)}</button>`).join('');
  $('tier').innerHTML = '<button data-tier="max">Max</button><button data-tier="cheap">Cheap</button>';
  $('rep').innerHTML = '<button data-rep="darkspear" title="Darkspear Raiders (Alliance: Theramore)">Darkspear</button><button data-rep="av" title="Frostwolf Clan (Alliance: Stormpike Guard)">AV</button>';
  $('topn').innerHTML = [3, 4, 6].map(n => `<button data-topn="${n}">${n}</button>`).join('');
  for (const axis of ['biome', 'mob'])
    $(axis).innerHTML = '<option value="">None</option>' + CONDS.filter(c => c.axis === axis).map(c => `<option value="${c.id}">${esc(c.label)}</option>`).join('');
}
// The cards' biome and creature type: the pick, and one line saying what moved.
function renderCond() {
  for (const axis of ['biome', 'mob']) { $(axis).value = state[axis]; $(axis).classList.toggle('on', !!state[axis]); }
  const on = picked().map(condOf);
  $('condnote').hidden = !on.length;
  $('condnote').textContent = on.length ? `Ranked for ${on.map(c => c.label).join(' and ')}: items with a bonus there move, against the same set.` : '';
}
function renderSources() {
  $('srcs').innerHTML = SOURCE_KINDS.map(([k, n]) => `<label><input type="checkbox" data-src="${k}"${state.srcs.has(k) ? ' checked' : ''}> ${n}</label>`).join('')
    + '<button class="why" type="button" data-srcall>Show all</button>';
  const on = SOURCE_KINDS.filter(([k]) => state.srcs.has(k)).length;
  $('srcsum').textContent = on === SOURCE_KINDS.length ? 'All sources' : `${on} of ${SOURCE_KINDS.length} sources`;
  $('srcsum').classList.toggle('on', on !== SOURCE_KINDS.length);
}
function render() {
  const pressed = (sel, key, v) => document.querySelectorAll(sel).forEach(b => b.setAttribute('aria-pressed', b.dataset[key] === String(v)));
  pressed('[data-ps]', 'ps', state.ps);
  pressed('[data-tier]', 'tier', state.tier);
  pressed('[data-rep]', 'rep', state.rep);
  pressed('[data-topn]', 'topn', state.topn);
  $('repgroup').hidden = state.tier !== 'max';
  const P = curPS();
  $('specgroup').hidden = !P.specs;
  if (P.specs) {
    $('speclabel').textContent = P.specLabel;
    $('spec').innerHTML = P.specs.map(x => `<button data-spec="${x.id}" title="${esc(x.name)}" aria-pressed="${x.id === state.spec[P.id]}">${esc(x.short)}</button>`).join('');
  }
  document.querySelectorAll('.tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.tab === state.tab));
  document.querySelectorAll('section[data-panel]').forEach(s => s.hidden = s.dataset.panel !== state.tab);
  $('bar').hidden = state.tab !== 'gear';
  if (state.tab === 'gear') { renderDoll(); renderCond(); renderCards(); }
  if (state.tab === 'all') renderMatrix();
  toHash();
}

document.addEventListener('click', e => {
  const t = e.target;
  if (t.closest('.modal-close') || t.classList.contains('modal')) { closeModals(); return; }
  if (!t.closest('#srcpick')) $('srcpick').open = false;
  const w = t.closest('[data-why]');
  if (w) { const why = whyOf(w.dataset.why); openInfo(why.label, why.lines.map(l => `<p>${esc(l)}</p>`).join('')); return; }
  if (t.closest('[data-srcall]')) { SOURCE_KINDS.forEach(([k]) => state.srcs.add(k)); renderSources(); renderCards(); return; }
  const og = t.closest('[data-grp]');
  if (og) {
    const body = $('card-' + og.dataset.grp);
    if (body) { body.scrollIntoView({ block: 'start' }); body.classList.add('flash'); setTimeout(() => body.classList.remove('flash'), 1400); }
    return;
  }
  const b = t.closest('button,[data-go]');
  if (!b) return;
  if (b.dataset.ps) state.ps = b.dataset.ps;
  else if (b.dataset.tier) state.tier = b.dataset.tier;
  else if (b.dataset.rep) state.rep = b.dataset.rep;
  else if (b.dataset.spec) state.spec[state.ps] = b.dataset.spec;
  else if (b.dataset.long) state.long = b.dataset.long === '1';
  else if (b.dataset.topn) state.topn = +b.dataset.topn;
  else if (b.dataset.tab) state.tab = b.dataset.tab;
  else if (b.dataset.go) {
    if (t.closest('a')) return;
    const L = loadout();
    const g = L.groups.find(g => g.id === b.dataset.go && b.dataset.go in g.best) || L.groups.find(g => b.dataset.go in g.best);
    const card = g && $('card-' + g.id);
    if (card) { card.scrollIntoView({ block: 'start' }); card.classList.add('flash'); setTimeout(() => card.classList.remove('flash'), 1400); }
    return;
  } else return;
  render();
});
document.addEventListener('change', e => {
  if (e.target.id === 'biome' || e.target.id === 'mob') {
    state[e.target.id] = e.target.value;
    renderCond(); renderCards(); toHash();
    return;
  }
  const s = e.target.dataset && e.target.dataset.src;
  if (!s) return;
  e.target.checked ? state.srcs.add(s) : state.srcs.delete(s);
  renderSources(); renderCards();
  $('srcpick').open = true;
});
$('q').addEventListener('input', e => { state.q = e.target.value; renderCards(); });
[narrow, wide].forEach(q => q.addEventListener('change', () => { if (state.tab === 'gear') renderCards(); }));
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeModals(); $('srcpick').open = false; } });

// The table's header row sticks just under the control bar, whatever height the bar wraps to.
new ResizeObserver(() => document.documentElement.style.setProperty('--barh', $('bar').offsetHeight + 'px')).observe($('bar'));

fromHash();
renderStatic();
renderSources();
render();

const T = window.TALENTS;
const G = window.GUIDE;
const ICON = (n, size = 'large') => `https://wow.zamimg.com/images/wow/icons/${size}/${n || 'inv_misc_questionmark'}.jpg`;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const $ = id => document.getElementById(id);
const BUILD = Object.fromEntries(G.builds.map(b => [b.id, b]));
const SPEC = Object.fromEntries(G.specs.map(s => [s.id, s]));
const FIGHTS = [[90, '1.5 min'], [180, '3 min'], [300, '5 min']];
// The build cards, recommended first.
// Short names for the build bar, where all eight have to fit on one line.
const SHORT = { 'mm-long': 'MM Long', 'mm-pet': 'MM Pet', 'sv-melee-lw': 'SV Melee LW' };
const ORDER = ['sv-weave', 'mm-turret', 'bm-turret', 'sv-melee', 'sv-turret', 'mm-long', 'mm-pet', 'sv-melee-lw'].filter(id => BUILD[id]);

// Talent strings: one digit per talent, tree by tree in the sim's order, trailing zeros dropped, trees split by "-".
const decode = s => T.trees.map((t, i) => {
  const part = (s.split('-')[i] || '');
  return t.talents.map((_, j) => +(part[j] || 0));
});
const sum = a => a.reduce((x, y) => x + y, 0);
const wowhead = s => `https://www.wowhead.com/forever/talent-calc/hunter/${T.hashVersion}${s}`;
const HAWK = T.trees[0].talents.findIndex(t => t.name === 'Summon Hawk');
const petLabel = b => b.pet ? `${b.pet}${decode(b.talents)[0][HAWK] ? ' + hawks' : ''}` : 'None (Lone Wolf)';
const psOf = b => b.ps;                                   // weave | turret | melee: the prep and stat tables
const raceCol = b => b.id === 'bm-turret' ? 'bm' : b.ps;

const state = { build: 'sv-weave', fight: 180, rot: null, talent: null };

// ---------- Text helpers ----------
const PREP_ITEMS = Object.fromEntries([...G.prep.consumables, ...G.prep.buffs].flatMap(x => [x, ...(x.alts || [])])
  .map(x => [x.name, [x.icon, x.spell || null, x.item || null]]));
function abilityLink(name, cls = 'sp') {
  const a = G.abilities[name] || PREP_ITEMS[name];
  const href = a && a[1] ? `https://www.wowhead.com/forever/spell=${a[1]}` : a && a[2] ? `https://www.wowhead.com/forever/item=${a[2]}` : null;
  return href ? `<a class="${cls}" href="${href}" target="_blank" rel="noopener">${esc(name)}</a>` : `<span class="${cls}">${esc(name)}</span>`;
}
const iconOf = name => (G.abilities[name] || PREP_ITEMS[name] || [])[0];
const abilityIcon = (name, cls = 'ai') => `<img class="${cls}" src="${ICON(iconOf(name), 'large')}" alt="">`;
const rich = s => esc(s).replace(/\[\[(.+?)\]\]/g, (_, n) => abilityLink(n.replace(/&#39;|&apos;/g, "'"))).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
const sgn = v => Math.abs(v) < 0.5 ? '0' : `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(0)}`;

// ---------- Talent values ----------
function valueOf(b, name, ti, i) {
  if (b.talentValues) return b.talentValues[name] ? b.talentValues[name][0] : null;
  const src = BUILD[b.valuesFrom];
  if (!src || !src.talentValues || !src.talentValues[name]) return null;
  if (decode(src.talents)[ti][i] !== decode(b.talents)[ti][i]) return null;
  return src.talentValues[name][0];
}
const tier = v => v >= 40 ? 'core' : v >= 10 ? 'good' : 'minor';
const noteFor = (b, name) => (G.buildTalentNotes[b.id] || {})[name] || G.talentNotes[name];
const hasBadge = (b, name, pts) => !!noteFor(b, name) && (pts > 0 || !!(G.buildTalentNotes[b.id] || {})[name] || name === 'Lone Wolf');
function hasTalent(b, name) {
  const pts = decode(b.talents);
  return T.trees.some((tree, ti) => tree.talents.some((t, i) => t.name === name && pts[ti][i] > 0));
}
const applies = (x, b) => (!x.talent || hasTalent(b, x.talent)) && (x.pet === undefined || !!b.pet === x.pet) && (!x.builds || x.builds.includes(b.id));

// ---------- 1 · Pick a build ----------
function renderPick() {
  const b = BUILD[state.build], f = state.fight;
  $('fights').innerHTML = FIGHTS.map(([v, l]) => `<button data-fight="${v}" aria-pressed="${v === f}">${l}</button>`).join('');
  const rank = ORDER.slice().sort((x, y) => BUILD[y].dps[f] - BUILD[x].dps[f]);
  const top = BUILD[rank[0]].dps[f];
  $('builds').innerHTML = ORDER.map(id => {
    const x = BUILD[id], on = id === state.build;
    return `<button class="bcard" role="listitem" data-build="${id}" aria-pressed="${on}">
      <span class="brow"><span class="diff ${x.difficulty}">${x.difficulty}</span><span class="rank">#${rank.indexOf(id) + 1}</span></span>
      <span class="bname"><img src="${ICON(SPEC[x.spec].icon, 'medium')}" alt="">${esc(x.name)}</span>
      <span class="bsub">${esc(x.sub)}</span>
      <span class="bdps"><b>${Math.round(x.dps[f])}</b> DPS</span>
      <span class="bar"><span style="width:${(x.dps[f] / top * 100).toFixed(1)}%"></span></span>
    </button>`;
  }).join('');
  $('bbchips').innerHTML = ORDER.map(id => {
    const x = BUILD[id];
    return `<button class="bb-chip" data-build="${id}" title="${esc(x.name)}" aria-pressed="${id === state.build}"><img src="${ICON(SPEC[x.spec].icon, 'small')}" alt=""><span>${esc(SHORT[id] || x.name)}</span><b>${Math.round(x.dps[f])}</b></button>`;
  }).join('');
  $('picked').innerHTML = `<div class="pk-main"><span class="small">You picked</span><h3>${esc(b.name)}</h3><p>${rich(b.when)}</p></div>
    <dl class="pk-facts">
      <div><dt>Spec</dt><dd>${SPEC[b.spec].name}</dd></div>
      <div><dt>Style</dt><dd>${esc(b.psLabel || G.playstyles[b.ps].name)}</dd></div>
      <div><dt>Pet</dt><dd>${esc(petLabel(b))}</dd></div>
      <div><dt>Difficulty</dt><dd>${b.difficulty}</dd></div>
    </dl>`;
}

// ---------- 2 · Talents (read only) ----------
function defaultTalent(b) {
  const pts = decode(b.talents);
  let best = null, bv = -1;
  T.trees.forEach((tree, ti) => tree.talents.forEach((t, i) => {
    const v = pts[ti][i] ? valueOf(b, t.name, ti, i) : null;
    if (v != null && v > bv) { bv = v; best = t.name; }
  }));
  return best || 'Lone Wolf';
}
function renderTalents() {
  const b = BUILD[state.build], pts = decode(b.talents);
  if (!state.talent) state.talent = defaultTalent(b);
  let sel = null;
  $('trees').innerHTML = T.trees.map((tree, ti) => {
    const rows = Math.max(...tree.talents.map(t => t.row)) + 1;
    const cells = tree.talents.map((t, i) => {
      const p = pts[ti][i], v = p ? valueOf(b, t.name, ti, i) : null;
      const on = t.name === state.talent;
      if (on) sel = { t, ti, i, p, v };
      const ring = p ? (v != null ? tier(v) : 'taken') : 'off';
      return `<button class="tal ${ring}" style="grid-row:${t.row + 1};grid-column:${t.col + 1}" data-tal="${esc(t.name)}" aria-pressed="${on}" aria-label="${esc(t.name)}, ${p} of ${t.max}">
        <img src="${ICON(t.icon)}" alt=""><span class="pts">${p}/${t.max}</span>${hasBadge(b, t.name, p) ? '<i class="idot">i</i>' : ''}</button>`;
    }).join('');
    return `<div class="tree"><div class="bgimg" style="background-image:url('${tree.bg}')"></div><div class="tree-h"><b>${tree.name}</b><span>${sum(pts[ti])} pts</span></div>
      <div class="tgrid">${cells}</div></div>`;
  }).join('') + '<aside class="talinfo-in"><div class="ti-body" id="talinfo" aria-live="polite"></div></aside>';
  if (!sel) { state.talent = defaultTalent(b); return renderTalents(); }
  renderTalInfo(sel);
  $('wowhead').href = wowhead(b.talents);
  $('splitpts').textContent = pts.map(sum).join(' / ');
}

// Clicking a talent only moves the highlight and refills the panel: the trees stay put.
function selectTalent(name) {
  state.talent = name;
  const b = BUILD[state.build], pts = decode(b.talents);
  document.querySelectorAll('.tal').forEach(el => el.setAttribute('aria-pressed', el.dataset.tal === name));
  T.trees.forEach((tree, ti) => tree.talents.forEach((t, i) => {
    if (t.name === name) { const p = pts[ti][i]; renderTalInfo({ t, ti, i, p, v: p ? valueOf(b, t.name, ti, i) : null }); }
  }));
}
function renderTalInfo(sel) {
  const b = BUILD[state.build];
  const { t, p, v } = sel;
  const rankText = t.ranks[Math.max(0, p - 1)] || t.ranks[0] || '';
  const worth = p ? (v != null ? `+${Math.round(v)} DPS in this build` : 'Taken: not simmed alone') : 'Not taken in this build';
  const note = noteFor(b, t.name) || (p ? 'Nothing tricky here: take the points and forget about it.' : 'This build skips it: the points do more elsewhere.');
  $('talinfo').innerHTML = `<span class="small">${T.trees[sel.ti].name}</span>
    <div class="ti-h"><img src="${ICON(t.icon)}" alt=""><h3>${esc(t.name)}</h3></div>
    <div class="chips"><span class="chip">${p} / ${t.max} points</span><span class="chip worth ${p && v != null ? tier(v) : 'off'}">${worth}</span></div>
    <p class="ti-rank">${esc(rankText)}</p>
    <p class="ti-note">${rich(note)}</p>
    ${t.spell ? `<a class="small" href="https://www.wowhead.com/forever/spell=${t.spell}" target="_blank" rel="noopener">Wowhead tooltip ↗</a>` : ''}`;
}

// ---------- 3 · How to play ----------
function renderPlay() {
  const b = BUILD[state.build];
  const rid = G.rotationOf[b.id];
  const variants = Array.isArray(rid) ? rid : null;
  if (variants && !variants.includes(state.rot)) state.rot = variants[0];
  const R = G.rotations[variants ? state.rot : rid];
  $('variants').hidden = !variants;
  $('variants').innerHTML = variants ? variants.map(v => {
    const V = G.rotations[v].variant;
    return `<button data-rot="${v}" aria-pressed="${v === state.rot}">${esc(V.name)} · ${V.difficulty}</button>`;
  }).join('') : '';
  $('playintro').innerHTML = variants ? rich(R.variant.text)
    : b.ps === 'melee' ? 'Stand in melee and fight. After the opener, press the first thing on the list that’s ready.'
    : 'Stand at range. Auto Shot fires by itself: after the opener, press the first shot on the list that’s ready.';

  const item = (cast, text, k) => `<li>${abilityIcon(cast, 'ai ' + k)}<span>${abilityLink(cast, 'pname')}<small>${rich(text)}</small></span></li>`;
  const steps = R.cycle
    ? R.cycle.map(c => c.step === 'move'
      ? { k: 'move', title: c.title, when: c.when, items: `<li>${abilityIcon(c.title, 'ai move')}<span><small>${rich(c.text)}</small></span></li>` }
      : { k: c.step, title: c.title, items: c.press.map(x => item(x.cast, x.text, c.step)).join('') })
    : [{ k: b.ps === 'melee' ? 'melee' : 'range', title: 'Press the first one ready', items: R.priority.filter(x => applies(x, b)).map(x => item(x.cast, x.text, x.where || (b.ps === 'melee' ? 'melee' : 'range'))).join('') }];
  $('loop').innerHTML = steps.map((s, i) => `<li class="step ${s.k}"><div class="step-h"><span class="num">${i + 1}</span><h3>${esc(s.title)}</h3></div>
    ${s.when ? `<p class="when"><b>When:</b> ${rich(s.when)}</p>` : ''}<ul class="press">${s.items}</ul></li>`).join('');
  $('after').innerHTML = `↻ ${rich(R.after)}`;
  $('howto').hidden = !variants;
  $('opener').innerHTML = R.opener.filter(x => applies(x, b)).map((x, i) => `<li><span class="on-n">${i + 1}</span>${x.cast.map(n => abilityIcon(n, 'ai xs')).join('')}
    <span class="on-t"><span>${x.cast.map(n => abilityLink(n, 'on')).join(' + ')}</span>${x.note ? `<small>${esc(x.note)}</small>` : ''}</span></li>`).join('');
  $('tips').innerHTML = R.tips.filter(x => applies(x, b)).map(x => `<li>${rich(x.text)}</li>`).join('');
}

// ---------- 4 · Before the pull ----------
function renderPrep() {
  const b = BUILD[state.build], ps = psOf(b), tot = G.prep.totals[ps];
  $('prepkey').innerHTML = rich(G.prep.keys[ps]);
  $('consworth').textContent = '+' + Math.round(tot.consumables);
  $('buffworth').textContent = '+' + Math.round(tot.buffs);
  const col = raceCol(b);
  const best = G.prep.races.list.slice().sort((x, y) => y.dps[col] - x.dps[col])[0];
  $('racetip').innerHTML = `Six races finish within about 1% of each other. For the last percent on ${esc(b.name)}: <b>${esc(best.name)}</b>.`;
}

// ---------- 5 · Stats ----------
function renderStats() {
  const ci = { weave: 1, turret: 2, melee: 3 }[psOf(BUILD[state.build])];
  const rows = G.stats.weights.map(r => [r[0].replace(' rating', '').replace(' (under the cap)', ' (to 8%)'), r[ci]]).sort((a, b) => b[1] - a[1]);
  const top = rows[0][1];
  $('statlist').innerHTML = rows.map(([n, w], i) => `<div class="srow"><span class="sr">${i + 1}</span><span class="sn">${esc(n)}</span>
    <span class="bar"><span class="${i ? '' : 'top'}" style="width:${(w / top * 100).toFixed(0)}%"></span></span><span class="sw">${w.toFixed(2)}</span></div>`).join('')
    + `<p class="small">What a point of each stat is worth, in attack power, for ${esc(G.playstyles[psOf(BUILD[state.build])].name.toLowerCase())}.</p>`;
}

// ---------- Info modal: consumables & buffs, races, fast bow, method ----------
let infoKind = null, prepTab = 'consumables';
function openInfo(kind) {
  infoKind = kind;
  const b = BUILD[state.build], ps = psOf(b);
  $('infofor').textContent = kind === 'method' || kind === 'fastbow' ? '' : `For ${b.name}`;
  let title = '', body = '';
  if (kind === 'prep') {
    title = prepTab === 'buffs' ? 'Raid buffs & debuffs' : 'Consumables';
    const list = G.prep[prepTab].filter(x => applies(x, b)).slice().sort((x, y) => y.v[ps] - x.v[ps]);
    const mx = Math.max(...list.map(x => x.v[ps]));
    body = `<p class="sub">Each number is what you lose without that one thing, with everything else on. Top of the list matters most.</p>
      <div class="seg" role="group" aria-label="List">${[['consumables', 'Consumables'], ['buffs', 'Buffs']].map(([k, l]) => `<button data-tab="${k}" aria-pressed="${k === prepTab}">${l}</button>`).join('')}</div>
      <ul class="mlist">${list.map((x, i) => {
        const v = x.v[ps], cls = v >= 40 ? 'core' : v > 0.5 ? 'pos' : v < -0.5 ? 'neg' : 'zero';
        return `<li><span class="mr">${i + 1}</span><img class="ai" src="${ICON(x.icon)}" alt="">
        <span class="mt">${abilityLink(x.name, 'pname')}<small>${esc(x.what)}</small>${x.note ? `<small class="mnote">${rich(x.note)}</small>` : ''}</span>
        <span class="mv ${cls}"><b>${Math.abs(v) < 0.5 ? 'nothing' : sgn(v) + ' DPS'}</b><span class="bar"><span style="width:${Math.max(0, v / mx * 100).toFixed(0)}%"></span></span></span></li>`;
      }).join('')}</ul>
      <p class="small">Sim values for the ${esc(G.playstyles[ps].name.toLowerCase())} playstyle, 3 minute boss.</p>`;
  } else if (kind === 'races') {
    title = 'Compare races';
    const col = raceCol(b);
    const list = G.prep.races.list.slice().sort((x, y) => y.dps[col] - x.dps[col]);
    const best = list[0].dps[col];
    body = `<p class="sub">${rich(G.prep.races.note)}</p><ul class="mlist">${list.map((r, i) => {
      const pct = (r.dps[col] / best - 1) * 100, cls = pct > -0.3 ? 'core' : pct > -1.2 ? 'pos' : 'neg';
      return `<li><span class="mr">${i + 1}</span><img class="ai" src="${ICON(r.icon)}" alt="">
        <span class="mt"><b>${esc(r.name)}</b> <small class="fac">${r.faction}</small><small>${r.racials.map(x => `<b>${esc(x.name)}</b>: ${esc(x.what)}`).join(' · ')}</small></span>
        <span class="mv ${cls}"><b>${Math.round(r.dps[col])}${i ? ` · ${pct.toFixed(1)}%` : ' · best'}</b><span class="bar"><span style="width:${Math.max(4, 100 + pct * 25).toFixed(0)}%"></span></span></span></li>`;
    }).join('')}</ul><p class="small">${rich(G.prep.races.foot)}</p>`;
  } else if (kind === 'fastbow') {
    title = 'Why turret wants a fast bow';
    const F = G.fastBow;
    body = `<p class="sub">Eaglehorn Long Bow (1.8 s) does <b>38 more DPS</b> than a 3.3 s bow with the same damage per second, and <b>80 more</b> in a 5 minute fight.</p>
      <table class="dtable"><thead><tr><th>A slow bow instead</th><th>3 min</th><th>5 min</th></tr></thead><tbody>
      ${[...F.rows, F.total].map((r, i, a) => `<tr class="${i === a.length - 1 ? 'total' : ''}"><td>${esc(r[0])}</td><td class="n">${sgn(r[1])}</td><td class="n">${sgn(r[2])}</td></tr>`).join('')}</tbody></table>
      <ul class="plain"><li><b>Aimed Shot is normalized:</b> its attack power bonus counts every bow as 2.8 s, so a slow bow only adds its own damage roll.</li>
      <li><b>Casting doesn't cost Auto Shots:</b> on Forever, Auto Shot keeps firing while you cast.</li>
      <li><b>More shots, more Quick Shots:</b> each Auto Shot can proc Deadly Aspects' +30% speed.</li>
      <li><b>More hits, more mana:</b> Judgement of Wisdom returns mana per hit.</li></ul>
      <p class="small">${esc(F.real)} Weaving is the other way round: your swing restarts Auto Shot, so a slow two-hander wants a slow bow.</p>`;
  } else if (kind === 'method') {
    title = 'How we tested';
    body = `<p>Every number is a WoWSims Forever sim (${G.meta.simDate}, ${G.meta.iterations} iterations): the sim's preset for each build, an Orc in the playstyle's best pre-raid gear, full raid buffs and consumables, a level 63 Dragonkin boss, a 3 minute fight.</p>
      <p>A talent's, consumable's or buff's worth is the build's DPS minus the same build without it. Races, consumables and buffs use Kings as the only blessing, as on Forever.</p>
      <h4>Least certain</h4><ul class="plain"><li><b>Pets.</b> The sim undercounts pet focus, so BM and SV Melee may be a little low.</li>
      <li><b>Target type.</b> Improved Tracking counts against the Dragonkin boss used here; against an untracked type it's worth nothing.</li></ul>
      <h4>Sources</h4><p>Talents and tooltips from Wowhead's Forever talent calculator. Hunter mechanics from the <a href="https://github.com/classic-hunter/forever-hunter/wiki" target="_blank" rel="noopener">Forever hunter wiki</a>, checked against the sim, the game files and combat logs.</p>`;
  }
  $('infotitle').textContent = title;
  $('infobody').innerHTML = body;
  if ($('infomodal').hidden) {
    $('infomodal').hidden = false;
    document.body.classList.add('modal-open');
    $('infomodal').querySelector('.modal-close').focus();
  }
}

// The How to weave player, in its own modal.
function openWeave() {
  $('weavemodal').hidden = false;
  document.body.classList.add('modal-open');
  $('weavemodal').querySelector('.modal-close').focus();
  if (window.weaveViewer) window.weaveViewer.open(state.rot === 'weave-max' ? 'max' : 'normal', { tour: true });
}
function closeModals() {
  if (!$('weavemodal').hidden && window.weaveViewer) window.weaveViewer.close();
  $('weavemodal').hidden = true;
  $('infomodal').hidden = true;
  infoKind = null;
  document.body.classList.remove('modal-open');
}

// ---------- URL state: ?build=<id>&rot=<variant>&fight=<s> ----------
function toURL() {
  const p = new URLSearchParams();
  p.set('build', state.build);
  if (Array.isArray(G.rotationOf[state.build]) && state.rot && state.rot !== G.rotationOf[state.build][0]) p.set('rot', state.rot);
  if (state.fight !== 180) p.set('fight', state.fight);
  history.replaceState(null, '', `?${p}${location.hash}`);
}
function fromURL() {
  const p = new URLSearchParams(location.search);
  state.build = BUILD[p.get('build')] ? p.get('build') : 'sv-weave';
  if (G.rotations[p.get('rot')]) state.rot = p.get('rot');
  const f = +p.get('fight');
  if (FIGHTS.some(([v]) => v === f)) state.fight = f;
}

function renderAll() { renderPick(); renderTalents(); renderPlay(); renderPrep(); renderStats(); }

// ---------- Events ----------
function toast(msg) {
  const el = $('toast');
  el.textContent = msg; el.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => el.hidden = true, 1600);
}
document.addEventListener('click', e => {
  const t = e.target;
  if (t.closest('[data-open="weave"]')) { e.preventDefault(); openWeave(); return; }
  if (t.closest('.modal-close') || t.classList.contains('modal')) { closeModals(); return; }
  const m = t.closest('[data-modal]');
  if (m) { e.preventDefault(); openInfo(m.dataset.modal); return; }
  const tab = t.closest('[data-tab]');
  if (tab) { prepTab = tab.dataset.tab; openInfo('prep'); return; }
  const bd = t.closest('[data-build]');
  if (bd) {
    // Re-rendering swaps out whole sections; keep the section you're reading at the same spot on screen.
    const anchor = [...document.querySelectorAll('section.sec')].find(el => el.getBoundingClientRect().bottom > 140);
    const before = anchor && anchor.getBoundingClientRect().top;
    state.build = bd.dataset.build; state.talent = null; renderAll(); toURL();
    if (anchor && bd.closest('#bbchips')) window.scrollBy({ top: anchor.getBoundingClientRect().top - before, behavior: 'instant' });
    return;
  }
  const f = t.closest('[data-fight]');
  if (f) { state.fight = +f.dataset.fight; renderPick(); toURL(); return; }
  const r = t.closest('[data-rot]');
  if (r) { state.rot = r.dataset.rot; renderPlay(); toURL(); return; }
  const tl = t.closest('[data-tal]');
  if (tl) { selectTalent(tl.dataset.tal); return; }
  const mc = t.closest('[data-macro]');
  if (mc) {
    const m = MACROS[+mc.dataset.macro][2];
    (navigator.clipboard ? navigator.clipboard.writeText(m) : Promise.reject()).then(() => { mc.textContent = 'Copied ✓'; setTimeout(() => mc.textContent = 'Copy', 1400); }, () => prompt('Macro', m));
    return;
  }
  if (t.closest('#copy')) {
    const s = BUILD[state.build].talents;
    (navigator.clipboard ? navigator.clipboard.writeText(s) : Promise.reject()).then(() => toast('Talent string copied'), () => prompt('Talent string', s));
  }
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModals(); });

// Once the build cards scroll out of view, a slim build bar folds out under the top bar.
new IntersectionObserver(([en]) => {
  const past = !en.isIntersecting && en.boundingClientRect.top < 0;
  $('buildbar').classList.toggle('show', past);
  // Keep the selected chip in view inside the bar, without scrolling the page.
  const row = $('bbchips'), on = row.querySelector('[aria-pressed="true"]');
  if (past && on) row.scrollLeft = Math.max(0, on.offsetLeft - row.offsetLeft - 8);
}, { rootMargin: '-70px 0px 0px 0px' }).observe($('builds'));

// Highlight the step in view.
const links = [...document.querySelectorAll('.steps a[data-sec]')];
const seen = new Map();
const io = new IntersectionObserver(entries => {
  entries.forEach(en => seen.set(en.target.id, en.intersectionRatio));
  let best = null, r = 0;
  for (const [id, ratio] of seen) if (ratio > r) { r = ratio; best = id; }
  links.forEach(a => a.classList.toggle('on', a.dataset.sec === best));
}, { threshold: [0, .1, .25, .5, .75, 1] });
document.querySelectorAll('section.sec[id]').forEach(s => io.observe(s));

$('foot').innerHTML = `Simulated ${G.meta.simDate} · ${G.meta.iterations} iterations per build · WoWSims Forever <code>${G.meta.forever}</code> · <a href="#" data-modal="method">How we tested</a> · <a href="../">Pre-raid best in slot</a>`;
// Macros from the Forever hunter wiki (Hunter Macros page), the ones a raider uses every fight.
const MACROS = [
  ['Auto Shot', 'Starts Auto Shot, picking a target if you have none. Pressing it again never turns it off.', '#showtooltip\n/targetenemy [noexists][dead][help]\n/cast !Auto Shot'],
  ['Melee Attack', 'For weaving: press it once you are in melee range. Queues Raptor Strike, starts your swing and tries Mongoose Bite.', '#showtooltip\n/stopcasting\n/cast Raptor Strike\n/startattack\n/cast Mongoose Bite'],
  ['Any shot', 'Casts the shot and picks a target if you have none. Swap Serpent Sting for any other shot.', '#showtooltip\n/targetenemy [noexists][dead][help]\n/cast Serpent Sting'],
  ['Pet Attack', 'Sends the pet in under your control, so it doesn\u2019t pick its own targets.', '#showtooltip\n/targetenemy [noexists][dead][help]\n/petfollow\n/petpassive\n/petattack\n/cast Charge\n/cast Dash\n/cast Dive'],
  ['Pet Follow', 'Calls the pet back and stops it doing anything on its own.', '/petpassive\n/petfollow'],
  ['Feign Death', 'Stops whatever you are casting and feigns straight away.', '#showtooltip\n/stopcasting\n/cast Feign Death'],
];
$('macros').innerHTML = MACROS.map(([n, d, m], i) => `<div class="card macro"><div class="macro-h"><b>${esc(n)}</b><button class="btn sm" data-macro="${i}">Copy</button></div>
  <span class="small">${esc(d)}</span><pre><code>${esc(m)}</code></pre></div>`).join('');

const SIM = new Date(G.meta.simDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
$('simdate').textContent = `DPS for a fight this long · simmed ${SIM}`;
fromURL();
renderAll();

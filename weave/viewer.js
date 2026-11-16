// The How to weave viewer: a few real weave cycles from the sim (weave/data.js), looped, with the field the sim's
// Movement view draws (the boss and you, melee and dead zone rings), the bow's and the two-hander's swing timers, the
// action bar, the cycle step you are on, and what just happened and why. It stands alone: the How to weave page and
// the class guide's modal both load it with the same markup (ids wv-*).
(() => {
  const W = window.WEAVE;
  if (!W) return;
  const ICONS = {
    'Auto Shot': 'ability_whirlwind', Swing: 'inv_axe_09', "Hunter's Mark": 'ability_hunter_snipershot', 'Serpent Sting': 'ability_hunter_quickshot',
    'Arcane Shot': 'ability_impalingbolt', 'Aimed Shot': 'inv_spear_07', 'Multi-Shot': 'ability_upgrademoonglaive', 'Raptor Strike': 'ability_meleedamage',
    'Strider Kick': 'ability_hunter_pet_tallstrider', 'Mongoose Bite': 'ability_hunter_swiftstrike', 'Immolation Trap': 'spell_fire_flameshock',
    'Wing Clip': 'ability_rogue_trip', 'Rapid Fire': 'ability_hunter_runningshot', 'Walk in': 'ability_rogue_sprint', 'Walk out': 'ability_rogue_sprint',
    Racial: 'racial_orc_berserkerstrength', 'Major Frenzy Potion': 'inv_potione_6',
  };
  // The weave cycle's four steps, as the class guide's rotation section words them.
  const STEPS = {
    max: [
      { title: 'At range', text: 'Serpent Sting, Arcane Shot, Multi-Shot: whatever is ready.' },
      { title: 'Walk in', text: 'When: your Auto Shot goes off.' },
      { title: 'In melee', text: 'Raptor Strike, Strider Kick, Mongoose Bite if lit, Immolation Trap.' },
      { title: 'Walk out', text: 'When: your two-hander has swung, hit or miss.' },
    ],
    normal: [
      { title: 'At range', text: 'Aimed Shot, Serpent Sting, Arcane Shot.' },
      { title: 'Walk in', text: 'When: Aimed Shot and Arcane Shot both have more than 1.5 s left, and your Auto Shot just went off.' },
      { title: 'In melee', text: 'Stay: Raptor Strike, Strider Kick, Mongoose Bite if lit, Immolation Trap.' },
      { title: 'Walk out', text: 'When: nothing in melee comes up within 1.5 s.' },
    ],
  };
  const MELEE = 5;
  const DEAD = 11.67;
  const REACH = 15;
  const SPEEDS = [0.25, 0.5, 1, 2];
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const iconUrl = name => `https://wow.zamimg.com/images/wow/icons/medium/${ICONS[name] || 'inv_misc_questionmark'}.jpg`;

  // What each moment means, per variant.
  const WHY = {
    max: {
      fire: 'Auto Shot fired. That is your cue: walk in now.',
      walkin: 'Walk in. Your swing will restart the bow\'s timer, so the sooner it lands after the shot, the less bow time it costs.',
      walkout: 'The swing is done: walk straight back out.',
      range: 'Back past the dead zone: shoot whatever is ready while the bow\'s timer runs.',
    },
    normal: {
      fire: 'Auto Shot fired.',
      walkin: 'Aimed Shot and Arcane Shot are both cooling and the shot just went off: walk in.',
      walkout: 'No melee cooldown comes up within 1.5 s: walk out.',
      range: 'Back past the dead zone: your shots come first out here.',
    },
  };
  const CAST_WHY = {
    'Strider Kick': 'Strider Kick: a weapon hit, and 30% run speed for the walk back out.',
    'Mongoose Bite': 'Mongoose Bite: it was lit.',
    'Immolation Trap': 'Immolation Trap, at your feet in melee.',
    'Wing Clip': 'Wing Clip: nothing better to press.',
    'Arcane Shot': 'Arcane Shot: instant.',
    'Multi-Shot': 'Multi-Shot: a short cast, standing.',
    'Aimed Shot': 'Aimed Shot: a 2 s cast, and Auto Shot keeps firing through it.',
    'Serpent Sting': 'Serpent Sting: it had fallen off.',
    'Rapid Fire': 'Rapid Fire, out at range.',
  };

  const view = { v: 'normal', t: 0, playing: false, speed: 0.5, frame: 0, last: null, open: false };
  const icons = new Map();
  const icon = name => {
    if (!icons.has(name)) {
      const img = new Image();
      img.src = iconUrl(name);
      icons.set(name, img);
    }
    return icons.get(name);
  };

  // The variant's events with copies a loop before and after, so the timers read across the loop's seam.
  const prepared = {};
  function prep(key) {
    if (prepared[key]) return prepared[key];
    const D = W[key];
    const base = D.events.filter(e => e.t >= 0 && e.t < D.duration);
    const shift = d => base.map(e => ({ ...e, t: e.t + d, ...(e.ready !== undefined ? { ready: e.ready + d } : {}) }));
    const ext = [...shift(-D.duration), ...base, ...shift(D.duration)];
    const shots = ext.filter(e => e.name === 'Auto Shot');
    const swings = ext.filter(e => e.swing);
    // Walks: a walk in starts out past the dead zone, a walk out in melee. Legs from a speed change continue a walk.
    const walks = D.legs.filter(l => l.e - l.s > 0.05 && Math.abs(l.to - l.from) > 1 && (l.from > DEAD || l.from <= MELEE + 0.05));
    const notes = [];
    for (const l of walks) {
      const into = l.to < l.from;
      notes.push({ t: l.s, kind: into ? 'walkin' : 'walkout', text: WHY[key][into ? 'walkin' : 'walkout'] });
    }
    for (const l of D.legs) {
      if (l.e - l.s < 0.05) continue;
      if (l.to <= MELEE + 0.05) notes.push({ t: l.e, kind: 'melee', text: 'In melee.' });
      else if (l.to > DEAD) notes.push({ t: l.e, kind: 'range', text: WHY[key].range });
    }
    for (const e of base) {
      if (e.name === 'Auto Shot') {
        notes.push({ t: e.t, kind: 'windup', text: 'Auto Shot winding up: stand still, moving would cancel it.' });
        notes.push({ t: e.t + e.cast, kind: 'fire', text: WHY[key].fire, out: e.out });
      } else if (e.swing) {
        const waited = e.ready !== undefined && e.t - e.ready > 0.05 ? ` It was ready ${(e.t - e.ready).toFixed(1)} s before you got there.` : '';
        const what = e.name === 'Raptor Strike' ? 'Raptor Strike on your swing' : 'Two-hander swing';
        const shot = shots.filter(s => s.t + s.cast <= e.t).pop();
        const cost = shot ? ` It restarts the bow's timer: your next shot moves back ${(e.t - shot.t - shot.cast).toFixed(1)} s.` : '';
        notes.push({ t: e.t, kind: 'swing', text: `${what}: ${(e.out || 'hit').toLowerCase()}.${waited}${cost}` });
      } else if (CAST_WHY[e.name]) {
        notes.push({ t: e.t, kind: 'cast', text: CAST_WHY[e.name], out: e.out });
      }
    }
    notes.sort((a, b) => a.t - b.t);
    const lit = [-D.duration, 0, D.duration].flatMap(d => (D.mongooseLit || []).map(([s, e]) => [s + d, e + d]));
    return (prepared[key] = { D, ext, shots, swings, notes, lit });
  }

  function posAt(D, t) {
    let y = D.startYards;
    for (const l of D.legs) {
      if (l.s > t) break;
      y = t >= l.e || l.e <= l.s ? l.to : l.from + ((l.to - l.from) * (t - l.s)) / (l.e - l.s);
    }
    return y;
  }
  function step(D, t) {
    const leg = D.legs.find(l => l.s <= t && t < l.e && l.e - l.s > 0.02);
    if (leg) return leg.to < leg.from ? 1 : 3;
    return posAt(D, t) <= MELEE + 0.05 ? 2 : 0;
  }

  // The bow: from the last shot its timer runs to the next windup. A swing restarts it: the next windup then comes
  // the same time after the swing as it would have after the shot, so the swing pushes the shot back by the time
  // between the shot and the swing. Before the swing lands the bar shows the bow's own time.
  function bowTimer(P, t) {
    const windup = P.shots.find(s => s.t <= t && t < s.t + s.cast);
    if (windup) return { fill: (t - windup.t) / windup.cast, label: 'Winding up: stand still', state: 'windup' };
    const prev = P.shots.filter(s => s.t + s.cast <= t).pop();
    const lastFire = prev.t + prev.cast;
    const next = P.shots.find(s => s.t > t);
    const swing = P.swings.filter(s => s.t > lastFire && s.t < next.t).pop();
    const due = next.ready !== undefined ? next.ready : next.t;
    const reset = swing ? swing.t : lastFire;
    const interval = due - reset;
    const swung = swing && swing.t <= t;
    const target = swung ? due : lastFire + interval;
    const from = swung ? swing.t : lastFire;
    if (t >= target) return { fill: 1, label: 'Ready, held while you move', state: 'held' };
    const pushed = swung ? ` · pushed back ${(swing.t - lastFire).toFixed(1)} s by your swing` : '';
    return { fill: (t - from) / (target - from), label: `Next Auto Shot in ${(target - t).toFixed(1)} s${pushed}`, state: swung ? 'reset' : 'run' };
  }
  // The two-hander: the last swing to the next one being ready; once ready it waits for you to be in melee.
  function meleeTimer(P, t) {
    const last = Math.max(...P.swings.filter(s => s.t <= t).map(s => s.t));
    const next = P.swings.find(s => s.t > t);
    const ready = next.ready !== undefined ? Math.min(next.ready, next.t) : next.t;
    if (t - last < 0.25) return { fill: 1, label: 'Swing!', state: 'swing' };
    if (t >= ready) return { fill: 1, label: 'Ready: it swings when you reach melee', state: 'ready' };
    return { fill: (t - last) / (ready - last), label: `Swing ready in ${(ready - t).toFixed(1)} s`, state: 'run' };
  }

  // ---------- The action bar ----------
  // Cooldowns from the game's spell rows (Wowhead Forever); Arcane Shot has SV Weave's 1 point of Improved Arcane Shot.
  // Multi-Shot and Aimed Shot share theirs. Raptor Strike goes off on the swing, off the global cooldown.
  const CD = { 'Raptor Strike': 6, 'Strider Kick': 8, 'Mongoose Bite': 5, 'Immolation Trap': 30, 'Arcane Shot': 5.7, 'Multi-Shot': 6, 'Aimed Shot': 6 };
  const SHARED = { 'Multi-Shot': 'aimed', 'Aimed Shot': 'aimed' };
  const ON_GCD = new Set(['Serpent Sting', 'Arcane Shot', 'Multi-Shot', 'Aimed Shot', 'Strider Kick', 'Mongoose Bite', 'Immolation Trap', 'Wing Clip']);
  const BARS = {
    max: [['At range', ['Auto Shot', 'Serpent Sting', 'Arcane Shot', 'Multi-Shot']], ['In melee', ['Swing', 'Raptor Strike', 'Strider Kick', 'Mongoose Bite', 'Immolation Trap', 'Wing Clip']], ['Move', ['Walk in', 'Walk out']]],
    normal: [['At range', ['Auto Shot', 'Aimed Shot', 'Serpent Sting', 'Arcane Shot']], ['In melee', ['Swing', 'Raptor Strike', 'Strider Kick', 'Mongoose Bite', 'Immolation Trap', 'Wing Clip']], ['Move', ['Walk in', 'Walk out']]],
  };
  const AUTO = new Set(['Auto Shot', 'Swing']);
  function barHTML(key) {
    let n = 0;
    return BARS[key].map(([label, slots]) => `<div class="ab-group"><span class="ab-label">${label}</span><div class="ab-slots">${slots.map(name => {
      const bind = AUTO.has(name) ? 'auto' : name.startsWith('Walk') ? 'move' : String(++n);
      return `<div class="ab-slot" data-slot="${esc(name)}" title="${esc(name)}"><img src="${iconUrl(name)}" alt=""><span class="ab-cd"></span><span class="ab-num"></span><span class="ab-bind">${bind}</span><span class="ab-name">${esc(name.replace('Immolation ', '').replace('Serpent ', '').replace('Mongoose ', ''))}</span></div>`;
    }).join('')}</div></div>`).join('');
  }
  // When each slot was last pressed: a swing for Swing (Raptor Strike replaces it), the shot going off for Auto Shot.
  const pressesOf = (P, name) =>
    name === 'Swing' ? P.swings.map(e => e.t)
      : name === 'Auto Shot' ? P.shots.map(e => e.t + e.cast)
        : P.ext.filter(e => e.name === name || (SHARED[name] && SHARED[e.name] === SHARED[name])).map(e => e.t);
  function slotState(P, name, t) {
    const D = P.D;
    if (name.startsWith('Walk')) {
      const leg = D.legs.find(l => l.s <= t && t < l.e && l.e - l.s > 0.02);
      return { active: !!leg && (name === 'Walk in') === leg.to < leg.from };
    }
    const own = name === 'Swing' || name === 'Auto Shot' ? pressesOf(P, name) : P.ext.filter(e => e.name === name).map(e => e.t);
    const pressed = own.some(p => p <= t && t - p < 0.4);
    let cd = 0;
    let left = 0;
    if (CD[name]) {
      const last = pressesOf(P, name).filter(p => p <= t).pop();
      if (last !== undefined && t - last < CD[name]) { left = CD[name] - (t - last); cd = left / CD[name]; }
    }
    if (ON_GCD.has(name)) {
      const g = P.ext.filter(e => e.gcd > 0 && e.t <= t).pop();
      if (g && t - g.t < g.gcd && g.gcd - (t - g.t) > left) { left = g.gcd - (t - g.t); cd = left / g.gcd; }
    }
    const lit = name === 'Mongoose Bite' && P.lit.some(([s, e]) => s <= t && t < e);
    const active = name === 'Auto Shot' && P.shots.some(s => s.t <= t && t < s.t + s.cast);
    return { pressed, cd, left, lit, active };
  }
  function renderBar(P, t) {
    document.querySelectorAll('#wv-bar .ab-slot').forEach(el => {
      const st = slotState(P, el.dataset.slot, t);
      el.classList.toggle('pressed', !!st.pressed);
      el.classList.toggle('lit', !!st.lit);
      el.classList.toggle('active', !!st.active);
      el.classList.toggle('cooling', st.cd > 0);
      el.style.setProperty('--cd', st.cd || 0);
      el.querySelector('.ab-num').textContent = st.left > 1.5 ? Math.ceil(st.left) : '';
    });
  }

  // ---------- Drawing ----------
  const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  function sizeCanvas(c) {
    const r = c.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (c.width !== Math.round(r.width * dpr) || c.height !== Math.round(r.height * dpr)) {
      c.width = Math.round(r.width * dpr);
      c.height = Math.round(r.height * dpr);
    }
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w: r.width, h: r.height };
  }

  function drawField(P, t) {
    const { ctx, w, h } = sizeCanvas($('wv-field'));
    const em = 13;
    ctx.clearRect(0, 0, w, h);
    ctx.font = `${em}px ${css('--body')}`;
    // The boss sits high and you stand below it, so your walk in and out runs down the field; the rings run off
    // the top, which leaves the room to your path.
    const cx = w * 0.58;
    const cy = h * 0.28;
    const k = (h - cy - 3 * em) / REACH;
    // The dead zone between melee range and where the bow can fire again.
    ctx.save();
    ctx.globalAlpha = 0.16;
    ctx.fillStyle = css('--bad');
    ctx.beginPath();
    ctx.arc(cx, cy, DEAD * k, 0, 2 * Math.PI);
    ctx.arc(cx, cy, MELEE * k, 0, 2 * Math.PI, true);
    ctx.fill();
    ctx.restore();
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = css('--muted');
    ctx.lineWidth = 1.2;
    for (const r of [MELEE, DEAD]) {
      ctx.beginPath();
      ctx.arc(cx, cy, r * k, 0, 2 * Math.PI);
      ctx.stroke();
    }
    ctx.restore();
    ctx.fillStyle = css('--muted');
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';
    const side = Math.PI / 5;
    ctx.fillText('Melee 5 yd', cx + MELEE * k * Math.cos(side) + 6, cy + MELEE * k * Math.sin(side));
    ctx.fillText('Dead zone to 11.67 yd', cx + DEAD * k * Math.cos(side) + 6, cy + DEAD * k * Math.sin(side));
    // The boss.
    ctx.fillStyle = css('--bad');
    ctx.beginPath();
    ctx.arc(cx, cy, 0.9 * em, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = css('--text');
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText('Boss', cx, cy - 1.1 * em);
    // You, straight down from the boss.
    const y = posAt(P.D, t);
    const px = cx;
    const py = cy + y * k;
    ctx.save();
    ctx.globalAlpha = 0.35;
    ctx.strokeStyle = css('--muted');
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(px, py);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = css('--hunter');
    ctx.beginPath();
    ctx.arc(px, py, 0.75 * em, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = css('--text');
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(`You ${y.toFixed(1)} yd`, px + 1.2 * em, py);
    // A cast under way fills a bar under you.
    const casting = P.ext.find(e => e.cast > 0 && e.t <= t && t < e.t + e.cast);
    if (casting) {
      const bw = 7 * em;
      const top = py + 1.2 * em;
      ctx.fillStyle = css('--bg');
      ctx.fillRect(px - bw / 2, top, bw, 0.45 * em);
      ctx.fillStyle = css('--gold');
      ctx.fillRect(px - bw / 2, top, (bw * (t - casting.t)) / casting.cast, 0.45 * em);
      ctx.strokeStyle = css('--muted');
      ctx.strokeRect(px - bw / 2, top, bw, 0.45 * em);
      ctx.fillStyle = css('--text');
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(`${casting.name} ${(casting.t + casting.cast - t).toFixed(2)} s`, px, top + 0.7 * em);
    }
    // What just went off fades out to your left, the latest nearest.
    const done = P.ext.filter(e => e.t + e.cast <= t && t - (e.t + e.cast) < 1.6).sort((a, b) => b.t + b.cast - (a.t + a.cast)).slice(0, 5);
    const size = 1.9 * em;
    done.forEach((e, i) => {
      const img = icon(e.name);
      if (!img.complete || !img.naturalWidth) return;
      ctx.save();
      ctx.globalAlpha = 1 - (t - (e.t + e.cast)) / 1.6;
      ctx.drawImage(img, px - 1.2 * em - (i + 1) * (size + 4), py - size / 2, size, size);
      ctx.restore();
    });
  }

  function drawStrip(P, t) {
    const { ctx, w, h } = sizeCanvas($('wv-strip'));
    const D = P.D;
    ctx.clearRect(0, 0, w, h);
    const pad = 6;
    const x = s => (s / D.duration) * w;
    const y = yd => pad + (1 - yd / REACH) * (h - 2 * pad);
    ctx.save();
    ctx.globalAlpha = 0.16;
    ctx.fillStyle = css('--bad');
    ctx.fillRect(0, y(DEAD), w, y(MELEE) - y(DEAD));
    ctx.restore();
    ctx.save();
    ctx.setLineDash([5, 4]);
    ctx.strokeStyle = css('--muted');
    for (const yd of [MELEE, DEAD]) {
      ctx.beginPath();
      ctx.moveTo(0, y(yd));
      ctx.lineTo(w, y(yd));
      ctx.stroke();
    }
    ctx.restore();
    ctx.strokeStyle = css('--hunter');
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i <= 240; i++) {
      const s = (i / 240) * D.duration;
      const yy = y(posAt(D, s));
      if (i === 0) ctx.moveTo(x(s), yy);
      else ctx.lineTo(x(s), yy);
    }
    ctx.stroke();
    // Shots on top, swings at the bottom.
    for (const e of P.ext) {
      if (e.t < 0 || e.t >= D.duration) continue;
      if (e.name === 'Auto Shot') {
        ctx.fillStyle = '#7fb4e0';
        const fx = x(Math.min(D.duration, e.t + e.cast));
        ctx.beginPath();
        ctx.moveTo(fx - 4, 1);
        ctx.lineTo(fx + 4, 1);
        ctx.lineTo(fx, 8);
        ctx.fill();
      } else if (e.swing) {
        ctx.fillStyle = '#e0a05f';
        const sx = x(e.t);
        ctx.beginPath();
        ctx.moveTo(sx - 4, h - 1);
        ctx.lineTo(sx + 4, h - 1);
        ctx.lineTo(sx, h - 8);
        ctx.fill();
      }
    }
    ctx.fillStyle = css('--text');
    ctx.fillRect(x(t) - 1, 0, 2, h);
  }

  function render() {
    const P = prep(view.v);
    const t = view.t;
    drawField(P, t);
    drawStrip(P, t);
    renderBar(P, t);
    const bow = bowTimer(P, t);
    const melee = meleeTimer(P, t);
    $('wv-bow').style.width = `${Math.min(100, bow.fill * 100)}%`;
    $('wv-bow').dataset.state = bow.state;
    $('wv-bow-label').textContent = bow.label;
    $('wv-melee').style.width = `${Math.min(100, melee.fill * 100)}%`;
    $('wv-melee').dataset.state = melee.state;
    $('wv-melee-label').textContent = melee.label;
    const s = step(P.D, t);
    document.querySelectorAll('#wv-steps li').forEach((li, i) => li.classList.toggle('on', i === s));
    const y = posAt(P.D, t);
    $('wv-time').textContent = `${t.toFixed(2)} s / ${P.D.duration.toFixed(2)} s`;
    $('wv-zone').textContent = y <= MELEE + 0.05 ? 'In melee' : y < DEAD ? 'Dead zone: no shots' : 'At range';
    $('wv-zone').dataset.zone = y <= MELEE + 0.05 ? 'melee' : y < DEAD ? 'dead' : 'range';
    const recent = P.notes.filter(n => n.t <= t).slice(-4).reverse();
    $('wv-feed').innerHTML = recent.map((n, i) => `<li class="${n.kind}${i === 0 ? ' now' : ''}"><span>${n.t.toFixed(2)} s</span>${esc(n.text)}${n.out && n.kind !== 'cast' ? ` <em>${esc(n.out)}</em>` : ''}</li>`).join('');
  }

  // ---------- Step by step: the first cycle, stopping at every action ----------
  // The tour runs from the start to the first time you are back at range after a trip into melee, and stops at each
  // moment something happens; the notes of one moment make one stop.
  const TITLE = { intro: 'You start at range', swing: 'Swing', fire: 'Auto Shot fired', walkin: 'Walk in', walkout: 'Walk out', windup: 'Auto Shot winds up', melee: 'In melee', range: 'Back at range' };
  const RANK = ['intro', 'swing', 'fire', 'walkin', 'walkout', 'windup', 'cast', 'melee', 'range'];
  const INTRO = {
    max: 'You stand at about 13 yd, just past the dead zone, shooting. The two bars on the right are your bow\'s Auto Shot timer and your two-hander\'s swing timer. Max weave fits one two-hander swing in after every shot. Watch when you walk in and when you walk out.',
    normal: 'You stand at about 13 yd, just past the dead zone, shooting. The two bars on the right are your bow\'s Auto Shot timer and your two-hander\'s swing timer. Normal weave shoots first and only walks in to spend the melee cooldowns while the shots are cooling.',
  };
  const tour = { on: false, stops: [], i: 0, waiting: false };
  function buildTour(P) {
    const out = P.D.legs.find(l => l.e - l.s > 0.05 && l.to > l.from && l.from <= MELEE + 0.05);
    const end = out ? out.e + 0.05 : P.D.duration;
    const stops = [{ t: 0, notes: [{ t: 0, kind: 'intro', text: INTRO[view.v] }] }];
    for (const n of P.notes.filter(n => n.t > 0.02 && n.t <= end)) {
      const last = stops[stops.length - 1];
      if (last && n.t - last.t < 0.06) last.notes.push(n);
      else stops.push({ t: n.t, notes: [n] });
    }
    return stops;
  }
  function showStop() {
    const s = tour.stops[tour.i];
    const main = [...s.notes].sort((a, b) => RANK.indexOf(a.kind) - RANK.indexOf(b.kind))[0];
    const title = main.kind === 'cast' ? main.text.split(':')[0] : TITLE[main.kind];
    $('wv-pop-step').textContent = `Step ${tour.i + 1} of ${tour.stops.length} · ${s.t.toFixed(2)} s`;
    $('wv-pop-title').textContent = title;
    $('wv-pop-text').innerHTML = s.notes.map(n => `<p>${esc(n.text)}${n.out && n.kind !== 'cast' ? ` <em>${esc(n.out)}</em>` : ''}</p>`).join('');
    $('wv-pop-next').textContent = 'Continue ▶';
    $('wv-pop').hidden = false;
  }
  function showTourEnd() {
    $('wv-pop-step').textContent = 'End of the tour';
    $('wv-pop-title').textContent = 'That was one full cycle';
    $('wv-pop-text').innerHTML = `<p>Shoot, walk in, swing, walk out, and back to shooting. From here it loops on its own: watch the two timers and the action bar. Press <b>Step by step</b> to go through it again.</p>`;
    $('wv-pop-next').textContent = 'Start the loop ▶';
    $('wv-pop').hidden = false;
  }
  function startTour() {
    tour.on = true;
    tour.stops = buildTour(prep(view.v));
    tour.i = 0;
    tour.waiting = false;
    view.t = 0;
    $('wv-pop').hidden = true;
    $('wv-tour').setAttribute('aria-pressed', 'true');
    setPlaying(true);
  }
  function endTour() {
    tour.on = false;
    tour.waiting = false;
    $('wv-pop').hidden = true;
    $('wv-tour').setAttribute('aria-pressed', 'false');
    try { localStorage.setItem('weaveTourDone', '1'); } catch (e) { /* private mode */ }
  }
  function continueTour() {
    if (!tour.on) return;
    if (tour.i >= tour.stops.length) { endTour(); setPlaying(true); return; }
    tour.waiting = false;
    tour.i++;
    $('wv-pop').hidden = true;
    setPlaying(true);
  }

  function loop(now) {
    if (!view.open) return;
    if (view.playing) {
      if (view.last !== null) {
        const D = W[view.v];
        const next = view.t + ((now - view.last) / 1000) * view.speed;
        if (tour.on && !tour.waiting) {
          const stop = tour.stops[tour.i];
          if (!stop) {
            tour.waiting = true;
            setPlaying(false);
            showTourEnd();
          } else if (next >= stop.t) {
            view.t = stop.t + 0.001;
            tour.waiting = true;
            setPlaying(false);
            showStop();
          } else view.t = next;
        } else if (!tour.on) view.t = next % D.duration;
      }
      view.last = now;
    }
    render();
    view.frame = requestAnimationFrame(loop);
  }

  // ---------- Controls ----------
  const stepsHTML = key => STEPS[key].map(c => `<li><b>${esc(c.title)}</b><small>${esc(c.text)}</small></li>`).join('');
  function setVariant(key) {
    view.v = key;
    view.t = 0;
    $('wv-steps').innerHTML = stepsHTML(key);
    $('wv-bar').innerHTML = barHTML(key);
    document.querySelectorAll('[data-wv]').forEach(b => b.setAttribute('aria-pressed', b.dataset.wv === key));
    const D = W[key];
    $('wv-source').textContent = `${key === 'max' ? 'Max weave' : 'Normal weave'}: ${D.duration.toFixed(1)} s of a real sim fight (seconds ${D.window[0].toFixed(1)} to ${D.window[1].toFixed(1)}), looped.`;
  }
  function setPlaying(on) {
    view.playing = on;
    view.last = null;
    $('wv-play').textContent = on ? '❚❚ Pause' : '▶ Play';
  }

  $('wv-speeds').innerHTML = SPEEDS.map(s => `<button data-speed="${s}" aria-pressed="${s === view.speed}">${s}×</button>`).join('');
  document.addEventListener('click', e => {
    const v = e.target.closest('[data-wv]');
    if (v) {
      setVariant(v.dataset.wv);
      if (tour.on) startTour();
      return;
    }
    const sp = e.target.closest('[data-speed]');
    if (sp) {
      view.speed = +sp.dataset.speed;
      document.querySelectorAll('[data-speed]').forEach(b => b.setAttribute('aria-pressed', +b.dataset.speed === view.speed));
      return;
    }
    if (e.target.closest('#wv-play')) {
      if (tour.on && tour.waiting) continueTour();
      else setPlaying(!view.playing);
    }
    if (e.target.closest('#wv-pop-next')) continueTour();
    if (e.target.closest('#wv-pop-skip')) { endTour(); setPlaying(true); }
    if (e.target.closest('#wv-tour')) {
      if (tour.on) { endTour(); setPlaying(true); } else startTour();
    }
  });
  document.addEventListener('keydown', e => {
    if (!view.open || $('wv-pop').hidden || (e.key !== 'Enter' && e.key !== ' ')) return;
    if (e.target.closest && e.target.closest('button')) return; // the button's own click handles it
    e.preventDefault();
    continueTour();
  });
  const strip = $('wv-strip');
  const scrub = e => {
    if (tour.on) endTour();
    const r = strip.getBoundingClientRect();
    view.t = Math.max(0, Math.min(0.999, (e.clientX - r.left) / r.width)) * W[view.v].duration;
  };
  strip.addEventListener('pointerdown', e => { strip.setPointerCapture(e.pointerId); scrub(e); });
  strip.addEventListener('pointermove', e => { if (strip.hasPointerCapture(e.pointerId)) scrub(e); });

  // The page or the modal opens and closes the viewer; it only draws while open.
  window.weaveViewer = {
    open(key) {
      view.open = true;
      setVariant(key || view.v);
      // The first time, the tour stops at every action; after that it opens straight on the loop.
      let done = false;
      try { done = localStorage.getItem('weaveTourDone') === '1'; } catch (e) { /* private mode */ }
      if (done) { tour.on = false; $('wv-pop').hidden = true; $('wv-tour').setAttribute('aria-pressed', 'false'); setPlaying(true); } else startTour();
      cancelAnimationFrame(view.frame);
      view.frame = requestAnimationFrame(loop);
    },
    close() {
      view.open = false;
      setPlaying(false);
      cancelAnimationFrame(view.frame);
    },
  };
  setVariant('normal');
})();

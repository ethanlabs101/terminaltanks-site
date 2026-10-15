'use strict';
/* The logic behind the web Workshop, kept free of the page so it can be tested on its own. */
const Workshop = (() => {
  const SLOTS = ['turret', 'hull', 'track', 'barrel', 'glow', 'ambient', 'accent'];
  const LABEL = { turret: 'Turret', hull: 'Hull', track: 'Tracks', barrel: 'Barrel', glow: 'Glow', ambient: 'Ambient', accent: 'Accent' };
  const source = (p) => (p.h === 'Shop' ? 'Shop, ' + p.c : p.h);
  const part = (P, slot, id) => P[slot].find((p) => p.id === id);

  function how(p) {
    if (p.free) return 'Free from the start';
    if (!p.providers.length) return 'Cheat only. No tank unlocks it.';
    const first = p.providers[0], extra = p.providers.length - 1 + p.more;
    return 'Own ' + first.n + ' (' + source(first) + ')' + (extra > 0 ? (extra === 1 ? ', or 1 other tank that uses it' : ', or any of ' + extra + ' other tanks that use it') : '');
  }

  function rows(P, sel) {
    return SLOTS.map((slot) => { const p = part(P, slot, sel[slot]) || { id: sel[slot], n: String(sel[slot]).toUpperCase(), free: true, providers: [], more: 0, tag: 'Free' };
      return { slot, label: LABEL[slot], id: p.id, name: p.n, tag: p.tag, free: !!p.free, premium: !!p.premium, how: how(p), providers: p.providers, more: p.more }; });
  }

  /* A short list of tanks to own that unlocks every non-free part in the build. */
  function needs(rowsList) {
    const open = rowsList.filter((r) => !r.free && r.providers.length).sort((a, b) => a.providers.length - b.providers.length), chosen = [];
    for (const r of open) {
      const hit = chosen.find((c) => r.providers.some((p) => p.k === c.k));
      if (hit) hit.covers.push(r.label); else chosen.push(Object.assign({}, r.providers[0], { covers: [r.label] }));
    }
    return chosen;
  }

  function text(R, P, sel, name, lore) {
    const rs = rows(P, sel), nd = needs(rs), L = [];
    L.push('# ' + (name || 'UNNAMED TANK'), '');
    if (lore) L.push('> ' + lore, '');
    L.push('| Slot | Part | How you get it |', '| --- | --- | --- |');
    rs.forEach((r) => L.push('| ' + r.label + ' | ' + r.name + (r.premium ? ' (premium)' : '') + ' | ' + r.how + ' |'));
    L.push('');
    if (nd.length) { L.push('## Tanks to own to unlock every part', ''); nd.forEach((n) => L.push('- ' + n.n + ' (' + source(n) + ') unlocks: ' + n.covers.join(', '))); L.push(''); }
    else L.push('Every part in this build is free from the start.', '');
    L.push('Saving a design in the game costs ' + R.fee.toLocaleString('en-US') + ' coins and uses one of ' + R.slots + ' slots.');
    return L.join('\n');
  }

  function json(R, P, sel, name, lore) {
    const id = Math.random().toString(36).slice(2, 10), rs = rows(P, sel);
    return { format: 1, tool: 'TerminalTanks web Workshop', record: { id, name, lore, fmt: R.fmt, parts: Object.assign({}, sel) },
      sheet: rs.map((r) => ({ slot: r.slot, part: r.id, name: r.name, free: r.free, premium: r.premium, how: r.how })), needs: needs(rs).map((n) => ({ tank: n.k, name: n.n, source: source(n), unlocks: n.covers })) };
  }

  const encode = (state) => btoa(unescape(encodeURIComponent(JSON.stringify(state)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  function decode(s) { try { return JSON.parse(decodeURIComponent(escape(atob(s.replace(/-/g, '+').replace(/_/g, '/'))))); } catch (e) { return null; } }

  /* Keep only ids that exist, falling back to the default part, the way the game treats a missing component. */
  function clean(R, P, sel) { const out = {}; SLOTS.forEach((s) => { out[s] = part(P, s, sel && sel[s]) ? sel[s] : R.fallback[s]; }); return out; }
  function random(P, free) { const out = {}; SLOTS.forEach((s) => { const pool = P[s].filter((p) => !free || p.free); out[s] = pool[Math.floor(Math.random() * pool.length)].id; }); return out; }
  return { SLOTS, LABEL, rows, needs, text, json, encode, decode, clean, random, how, source, part };
})();
if (typeof module !== 'undefined') module.exports = Workshop;

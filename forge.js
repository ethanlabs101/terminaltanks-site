'use strict';
/* The Save Forge's file handling, kept free of the page so it can be tested on its own (tools/tests/forge_roundtrip.py).
   It mirrors terminaltanks.py's SaveData (format version 5): what the game reads, what it ignores, and what it rewrites.

   Inputs it understands
     - a plain save.json from the downloaded game (or any profile file, save_profileN.json)
     - a browser backup: {"app": "TerminalTanks", "format": 1, "files": [{"path", "b64"}]} as play.html exports it, which can
       hold several profiles (profiles.json + save.json + save_profileN.json) and other files; all of them are kept
   Nothing it does not edit is dropped: unknown fields, custom tanks, settings, story progress and playtime pass through. */
const Forge = (() => {
  const SAVE_RE = /(^|\/)(save(_profile\d+)?\.json)$/;
  const SAFE_PATH = /^(?!\/)(?!.*(^|\/)\.\.(\/|$))[\w .@+\-\/]{1,200}$/;          // the same rule play.html enforces on import
  const MAX_BYTES = 5 * 1048576;

  /* ---- UTF-8 safe base64 (btoa/atob only handle Latin-1) ----------------------------------------------------------- */
  const b64ToBytes = (b) => { const s = atob(b), u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u; };
  const bytesToB64 = (u) => { let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
  const utf8 = { dec: (u) => new TextDecoder('utf-8').decode(u), enc: (s) => new TextEncoder().encode(s) };

  class ForgeError extends Error {}
  const fail = (m) => { throw new ForgeError(m); };

  /* What a save document says about itself; also catches anything that would make the game start fresh. */
  function checkDoc(d, where, maxVersion) {
    if (!d || typeof d !== 'object' || Array.isArray(d)) fail(where + ' is not a TerminalTanks save (expected a JSON object)');
    const v = d.version === undefined ? 1 : d.version;
    if (!Number.isInteger(v) || v < 1) fail(where + ' has an invalid version field');
    const warn = [];
    if (v > maxVersion) warn.push('This save is format ' + v + ', newer than this forge knows (' + maxVersion + '). Fields it does not know are kept, but check the result in the game.');
    for (const k of ['granted', 'tournament_completed', 'missions_completed', 'missions_paid', 'custom_tanks', 'loadouts', 'story']) {
      if (d[k] !== undefined && !Array.isArray(d[k])) warn.push('"' + k + '" is not a list, so the game ignores it.');
    }
    for (const k of ['wallet', 'settings', 'tickets', 'martyr']) {
      if (d[k] !== undefined && (typeof d[k] !== 'object' || Array.isArray(d[k]) || d[k] === null)) warn.push('"' + k + '" is not an object, so the game ignores it.');
    }
    return { version: v, warnings: warn };
  }

  /* Reads a file's text. Returns { kind: 'plain' | 'bundle', bundle, saves: [{path, name, doc, raw}], active, other } */
  function parse(text, opts = {}) {
    const maxVersion = opts.maxVersion || 5;
    if (typeof text !== 'string') fail('could not read the file');
    if (text.length > MAX_BYTES) fail('the file is too large to be a save (over 5 MB)');
    let j;
    try { j = JSON.parse(text.replace(/^﻿/, '')); } catch (e) { fail('the file is not valid JSON (' + e.message + ')'); }
    if (j && typeof j === 'object' && Array.isArray(j.files)) {
      if (j.app !== 'TerminalTanks') fail('this is a backup from a different app, not TerminalTanks');
      if (j.format !== undefined && j.format !== 1) fail('this backup uses format ' + j.format + ', which this forge does not know');
      for (const f of j.files) {
        if (!f || typeof f.path !== 'string' || typeof f.b64 !== 'string') fail('the backup has a damaged file entry');
        if (!SAFE_PATH.test(f.path)) fail('the backup contains an unsafe file path: ' + f.path);
      }
      let profiles = null;
      const pf = j.files.find((f) => /(^|\/)profiles\.json$/.test(f.path));
      if (pf) { try { profiles = JSON.parse(utf8.dec(b64ToBytes(pf.b64))); } catch (e) { profiles = null; } }
      const saves = [];
      for (const f of j.files) {
        if (!SAVE_RE.test(f.path)) continue;
        let raw, doc;
        try { raw = utf8.dec(b64ToBytes(f.b64)); doc = JSON.parse(raw); } catch (e) { fail(f.path + ' inside the backup is not readable JSON'); }
        const info = checkDoc(doc, f.path, maxVersion);
        const file = f.path.split('/').pop(), p = profiles && Array.isArray(profiles.profiles) ? profiles.profiles.find((q) => q && q.file === file) : null;
        saves.push({ path: f.path, name: p ? String(p.name || 'PROFILE ' + p.id) : file === 'save.json' ? 'PROFILE 1' : file, id: p ? p.id : '', doc, raw, info });
      }
      if (!saves.length) fail('this backup has no save file yet. Play a match in the browser game first, then export again');
      const order = (s) => (s.id ? +s.id || 99 : s.path.endsWith('/save.json') || s.path === 'save.json' ? 0 : 50);   /* profile 1 first, as in the game */
      saves.sort((a, b) => order(a) - order(b) || (a.path < b.path ? -1 : 1));
      const activeId = profiles && profiles.active;
      const active = Math.max(0, saves.findIndex((s) => s.id && s.id === activeId));
      return { kind: 'bundle', bundle: j, saves, active, profiles };
    }
    const info = checkDoc(j, 'The file', maxVersion);
    if (!(Array.isArray(j.granted) || Array.isArray(j.tournament_completed) || j.wallet || j.loadouts)) fail('this JSON does not look like a TerminalTanks save.json');
    return { kind: 'plain', bundle: null, saves: [{ path: '.config/terminaltanks/save.json', name: 'save.json', doc: j, raw: text, info }], active: 0, profiles: null };
  }

  /* The game's own chain rule: a level (or mission) only counts as cleared if the one before it was cleared or it was opened. */
  function chain(done, granted, prefix, total) {
    const ok = new Set();
    for (let n = 1; n <= total; n++) if (done.includes(n) && (n === 1 || ok.has(n - 1) || granted.includes(prefix + n))) ok.add(n);
    return [...ok];
  }

  /* Builds the edited document. `form` carries only what the page edits; everything else comes from `old` untouched. */
  function build(old, form, T) {
    const doc = old ? JSON.parse(JSON.stringify(old)) : {};
    const range = (n) => Array.from({ length: n }, (_, i) => i + 1);
    const known = new Set(form.known);
    const keep = (Array.isArray(doc.granted) ? doc.granted : []).filter((u) => typeof u === 'string' && !known.has(u));   /* ids the form has no chip for */
    doc.version = Math.max(T.saveVersion, Number.isInteger(doc.version) ? doc.version : 1);
    const knownT = new Set(Object.keys(T.ticketUids));
    const oldWon = doc.tickets && Array.isArray(doc.tickets.won) ? doc.tickets.won.filter((k) => typeof k === 'string' && !knownT.has(k)) : [];
    const won = [...new Set([...form.ticketsWon, ...oldWon])].sort();
    const wasWon = new Set(doc.tickets && Array.isArray(doc.tickets.won) ? doc.tickets.won : []);
    const bossUids = new Set(); won.filter((k) => !wasWon.has(k)).forEach((k) => (T.ticketUids[k] || []).forEach((u) => bossUids.add(u)));   /* a newly beaten boss hands over its kit, as in the game */
    doc.granted = [...new Set([...form.granted, ...bossUids, ...keep])].filter((u) => u !== T.blessing).sort();
    doc.tournament_completed = form.levels === null ? (Array.isArray(doc.tournament_completed) ? doc.tournament_completed : []) : range(form.levels);
    doc.missions_completed = form.missions === null ? (Array.isArray(doc.missions_completed) ? doc.missions_completed : []) : range(form.missions);
    const paid = new Set((Array.isArray(doc.missions_paid) ? doc.missions_paid : []).filter(Number.isInteger));
    doc.missions_completed.forEach((n) => paid.add(n));
    doc.missions_paid = [...paid].filter((n) => n >= 1 && n <= T.missions).sort((a, b) => a - b);
    const tk = doc.tickets && typeof doc.tickets === 'object' && !Array.isArray(doc.tickets) ? doc.tickets : {};
    const active = typeof tk.active === 'string' && !won.includes(tk.active) ? tk.active : '';
    doc.tickets = Object.assign({}, tk, { won, active });
    const mt = doc.martyr && typeof doc.martyr === 'object' && !Array.isArray(doc.martyr) ? doc.martyr : {};
    const M = form.martyr;
    doc.martyr = Object.assign({}, mt, { paid: !!(M.paid || M.won), phase: M.won ? 3 : Math.max(0, Math.min(3, M.phase | 0)), won: !!M.won, seen: !!(M.seen || M.won || M.phase > 0), open: !!(M.open || M.paid || M.won) });
    if (M.won) T.martyrRewards.forEach((u) => { if (!doc.granted.includes(u) && u !== T.blessing) doc.granted.push(u); });
    doc.granted.sort();
    doc.wallet = Object.assign({}, doc.wallet && typeof doc.wallet === 'object' ? doc.wallet : {}, { coins: form.coins, credits: form.credits });
    const defaults = [['ranger', 'CYAN', 'standard', 'YELLOW'], ['ranger', 'ORANGE', 'standard', 'MAGENTA']];
    const oldLo = Array.isArray(doc.loadouts) ? doc.loadouts : [];
    doc.loadouts = [0, 1].map((i) => Object.assign({ tank: defaults[i][0], tank_color: defaults[i][1], ammo: defaults[i][2], shot_color: defaults[i][3] },
      oldLo[i] && typeof oldLo[i] === 'object' ? oldLo[i] : {}, form.loadouts[i] || {}));
    for (const k of ['custom_tanks', 'story']) if (!Array.isArray(doc[k])) doc[k] = [];
    if (!doc.settings || typeof doc.settings !== 'object' || Array.isArray(doc.settings)) doc.settings = {};
    if (typeof doc.playtime !== 'number') doc.playtime = 0;
    delete doc.unlocked;                      /* a summary the game rewrites from the fields above on its next save */
    return doc;
  }

  /* What the game will make of a document: the same reading rules as SaveData.load, summarised for the page. */
  function inspect(doc, T) {
    const g = Array.isArray(doc.granted) ? doc.granted.filter((u) => typeof u === 'string') : [];
    const known = new Set(T.unlockables), unknown = g.filter((u) => !known.has(u));
    const lv = chain((doc.tournament_completed || []).filter(Number.isInteger), g, 'level:', T.levels);
    const ms = chain((doc.missions_completed || []).filter(Number.isInteger), g, 'mission:', T.missions);
    const w = doc.wallet || {}, mt = doc.martyr || {};
    const warnings = [];
    if (unknown.length) warnings.push(unknown.length + ' unlock id' + (unknown.length === 1 ? '' : 's') + ' the game does not know (' + unknown.slice(0, 4).join(', ') + (unknown.length > 4 ? ', ...' : '') + '): the game drops them when it loads.');
    if (lv.length < (doc.tournament_completed || []).length) warnings.push('Some cleared levels are not reachable (the level before them is not cleared), so the game will not count them.');
    if (ms.length < (doc.missions_completed || []).length) warnings.push('Some cleared missions are not reachable, so the game will not count them.');
    if (g.includes(T.blessing)) warnings.push("Martyr's Blessing is in the granted list, but the game ignores that: only defeating the Martyr unlocks it.");
    const ct = Array.isArray(doc.custom_tanks) ? doc.custom_tanks : [];
    const ids = ct.map((r) => r && r.id), dupes = ids.filter((x, i) => ids.indexOf(x) !== i);
    if (dupes.length) warnings.push('Custom tanks with duplicate ids: the game keeps only the first of each.');
    if (ct.some((r) => !r || typeof r.id !== 'string')) warnings.push('A custom tank has no id: the game skips it.');
    return { version: doc.version, unlocks: g.filter((u) => known.has(u)).length, unknown: unknown.length, levels: lv.length, missions: ms.length,
      coins: Number.isInteger(w.coins) ? w.coins : 0, credits: Number.isInteger(w.credits) ? w.credits : 0, custom: ct.length,
      tickets: ((doc.tickets || {}).won || []).length, martyr: mt.won ? 'defeated' : mt.paid ? 'Time Machine bought' : mt.open ? 'Time Machine open' : 'not met',
      playtime: typeof doc.playtime === 'number' ? doc.playtime : 0, story: (doc.story || []).length, settings: Object.keys(doc.settings || {}).length, warnings };
  }

  const pretty = (doc) => JSON.stringify(doc, null, 2);

  /* A new browser backup: the edited save replaces its own file, every other file in the original backup is kept. */
  function bundle(parsed, index, doc, now) {
    const target = parsed.saves[index].path;
    const files = parsed.bundle ? parsed.bundle.files.filter((f) => f.path !== target) : [];
    files.push({ path: target, b64: bytesToB64(utf8.enc(pretty(doc))) });
    files.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
    return Object.assign({}, parsed.bundle || {}, { app: 'TerminalTanks', format: 1, exported: now || new Date().toISOString(), files });
  }

  return { parse, build, inspect, bundle, pretty, chain, ForgeError, b64ToBytes, bytesToB64, utf8, SAFE_PATH };
})();
if (typeof module !== 'undefined') module.exports = Forge;

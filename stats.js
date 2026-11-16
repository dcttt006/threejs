// =====================================================
// PITCH ROYALE — statistics page (stats.html)
// Logs the owner in at Supabase, reads the rows game.stats.js wrote
// (only that login may, see stats.sql) and turns them into numbers,
// a daily chart, bars and tables. Everything is worked out here in
// the browser; nothing is changed in the database.
// =====================================================
(() => {
    const cfg = typeof STATS_CONFIG !== 'undefined' ? STATS_CONFIG : {};
    const base = (cfg.url || '').replace(/\/$/, '');
    const $ = (id) => document.getElementById(id);

    const TOKEN_KEY = 'prStats.token';
    const PERIOD_KEY = 'prStats.days';
    const OWNER_KEY = 'pitchRoyale.owner';
    const VISITOR_KEY = 'pitchRoyale.visitor';

    const store = (area) => ({
        get(k) { try { return window[area].getItem(k); } catch (_) { return null; } },
        set(k, v) { try { window[area].setItem(k, v); } catch (_) { /* private mode */ } },
        del(k) { try { window[area].removeItem(k); } catch (_) { /* private mode */ } },
    });
    const local = store('localStorage');
    const session = store('sessionStorage');

    const ROUND = { group: 'Groepsfase', r32: 'Laatste 32', r16: 'Achtste finale', qf: 'Kwartfinale', sf: 'Halve finale', bronze: 'Troostfinale', final: 'Finale' };
    const OUT = {
        champion: 'Wereldkampioen', runnerup: 'Verloren in de finale', third: 'Derde van de wereld', fourth: 'Vierde',
        group: 'Uit in de groep', r32: 'Uit in de laatste 32', r16: 'Uit in de achtste finale', qf: 'Uit in de kwartfinale',
        sf: 'Uit in de halve finale',
    };
    const LEVEL = { easy: 'Makkelijk', medium: 'Gemiddeld', hard: 'Moeilijk' };
    const MODE = { cpu: 'Tegen de computer', duo: '2 spelers' };

    // ---------- small helpers ----------
    function el(tag, cls, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined && text !== null) e.textContent = String(text);
        return e;
    }
    const pad = (n) => String(n).padStart(2, '0');
    const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    function fmtSecs(s) {
        if (s === null || s === undefined || !isFinite(s)) return '–';
        s = Math.round(s);
        if (s < 60) return `${s} s`;
        const m = Math.floor(s / 60), r = s % 60;
        if (m < 60) return `${m}:${pad(r)}`;
        return `${Math.floor(m / 60)} u ${m % 60} min`;
    }
    const fmtWhen = (iso) => new Date(iso).toLocaleString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    const fmtDay = (d) => d.toLocaleDateString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short' });
    const fmtInt = (n) => Number(n || 0).toLocaleString('nl-NL');
    const median = (a) => {
        if (!a.length) return null;
        const s = [...a].sort((x, y) => x - y), h = Math.floor(s.length / 2);
        return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
    };
    function count(list, key) {
        const m = new Map();
        list.forEach(x => { const k = key(x) || 'onbekend'; m.set(k, (m.get(k) || 0) + 1); });
        return [...m.entries()].sort((a, b) => b[1] - a[1]);
    }
    // a match from player 1's side: won, drawn or lost (penalties count)
    function outcome(d) {
        const p = d.wk && d.wk.pens;
        if (d.s1 > d.s2 || (p && p[0] > p[1])) return 'W';
        if (d.s1 < d.s2 || (p && p[0] < p[1])) return 'V';
        return 'G';
    }

    // ---------- talking to Supabase ----------
    function token() {
        try {
            const t = JSON.parse(session.get(TOKEN_KEY));
            return t && t.until > Date.now() + 30000 ? t : null;
        } catch (_) { return null; }
    }
    async function login(email, password) {
        const r = await fetch(`${base}/auth/v1/token?grant_type=password`, {
            method: 'POST',
            headers: { apikey: cfg.key, 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) {
            const msg = j.error_description || j.msg || j.message || '';
            throw new Error(/invalid/i.test(msg) ? 'E-mail of wachtwoord klopt niet.' : (msg || 'Inloggen lukte niet.'));
        }
        session.set(TOKEN_KEY, JSON.stringify({
            token: j.access_token,
            until: Date.now() + (j.expires_in || 3600) * 1000,
            email: (j.user && j.user.email) || email,
        }));
        local.set(OWNER_KEY, '1');           // from now on this device is not counted
    }
    async function fetchEvents(days) {
        const t = token();
        if (!t) throw Object.assign(new Error('Log opnieuw in.'), { login: true });
        const rows = [];
        const page = 1000;
        const since = days ? new Date(Date.now() - days * 86400000).toISOString() : null;
        for (let offset = 0; offset < 500000; offset += page) {
            let q = `${base}/rest/v1/events?select=*&order=created_at.asc&limit=${page}&offset=${offset}`;
            if (since) q += `&created_at=gte.${encodeURIComponent(since)}`;
            const r = await fetch(q, { headers: { apikey: cfg.key, Authorization: `Bearer ${t.token}` } });
            if (r.status === 401) {
                session.del(TOKEN_KEY);
                throw Object.assign(new Error('Je sessie is verlopen, log opnieuw in.'), { login: true });
            }
            if (!r.ok) throw new Error(`De gegevens laden lukte niet (fout ${r.status}).`);
            const part = await r.json();
            rows.push(...part);
            if (part.length < page) break;
        }
        return rows;
    }

    // ---------- from rows to a picture ----------
    function build(allRows, days) {
        const me = local.get(VISITOR_KEY);
        const rows = allRows.filter(r => r.visitor !== me);       // never this device
        const sessions = new Map();
        rows.forEach(r => {
            let s = sessions.get(r.session);
            if (!s) {
                s = {
                    id: r.session, visitor: r.visitor, start: r.created_at, end: r.created_at,
                    device: r.device, os: r.os, browser: r.browser, screen: r.screen, lang: r.lang,
                    referrer: '', secs: null, matches: 0, names: new Set(), model: '', osv: '',
                };
                sessions.set(r.session, s);
            }
            s.end = r.created_at;
            if (r.referrer && !s.referrer) s.referrer = r.referrer;
            const d = r.data || {};
            if (r.type === 'time') s.secs = Math.max(s.secs || 0, d.secs || 0);
            if (r.type === 'visit' && d.model) { s.model = d.model; s.osv = d.osVersion || ''; }
            if (r.type === 'match') {
                s.matches++;
                if (d.wk) s.names.add(d.wk.teamName || d.wk.team);
                else {
                    if (d.p1) s.names.add(d.p1);
                    if (d.mode === 'duo' && d.p2) s.names.add(d.p2);
                }
            }
        });
        const list = [...sessions.values()].sort((a, b) => a.start < b.start ? 1 : -1);
        const matches = rows.filter(r => r.type === 'match');
        const normal = matches.filter(r => !(r.data || {}).wk);
        const wkMatches = matches.filter(r => (r.data || {}).wk);
        const wkStarts = rows.filter(r => r.type === 'wk_start');
        const known = list.map(s => s.secs).filter(x => x !== null && x > 0);

        // visits per day, oldest first
        const today = new Date(); today.setHours(0, 0, 0, 0);
        let first = new Date(today);
        if (days) first.setDate(first.getDate() - (days - 1));
        else if (list.length) { first = new Date(list[list.length - 1].start); first.setHours(0, 0, 0, 0); }
        const span = Math.min(366, Math.round((today - first) / 86400000) + 1);
        const perDay = [];
        for (let i = 0; i < span; i++) {
            const d = new Date(first); d.setDate(first.getDate() + i);
            perDay.push({ day: d, key: dayKey(d), n: 0 });
        }
        const byKey = new Map(perDay.map(p => [p.key, p]));
        list.forEach(s => { const p = byKey.get(dayKey(new Date(s.start))); if (p) p.n++; });

        // names typed in (not the computer, not WK countries)
        const names = new Map();
        normal.forEach(r => {
            const d = r.data;
            const add = (n) => {
                const k = String(n || '').trim().toLowerCase();
                if (!k || k === 'computer') return;
                const e = names.get(k) || { name: String(n).trim(), n: 0, last: r.created_at, devices: new Set() };
                e.n++; e.last = r.created_at; e.devices.add(r.device);
                names.set(k, e);
            };
            add(d.p1);
            if (d.mode === 'duo') add(d.p2);
        });

        // WK tournaments: each start, with that visitor's matches for that country until the next start
        const tournaments = wkStarts.map((st, i) => {
            const next = wkStarts.slice(i + 1).find(x => x.visitor === st.visitor);
            const ms = wkMatches.filter(m => m.visitor === st.visitor
                && m.created_at >= st.created_at && (!next || m.created_at < next.created_at)
                && m.data.wk.team === st.data.team);
            const done = ms.filter(m => m.data.finished);
            const tally = { W: 0, G: 0, V: 0 };
            done.forEach(m => tally[outcome(m.data)]++);
            const last = done[done.length - 1];
            let status = 'Nog niet gespeeld', tag = '';
            if (last && last.data.wk.out) { status = OUT[last.data.wk.out] || last.data.wk.out; tag = last.data.wk.out === 'champion' ? 'gold' : 'bad'; }
            else if (last) status = `Loopt nog: ${ROUND[last.data.wk.next] || last.data.wk.next}`;
            const s = sessions.get(st.session);
            return {
                when: st.created_at, device: s ? s.device : '', team: st.data.teamName || st.data.team,
                level: LEVEL[st.data.level] || st.data.level, played: done.length, quit: ms.length - done.length,
                tally, status, tag,
            };
        }).reverse();

        return { rows, list, matches, normal, wkMatches, wkStarts, known, perDay, names, tournaments };
    }

    // ---------- drawing ----------
    function kpi(label, value, sub, gold) {
        const k = el('div', 'st-kpi' + (gold ? ' st-kpi--gold' : ''));
        k.append(el('span', 'st-kpi__value', value), el('span', 'st-kpi__label', label));
        if (sub) k.appendChild(el('span', 'st-kpi__sub', sub));
        return k;
    }
    function card(title) {
        const c = el('section', 'st-card');
        if (title) c.appendChild(el('h2', '', title));
        return c;
    }
    // one bar per row, longest first; the rest folds into "overig"
    function bars(entries, max = 8) {
        if (!entries.length) return el('p', 'st-empty', 'Nog niets.');
        let rows = entries;
        if (entries.length > max) {
            const rest = entries.slice(max - 1).reduce((a, e) => a + e[1], 0);
            rows = [...entries.slice(0, max - 1), ['overig', rest]];
        }
        const total = entries.reduce((a, e) => a + e[1], 0);
        const top = Math.max(...rows.map(e => e[1]));
        const ul = el('ul', 'st-bars');
        rows.forEach(([label, n]) => {
            const li = el('li', 'st-bar');
            const track = el('span', 'st-bar__track');
            const fill = el('span', 'st-bar__fill');
            fill.style.width = `${(n / top) * 100}%`;
            track.appendChild(fill);
            const v = el('span', 'st-bar__value', fmtInt(n));
            v.appendChild(el('small', '', ` ${Math.round((n / total) * 100)}%`));
            li.append(el('span', 'st-bar__label', label), track, v);
            li.title = `${label}: ${n}`;
            ul.appendChild(li);
        });
        return ul;
    }
    function table(heads, rows, limit = 40) {
        const wrap = el('div', 'st-table-wrap');
        if (!rows.length) { wrap.appendChild(el('p', 'st-empty', 'Nog niets.')); return wrap; }
        const t = el('table', 'st-table');
        const tr = el('tr');
        heads.forEach(h => { const th = el('th', h.num ? 'num' : '', h.label); th.scope = 'col'; tr.appendChild(th); });
        const thead = el('thead'); thead.appendChild(tr);
        const tbody = el('tbody');
        rows.slice(0, limit).forEach(cells => {
            const r = el('tr');
            cells.forEach((c, i) => {
                const td = el('td', heads[i].cls || (heads[i].num ? 'num' : ''));
                if (c instanceof Node) td.appendChild(c); else td.textContent = c ?? '–';
                r.appendChild(td);
            });
            tbody.appendChild(r);
        });
        t.append(thead, tbody);
        wrap.appendChild(t);
        if (rows.length > limit) {
            const box = el('div');
            const more = el('p', 'st-more', `De nieuwste ${limit} van ${fmtInt(rows.length)}. `);
            const all = el('button', 'st-link', 'Toon alles');
            all.type = 'button';
            all.addEventListener('click', () => box.replaceWith(table(heads, rows, rows.length)));
            more.appendChild(all);
            box.append(wrap, more);
            return box;
        }
        return wrap;
    }
    const tag = (text, kind) => el('span', 'st-tag' + (kind ? ` st-tag--${kind}` : ''), text);

    // visits per day: gold bars on a quiet grid, a label on hover
    function dayChart(perDay, width) {
        const box = el('div', 'st-chart');
        // drawn at the width it is shown at, so the labels stay readable on a phone
        const W = Math.max(280, Math.round(width || 720)), H = W < 500 ? 180 : 220, L = 28, B = 22, T = 8;
        const n = perDay.length;
        const top = Math.max(1, ...perDay.map(p => p.n));
        const step = top <= 4 ? 1 : Math.ceil(top / 4);
        const yMax = Math.ceil(top / step) * step;
        const y = (v) => T + (H - T - B) * (1 - v / yMax);
        const slot = (W - L) / n;
        const gap = Math.min(2, slot * 0.2);
        const ns = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', 'Bezoeken per dag');
        const mk = (tagName, attrs, text) => {
            const e = document.createElementNS(ns, tagName);
            Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
            if (text !== undefined) e.textContent = text;
            svg.appendChild(e);
            return e;
        };
        for (let v = step; v <= yMax; v += step) {
            mk('line', { class: 'grid', x1: L, x2: W, y1: y(v), y2: y(v) });
            mk('text', { class: 'axis', x: L - 6, y: y(v) + 4, 'text-anchor': 'end' }, String(v));
        }
        mk('text', { class: 'axis', x: L - 6, y: y(0) + 4, 'text-anchor': 'end' }, '0');
        const every = Math.max(1, Math.ceil(n / Math.max(3, Math.floor((W - L) / 70))));
        const tip = $('st-tip');
        perDay.forEach((p, i) => {
            const x = L + i * slot + gap / 2, w = Math.max(1, slot - gap);
            const hit = mk('rect', { class: 'hit', x: L + i * slot, y: T, width: slot, height: H - T - B });
            let bar = null;
            if (p.n > 0) {
                const yt = y(p.n), h = y(0) - yt, r = Math.min(4, w / 2, h);
                // rounded at the top, square on the baseline
                bar = mk('path', { class: 'bar', d: `M${x},${y(0)}V${yt + r}Q${x},${yt} ${x + r},${yt}H${x + w - r}Q${x + w},${yt} ${x + w},${yt + r}V${y(0)}Z` });
            }
            if (i % every === 0 || (i === n - 1 && (n - 1) % every >= every * 0.6)) {
                mk('text', { class: 'axis', x: L + i * slot + slot / 2, y: H - 6, 'text-anchor': 'middle' },
                    p.day.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' }));
            }
            const show = (e) => {
                tip.textContent = `${fmtDay(p.day)}: ${p.n} ${p.n === 1 ? 'bezoek' : 'bezoeken'}`;
                tip.hidden = false;
                tip.style.left = `${Math.min(innerWidth - tip.offsetWidth - 8, e.clientX + 12)}px`;
                tip.style.top = `${e.clientY - 34}px`;
                if (bar) bar.classList.add('is-hover');
            };
            hit.addEventListener('pointermove', show);
            hit.addEventListener('pointerleave', () => { tip.hidden = true; if (bar) bar.classList.remove('is-hover'); });
        });
        mk('line', { class: 'base', x1: L, x2: W, y1: y(0), y2: y(0) });
        box.appendChild(svg);
        // the same numbers as a table, for reading them exactly
        const det = el('details', 'st-table-view');
        det.appendChild(el('summary', '', 'Als tabel'));
        det.appendChild(table([{ label: 'Dag' }, { label: 'Bezoeken', num: true }],
            [...perDay].reverse().map(p => [fmtDay(p.day), fmtInt(p.n)]), 400));
        box.appendChild(det);
        return box;
    }

    function render(m, days) {
        const dash = $('st-dash');
        dash.replaceChildren();

        // whose device is this
        const ownerLine = el('div', 'st-owner');
        const owner = local.get(OWNER_KEY) === '1';
        ownerLine.appendChild(el('span', '', owner
            ? 'Dit apparaat telt niet mee in de statistieken.'
            : 'Let op: dit apparaat telt nu mee in de statistieken.'));
        const toggle = el('button', 'st-link', owner ? 'Toch meetellen' : 'Niet meer meetellen');
        toggle.type = 'button';
        toggle.addEventListener('click', () => {
            if (owner) local.del(OWNER_KEY); else local.set(OWNER_KEY, '1');
            render(m, days);
        });
        ownerLine.appendChild(toggle);
        dash.appendChild(ownerLine);

        if (!m.rows.length) {
            const c = card('Nog geen gegevens');
            c.appendChild(el('p', 'st-muted', days
                ? 'In deze periode heeft nog niemand (behalve jij) de game bezocht.'
                : 'Nog geen bezoeken. Zie je er wel een paar verwacht? Kijk of het e-mailadres in stats.sql hetzelfde is als waarmee je inlogt.'));
            dash.appendChild(c);
            return;
        }

        // headline numbers
        const finished = m.matches.filter(r => r.data.finished).length;
        const kp = el('div', 'st-kpis');
        kp.append(
            kpi('Bezoeken', fmtInt(m.list.length), null, true),
            kpi('Verschillende bezoekers', fmtInt(new Set(m.list.map(s => s.visitor)).size)),
            kpi('Gemiddelde tijd per bezoek', fmtSecs(m.known.length ? m.known.reduce((a, b) => a + b, 0) / m.known.length : null),
                m.known.length ? `mediaan ${fmtSecs(median(m.known))}` : 'nog geen tijden'),
            kpi('Wedstrijden', fmtInt(m.matches.length), `${fmtInt(finished)} uitgespeeld, ${fmtInt(m.matches.length - finished)} gestopt`),
            kpi("WK's gestart", fmtInt(m.wkStarts.length), `${fmtInt(m.wkMatches.length)} WK-wedstrijden`),
        );
        dash.appendChild(kp);

        // visits per day
        const daily = card('Bezoeken per dag');
        dash.appendChild(daily);
        daily.appendChild(dayChart(m.perDay, daily.clientWidth - 34));

        // who and from where
        const g1 = el('div', 'st-grid st-grid--4');
        const c1 = card('Apparaat'); c1.appendChild(bars(count(m.list, s => s.device)));
        const c2 = card('Systeem'); c2.appendChild(bars(count(m.list, s => s.os)));
        const c3 = card('Browser'); c3.appendChild(bars(count(m.list, s => s.browser)));
        const c4 = card('Waar vandaan'); c4.appendChild(bars(count(m.list, s => s.referrer || 'direct of link')));
        g1.append(c1, c2, c3, c4);
        dash.appendChild(g1);

        // which phone, tablet or computer exactly (an iPhone by its screen size)
        const cd = card('Toestel');
        cd.classList.add('st-card--wide');
        cd.appendChild(bars(count(m.list.filter(s => s.model), s => s.model), 12));
        cd.appendChild(el('p', 'st-note', 'Android geeft het echte model door. Apple verbergt het: een iPhone of iPad wordt herkend aan zijn schermmaat, die een paar modellen delen.'));
        dash.appendChild(cd);

        // names and choices
        dash.appendChild(el('h2', 'st-section-title', 'Spelen'));
        const g2 = el('div', 'st-grid st-grid--3');
        const cn = card('Gekozen namen');
        const names = [...m.names.values()].sort((a, b) => b.n - a.n);
        cn.appendChild(table(
            [{ label: 'Naam' }, { label: 'Keer', num: true }, { label: 'Laatst' }, { label: 'Apparaat' }],
            names.map(e => [e.name, fmtInt(e.n), fmtWhen(e.last), [...e.devices].join(', ')]), 25));
        const cm = card('Modus en niveau');
        cm.appendChild(bars(count(m.normal, r => MODE[r.data.mode] || r.data.mode)));
        cm.appendChild(el('p', 'st-note', 'Niveau tegen de computer'));
        cm.appendChild(bars(count(m.normal.filter(r => r.data.mode === 'cpu'), r => LEVEL[r.data.level] || r.data.level)));
        const cs = card('Stadion');
        cs.appendChild(bars(count(m.normal, r => r.data.stadium)));
        g2.append(cn, cm, cs);
        dash.appendChild(g2);

        // every match
        const cmat = card('Wedstrijden');
        const matchRows = [...m.matches].reverse().map(r => {
            const d = r.data;
            const where = d.wk ? `WK: ${ROUND[d.wk.round] || d.wk.round}${d.wk.md ? ` ${d.wk.md}` : ''}` : (d.stadium || '–');
            const pens = d.wk && d.wk.pens ? ` (${d.wk.pens[0]}-${d.wk.pens[1]} str.)` : '';
            const res = outcome(d);
            return [
                fmtWhen(r.created_at), r.device,
                d.wk ? 'WK' : (MODE[d.mode] || d.mode), LEVEL[d.level] || '–', where,
                d.wk ? (d.wk.teamName || d.p1) : d.p1,
                el('span', 'score', `${d.s1} - ${d.s2}${pens}`),
                d.wk ? (d.wk.oppName || d.p2) : d.p2,
                fmtSecs(d.secs),
                d.finished ? tag(res === 'W' ? 'Gewonnen' : res === 'V' ? 'Verloren' : 'Gelijk', res === 'W' ? 'good' : res === 'V' ? 'bad' : '') : tag('Gestopt'),
            ];
        });
        cmat.appendChild(table([
            { label: 'Wanneer' }, { label: 'Apparaat' }, { label: 'Modus' }, { label: 'Niveau' }, { label: 'Stadion of ronde' },
            { label: 'Speler 1' }, { label: 'Uitslag' }, { label: 'Tegenstander' }, { label: 'Duur', num: true }, { label: 'Afloop' },
        ], matchRows));
        dash.appendChild(cmat);

        // the WK
        dash.appendChild(el('h2', 'st-section-title', 'WK 2026'));
        const g3 = el('div', 'st-grid st-grid--2');
        const cl = card('Gekozen landen');
        cl.appendChild(bars(count(m.wkStarts, r => r.data.teamName || r.data.team), 10));
        const cr = card('Hoe ver ze komen');
        cr.appendChild(bars(count(m.tournaments, t => t.status.replace(/^Loopt nog:.*/, 'Loopt nog')), 10));
        g3.append(cl, cr);
        dash.appendChild(g3);

        const ct = card('Toernooien');
        ct.appendChild(table([
            { label: 'Begonnen' }, { label: 'Apparaat' }, { label: 'Land' }, { label: 'Niveau' },
            { label: 'Gespeeld', num: true }, { label: 'W-G-V' }, { label: 'Gestopt', num: true }, { label: 'Stand' },
        ], m.tournaments.map(t => [
            fmtWhen(t.when), t.device, t.team, t.level, fmtInt(t.played),
            `${t.tally.W}-${t.tally.G}-${t.tally.V}`, fmtInt(t.quit), tag(t.status, t.tag),
        ])));
        dash.appendChild(ct);

        // every visit
        dash.appendChild(el('h2', 'st-section-title', 'Bezoeken'));
        const cv = card('Alle bezoeken');
        cv.appendChild(table([
            { label: 'Wanneer' }, { label: 'Apparaat' }, { label: 'Toestel' }, { label: 'Systeem' }, { label: 'Browser' }, { label: 'Scherm' },
            { label: 'Taal' }, { label: 'Vandaan' }, { label: 'Tijd', num: true }, { label: 'Wedstrijden', num: true },
            { label: 'Namen', cls: 'wrap' },
        ], m.list.map(s => [
            fmtWhen(s.start), s.device, s.model || '–', s.osv ? `${s.os} ${s.osv}` : s.os, s.browser, s.screen, s.lang, s.referrer || 'direct',
            fmtSecs(s.secs), fmtInt(s.matches), [...s.names].join(', ') || '–',
        ]), 60));
        dash.appendChild(cv);
    }

    // ---------- the page ----------
    let days = Number(local.get(PERIOD_KEY) ?? 30);
    if (![0, 7, 30, 90].includes(days)) days = 30;

    function show(which) {
        $('st-setup').hidden = which !== 'setup';
        $('st-login').hidden = which !== 'login';
        $('st-dash').hidden = which !== 'dash';
        $('st-actions').hidden = which !== 'dash';
    }
    function status(text) {
        const s = $('st-status');
        s.hidden = !text;
        s.textContent = text || '';
    }
    function paintPeriod() {
        document.querySelectorAll('#st-period button').forEach(b => {
            b.setAttribute('aria-checked', Number(b.dataset.days) === days ? 'true' : 'false');
        });
    }
    async function load() {
        show('dash');
        paintPeriod();
        status('Laden…');
        $('st-refresh').disabled = true;
        try {
            const rows = await fetchEvents(days);
            render(build(rows, days), days);
            status(`${fmtInt(rows.length)} regels geladen, ${new Date().toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' })}.`);
        } catch (err) {
            if (err.login) { show('login'); $('st-login-error').textContent = err.message; $('st-login-error').hidden = false; status(''); }
            else status(err.message || 'Er ging iets mis.');
        } finally {
            $('st-refresh').disabled = false;
        }
    }

    document.querySelectorAll('#st-period button').forEach(b => {
        b.addEventListener('click', () => {
            days = Number(b.dataset.days);
            local.set(PERIOD_KEY, String(days));
            load();
        });
    });
    $('st-refresh').addEventListener('click', load);
    $('st-logout').addEventListener('click', () => {
        session.del(TOKEN_KEY);
        $('st-dash').replaceChildren();
        status('');
        show('login');
    });
    $('st-login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const go = $('st-login-go'), err = $('st-login-error');
        err.hidden = true;
        go.disabled = true;
        try {
            await login($('st-email').value.trim(), $('st-password').value);
            $('st-password').value = '';
            await load();
        } catch (ex) {
            err.textContent = ex.message || 'Inloggen lukte niet.';
            err.hidden = false;
        } finally {
            go.disabled = false;
        }
    });

    if (!base || !cfg.key) show('setup');
    else if (token()) load();
    else show('login');
})();

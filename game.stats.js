// =====================================================
// PITCH ROYALE — play statistics
// Sends a few anonymous rows to the owner's Supabase table (stats.config.js,
// stats.sql), read back on stats.html:
//   visit     a new visit (a tab opened, or back after 30 minutes away)
//   time      seconds the game was on screen during that visit, so far
//   match     a match that ended or was left: names, score, level, stadium,
//             how long it lasted, and for a WK match the round and result
//   wk_start  a WK tournament started: the country and the level
// Every row also carries the kind of device, its system and browser, the
// screen size, the language and the site the visitor came from. No IP
// address, no account, no exact location: a visitor is a random id kept in
// this browser.
// Nothing is sent when the config is empty, when the browser asks not to be
// tracked (Global Privacy Control / Do Not Track), or on the owner's own
// devices (logging in on stats.html marks the device).
// =====================================================
const PR_STATS = (() => {
    const cfg = typeof STATS_CONFIG !== 'undefined' ? STATS_CONFIG : {};
    const OWNER_KEY = 'pitchRoyale.owner';
    const VISITOR_KEY = 'pitchRoyale.visitor';
    const SESSION_KEY = 'pitchRoyale.session';
    const VISIT_GAP_MS = 30 * 60 * 1000;          // away this long: the next look is a new visit

    const get = (s, k) => { try { return s.getItem(k); } catch (_) { return null; } };
    const put = (s, k, v) => { try { s.setItem(k, v); } catch (_) { /* private mode */ } };
    const local = (() => { try { return window.localStorage; } catch (_) { return null; } })();
    const sess = (() => { try { return window.sessionStorage; } catch (_) { return null; } })();

    const rid = () => (window.crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).slice(2, 14);
    const clip = (v, n) => String(v ?? '').slice(0, n);

    const owner = local && get(local, OWNER_KEY) === '1';
    const optOut = navigator.globalPrivacyControl === true || navigator.doNotTrack === '1';
    const on = !!(cfg.url && cfg.key) && !owner && !optOut;

    // ---- who and on what ----
    let visitor = local && get(local, VISITOR_KEY);
    if (!visitor) { visitor = rid(); if (local) put(local, VISITOR_KEY, visitor); }

    function device() {
        const ua = navigator.userAgent || '';
        const touchMac = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1;   // an iPad asking for the desktop site
        let kind = 'computer';
        if (/iPad|Tablet/i.test(ua) || touchMac || (/Android/i.test(ua) && !/Mobile/i.test(ua))) kind = 'tablet';
        else if (/iPhone|iPod|Mobi|Android.*Mobile|Windows Phone/i.test(ua)) kind = 'telefoon';
        let os = 'anders';
        if (/iPhone|iPad|iPod/.test(ua) || touchMac) os = 'iOS';
        else if (/Android/i.test(ua)) os = 'Android';
        else if (/Windows/i.test(ua)) os = 'Windows';
        else if (/CrOS/.test(ua)) os = 'ChromeOS';
        else if (/Mac OS X|Macintosh/.test(ua)) os = 'macOS';
        else if (/Linux/i.test(ua)) os = 'Linux';
        let browser = 'anders';
        if (/SamsungBrowser/i.test(ua)) browser = 'Samsung Internet';
        else if (/Edg\//.test(ua)) browser = 'Edge';
        else if (/OPR\/|Opera/.test(ua)) browser = 'Opera';
        else if (/Firefox|FxiOS/.test(ua)) browser = 'Firefox';
        else if (/Chrome|CriOS/.test(ua)) browser = 'Chrome';
        else if (/Safari/.test(ua)) browser = 'Safari';
        return { kind, os, browser };
    }
    const dev = device();
    function referrer() {
        try {
            if (!document.referrer) return '';
            const h = new URL(document.referrer).hostname.replace(/^www\./, '');
            return h === location.hostname ? '' : h;
        } catch (_) { return ''; }
    }
    const ref = referrer();

    // ---- the visit ----
    function readSession() {
        try { return JSON.parse(get(sess, SESSION_KEY)) || null; } catch (_) { return null; }
    }
    let session = sess && readSession();
    let isNew = false;
    function freshSession() {
        session = { id: rid(), last: Date.now(), secs: 0 };
        isNew = true;
    }
    if (!session || Date.now() - session.last > VISIT_GAP_MS) freshSession();
    const save = () => { session.last = Date.now(); if (sess) put(sess, SESSION_KEY, JSON.stringify(session)); };
    save();

    // ---- sending ----
    function send(type, data, keepalive) {
        if (!on) return;
        const headers = { 'Content-Type': 'application/json', apikey: cfg.key, Prefer: 'return=minimal' };
        // the old anon keys are tokens and go in Authorization too; the new publishable keys don't
        if (/^eyJ/.test(cfg.key)) headers.Authorization = `Bearer ${cfg.key}`;
        const row = {
            visitor, session: session.id, type,
            device: dev.kind, os: dev.os, browser: dev.browser,
            screen: `${screen.width}x${screen.height}`,
            lang: clip(navigator.language, 16),
            referrer: clip(ref, 100),
            data: data || {},
        };
        try {
            fetch(cfg.url.replace(/\/$/, '') + '/rest/v1/events', {
                method: 'POST', headers, body: JSON.stringify(row), keepalive: !!keepalive, mode: 'cors',
            }).catch(() => {});
        } catch (_) { /* never let statistics break the game */ }
        save();
    }

    // ---- time on screen: only while the game is actually visible ----
    let since = document.visibilityState === 'visible' ? performance.now() : null;
    let lastSent = session.secs;
    function flushTime() {
        if (since !== null) {
            session.secs += (performance.now() - since) / 1000;
            since = document.visibilityState === 'visible' ? performance.now() : null;
        }
        save();
        if (session.secs - lastSent >= 2) {
            lastSent = session.secs;
            send('time', { secs: Math.round(session.secs) }, true);
        }
    }
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') { flushTime(); since = null; }
        else {
            // back after a long time away: that is a new visit
            if (Date.now() - session.last > VISIT_GAP_MS) {
                freshSession(); save(); lastSent = 0;
                send('visit', { back: true });
            }
            since = performance.now();
        }
    });
    window.addEventListener('pagehide', flushTime);
    setInterval(() => { if (since !== null) flushTime(); }, 60000);   // a long visit in one go still counts

    if (isNew) send('visit', { standalone: !!(window.matchMedia && matchMedia('(display-mode: standalone)').matches) });

    // ---- matches ----
    let match = null;              // { t } while a match is being played
    function matchStart() { match = { t: Date.now() }; }
    function matchEnd(finished) {
        if (!match) return;
        const started = match.t;
        match = null;
        if (typeof STATE === 'undefined') return;
        const p1 = STATE.p1, p2 = STATE.p2;
        const score = (p) => (p.team === 1 ? STATE.score1 : STATE.score2);
        const m = STATE.wkMatch;
        const stadium = !m && typeof getSelectedStadium === 'function' ? getSelectedStadium() : null;
        const data = {
            mode: STATE.mode,
            level: STATE.mode === 'cpu' ? STATE.difficulty : null,
            stadium: stadium ? stadium.name : null,
            p1: clip(p1.name, 30), p2: clip(p2.name, 30),
            s1: score(p1), s2: score(p2),
            secs: Math.round((Date.now() - started) / 1000),
            finished: !!finished,
        };
        if (m) {
            const w = typeof wk !== 'undefined' ? wk : null;
            const k = m.f.kind === 'ko' && w && w.ko ? w.ko[m.f.m] : null;
            const name = (c) => (typeof WK_TEAMS !== 'undefined' && WK_TEAMS[c] ? WK_TEAMS[c].name : c);
            data.wk = {
                team: m.me, opp: m.opp, teamName: name(m.me), oppName: name(m.opp),
                round: m.f.kind === 'group' ? 'group' : m.f.round,
                md: m.f.kind === 'group' ? m.f.md + 1 : null,
                city: m.city || null,
                extra: !!m.extra,
                pens: k && k.pens ? (k.a === m.me ? k.pens : [k.pens[1], k.pens[0]]) : null,
                level: w ? w.level : null,
                out: finished && w ? (w.out || null) : null,
                next: finished && w ? w.round : null,
            };
        }
        send('match', data);
    }
    function wkStart(team, level) {
        const name = typeof WK_TEAMS !== 'undefined' && WK_TEAMS[team] ? WK_TEAMS[team].name : team;
        send('wk_start', { team, teamName: name, level });
    }

    // a short line on the start screen says what is measured
    document.addEventListener('DOMContentLoaded', () => {
        const note = document.getElementById('stats-note');
        if (note) note.hidden = !on;
    });

    return { on, matchStart, matchEnd, wkStart };
})();

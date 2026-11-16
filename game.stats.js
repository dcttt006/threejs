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

    // ---- which phone exactly, as far as the browser tells ----
    // Android (Chrome, Samsung Internet, Edge) gives the real model through
    // client hints; Apple hides it, so an iPhone or iPad is recognised by its
    // screen size and pixel density, which a few models share. The iOS version
    // then narrows it down: [model, iOS it came out with, last iOS it got].
    const IPHONES = {
        '320x568@2': [['iPhone 5s', 7, 12], ['iPhone SE (1e gen.)', 9, 15]],
        '375x667@2': [['iPhone 6', 8, 12], ['iPhone 6s', 9, 15], ['iPhone 7', 10, 15], ['iPhone 8', 11, 16],
                      ['iPhone SE (2e gen.)', 13], ['iPhone SE (3e gen.)', 15]],
        '414x736@3': [['iPhone 6 Plus', 8, 12], ['iPhone 6s Plus', 9, 15], ['iPhone 7 Plus', 10, 15], ['iPhone 8 Plus', 11, 16]],
        '375x812@3': [['iPhone X', 11, 16], ['iPhone XS', 12, 18], ['iPhone 11 Pro', 13], ['iPhone 12 mini', 14], ['iPhone 13 mini', 15]],
        '414x896@2': [['iPhone XR', 12, 18], ['iPhone 11', 13]],
        '414x896@3': [['iPhone XS Max', 12, 18], ['iPhone 11 Pro Max', 13]],
        '390x844@3': [['iPhone 12', 14], ['iPhone 12 Pro', 14], ['iPhone 13', 15], ['iPhone 13 Pro', 15], ['iPhone 14', 16], ['iPhone 16e', 18]],
        '428x926@3': [['iPhone 12 Pro Max', 14], ['iPhone 13 Pro Max', 15], ['iPhone 14 Plus', 16]],
        '393x852@3': [['iPhone 14 Pro', 16], ['iPhone 15', 17], ['iPhone 15 Pro', 17], ['iPhone 16', 18]],
        '430x932@3': [['iPhone 14 Pro Max', 16], ['iPhone 15 Plus', 17], ['iPhone 15 Pro Max', 17], ['iPhone 16 Plus', 18]],
        '402x874@3': [['iPhone 16 Pro', 18], ['iPhone 17', 26], ['iPhone 17 Pro', 26]],
        '420x912@3': [['iPhone Air', 26]],
        '440x956@3': [['iPhone 16 Pro Max', 18], ['iPhone 17 Pro Max', 26]],
    };
    // "iPhone 15 / 15 Pro / 16": the models that fit this iOS version
    function iphoneName(key, ios, maybeNewer) {
        const all = IPHONES[key];
        if (!all) return '';
        let fit = all;
        if (ios) {
            fit = all.filter(([, from, last]) =>
                (from <= ios || (maybeNewer && from >= 26)) && (!last || last >= ios));
            if (!fit.length) fit = all;            // an odd version: show the whole group
        }
        return fit.map(([n], i) => (i ? n.replace(/^iPhone /, '') : n)).join(' / ');
    }
    const IPADS = {
        '768x1024': 'iPad mini / iPad (oud)',
        '744x1133': 'iPad mini (6e/7e gen.)',
        '810x1080': 'iPad (7e-9e gen.)',
        '820x1180': 'iPad Air / iPad (10e gen.)',
        '834x1112': 'iPad Air (3e gen.) / iPad Pro 10,5"',
        '834x1194': 'iPad Pro 11"',
        '834x1210': 'iPad Pro 11" (M4)',
        '1024x1366': 'iPad Pro 12,9"',
        '1032x1376': 'iPad Pro 13" (M4)',
    };
    // Samsung model codes to names (SM-S911B -> Galaxy S23)
    function samsungName(code) {
        const c = code.toUpperCase();
        const table = [
            [/^SM-S93/, 'Galaxy S25'], [/^SM-S92/, 'Galaxy S24'], [/^SM-S91/, 'Galaxy S23'], [/^SM-S90/, 'Galaxy S22'],
            [/^SM-S72/, 'Galaxy S24 FE'], [/^SM-S71/, 'Galaxy S23 FE'], [/^SM-G99/, 'Galaxy S21'], [/^SM-G98/, 'Galaxy S20'],
            [/^SM-F9/, 'Galaxy Z Fold'], [/^SM-F7/, 'Galaxy Z Flip'], [/^SM-X/, 'Galaxy Tab'], [/^SM-T/, 'Galaxy Tab'],
        ];
        for (const [re, name] of table) if (re.test(c)) return name;
        const a = c.match(/^SM-([AMN])(\d{2})/);
        if (a) return `Galaxy ${a[1] === 'N' ? 'Note' : a[1]}${a[2].replace(/^0/, '')}`;
        return '';
    }
    const hints = (async () => {
        const ua = navigator.userAgent || '';
        let model = '', osVersion = '';
        try {
            if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
                const h = await navigator.userAgentData.getHighEntropyValues(['model', 'platformVersion']);
                model = h.model || '';
                osVersion = h.platformVersion || '';
            }
        } catch (_) { /* not offered: fall back to the user agent */ }
        const w = Math.min(screen.width, screen.height), hgt = Math.max(screen.width, screen.height);
        const dpr = Math.round(window.devicePixelRatio || 1);
        if (dev.os === 'iOS') {
            const v = ua.match(/OS (\d+)[_.](\d+)/);
            let major = v ? +v[1] : 0;
            osVersion = v ? `${v[1]}.${v[2]}` : '';
            // Safari 26 leaves "OS 18_6" in the user agent; its own version tells the truth
            const sv = ua.match(/Version\/(\d+)(?:\.(\d+))?/);
            if (sv && +sv[1] >= 26) { major = +sv[1]; osVersion = `${sv[1]}.${sv[2] || 0}`; }
            // other browsers on iOS 26 keep saying 18.6 too: a 26 model may still fit
            const maybeNewer = major === 18 && v && +v[2] >= 6;
            model = dev.kind === 'tablet'
                ? (IPADS[`${w}x${hgt}`] || `iPad (${w}x${hgt})`)
                : (iphoneName(`${w}x${hgt}@${dpr}`, major, maybeNewer) || `iPhone (${w}x${hgt})`);
        } else if (dev.os === 'Android') {
            if (!model) {
                const m = ua.match(/Android [\d.]+; ([^;)]+)/);
                // old user agents name the phone; newer ones say only "K" or "Mobile"
                if (m && !/^(K|Mobile|Tablet|rv:.*|wv)$/i.test(m[1].trim())) model = m[1].trim();
            }
            if (!osVersion) { const v = ua.match(/Android ([\d.]+)/); osVersion = v ? v[1] : ''; }
            osVersion = osVersion.replace(/(\.0)+$/, '');                  // 14.0.0 -> 14
            const named = /^SM-/i.test(model) ? samsungName(model) : '';
            model = named ? `${named} (${model})` : (model || 'Android-toestel');
        } else if (dev.os === 'Windows') {
            const major = parseInt(osVersion, 10);
            osVersion = isNaN(major) ? '' : (major >= 13 ? '11' : '10');
            model = 'Windows-pc';
        } else if (dev.os === 'macOS') {
            osVersion = osVersion ? osVersion.split('.').slice(0, 2).join('.') : '';
            model = 'Mac';
        } else if (dev.os === 'ChromeOS') model = 'Chromebook';
        else if (dev.os === 'Linux') model = 'Linux-computer';
        return { model: clip(model, 60), osVersion: clip(osVersion, 12), dpr };
    })();

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
                hints.then(h => send('visit', { back: true, ...h }));
            }
            since = performance.now();
        }
    });
    window.addEventListener('pagehide', flushTime);
    setInterval(() => { if (since !== null) flushTime(); }, 60000);   // a long visit in one go still counts

    if (isNew) {
        const standalone = !!(window.matchMedia && matchMedia('(display-mode: standalone)').matches);
        hints.then(h => send('visit', { standalone, ...h }));
    }

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

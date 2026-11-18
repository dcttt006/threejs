// =====================================================
// PITCH ROYALE — online
// Accounts (a username and a password, no email), friends, challenges and
// a match between two browsers, on the same Supabase project as the
// statistics (stats.config.js; run online.sql once, see ONLINE.md).
//
// The match: the browser that made the room (the host) plays red and runs
// the real game: the ball, the keepers, the computer teammates. The other
// browser (the guest, blue) only draws: it sends its keys and stick to the
// host and gets the whole pitch back 15 times a second, which it plays out
// a tenth of a second late so the movement stays smooth.
// A room is a Supabase Realtime channel named after its four-digit code; the
// lobby channel tells who is online and carries challenges and friend-request
// nudges. Once a match starts the two browsers also try a direct connection
// (WebRTC): much quicker than going through Supabase, so then the pitch comes
// 30 times a second. Where that can't be made (some mobile networks) the
// match simply stays on the Supabase channel.
// =====================================================
const ONLINE = (() => {
    const cfg = typeof STATS_CONFIG !== 'undefined' ? STATS_CONFIG : {};
    const ENABLED = !!(cfg.url && cfg.key);
    const LIB = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js';
    const AUTH_KEY = 'pitchRoyale.auth';
    // Supabase logs in with an email address: a username becomes an address
    // nobody reads (ONLINE.md: "Confirm email" must be off, so nothing is sent)
    const EMAIL_DOMAIN = 'spelers.pitchroyale.nl';
    const NAME_OK = /^[a-z0-9_.]{3,16}$/;
    const SNAP_EVERY = 4;           // ticks: 15 pictures of the pitch a second through Supabase
    const SNAP_EVERY_P2P = 2;       // 30 a second over the direct connection
    const INTERP_MS = 120;          // the guest plays them out this far behind
    const INTERP_MS_P2P = 60;
    const ICE = [{ urls: 'stun:stun.cloudflare.com:3478' }, { urls: 'stun:stun.l.google.com:19302' }];
    const INVITE_MS = 30000;        // a challenge waits this long for an answer
    const SILENT_MS = 6000;         // no picture from the host this long: gone

    let sb = null;
    let me = null;                  // { id, username }
    let lobby = null;
    let lobbyState = {};
    let myStatus = 'menu';
    let friends = [];               // { fid, id, username, kind: 'friend' | 'in' | 'out' }
    let records = {};               // friend id -> [won, drawn, lost]
    let room = null;                // the match room, see openRoom()
    let view = 'login';
    let signUp = false;
    let saved = null;               // the local players and mode, put back after online play
    let invite = null;              // the challenge on screen
    let pending = null;             // what Uitdagen / Code maken was for, while you pick what to play
    let overTitle = null;           // the full-time screen's own title, put back after a shoot-out

    // what you can play online
    const KINDS = {
        match:  { label: 'Wedstrijd', meta: '90 seconden' },
        pens:   { label: 'Strafschoppen', meta: 'Normaal' },
        wkpens: { label: 'Strafschoppen WK', meta: 'MetLife Stadium · jullie kiezen een land' },
    };
    const isPens = (kind) => kind === 'pens' || kind === 'wkpens';

    const clean = (s) => String(s || '').trim().toLowerCase();
    const el = (tag, cls, text) => {
        const n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text !== undefined) n.textContent = text;
        return n;
    };

    // ------------------------------------------------- the library
    let libLoad = null;
    function loadLib() {
        if (window.supabase && window.supabase.createClient) return Promise.resolve();
        if (!libLoad) {
            libLoad = new Promise((resolve, reject) => {
                const s = document.createElement('script');
                s.src = LIB;
                s.onload = resolve;
                s.onerror = () => { libLoad = null; reject(new Error('lib')); };
                document.head.appendChild(s);
            });
        }
        return libLoad;
    }
    async function client() {
        if (sb) return sb;
        await loadLib();
        sb = window.supabase.createClient(cfg.url, cfg.key, {
            auth: { storageKey: AUTH_KEY, persistSession: true, autoRefreshToken: true },
            realtime: { params: { eventsPerSecond: 40 } },
        });
        return sb;
    }
    function hasStoredSession() {
        try { return !!localStorage.getItem(AUTH_KEY); } catch (_) { return false; }
    }

    // ------------------------------------------------- accounts
    function usernameOf(user) {
        return clean(user && user.user_metadata && user.user_metadata.username)
            || clean(String(user && user.email || '').split('@')[0]);
    }
    function setMe(user) {
        me = { id: user.id, username: usernameOf(user) };
        startLobby();
        loadFriends();
    }
    async function restore() {
        if (!ENABLED || !hasStoredSession()) return;
        try {
            await client();
            const { data } = await sb.auth.getSession();
            if (data && data.session) setMe(data.session.user);
        } catch (_) { /* offline: the Online screen tries again */ }
    }

    function authError(err) {
        const m = String(err && err.message || '').toLowerCase();
        if (m.includes('already registered') || m.includes('already been registered')) return 'Deze gebruikersnaam is al bezet. Kies een andere.';
        if (m.includes('invalid login')) return 'Gebruikersnaam of wachtwoord klopt niet.';
        if (m.includes('password') && (m.includes('6') || m.includes('short') || m.includes('weak'))) return 'Je wachtwoord moet minstens 6 tekens hebben.';
        if (m.includes('email not confirmed') || m.includes('confirm')) return 'Online staat nog niet goed aan: zet in Supabase "Confirm email" uit (zie ONLINE.md).';
        if (m.includes('email') && m.includes('invalid')) return 'Supabase weigert het adres achter je gebruikersnaam. Zie ONLINE.md, stap 2.';
        if (m.includes('signups not allowed') || m.includes('signup is disabled')) return 'Nieuwe accounts staan uit in Supabase. Zet bij Authentication "Allow new users to sign up" aan.';
        if (m.includes('database error')) return 'Online staat nog niet aan: run eerst online.sql (zie ONLINE.md).';
        if (m.includes('rate') || m.includes('too many')) return 'Even te veel pogingen. Wacht een minuut en probeer het opnieuw.';
        if (m.includes('fetch') || m.includes('network') || m.includes('lib')) return 'Geen verbinding. Ben je online?';
        return 'Dat lukte niet. Probeer het nog eens.';
    }

    async function submitAuth(e) {
        e.preventDefault();
        const user = clean($('online-user').value);
        const pass = $('online-pass').value;
        if (!NAME_OK.test(user)) return say('online-auth-msg', 'Een gebruikersnaam heeft 3 tot 16 tekens: kleine letters, cijfers, een punt of een _.');
        if (pass.length < 6) return say('online-auth-msg', 'Je wachtwoord moet minstens 6 tekens hebben.');
        const go = $('online-auth-go');
        go.disabled = true;
        say('online-auth-msg', '');
        try {
            await client();
            const email = `${user}@${EMAIL_DOMAIN}`;
            const res = signUp
                ? await sb.auth.signUp({ email, password: pass, options: { data: { username: user } } })
                : await sb.auth.signInWithPassword({ email, password: pass });
            if (res.error) throw res.error;
            if (!res.data.session) throw new Error('confirm');
            $('online-pass').value = '';
            setMe(res.data.session.user);
            show('friends');
        } catch (err) {
            say('online-auth-msg', authError(err));
        } finally {
            go.disabled = false;
        }
    }

    async function logout() {
        await leaveRoom();
        if (lobby) { try { await sb.removeChannel(lobby); } catch (_) {} }
        lobby = null;
        lobbyState = {};
        friends = [];
        records = {};
        me = null;
        try { await sb.auth.signOut(); } catch (_) {}
        show('login');
    }

    // ------------------------------------------------- lobby: who is online, challenges
    function startLobby() {
        if (lobby || !me) return;
        lobby = sb.channel('pr-lobby', { config: { presence: { key: me.id }, broadcast: { self: false } } });
        lobby
            .on('presence', { event: 'sync' }, () => { lobbyState = lobby.presenceState(); renderFriends(); })
            .on('broadcast', { event: 'invite' }, ({ payload }) => onInvite(payload))
            .on('broadcast', { event: 'answer' }, ({ payload }) => onAnswer(payload))
            .on('broadcast', { event: 'friends' }, ({ payload }) => { if (me && payload && payload.to === me.id) loadFriends(); })
            .subscribe((status) => { if (status === 'SUBSCRIBED') track(); });
    }
    function track() {
        if (lobby && me) lobby.track({ username: me.username, status: myStatus }).catch(() => {});
    }
    function setStatus(s) {
        if (myStatus === s) return;
        myStatus = s;
        track();
    }
    function statusOf(id) {
        const metas = lobbyState[id];
        if (!metas || !metas.length) return 'off';
        return metas.some(m => m.status === 'playing') ? 'busy' : 'on';
    }
    function shout(event, payload) {
        if (lobby) lobby.send({ type: 'broadcast', event, payload }).catch(() => {});
    }

    // ------------------------------------------------- friends
    function dbProblem(error) {
        const m = String(error && (error.code || '') + ' ' + (error.message || '')).toLowerCase();
        if (m.includes('42p01') || m.includes('pgrst205') || m.includes('does not exist') || m.includes('schema cache')) {
            return 'Online staat nog niet aan: run eerst online.sql in Supabase (zie ONLINE.md).';
        }
        return 'De vriendenlijst laden lukte niet. Probeer het straks nog eens.';
    }
    async function loadFriends() {
        if (!me || !sb) return;
        const [fr, games] = await Promise.all([
            sb.from('friendships').select('id, requester, addressee, status'),
            sb.from('matches').select('red, blue, score_red, score_blue'),
        ]);
        if (fr.error) { say('online-add-msg', dbProblem(fr.error)); return; }
        const rows = fr.data || [];
        const ids = [...new Set(rows.map(r => r.requester === me.id ? r.addressee : r.requester))];
        const names = {};
        if (ids.length) {
            const { data } = await sb.from('profiles').select('id, username').in('id', ids);
            (data || []).forEach(p => { names[p.id] = p.username; });
        }
        friends = rows.map(r => {
            const other = r.requester === me.id ? r.addressee : r.requester;
            return {
                fid: r.id, id: other, username: names[other] || '?',
                kind: r.status === 'accepted' ? 'friend' : (r.addressee === me.id ? 'in' : 'out'),
            };
        });
        records = {};
        (games.data || []).forEach(g => {
            const red = g.red === me.id;
            const opp = red ? g.blue : g.red;
            const mine = red ? g.score_red : g.score_blue;
            const theirs = red ? g.score_blue : g.score_red;
            const r = records[opp] || (records[opp] = [0, 0, 0]);
            r[mine > theirs ? 0 : mine === theirs ? 1 : 2]++;
        });
        renderFriends();
    }
    async function addFriend(e) {
        e.preventDefault();
        if (!me) return;
        const input = $('online-add');
        const name = clean(input.value);
        if (!name) return;
        if (!NAME_OK.test(name)) return say('online-add-msg', 'Een gebruikersnaam heeft 3 tot 16 tekens: kleine letters, cijfers, een punt of een _.');
        if (name === me.username) return say('online-add-msg', 'Dat ben je zelf.');
        const known = friends.find(f => f.username === name);
        if (known) {
            return say('online-add-msg', known.kind === 'friend' ? `${name} is al je vriend.`
                : known.kind === 'out' ? `Je hebt ${name} al een verzoek gestuurd.`
                : `${name} heeft jou al een verzoek gestuurd. Accepteer het hieronder.`);
        }
        const { data: p, error } = await sb.from('profiles').select('id, username').eq('username', name).maybeSingle();
        if (error) return say('online-add-msg', dbProblem(error));
        if (!p) return say('online-add-msg', `Er is geen speler die ${name} heet.`);
        const ins = await sb.from('friendships').insert({ requester: me.id, addressee: p.id });
        if (ins.error) return say('online-add-msg', 'Het verzoek sturen lukte niet. Probeer het nog eens.');
        input.value = '';
        say('online-add-msg', `Verzoek gestuurd naar ${name}.`, true);
        shout('friends', { to: p.id });
        loadFriends();
    }
    async function acceptFriend(f) {
        await sb.from('friendships').update({ status: 'accepted' }).eq('id', f.fid);
        shout('friends', { to: f.id });
        loadFriends();
    }
    async function removeFriend(f) {
        await sb.from('friendships').delete().eq('id', f.fid);
        shout('friends', { to: f.id });
        loadFriends();
    }

    const STATUS_TEXT = { on: 'Online', busy: 'In een wedstrijd', off: 'Offline' };
    function renderFriends() {
        const list = $('online-list');
        const reqs = $('online-requests');
        if (!list || !reqs || !me) return;

        // requests to you
        const incoming = friends.filter(f => f.kind === 'in');
        reqs.replaceChildren(...incoming.map(f => {
            const row = el('div', 'o-row');
            const who = el('div', 'o-who');
            who.append(el('div', 'o-name', f.username), el('div', 'o-sub', 'wil je vriend worden'));
            const yes = el('button', 'o-sbtn', 'Accepteren');
            const no = el('button', 'o-sbtn o-sbtn--slate', 'Weigeren');
            yes.type = no.type = 'button';
            yes.addEventListener('click', () => { yes.disabled = no.disabled = true; acceptFriend(f); });
            no.addEventListener('click', () => { yes.disabled = no.disabled = true; removeFriend(f); });
            row.append(who, yes, no);
            return row;
        }));
        reqs.hidden = !incoming.length;

        // your friends as a table: online first, then in a match, then offline
        const order = { on: 0, busy: 1, off: 2 };
        const shown = friends.filter(f => f.kind !== 'in').sort((a, b) =>
            (a.kind === 'out') - (b.kind === 'out')
            || order[statusOf(a.id)] - order[statusOf(b.id)]
            || a.username.localeCompare(b.username));
        const head = el('div', 'o-frow o-frow--head');
        ['Naam', 'Status', 'Onderling', ''].forEach(t => head.append(el('span', '', t)));
        const rows = shown.map(f => {
            const row = el('div', 'o-frow');
            const st = f.kind === 'out' ? 'off' : statusOf(f.id);
            const status = el('span', 'o-status');
            status.append(el('i', 'o-dot' + (st === 'off' ? ' o-dot--off' : st === 'busy' ? ' o-dot--busy' : '')),
                document.createTextNode(f.kind === 'out' ? 'Verzoek verstuurd' : STATUS_TEXT[st]));
            const rec = el('span', 'o-rec');
            const r = records[f.id];
            if (r) { rec.textContent = r.join(' - '); rec.append(el('small', '', 'W G V')); }
            else { rec.textContent = '–'; rec.append(el('small', '', f.kind === 'out' ? '' : 'nog niet gespeeld')); }
            const act = el('span', 'o-act');
            const btn = el('button', 'o-sbtn' + (f.kind === 'out' ? ' o-sbtn--slate' : ''), f.kind === 'out' ? 'Intrekken' : 'Uitdagen');
            btn.type = 'button';
            if (f.kind === 'out') btn.addEventListener('click', () => { btn.disabled = true; removeFriend(f); });
            else {
                btn.disabled = st !== 'on';
                btn.addEventListener('click', () => challenge(f));
            }
            act.append(btn);
            row.append(el('span', 'o-name', f.username), status, rec, act);
            return row;
        });
        if (!rows.length) {
            const empty = el('p', 'o-empty', 'Nog geen vrienden. Typ hierboven de gebruikersnaam van een vriend en stuur een verzoek.');
            list.replaceChildren(empty);
        } else {
            list.replaceChildren(head, ...rows);
        }
    }

    // ------------------------------------------------- the screen
    function say(id, text, good) {
        const n = $(id);
        if (!n) return;
        n.textContent = text || '';
        n.hidden = !text;
        n.classList.toggle('o-msg--good', !!good);
    }
    function show(v) {
        view = v;
        ['login', 'friends', 'code', 'pick', 'land', 'wait'].forEach(id => { const s = $('online-' + id); if (s) s.hidden = id !== v; });
        const meBox = $('online-me');
        if (meBox) meBox.hidden = !me;
        if ($('online-me-name') && me) $('online-me-name').textContent = me.username;
        if ($('online-brand')) $('online-brand').hidden = !!me;
        $('online-back').querySelector('span').textContent = v === 'wait' || v === 'land' ? 'Annuleren' : 'Terug';
        if (v === 'friends') { say('online-add-msg', ''); renderFriends(); loadFriends(); }
        if (v === 'code') { say('online-code-msg', ''); $('online-code-in').value = ''; $('online-join').disabled = true; }
        if (v === 'login') {
            say('online-auth-msg', ENABLED ? '' : 'Online spelen staat nog niet aan: vul stats.config.js in (zie ONLINE.md).');
            setAuthTab(signUp);
        }
    }
    function setAuthTab(up) {
        signUp = up;
        document.querySelectorAll('[data-auth]').forEach(b => {
            const on = (b.dataset.auth === 'up') === up;
            b.classList.toggle('active', on);
            b.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        $('online-auth-go').textContent = up ? 'Account maken' : 'Inloggen';
        $('online-pass').autocomplete = up ? 'new-password' : 'current-password';
        say('online-auth-msg', '');
    }
    async function open() {
        if (STATE.screen !== 'online') gotoScreen('online');
        if (!me && ENABLED && hasStoredSession()) await restore();
        show(me ? 'friends' : 'login');
    }
    async function back() {
        if (view === 'wait' || view === 'land') { await leaveRoom(); show(me ? 'friends' : 'login'); return; }
        if (view === 'pick') { show(pending && pending.invite ? 'friends' : 'code'); pending = null; return; }
        if (view === 'code') { show('friends'); return; }
        gotoScreen('launch', { replace: true });
    }

    function bind() {
        if (!$('online-screen')) return;
        $('launch-online')?.addEventListener('click', open);
        $('online-back').addEventListener('click', back);
        $('online-logout').addEventListener('click', logout);
        document.querySelectorAll('[data-auth]').forEach(b => b.addEventListener('click', () => setAuthTab(b.dataset.auth === 'up')));
        $('online-auth-form').addEventListener('submit', submitAuth);
        $('online-add-form').addEventListener('submit', addFriend);
        $('online-to-code').addEventListener('click', () => show('code'));
        $('online-make').addEventListener('click', () => pickKind({}));
        document.querySelectorAll('[data-kind]').forEach(b => b.addEventListener('click', () => {
            const target = pending || {};
            pending = null;
            hostRoom({ ...target, kind: b.dataset.kind });
        }));
        const codeIn = $('online-code-in');
        codeIn.addEventListener('input', () => {
            codeIn.value = codeIn.value.replace(/\D/g, '').slice(0, 4);
            $('online-join').disabled = codeIn.value.length !== 4;
            say('online-code-msg', '');
        });
        codeIn.addEventListener('keydown', (e) => { if (e.key === 'Enter' && codeIn.value.length === 4) $('online-join').click(); });
        $('online-join').addEventListener('click', () => joinRoom(codeIn.value));
        $('online-copy').addEventListener('click', async () => {
            if (!room) return;
            try { await navigator.clipboard.writeText(room.code); $('online-copy').textContent = 'Gekopieerd'; }
            catch (_) { $('online-copy').textContent = room.code; }
            setTimeout(() => { $('online-copy').textContent = 'Code kopiëren'; }, 1600);
        });
        $('online-invite-yes').addEventListener('click', () => answerInvite(true));
        $('online-invite-no').addEventListener('click', () => answerInvite(false));
        $('pause-leave')?.addEventListener('click', (e) => { e.currentTarget.blur(); quitToLobby(); });
        restore();
    }

    // ------------------------------------------------- rooms
    // A room: { code, role: 'host' | 'guest', ch, opp: { id, name }, started,
    //           over, wantAgain: { me, opp }, oppGone, invite }
    function roomChannel(code) {
        return sb.channel('pr-room-' + code, {
            config: { presence: { key: me.id }, broadcast: { self: false, ack: false } },
        });
    }
    function others(ch) {
        return Object.entries(ch.presenceState())
            .filter(([key]) => key !== me.id)
            .map(([key, metas]) => ({ id: key, ...(metas[0] || {}) }));
    }
    // Joins the channel and looks who is in it. Supabase only sends that list
    // once you are in the room yourself, so both sides announce themselves
    // first: a guest goes on as soon as a host shows up, a host when no other
    // host turned up in a moment (two people picked the same code).
    function enter(code, role) {
        return new Promise((resolve) => {
            const ch = roomChannel(code);
            let done = false;
            const finish = (ok) => { if (done) return; done = true; resolve(ok ? ch : (sb.removeChannel(ch), null)); };
            const hostThere = () => others(ch).some(o => o.role === 'host');
            ch.on('presence', { event: 'sync' }, () => {
                if (!done && role === 'guest' && hostThere()) finish(true);
            });
            ch.subscribe(async (status) => {
                if (status === 'SUBSCRIBED') {
                    try { await ch.track({ role, username: me.username }); } catch (_) {}
                    setTimeout(() => {
                        if (!done) finish(role === 'host' ? !hostThere() : hostThere());
                    }, role === 'host' ? 1200 : 4000);
                } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') finish(false);
            });
        });
    }
    function wireRoom(ch) {
        ch.on('broadcast', { event: 'm' }, ({ payload }) => onMessage(payload));
        ch.on('presence', { event: 'leave' }, ({ key }) => {
            if (room && room.ch === ch && room.opp && key === room.opp.id) oppLeft();
        });
    }
    // over the direct connection when it is open (pictures of the pitch on the
    // quick channel that may drop one, the rest on the one that doesn't),
    // through Supabase otherwise
    function send(msg) {
        if (!room) return;
        const dc = msg.t === 's' ? room.fast : room.safe;
        if (dc && dc.readyState === 'open') {
            try { dc.send(JSON.stringify(msg)); return; } catch (_) { /* fall back */ }
        }
        if (room.ch) room.ch.send({ type: 'broadcast', event: 'm', payload: msg }).catch(() => {});
    }
    function direct() {
        return !!(room && room.fast && room.fast.readyState === 'open');
    }

    // ------------------------------------------------- the direct connection
    // The host offers, the guest answers; the offer, the answer and the
    // network candidates go through the room channel. Made once per room.
    function wireDc(dc) {
        dc.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch (_) {} };
        if (dc.label === 'fast') room.fast = dc; else room.safe = dc;
    }
    function newPeer() {
        if (typeof RTCPeerConnection === 'undefined') return null;
        const pc = new RTCPeerConnection({ iceServers: ICE });
        pc.onicecandidate = (e) => { if (e.candidate) send({ t: 'ice', c: e.candidate.toJSON ? e.candidate.toJSON() : e.candidate }); };
        pc.ondatachannel = (e) => { if (room && room.pc === pc) wireDc(e.channel); };
        pc.onconnectionstatechange = () => {
            if (pc.connectionState === 'failed' && room && room.pc === pc) { room.fast = room.safe = null; }
        };
        return pc;
    }
    async function offerPeer() {
        if (!room || room.pc) return;
        const pc = newPeer();
        if (!pc) return;
        room.pc = pc;
        try {
            wireDc(pc.createDataChannel('safe', { ordered: true }));
            wireDc(pc.createDataChannel('fast', { ordered: false, maxRetransmits: 0 }));
            await pc.setLocalDescription(await pc.createOffer());
            send({ t: 'sdp', sdp: { type: pc.localDescription.type, sdp: pc.localDescription.sdp } });
        } catch (_) { /* no direct connection: Supabase carries the match */ }
    }
    async function onSignal(m) {
        if (!room) return;
        try {
            if (m.t === 'sdp' && m.sdp.type === 'offer' && room.role === 'guest') {
                if (room.pc) room.pc.close();
                room.pc = newPeer();
                if (!room.pc) return;
                room.fast = room.safe = null;
                await room.pc.setRemoteDescription(m.sdp);
                (room.iceWait || []).forEach(c => room.pc.addIceCandidate(c).catch(() => {}));
                room.iceWait = [];
                await room.pc.setLocalDescription(await room.pc.createAnswer());
                send({ t: 'sdp', sdp: { type: room.pc.localDescription.type, sdp: room.pc.localDescription.sdp } });
            } else if (m.t === 'sdp' && m.sdp.type === 'answer' && room.role === 'host' && room.pc) {
                await room.pc.setRemoteDescription(m.sdp);
                (room.iceWait || []).forEach(c => room.pc.addIceCandidate(c).catch(() => {}));
                room.iceWait = [];
            } else if (m.t === 'ice') {
                if (room.pc && room.pc.remoteDescription) await room.pc.addIceCandidate(m.c);
                else (room.iceWait = room.iceWait || []).push(m.c);
            }
        } catch (_) { /* stays on Supabase */ }
    }
    function closePeer(r) {
        try { if (r.pc) r.pc.close(); } catch (_) {}
        r.pc = r.fast = r.safe = null;
    }

    async function hostRoom(opts = {}) {
        if (!me) return;
        await leaveRoom();
        $('online-make').disabled = true;
        try {
            await client();
            for (let tries = 0; tries < 6; tries++) {
                const code = String(1000 + Math.floor(Math.random() * 9000));
                const ch = await enter(code, 'host');
                if (!ch) continue;
                room = { code, role: 'host', ch, opp: null, started: false, over: false, wantAgain: { me: false, opp: false },
                         invite: opts.invite || null, kind: opts.kind || 'match', lands: {} };
                wireRoom(ch);
                showWait();
                if (room.invite) sendInvite(room.invite);
                return;
            }
            say('online-code-msg', 'Er ging iets mis bij het maken van een code. Probeer het nog eens.');
        } catch (_) {
            say('online-code-msg', 'Geen verbinding. Ben je online?');
        } finally {
            $('online-make').disabled = false;
        }
    }
    async function joinRoom(code, fromInvite) {
        if (!me || !/^\d{4}$/.test(code)) return;
        await leaveRoom();
        $('online-join').disabled = true;
        say('online-code-msg', fromInvite ? '' : 'Zoeken…', true);
        try {
            await client();
            const ch = await enter(code, 'guest');
            if (!ch) {
                if (fromInvite) { show('friends'); say('online-add-msg', 'Die uitdaging bestaat niet meer.'); }
                else say('online-code-msg', 'Er is geen wedstrijd met deze code.');
                return;
            }
            const there = others(ch);
            const host = there.find(o => o.role === 'host');
            if (there.some(o => o.role === 'guest') || host.id === me.id) {
                sb.removeChannel(ch);
                say('online-code-msg', host.id === me.id ? 'Dat is je eigen code.' : 'Deze wedstrijd is al vol.');
                return;
            }
            room = { code, role: 'guest', ch, opp: { id: host.id, name: host.username }, started: false, over: false,
                     wantAgain: { me: false, opp: false }, kind: 'match', lands: {} };
            wireRoom(ch);
            send({ t: 'hello', id: me.id, name: me.username });
            say('online-code-msg', `Verbonden met ${host.username}. De wedstrijd begint…`, true);
        } catch (_) {
            say('online-code-msg', 'Geen verbinding. Ben je online?');
        } finally {
            $('online-join').disabled = ($('online-code-in').value || '').length !== 4;
        }
    }
    async function leaveRoom() {
        clearTimeout(waitTimer);
        stopWorker();
        if (!room) return;
        const r = room;
        try { send({ t: 'bye' }); } catch (_) {}
        room = null;
        try { r.ch.send({ type: 'broadcast', event: 'm', payload: { t: 'bye' } }); } catch (_) {}
        setTimeout(() => closePeer(r), 200);        // let the bye go out first
        try { await sb.removeChannel(r.ch); } catch (_) {}
        setStatus('menu');
    }

    let waitTimer = 0;
    function showWait() {
        const inv = room.invite;
        $('online-wait-red').textContent = me.username;
        $('online-wait-blue').textContent = inv ? inv.username : '…';
        $('online-wait-blue').classList.add('o-team--wait');
        $('online-wait-title').textContent = inv ? `Wachten op ${inv.username}` : 'Wachten op je vriend';
        const what = `${KINDS[room.kind].label}${room.kind === 'match' ? '' : ' · ' + KINDS[room.kind].meta}. `;
        $('online-wait-lead').textContent = what + (inv
            ? `${inv.username} krijgt je uitdaging nu te zien.`
            : 'Stuur deze code naar je vriend. Die typt hem in bij Online › Spelen met een code.');
        const box = $('online-wait-code');
        box.replaceChildren(...room.code.split('').map(d => el('span', '', d)));
        box.hidden = !!inv;
        $('online-copy').hidden = !!inv;
        show('wait');
        if (inv) {
            waitTimer = setTimeout(() => {
                if (!room || room.started) return;
                $('online-wait-lead').textContent = `${inv.username} reageert niet.`;
                setTimeout(() => { if (room && !room.started) back(); }, 2200);
            }, INVITE_MS + 2000);
        }
    }

    // ------------------------------------------------- challenges
    function challenge(f) {
        if (statusOf(f.id) !== 'on' || room) return;
        pickKind({ invite: f });
    }
    // what do you play: a match, a shoot-out, or a World Cup shoot-out
    function pickKind(target) {
        pending = target;
        $('online-pick-lead').textContent = target.invite ? `Tegen ${target.invite.username}` : 'Met een code';
        show('pick');
    }
    function sendInvite(f) {
        shout('invite', { to: f.id, from: me.id, name: me.username, code: room.code, stadium: getSelectedStadium().name, kind: room.kind });
    }
    function onInvite(p) {
        if (!me || !p || p.to !== me.id) return;
        const friend = friends.find(f => f.id === p.from && f.kind === 'friend');
        if (!friend) return;
        // already in a match or about to start one: say no straight away
        if (room || STATE.screen === 'playing') { shout('answer', { to: p.from, code: p.code, ok: false, busy: true }); return; }
        invite = p;
        $('online-invite-title').textContent = `${p.name} daagt je uit`;
        $('online-invite-sub').textContent =
            p.kind === 'wkpens' ? 'Strafschoppen WK in MetLife Stadium. Jullie kiezen allebei een land.'
            : p.kind === 'pens' ? `Strafschoppen in ${p.stadium}. ${p.name} is rood, jij bent blauw.`
            : `90 seconden in ${p.stadium}. ${p.name} is rood, jij bent blauw.`;
        const bar = $('online-invite-time');
        bar.style.transition = 'none';
        bar.style.width = '100%';
        $('online-invite').hidden = false;
        void bar.offsetWidth;
        bar.style.transition = `width ${INVITE_MS}ms linear`;
        bar.style.width = '0%';
        clearTimeout(onInvite.timer);
        onInvite.timer = setTimeout(() => answerInvite(false, true), INVITE_MS);
        $('online-invite-yes').focus();
    }
    function hideInvite() {
        clearTimeout(onInvite.timer);
        const box = $('online-invite');
        if (box) box.hidden = true;
        invite = null;
    }
    async function answerInvite(ok, timedOut) {
        const p = invite;
        hideInvite();
        if (!p) return;
        if (!timedOut) shout('answer', { to: p.from, code: p.code, ok });
        if (!ok) return;
        if (STATE.screen !== 'online') gotoScreen('online');
        show('code');
        say('online-code-msg', `Verbinden met ${p.name}…`, true);
        joinRoom(p.code, true);
    }
    function onAnswer(p) {
        if (!me || !p || p.to !== me.id || !room || room.code !== p.code || room.started || p.ok) return;
        const who = room.invite ? room.invite.username : 'Je vriend';
        $('online-wait-lead').textContent = p.busy ? `${who} is al bezig met een wedstrijd.` : `${who} wil nu niet spelen.`;
        clearTimeout(waitTimer);
        setTimeout(() => { if (room && !room.started) back(); }, 2200);
    }

    // ------------------------------------------------- messages
    function onMessage(m) {
        if (!room || !m) return;
        switch (m.t) {
            case 'hello':                                  // host: a guest came in
                if (room.role !== 'host' || (room.opp && room.opp.id !== m.id)) return;
                if (room.started && !room.over) return;
                room.opp = { id: m.id, name: m.name };
                lastInSeq = 0;                             // a new guest counts from the start
                kickOff();
                break;
            case 'start':                                  // guest: the host starts a match
                if (room.role !== 'guest') return;
                beginMatch(m);
                break;
            case 'lands':                                  // guest: a World Cup shoot-out, pick a country
                if (room.role !== 'guest') return;
                room.kind = 'wkpens';
                showLands();
                break;
            case 'land': takeLand(m); break;
            case 'pkc': if (room.role === 'host' && typeof PENS !== 'undefined') PENS.netChoice(m); break;
            case 'pko': if (room.role === 'guest' && typeof PENS !== 'undefined') PENS.netOutcome(m); break;
            case 'sdp':
            case 'ice': onSignal(m); break;
            case 'in':  if (room.role === 'host') takeInput(m); break;
            case 's':   if (room.role === 'guest') takeSnap(m); break;
            case 'goal': if (room.role === 'guest') guestGoal(m); break;
            case 'end': if (room.role === 'guest') guestEnd(m); break;
            case 'again':
                room.wantAgain.opp = true;
                paintAgain();
                if (room.role === 'host' && room.wantAgain.me) kickOff();
                break;
            case 'bye': oppLeft(); break;
        }
    }

    // host: pick who kicks off and the stadium, start both sides
    function kickOff() {
        const kind = room.kind || 'match';
        // a World Cup shoot-out: first both pick a country
        if (kind === 'wkpens' && !(room.lands.host && room.lands.guest)) {
            send({ t: 'lands' });
            if (room.lands.host) send({ t: 'land', role: 'host', code: room.lands.host });
            showLands();
            return;
        }
        const start = {
            t: 'start',
            kind,
            stadium: kind === 'wkpens' ? 'metlife' : getSelectedStadium().id,
            kick: Math.random() < 0.5 ? 1 : 2,
            turn: Math.random() < 0.5 ? 1 : 2,
            host: { id: me.id, name: me.username },
            red: room.lands.host || null,
            blue: room.lands.guest || null,
        };
        send(start);
        beginMatch(start);
        offerPeer();
    }

    // ------------------------------------------------- World Cup: pick your country
    function landName(code) { return WK_TEAMS[code] ? WK_TEAMS[code].name : code; }
    function showLands() {
        const mine = room.lands[room.role];
        const theirs = room.lands[room.role === 'host' ? 'guest' : 'host'];
        const opp = room.opp ? room.opp.name : 'je vriend';
        $('online-land-lead').textContent = mine && theirs ? 'De strafschoppen beginnen…'
            : mine ? `Je speelt met ${landName(mine)}. Wachten tot ${opp} een land kiest…`
            : theirs ? `${opp} speelt met ${landName(theirs)}. Kies jouw land.`
            : `Strafschoppen in MetLife Stadium. ${opp} kiest ook een land.`;
        const grid = $('online-land-grid');
        const codes = Object.keys(WK_TEAMS).sort((a, b) => landName(a).localeCompare(landName(b), 'nl'));
        grid.replaceChildren(...codes.map(code => {
            const b = el('button', 'o-land');
            b.type = 'button';
            const img = el('img', 'o-land__flag');
            img.src = wkFlagSrc(code);
            img.alt = '';
            img.width = 36; img.height = 24;
            b.append(img, el('span', 'o-land__name', landName(code)));
            if (code === theirs) { b.disabled = true; b.append(el('span', 'o-land__who', opp)); }
            if (code === mine) b.classList.add('is-mine');
            b.addEventListener('click', () => pickLand(code));
            return b;
        }));
        if (view !== 'land') show('land');
    }
    function pickLand(code) {
        if (!room || room.started) return;
        const other = room.lands[room.role === 'host' ? 'guest' : 'host'];
        if (code === other) return;
        room.lands[room.role] = code;
        send({ t: 'land', role: room.role, code });
        showLands();
        if (room.role === 'host' && room.lands.guest) kickOff();
    }
    function takeLand(m) {
        if (!WK_TEAMS[m.code] || m.role === room.role) return;
        // both picked the same one at once: the host keeps it
        if (room.role === 'host' && m.code === room.lands.host) {
            send({ t: 'land', role: 'host', code: room.lands.host });
            return;
        }
        if (room.role === 'guest' && m.code === room.lands.guest) room.lands.guest = null;
        room.lands[m.role] = m.code;
        showLands();
        if (room.role === 'host' && room.lands.host && room.lands.guest) kickOff();
    }

    function beginMatch(start) {
        hideInvite();
        clearTimeout(waitTimer);
        if (room.role === 'guest') room.opp = { id: start.host.id, name: start.host.name };
        if (!saved) saved = { mode: STATE.mode, p1: { ...STATE.p1 }, p2: { ...STATE.p2 } };
        const host = room.role === 'host';
        room.started = true;
        room.over = false;
        room.wantAgain = { me: false, opp: false };
        STATE.mode = 'online';
        STATE.onlineRole = room.role;
        STATE.onlineStadium = start.stadium;
        STATE.wkStarting = false;
        STATE.p1 = { name: me.username, team: host ? 1 : 2 };
        STATE.p2 = { name: room.opp.name, team: host ? 2 : 1 };
        STATE.kickoffTeam = start.kick;
        STATE.gameDuration = 90;
        STATE.score1 = 0;
        STATE.score2 = 0;
        STATE.onlineElapsed = 0;
        resetNet();
        setStatus('playing');
        if (overTitle !== null) $('over-screen').querySelector('.title').textContent = overTitle;
        if (isPens(start.kind)) { beginPens(start); return; }
        if (host) startWorker();
        startGame();
        $('game-screen').classList.add('is-online');
    }

    // straight to the penalty spot
    function beginPens(start) {
        const host = room.role === 'host';
        room.kind = start.kind;
        if (start.kind === 'wkpens') {
            room.lands = { host: start.red, guest: start.blue };
            STATE.wkMatch = { me: start.red, opp: start.blue, online: true };
            STATE.wkStarting = true;
        } else {
            STATE.wkMatch = null;
            STATE.wkStarting = false;
        }
        startShootout({ me: host ? 1 : 2, turn: start.turn, net: { host, send }, onDone: pensDone });
        STATE.wkStarting = false;
        $('game-screen').classList.add('is-online');
    }
    // the shoot-out is over, on both sides: the result screen, and the host keeps it
    function pensDone(score) {
        if (!room) return;
        room.over = true;
        setStatus('menu');
        const m = STATE.wkMatch;
        const nameOf = (team) => m ? landName(team === 1 ? m.me : m.opp) : (STATE.p1.team === team ? STATE.p1 : STATE.p2).name;
        STATE.score1 = score[0];
        STATE.score2 = score[1];
        const title = $('over-screen').querySelector('.title');
        if (overTitle === null) overTitle = title.textContent;
        title.textContent = 'Strafschoppen';
        $('over-p1-name').textContent = nameOf(1);
        $('over-p2-name').textContent = nameOf(2);
        $('over-s1').textContent = score[0];
        $('over-s2').textContent = score[1];
        $('over-winner').textContent = `${nameOf(score[0] > score[1] ? 1 : 2)} wint de strafschoppen`;
        $('over-stats').replaceChildren();
        $('play-again').hidden = false;
        $('back-home').hidden = false;
        $('wk-continue').hidden = true;
        if (room.role === 'host' && room.opp) {
            sb.from('matches').insert({ red: me.id, blue: room.opp.id, score_red: score[0], score_blue: score[1] })
                .then(() => loadFriends(), () => {});
        } else setTimeout(loadFriends, 1500);
        gotoScreen('over');
        paintAgain();
    }

    // puts the local game back the way it was before online play
    function restoreLocal() {
        if (!saved) return;
        STATE.mode = saved.mode;
        STATE.p1 = saved.p1;
        STATE.p2 = saved.p2;
        saved = null;
        STATE.onlineRole = null;
        STATE.onlineStadium = null;
        // a World Cup shoot-out left its kits and colours: back to red and blue
        STATE.wkMatch = null;
        STATE.wkStarting = false;
        if (typeof wkApply === 'function') wkApply();
        if (overTitle !== null) { $('over-screen').querySelector('.title').textContent = overTitle; overTitle = null; }
        $('game-screen')?.classList.remove('is-online');
        const again = $('play-again');
        if (again) { again.disabled = false; again.textContent = 'Revanche'; }
        overlay(null);
    }

    async function quitToLobby() {
        await leaveRoom();
        if (STATE.screen === 'playing' || STATE.screen === 'over') {
            gotoScreen('online', { replace: true });       // ends the match (teardownGame)
            STATE.score1 = 0; STATE.score2 = 0;
        }
        restoreLocal();
        if (STATE.screen === 'online') show(me ? 'friends' : 'login');
    }

    function oppLeft() {
        if (!room || room.oppGone) return;
        const name = room.opp ? room.opp.name : 'Je tegenstander';
        if (!room.started) {
            if (view === 'land') {
                // gone while picking a country
                $('online-land-lead').textContent = `${name} is weg.`;
                setTimeout(() => { if (room && !room.started && view === 'land') back(); }, 2000);
                return;
            }
            // the guest left before kick-off: wait for the next one
            room.opp = null;
            return;
        }
        room.oppGone = true;
        if (STATE.screen === 'playing' && !room.over) {
            STATE.paused = true;
            STATE.inputLocked = true;
            overlay('gone', name);
        } else if (STATE.screen === 'over') {
            const again = $('play-again');
            if (again) { again.disabled = true; again.textContent = `${name} is weg`; }
        }
    }

    // the pause panel, used online for "leave the match?" and "your opponent left"
    let pauseText = null;
    function overlay(kind, name) {
        const box = $('pause-overlay');
        if (!box) return;
        const title = box.querySelector('.pause-overlay__title');
        const sub = box.querySelector('.pause-overlay__sub');
        const resume = $('pause-resume');
        const leave = $('pause-leave');
        if (!pauseText) pauseText = { title: title.innerHTML, sub: sub.innerHTML };
        if (!kind) {
            title.innerHTML = pauseText.title;
            sub.innerHTML = pauseText.sub;
            sub.classList.remove('is-shown');
            resume.hidden = false;
            if (leave) leave.hidden = true;
            box.hidden = !STATE.paused;
            return;
        }
        if (kind === 'menu') {
            title.textContent = 'De wedstrijd loopt door';
            sub.textContent = 'Online kun je niet pauzeren.';
            resume.hidden = false;
            leave.textContent = 'Wedstrijd verlaten';
        } else {
            title.textContent = `${name} is weg`;
            sub.textContent = 'De verbinding met je tegenstander is verbroken.';
            resume.hidden = true;
            leave.textContent = 'Naar het menu';
        }
        sub.classList.add('is-shown');
        leave.hidden = false;
        box.hidden = false;
    }
    // the pause button and P / Esc during an online match
    function togglePanel(force) {
        if (room && room.oppGone) return;
        const box = $('pause-overlay');
        const want = force === undefined ? box.hidden : !!force;
        if (want) overlay('menu');
        else overlay(null);
    }

    // ------------------------------------------------- the match: host side
    // The guest's keys live here, under codes of their own (R_up ...), and are
    // written into the game's keys before every tick. A key that went down and
    // up between two ticks still counts for one tick.
    const R_BITS = [['R_up', 1], ['R_down', 2], ['R_left', 4], ['R_right', 8], ['R_sprint', 16], ['R_shoot', 32], ['R_pass', 64], ['R_high', 128]];
    const rDown = {}, rFresh = {}, rUpLater = {}, rEdge = {};
    let tickNo = 0;
    let lastGuestIn = 0;

    function resetNet() {
        R_BITS.forEach(([c]) => { rDown[c] = rFresh[c] = rUpLater[c] = rEdge[c] = false; keys[c] = false; });
        tickNo = 0;
        snaps.length = 0;
        clockOff = null;
        lastSnapAt = 0;
        lastSig = '';
        lastSent = 0;
        highUntil = 0;
        lastGuestIn = 0;
    }
    let lastInSeq = 0;
    function takeInput(m) {
        // the two ways can overtake each other: an older state of the keys is ignored
        if (m.q) { if (m.q <= lastInSeq) return; lastInSeq = m.q; }
        lastGuestIn = performance.now();
        const b = m.b | 0;
        R_BITS.forEach(([c, bit]) => {
            const down = !!(b & bit);
            if (down && !rDown[c]) { rDown[c] = true; rFresh[c] = true; rEdge[c] = true; rUpLater[c] = false; }
            else if (!down && rDown[c]) { if (rFresh[c]) rUpLater[c] = true; else rDown[c] = false; }
            else if (down) rUpLater[c] = false;
        });
        if (controlledP2) {
            controlledP2.userData.remoteStick = m.s ? { active: true, x: +m.x || 0, z: +m.z || 0 } : null;
        }
    }
    // one game tick on the host, in place of gameTick()
    function step() {
        R_BITS.forEach(([c]) => {
            keys[c] = rDown[c];
            if (rEdge[c]) { keysPressed[c] = true; rEdge[c] = false; }
        });
        gameTick();
        R_BITS.forEach(([c]) => {
            rFresh[c] = false;
            if (rUpLater[c]) { rDown[c] = false; rUpLater[c] = false; }
        });
        tickNo++;
        if (tickNo % (direct() ? SNAP_EVERY_P2P : SNAP_EVERY) === 0) send(snapshot());
    }
    const r2 = (v) => Math.round(v * 100) / 100;
    function snapshot() {
        const all = [...team1Players, ...team2Players];
        const now = performance.now();
        return {
            t: 's',
            n: tickNo,
            p: all.map(p => {
                const u = p.userData;
                let fx = 0;
                if (u.kickT > 0.12) fx |= 1;
                if (u.callT > 0.35) fx |= 2;
                if (u.tackleT > 0 || u.getUpT > 0) fx |= 4;
                if (u.diveT > 0.3) fx |= 8;
                if (u.tired) fx |= 16;
                return [r2(p.position.x), r2(p.position.z), fx, Math.round((u.stamina ?? 1) * 100),
                    u.charging ? Math.round(now - (u.chargeStart || now)) : -1, r2(u.diveX || 0), r2(u.diveZ || 0)];
            }),
            b: [r2(ball.position.x), r2(ball.position.y), r2(ball.position.z)],
            c: carrier ? all.indexOf(carrier) : -1,
            s: [STATE.score1, STATE.score2],
            e: STATE.gameStartTime ? Math.floor((Date.now() - STATE.gameStartTime) / 1000) : 0,
            k: STATE.inputLocked ? 1 : 0,
        };
    }
    function hostGoal(team) {
        if (!room || room.role !== 'host') return;
        send(snapshot());
        send({ t: 'goal', team, s: [STATE.score1, STATE.score2] });
    }
    // full time, on both sides: the host tells the guest and keeps the result
    function onEnd() {
        if (!room) return;
        room.over = true;
        stopWorker();
        setStatus('menu');
        if (room.role === 'host') {
            send({ t: 'end', s: [STATE.score1, STATE.score2], match: MATCH });
            if (room.opp) {
                sb.from('matches').insert({ red: me.id, blue: room.opp.id, score_red: STATE.score1, score_blue: STATE.score2 })
                    .then(() => loadFriends(), () => {});
            }
        } else {
            setTimeout(loadFriends, 1500);      // the host writes the result
        }
        setTimeout(paintAgain, 0);
    }
    function wantAgain() {
        if (!room || room.oppGone) return;
        room.wantAgain.me = true;
        send({ t: 'again' });
        paintAgain();
        if (room.role === 'host' && room.wantAgain.opp) kickOff();
    }
    function paintAgain() {
        const again = $('play-again');
        if (!again || !room) return;
        const name = room.opp ? room.opp.name : 'je tegenstander';
        if (room.oppGone) { again.disabled = true; again.textContent = `${name} is weg`; return; }
        if (room.wantAgain.me) { again.disabled = true; again.textContent = `Wachten op ${name}`; return; }
        again.disabled = false;
        again.textContent = room.wantAgain.opp ? `Revanche: ${name} wil ook` : 'Revanche';
    }

    // The host keeps playing in a background tab: requestAnimationFrame stops
    // there, so a worker's timer (which browsers don't slow down) drives the ticks.
    let worker = null;
    function startWorker() {
        if (worker) return;
        try {
            const src = 'setInterval(function(){postMessage(0)},16)';
            worker = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
            worker.onmessage = backgroundStep;
        } catch (_) { worker = null; }
    }
    function stopWorker() {
        if (worker) { worker.terminate(); worker = null; }
    }
    function backgroundStep() {
        if (!document.hidden || !room || room.role !== 'host' || STATE.screen !== 'playing') return;
        const now = performance.now();
        let dt = (now - lastFrameTime) / 1000;
        if (!Number.isFinite(dt) || dt <= 0) dt = PHYSICS_STEP;
        if (dt > 0.25) dt = 0.25;
        lastFrameTime = now;
        if (!STATE.paused) {
            physicsAccum += dt;
            let safety = 5;
            while (physicsAccum >= PHYSICS_STEP && safety-- > 0) { physicsAccum -= PHYSICS_STEP; step(); }
            if (safety <= 0) physicsAccum = 0;
            animatePlayers(dt);
        }
        updateTimer();
    }

    // ------------------------------------------------- the match: guest side
    const snaps = [];              // { at: host ms, m }
    let clockOff = null;           // local ms minus host ms, about the travel time
    let lastSnapAt = 0;
    let lastSig = '', lastSent = 0, highUntil = 0, inSeq = 0;
    let lastBallX = 0, lastBallZ = 0;

    function takeSnap(m) {
        const now = performance.now();
        const hostMs = m.n * 1000 / 60;
        const est = now - hostMs;
        // follow the quickest arrival; drift up slowly if the connection gets slower
        clockOff = clockOff === null || est < clockOff ? est : clockOff + (est - clockOff) * 0.02;
        if (snaps.length && hostMs <= snaps[snaps.length - 1].at) return;   // came in late over the quick channel
        snaps.push({ at: hostMs, m });
        if (snaps.length > 40) snaps.shift();
        lastSnapAt = now;
        if (STATE.score1 !== m.s[0] || STATE.score2 !== m.s[1]) {
            STATE.score1 = m.s[0];
            STATE.score2 = m.s[1];
            $('hud-s1').textContent = STATE.score1;
            $('hud-s2').textContent = STATE.score2;
        }
        STATE.onlineElapsed = m.e;
    }
    function guestGoal(m) {
        STATE.score1 = m.s[0];
        STATE.score2 = m.s[1];
        $('hud-s1').textContent = STATE.score1;
        $('hud-s2').textContent = STATE.score2;
        showGoalFlash(m.team);
    }
    function guestEnd(m) {
        STATE.score1 = m.s[0];
        STATE.score2 = m.s[1];
        if (m.match) ['poss', 'shots', 'onTarget', 'passes'].forEach(k => { if (Array.isArray(m.match[k])) MATCH[k] = m.match[k].slice(0, 2); });
        if (STATE.screen === 'playing') endGame();
    }

    const lerp = (a, b, k) => a + (b - a) * k;
    // every frame on the guest, in place of the game ticks
    function guestFrame() {
        sendInput();
        const now = performance.now();
        if (lastSnapAt && now - lastSnapAt > SILENT_MS && !room.over) { oppLeft(); return; }
        if (!snaps.length || clockOff === null) return;
        const t = now - clockOff - (direct() ? INTERP_MS_P2P : INTERP_MS);
        let i = snaps.length - 1;
        while (i > 0 && snaps[i].at > t) i--;
        const a = snaps[i];
        const b = snaps[i + 1] || a;
        const k = b === a ? 0 : Math.max(0, Math.min(1, (t - a.at) / (b.at - a.at)));
        if (i > 2) snaps.splice(0, i - 1);

        const all = [...team1Players, ...team2Players];
        const now2 = performance.now();
        all.forEach((p, j) => {
            const pa = a.m.p[j], pb = b.m.p[j];
            if (!pa || !pb) return;
            const jump = Math.hypot(pb[0] - pa[0], pb[1] - pa[1]) > 12;
            p.position.x = jump ? pb[0] : lerp(pa[0], pb[0], k);
            p.position.z = jump ? pb[1] : lerp(pa[1], pb[1], k);
            const u = p.userData;
            const fx = pb[2];
            if (fx & 1) { if (!u.kickSeen) { u.kickT = 0.28; u.kickSeen = true; } } else u.kickSeen = false;
            if (fx & 2) { if (!u.callSeen) { u.callT = 0.7; u.callSeen = true; } } else u.callSeen = false;
            u.tackleT = fx & 4 ? 1 : 0;
            u.getUpT = 0;
            if (fx & 8) { if (!u.diveSeen) { u.diveT = 0.6; u.diveX = pb[5]; u.diveZ = pb[6]; u.diveSeen = true; } } else u.diveSeen = false;
            u.stamina = pb[3] / 100;
            u.tired = !!(fx & 16);
            u.charging = pb[4] >= 0;
            if (u.charging) u.chargeStart = now2 - pb[4];
        });
        const ba = a.m.b, bb = b.m.b;
        const jump = Math.hypot(bb[0] - ba[0], bb[2] - ba[2]) > 15;
        ball.position.set(jump ? bb[0] : lerp(ba[0], bb[0], k), jump ? bb[1] : lerp(ba[1], bb[1], k), jump ? bb[2] : lerp(ba[2], bb[2], k));
        // let it roll
        const mesh = ball.userData.mesh;
        const dx = ball.position.x - lastBallX, dz = ball.position.z - lastBallZ;
        if (mesh && Math.hypot(dx, dz) < 5) { mesh.rotation.x += dz * 0.16; mesh.rotation.z -= dx * 0.16; }
        lastBallX = ball.position.x;
        lastBallZ = ball.position.z;
        carrier = b.m.c >= 0 ? all[b.m.c] || null : null;
        STATE.inputLocked = !!b.m.k;
    }

    // the guest's keys and stick, sent whenever they change
    function sendInput() {
        const now = performance.now();
        const on = (c) => !!(keys[c] || keysPressed[c]);
        let b = 0;
        if (on('KeyW') || on('ArrowUp')) b |= 1;
        if (on('KeyS') || on('ArrowDown')) b |= 2;
        if (on('KeyA') || on('ArrowLeft')) b |= 4;
        if (on('KeyD') || on('ArrowRight')) b |= 8;
        if (on('ShiftLeft') || on('ShiftRight')) b |= 16;
        if (on('Space') || on('Enter')) b |= 32;
        if (on('KeyQ')) b |= 64;
        for (const c in keysPressed) keysPressed[c] = false;
        // a swipe up as Schiet was let go: a high shot. Held a moment, so the
        // host still has it when the release arrives
        if (typeof touchShotHigh !== 'undefined' && touchShotHigh) { highUntil = now + 250; touchShotHigh = false; }
        if ((b & 1) || now < highUntil) b |= 128;
        const stick = typeof touchMove !== 'undefined' && touchMove.active;
        const x = stick ? Math.round(touchMove.x * 10) / 10 : 0;
        const z = stick ? Math.round(touchMove.z * 10) / 10 : 0;
        const sig = `${b}|${stick ? x + ',' + z : ''}`;
        if (sig === lastSig && now - lastSent < 1000) return;      // and once a second regardless
        const keysChanged = sig.split('|')[0] !== lastSig.split('|')[0];
        if (!keysChanged && now - lastSent < 60) return;           // the stick at most 15 times a second
        lastSig = sig;
        lastSent = now;
        inSeq++;
        send(stick ? { t: 'in', q: inSeq, b, s: 1, x, z } : { t: 'in', q: inSeq, b });
    }

    // ------------------------------------------------- public
    document.addEventListener('DOMContentLoaded', () => { if (!QUICK_MODE) bind(); });

    return {
        enabled: () => ENABLED,
        isHost: () => !!room && room.role === 'host' && STATE.mode === 'online',
        isGuest: () => !!room && room.role === 'guest' && STATE.mode === 'online',
        open,
        step,
        guestFrame,
        hostGoal,
        onEnd,
        wantAgain,
        quitToLobby,
        togglePanel,
        // a match left some other way (the browser's back button): leave the room too
        onTeardown() {
            if (room && !room.over) {
                leaveRoom();
                restoreLocal();
                setTimeout(() => { if (STATE.screen === 'online') show(me ? 'friends' : 'login'); }, 0);
            }
        },
        onScreen(target) {
            // back in the menus after a match: the room is done
            if (room && room.started && target !== 'playing' && target !== 'over') { leaveRoom(); restoreLocal(); }
        },
    };
})();

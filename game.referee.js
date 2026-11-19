// =====================================================
// PITCH ROYALE — the officials
// A referee and two assistant referees on the pitch; offside, fouls and
// handball; yellow and red cards; free kicks and penalties; and the VAR: a
// check, a review at the pitchside monitor and a slow-motion replay with the
// lines on the grass.
//
// It runs on the side that plays the match (on your own, or the host online).
// The online guest only shows what the host sends (snap / applySnap): the
// officials, the calls on screen and the replay (the players' positions in
// the replay come with the normal snapshot).
//
// The match calls in from game.js:
//   onPass(from, to, kind)       a pass: who of that side stands offside
//   onReceive(p)                 p gets the ball: offside if he stood there
//   onChallenge(by, on, slide)   the ball won off a man (a steal or a slide): a foul?
//   onBlock(p, touchedBefore)    the ball hits a player: handball?
//   onGoal(team)                 a goal: the VAR checks a tight offside before it
// and gameTick() hands over to tick() while play is stopped (stopped()).
// =====================================================

const REF = (() => {
    const TICK_MS = 1000 / 60;
    const OFFSIDE_WAIT = 180;        // the three seconds between the flag and the free kick
    const FOUL_WAIT = 80;
    const CHECK_TICKS = 100;
    const DECIDE_TICKS = 130;
    const CARD_SHOW = 95;
    const GOAL_WAIT = 100;           // the goal is celebrated for a moment before the VAR looks at it
    const FREE_GAP = 17;             // 9.15 metres, in pitch units
    const BUFFER_TICKS = 600;        // ten seconds of the match, for the replay
    const AR_OUT = FIELD_L / 2 + 2.6;  // the assistants run just outside the touchlines
    const MONITOR = { x: 0, z: -(FIELD_L / 2 + 7) };

    let officials = null;            // { ref, arR, arL }
    let monitor = null;
    let fx = null;                   // the replay's lines and ring on the grass
    let inc = null;                  // the stoppage: what happened and where it is in its steps
    let pending = null;              // the last pass: who of that side stood offside when it was played
    let watch = null;                // a tight one the assistant let go: the VAR looks at it if a goal follows
    let buffer = [];
    let lineCache = { t: -1 };
    let incId = 0;
    let removed = [];                // pids of the players sent off
    let view = null;                 // what the screens show (the host builds it, the guest receives it)
    let shown = '';                  // what the HUD shows now, so it is only touched on a change
    let heard = '';                  // the last whistle blown
    let cutFor = '';
    let forced = null;               // the test page (var-test.html): how the next call goes                 // the stoppage the screen last dipped for (guest)

    const all = () => [...team1Players, ...team2Players];
    const sideOf = (team) => (team === 1 ? team1Players : team2Players);
    const dirOf = (team) => (team === 1 ? 1 : -1);              // the way a side attacks
    const clampTo = (v, lim) => Math.max(-lim, Math.min(lim, v));
    const isHuman = (p) => p === controlledP1 || p === controlledP2;
    const codeOf = (team) => {
        const c = typeof hudCodes === 'function' ? hudCodes() : { red: 'ROOD', blue: 'BLAUW' };
        return team === 1 ? c.red : c.blue;
    };
    const labelOf = (p) => {
        if (!p) return '';
        const u = p.userData;
        if (u.star && u.star.back) return u.star.back;
        const n = typeof ROLE_NUMBER !== 'undefined' ? ROLE_NUMBER[u.isKeeper ? 'keeper' : u.role] : 0;
        return n ? `Nr. ${n}` : '';
    };
    const byPid = (pid) => all().find(p => p.userData.pid === pid) || null;

    // ------------------------------------------------ the officials
    function kitUp() {
        // black, with the white trim makeFootballer gives a dark shirt
        if (!KIT[3]) KIT[3] = { shirt: 0x17181b, shorts: 0x17181b, socks: 0x17181b, keeper: 0x17181b };
    }
    function makeOfficial(seed, flag) {
        kitUp();
        const look = {
            skin: SKIN_TONES[seed % SKIN_TONES.length], hair: HAIR_TONES[(seed * 3) % HAIR_TONES.length],
            cut: seed % 2 ? 'buzz' : 'short', beard: seed === 2, boots: 0x141414, number: 0, back: '',
        };
        const o = makeFootballer(3, false, look);
        const u = o.userData;
        u.isOfficial = true;
        u.stride = 0;
        u.vx = 0; u.vz = 0;
        const arm = u.rig.armR;
        // the card in his right hand, shown above his head
        const card = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.72),
            new THREE.MeshBasicMaterial({ color: srgb(0xffd60a), side: THREE.DoubleSide }));
        card.position.set(0, -2.55, 0.12);
        card.visible = false;
        arm.add(card);
        u.card = card;
        if (flag) {
            // the assistant's flag: a stick on from his hand, yellow and red cloth
            const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 2.3, 6), litMat(0x2a2a2a));
            stick.position.set(0, -3.2, 0.05);
            arm.add(stick);
            const half = (hex, x) => {
                const m = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.78), new THREE.MeshBasicMaterial({ color: srgb(hex), side: THREE.DoubleSide }));
                m.position.set(x, -3.95, 0.05);
                m.rotation.y = Math.PI / 2;
                arm.add(m);
            };
            half(0xffd60a, 0);
            const red = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.78), new THREE.MeshBasicMaterial({ color: srgb(0xe0203a), side: THREE.DoubleSide }));
            red.position.set(0, -3.95, 0.47);
            red.rotation.y = Math.PI / 2;
            arm.add(red);
        }
        return o;
    }
    function makeMonitor() {
        const g = new THREE.Group();
        const dark = litMat(0x1b1d22);
        const post = new THREE.Mesh(new THREE.BoxGeometry(0.35, 4.2, 0.35), dark);
        post.position.y = 2.1;
        g.add(post);
        const foot = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.2, 1.4), dark);
        foot.position.y = 0.1;
        g.add(foot);
        const box = new THREE.Mesh(new THREE.BoxGeometry(3.6, 2.4, 0.3), dark);
        box.position.y = 5.1;
        g.add(box);
        // the screen: VAR on it, as the referee walks up
        let map = null;
        try {
            const c = document.createElement('canvas');
            c.width = 256; c.height = 160;
            const x = c.getContext('2d');
            x.fillStyle = '#0d1a6e'; x.fillRect(0, 0, 256, 160);
            x.fillStyle = '#ffffff'; x.font = '800 86px "Barlow Condensed", Arial Narrow, sans-serif';
            x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('VAR', 128, 84);
            map = new THREE.CanvasTexture(c);
        } catch (_) {}
        const screen = new THREE.Mesh(new THREE.PlaneGeometry(3.3, 2.1), new THREE.MeshBasicMaterial(map ? { map } : { color: srgb(0x0d1a6e) }));
        screen.position.set(0, 5.1, 0.16);
        g.add(screen);
        g.position.set(MONITOR.x, 0, MONITOR.z);
        return g;
    }
    function makeFx() {
        const flat = (w, l, hex) => {
            const m = new THREE.Mesh(new THREE.PlaneGeometry(w, l),
                new THREE.MeshBasicMaterial({ color: srgb(hex), transparent: true, opacity: 0.95, depthWrite: false, depthTest: false, side: THREE.DoubleSide }));
            m.rotation.x = -Math.PI / 2;
            m.position.y = 0.12;
            m.renderOrder = 20;
            m.visible = false;
            scene.add(m);
            return m;
        };
        const ring = new THREE.Group();
        const mat = (c) => new THREE.MeshBasicMaterial({ color: srgb(c), transparent: true, side: THREE.DoubleSide, depthWrite: false, depthTest: false });
        [[new THREE.RingGeometry(3.4, 5.4, 48), 0x121512], [new THREE.RingGeometry(3.8, 5.0, 48), 0xffd60a]].forEach(([geo, c], i) => {
            const m = new THREE.Mesh(geo, mat(c));
            m.rotation.x = -Math.PI / 2;
            m.renderOrder = 21 + i;
            ring.add(m);
        });
        ring.position.y = 0.1;
        ring.visible = false;
        scene.add(ring);
        return { atk: flat(0.55, FIELD_L, 0xe0203a), def: flat(0.55, FIELD_L, 0x1f5dff), ring };
    }

    function build() {
        reset();
        if (typeof scene === 'undefined' || !scene) return;
        officials = { ref: makeOfficial(1, false), arR: makeOfficial(3, true), arL: makeOfficial(2, true) };
        officials.ref.position.set(-12, 0, -16);
        officials.arR.position.set(0, 0, AR_OUT);
        officials.arL.position.set(0, 0, -AR_OUT);
        officials.arR.userData.ar = 1;
        officials.arL.userData.ar = -1;
        Object.values(officials).forEach(o => scene.add(o));
        monitor = makeMonitor();
        scene.add(monitor);
        fx = makeFx();
        // every player a fixed number, the same on both sides of an online match
        all().forEach((p, i) => { p.userData.pid = i; p.userData.yellows = 0; });
    }
    function reset() {
        inc = null; pending = null; watch = null; buffer = []; removed = []; view = null;
        lineCache = { t: -1 };
        shown = ''; heard = '';
        paint(null);
    }

    // ------------------------------------------------ offside
    // the x (in the defending side's own direction) of its second-last man,
    // keeper included: the offside line for the other side
    function secondLast(defTeam) {
        const g = -dirOf(defTeam);                     // towards the defenders' own goal
        const xs = sideOf(defTeam).map(p => p.position.x * g).sort((a, b) => b - a);
        return xs.length > 1 ? xs[1] : FIELD_W / 2;
    }
    // the offside line for the attacking side `team`, in its own direction
    function lineFor(team) {
        if (lineCache.t !== aiTick) lineCache = { t: aiTick, 1: secondLast(2), 2: secondLast(1) };
        return lineCache[team];
    }
    // how far a player stands offside right now (> 0: offside), against the ball at bx
    function marginOf(p, bx) {
        const g = dirOf(p.team), a = p.position.x * g;
        if (a <= 0) return -Infinity;                  // in his own half: never
        const ball_ = (bx ?? ball.position.x) * g;
        if (a <= ball_) return -Infinity;              // level with or behind the ball
        return a - lineFor(p.team);
    }
    function isOffside(p) {
        return !p.userData.isKeeper && marginOf(p) > 0.4;
    }

    function onPass(from, to, kind) {
        if (!from || from.userData.isKeeper) { pending = null; return; }
        lineCache.t = -1;
        const g = dirOf(from.team);
        const offenders = new Map();
        sideOf(from.team).forEach((m) => {
            if (m === from || m.userData.isKeeper) return;
            const margin = marginOf(m, from.position.x);
            if (margin > -1.8) offenders.set(m, {
                margin, x: m.position.x, z: m.position.z,
                atkX: m.position.x, defX: lineFor(from.team) * g, tick: aiTick,
            });
        });
        pending = { team: from.team, offenders, until: aiTick + 260, kind, byHuman: isHuman(from) };
    }
    // returns true when the flag goes up and play stops
    function onReceive(p) {
        if (!pending || inc) return false;
        if (aiTick > pending.until || p.team !== pending.team) { pending = null; return false; }
        const o = pending.offenders.get(p);
        const byHuman = pending.byHuman;
        const f = forced && forced.kind === 'offside' ? forced : null;
        if (f) forced = null;
        pending = null;
        if (!o) return false;
        if (o.margin > 0.4) {
            // the assistant sees most, not all: the tight ones now and then get through
            const seen = f && 'seen' in f ? f.seen : o.margin > 2.6 || Math.random() < 0.5 + o.margin * 0.16;
            if (seen) { callOffside(p, o, byHuman); return true; }
            if (!watch || !watch.offside) watch = Object.assign({ team: p.team, pid: p.userData.pid, offside: true, until: aiTick + 600 }, o);
        } else if (!watch) {
            // onside, but only just: the VAR looks if this ends in a goal
            watch = Object.assign({ team: p.team, pid: p.userData.pid, offside: false, until: aiTick + 600 }, o);
        }
        return false;
    }
    function callOffside(p, o, byHuman) {
        MATCH.offsides[p.team - 1]++;
        stopBall();
        start({
            kind: 'offside', team: p.team, x: o.x, z: o.z, offender: p, byHuman, margin: o.margin,
            ar: o.x > 0 ? 'arR' : 'arL',
            restart: { kind: 'free', team: 3 - p.team, x: o.x, z: o.z },
        }, 'whistle');
    }

    // ------------------------------------------------ fouls and handball
    const ownGoalX = (team) => -dirOf(team) * FIELD_W / 2;
    function inOwnBox(team, x, z) {
        const gx = ownGoalX(team);
        return Math.abs(x - gx) < PEN_DEPTH && Math.abs(z) < PEN_WIDTH / 2 && Math.sign(x) === Math.sign(gx);
    }
    // the man fouled was through on goal with nobody left to stop him but the keeper
    function denied(offender, victim) {
        const gx = ownGoalX(offender.team), g = -dirOf(offender.team);
        if (Math.abs(gx - victim.position.x) > FIELD_W * 0.38) return false;
        const vA = victim.position.x * g;
        return !sideOf(offender.team).some(m => m !== offender && !m.userData.isKeeper && m.position.x * g > vA - 1);
    }
    // a challenge that won the ball: by `by` on `on`. True when it is a foul.
    function onChallenge(by, on, slide) {
        if (inc || !on || on.team === by.team) return false;
        const face = facingOf(on);
        const rx = by.position.x - on.position.x, rz = by.position.z - on.position.z, rl = Math.hypot(rx, rz) || 1;
        const from = (face.x * rx + face.z * rz) / rl;            // 1: in front of him, -1: from behind
        const behind = from < -0.3, side = !behind && from < 0.3;
        const chance = slide ? (behind ? 0.7 : side ? 0.25 : 0.06) : (behind ? 0.5 : 0.1);
        const f = forced && forced.kind === 'foul' ? forced : null;
        if (!f && Math.random() >= chance) return false;
        const dogso = behind && denied(by, on);
        let card = null;
        if (dogso && Math.random() < 0.65) card = 'red';
        else if (behind && Math.random() < (slide ? 0.6 : 0.45)) card = 'yellow';
        else if (side && Math.random() < (slide ? 0.25 : 0.1)) card = 'yellow';
        if (f && 'card' in f) card = f.card;
        callFoul({ kind: 'foul', offender: by, victim: on, x: on.position.x, z: on.position.z, card, clear: behind });
        return true;
    }
    function onBlock(p, touchedBefore) {
        if (inc || p.userData.isKeeper || touchedBefore === p.team || !touchedBefore) return false;
        const y = ball.position.y, speed = Math.hypot(ball.velocity.x, ball.velocity.z);
        const f = forced && forced.kind === 'hands' ? forced : null;
        if (!f) {
            if (y < 3.2 || y > 8.2 || speed < 0.8) return false;   // only a ball at arm's height, struck
            if (Math.random() >= 0.22) return false;
        }
        const shot = !!(lastKick && lastKick.kind === 'shot');
        let card = shot && inOwnBox(p.team, p.position.x, p.position.z) && Math.random() < 0.3 ? 'yellow' : Math.random() < 0.12 ? 'yellow' : null;
        if (f && 'card' in f) card = f.card;
        callFoul({ kind: 'hands', offender: p, victim: null, x: p.position.x, z: p.position.z, card, clear: Math.random() < 0.6 });
        return true;
    }
    function callFoul(f) {
        const off = f.offender, team = off.team, victimTeam = 3 - team;
        MATCH.fouls[team - 1]++;
        stopBall();
        off.userData.tackleT = 0;
        off.userData.getUpT = Math.max(off.userData.getUpT || 0, 18);
        if (f.victim) {
            const vu = f.victim.userData;
            vu.fallT = 1.4;
            vu.vx = 0; vu.vz = 0;
        }
        const box = inOwnBox(team, f.x, f.z);
        const restart = box
            ? { kind: 'penalty', team: victimTeam, x: 0, z: 0 }
            : { kind: 'free', team: victimTeam, x: f.x, z: f.z };
        let varCheck = null;
        if (box) {
            // a penalty: the VAR always looks, and the referee goes to the monitor
            const stands = f.clear || Math.random() < (f.kind === 'hands' ? 0.5 : 0.45);
            varCheck = {
                subject: f.kind === 'hands' ? 'Hands · mogelijke strafschop' : 'Mogelijke strafschop',
                review: true, stands,
                yes: 'Strafschop', no: 'Geen strafschop',
                yesSub: f.kind === 'hands' ? 'Hands in het strafschopgebied' : 'Overtreding in het strafschopgebied',
                noSub: f.kind === 'hands' ? 'Geen hands' : 'Eerst de bal',
            };
        } else if (f.card === 'red') {
            const stands = f.clear && Math.random() < 0.75;
            varCheck = {
                subject: 'Mogelijke rode kaart', review: true, stands,
                yes: 'Rode kaart', no: 'Gele kaart', yesSub: 'Doorgebroken speler neergehaald', noSub: 'Geen rood: geel',
            };
        }
        if (forced && forced.kind === f.kind) {
            if (varCheck && 'stands' in forced) varCheck.stands = forced.stands;
            forced = null;
        }
        start({
            kind: f.kind, team, x: f.x, z: f.z, offender: off, victim: f.victim, inBox: box,
            card: f.card, restart, varCheck, tick: aiTick,
        }, 'whistle');
    }

    // ------------------------------------------------ a goal: the VAR checks the offside before it
    function onGoal(team) {
        if (inc) return;
        const w = watch && watch.team === team && aiTick <= watch.until ? watch : null;
        watch = null;
        pending = null;
        if (!w || !buffer.length || w.tick < buffer[0].t) return;
        const offender = byPid(w.pid);
        start({
            kind: 'goalcheck', team, x: w.x, z: w.z, offender, tick: w.tick, lines: { a: w.atkX, d: w.defX },
            restart: w.offside ? { kind: 'free', team: 3 - team, x: w.x, z: w.z } : { kind: 'goal' },
            varCheck: {
                subject: 'Mogelijk buitenspel', review: false, stands: !w.offside,
                yes: 'Goal', no: 'Geen goal', yesSub: 'Geen buitenspel', noSub: 'Buitenspel',
            },
        }, 'wait');
    }

    // ------------------------------------------------ the stoppage, step by step
    function stopBall() {
        carrier = null;
        passTarget = null;
        curl = null;
        lastKick = null;
        ballCall = null;
        pending = null;
        ball.velocity.x *= 0.2; ball.velocity.z *= 0.2;
        if (ball.velocity.y > 0) ball.velocity.y = 0;
        all().forEach((p) => { const u = p.userData; u.charging = false; u.chargeStart = 0; u.volley = null; });
    }
    function start(o, phase) {
        inc = Object.assign({ id: ++incId, phase, t: 0, tick: aiTick }, o);
        if (phase !== 'wait') whistleFor(inc);
        build_view();
    }
    function next(phase) {
        inc.phase = phase;
        inc.t = 0;
        build_view();
    }
    function stopped() { return !!inc && inc.phase !== 'wait'; }

    // the referee's next step after the whistle (or after the VAR)
    function afterCall() {
        if (inc.varCheck && !inc.varDone) { next('check'); return; }
        if (inc.card && !inc.cardDone) { next('card'); return; }
        next('restart');
    }

    function tick() {
        if (!inc) return;
        if (STATE.gameStartTime) STATE.gameStartTime += TICK_MS;     // the clock stops while play does
        inc.t++;
        const t = inc.t;
        const ref = officials && officials.ref;
        if (ref) ref.userData.pose = null;
        switch (inc.phase) {
            case 'whistle': {
                const wait = inc.kind === 'offside' ? OFFSIDE_WAIT : FOUL_WAIT;
                if (inc.kind === 'offside' && officials) officials[inc.ar].userData.pose = 'flag';
                if (ref) { ref.userData.pose = t < 50 ? 'whistle' : 'point'; ref.userData.faceTo = restartFace(); }
                if (t >= wait) afterCall();
                break;
            }
            case 'check':
                if (ref) ref.userData.pose = 'ear';
                if (t >= CHECK_TICKS) next(inc.varCheck.review ? 'walk' : 'replay');
                break;
            case 'walk':
                if (ref && Math.hypot(ref.position.x - MONITOR.x, ref.position.z - (MONITOR.z + 3)) < 2.2 || t > 260) next('tv');
                break;
            case 'tv':
                if (ref) { ref.userData.pose = 'tv'; ref.userData.faceTo = { x: 0, z: 1 }; }
                if (t >= 50) next('replay');
                break;
            case 'replay':
                if (ref && inc.varCheck.review) { ref.userData.pose = 'watch'; ref.userData.faceTo = { x: 0, z: -1 }; }
                if (replayStep()) next('decide');
                break;
            case 'decide': {
                const v = inc.varCheck;
                if (ref) {
                    ref.userData.pose = v.review && t < 60 ? 'tv' : 'point';
                    ref.userData.faceTo = v.review && t < 60 ? { x: 0, z: 1 } : restartFace();
                }
                if (t === 1) applyDecision();
                if (t >= DECIDE_TICKS) { inc.varDone = true; if (inc.kind === 'goalcheck') finishGoalcheck(); else afterCall(); }
                break;
            }
            case 'card': {
                const p = inc.offender;
                if (!p || p.userData.offPitch) { inc.cardDone = true; afterCall(); break; }
                const d = ref ? Math.hypot(ref.position.x - p.position.x, ref.position.z - p.position.z) : 0;
                if (!inc.showAt && (d < 7 || t > 100)) {
                    inc.showAt = t;
                    applyCard();
                    build_view();
                }
                if (inc.showAt && ref) {
                    ref.userData.pose = inc.cardColor === 'red' ? 'red' : 'yellow';
                    ref.userData.faceTo = { x: p.position.x - ref.position.x, z: p.position.z - ref.position.z };
                    p.userData.faceTo = { x: ref.position.x - p.position.x, z: ref.position.z - p.position.z };
                }
                if (inc.showAt && t - inc.showAt >= CARD_SHOW) {
                    p.userData.faceTo = null;
                    inc.cardDone = true;
                    afterCall();
                }
                break;
            }
            case 'restart':
                if (t === 1) flashCut();
                if (t >= 14) doRestart();
                break;
        }
        if (inc) walkPlayers();                     // (play may have just restarted)
        moveOfficials();
    }

    // which way the referee points: the side that gets the ball, attacking
    function restartFace() {
        const r = inc && inc.restart;
        return r && r.team ? { x: dirOf(r.team), z: 0 } : null;
    }

    // while play is stopped: the players walk, the man on the ground stays down,
    // a man sent off walks to the touchline
    function walkPlayers() {
        if (inc.phase === 'replay') return;                 // the replay moves them
        const goal = inc.kind === 'goalcheck';
        const restartTeam = inc.restart && inc.restart.team;
        all().forEach((p) => {
            const u = p.userData;
            if (u.tackleT > 0) u.tackleT = 0;
            if (u.getUpT > 0) u.getUpT--;
            let tx = p.position.x, tz = p.position.z, speed = 0.14;
            if (u.fallT > 0 || u.getUpT > 0) { tx = p.position.x; tz = p.position.z; }
            else if (inc.sentOff === p) { tz = Math.sign(p.position.z || 1) * (FIELD_L / 2 + 8); speed = 0.16; }
            else if (inc.phase === 'card' && p === inc.offender) { /* waits for the card */ }
            else if (goal) { const at = kickoffSpot(p); tx = at.x; tz = at.z; speed = 0.2; }
            else if (u.isKeeper) { tx = ownGoalX(p.team) + dirOf(p.team) * 5; tz = p.position.z * 0.9; }
            else { const s = roleSpot(p, p.team === restartTeam); tx = s.x; tz = s.z; }
            const dx = tx - p.position.x, dz = tz - p.position.z, d = Math.hypot(dx, dz);
            if (d > 0.8) steer(p, dx / d * Math.min(speed, d * 0.05), dz / d * Math.min(speed, d * 0.05), RUN_ACCEL);
            else steer(p, 0, 0, RUN_BRAKE);
            p.position.x += u.vx || 0;
            p.position.z += u.vz || 0;
            if (typeof sprintFor === 'function') sprintFor(p, false);
        });
        separatePlayers();
    }

    // ------------------------------------------------ the replay
    function record() {
        buffer.push({ t: aiTick, b: [ball.position.x, ball.position.y, ball.position.z],
            p: all().map(p => [p.userData.pid, p.position.x, p.position.z]) });
        if (buffer.length > BUFFER_TICKS) buffer.shift();
    }
    function frameAt(t) {
        if (!buffer.length) return null;
        const i = Math.max(0, Math.min(buffer.length - 1, t - buffer[0].t));
        const i0 = Math.floor(i), i1 = Math.min(buffer.length - 1, i0 + 1), k = i - i0;
        return { a: buffer[i0], b: buffer[i1], k };
    }
    function applyFrame(t) {
        const f = frameAt(t);
        if (!f) return;
        const map = new Map(f.b.p.map(e => [e[0], e]));
        f.a.p.forEach((e) => {
            const p = byPid(e[0]);
            const e2 = map.get(e[0]) || e;
            if (!p) return;
            p.position.x = e[1] + (e2[1] - e[1]) * f.k;
            p.position.z = e[2] + (e2[2] - e[2]) * f.k;
            p.userData.vx = 0; p.userData.vz = 0;
        });
        ball.position.set(f.a.b[0] + (f.b.b[0] - f.a.b[0]) * f.k, f.a.b[1] + (f.b.b[1] - f.a.b[1]) * f.k, f.a.b[2] + (f.b.b[2] - f.a.b[2]) * f.k);
    }
    function saveScene() {
        return { p: all().map(p => [p, p.position.x, p.position.z]), b: [ball.position.x, ball.position.y, ball.position.z],
            v: { x: ball.velocity.x, y: ball.velocity.y, z: ball.velocity.z } };
    }
    function restoreScene(s) {
        s.p.forEach(([p, x, z]) => { p.position.x = x; p.position.z = z; p.userData.lastX = x; p.userData.lastZ = z; p.userData.vx = 0; p.userData.vz = 0; });
        ball.position.set(s.b[0], s.b[1], s.b[2]);
        ball.velocity = { x: s.v.x, y: s.v.y, z: s.v.z };
    }
    // one tick of the replay; true when it is over
    function replayStep() {
        if (!inc.rp) {
            const pre = inc.kind === 'goalcheck' ? 70 : 80, post = inc.kind === 'goalcheck' ? 40 : 25;
            const first = buffer.length ? buffer[0].t : inc.tick, last = buffer.length ? buffer[buffer.length - 1].t : inc.tick;
            inc.rp = { f: Math.max(first, inc.tick - pre), end: Math.min(last, inc.tick + post), freeze: 0, save: saveScene() };
            all().forEach((p) => { p.userData.fallT = 0; p.userData.getUpT = 0; });
            if (!buffer.length) { restoreScene(inc.rp.save); return true; }
        }
        const rp = inc.rp;
        const hold = inc.kind === 'goalcheck' ? 120 : 85;
        if (rp.f >= inc.tick && rp.freeze < hold) {
            // frozen at the moment that counts: the pass (lines) or the contact (ring)
            if (rp.freeze === 0) { applyFrame(inc.tick); inc.frozen = true; build_view(); }
            rp.freeze++;
            if (rp.freeze >= hold) { inc.frozen = false; build_view(); }
            return false;
        }
        rp.f += 0.55;                                // slow motion
        if (rp.f > rp.end) {
            restoreScene(rp.save);
            inc.rp = null;
            return true;
        }
        applyFrame(rp.f);
        return false;
    }

    // ------------------------------------------------ the outcome
    function applyDecision() {
        const v = inc.varCheck;
        if (inc.kind === 'goalcheck') return;              // finishGoalcheck, after the call is shown
        if (inc.inBox && !v.stands) {
            // no penalty: the defending side's keeper gets the ball, no card
            inc.restart = { kind: 'keeper', team: inc.team };
            inc.card = null;
        } else if (!inc.inBox && inc.card === 'red' && !v.stands) {
            inc.card = 'yellow';
        }
    }
    function finishGoalcheck() {
        const v = inc.varCheck;
        if (v.stands) { inc = null; build_view(); return; }        // the goal counts: on to the kick-off
        // no goal: off the scoreboard, and a free kick to the defending side
        if (inc.team === 1) STATE.score1 = Math.max(0, STATE.score1 - 1);
        else STATE.score2 = Math.max(0, STATE.score2 - 1);
        MATCH.offsides[inc.team - 1]++;
        const s1 = $('hud-s1'), s2 = $('hud-s2');
        if (s1) s1.textContent = STATE.score1;
        if (s2) s2.textContent = STATE.score2;
        STATE.scoring = false;
        STATE.restartTicks = 0;
        STATE.inputLocked = false;
        next('restart');
    }
    function applyCard() {
        const p = inc.offender;
        if (!p) return;
        const u = p.userData;
        let color = inc.card;
        inc.second = false;
        if (color === 'yellow') {
            u.yellows = (u.yellows || 0) + 1;
            MATCH.yellows[p.team - 1]++;
            if (u.yellows >= 2) { color = 'red'; inc.second = true; }
        } else MATCH.reds[p.team - 1]++;
        if (inc.second) MATCH.reds[p.team - 1]++;
        inc.cardColor = color;
        // never fewer than two outfield players: the last ones stay on with the card
        const left = sideOf(p.team).filter(m => !m.userData.isKeeper).length;
        if (color === 'red' && left > 2) inc.sentOff = p;
    }
    function sendOff(p) {
        const team = p.team, side = sideOf(team);
        const slot = p === controlledP1 ? 1 : p === controlledP2 ? 2 : 0;
        if (slot) {
            const mate = side.find(m => m !== p && !m.userData.isKeeper);
            if (mate) setControlled(slot, mate, true);     // even a locked slot: your star is off
        }
        const i = side.indexOf(p);
        if (i >= 0) side.splice(i, 1);
        if (scene) scene.remove(p);
        p.userData.offPitch = true;
        removed.push(p.userData.pid);
        if (carrier === p) carrier = null;
        if (passTarget && passTarget.to === p) passTarget = null;
        if (typeof teamPlan !== 'undefined') { teamPlan[1] = null; teamPlan[2] = null; }
        lineCache.t = -1;
    }
    function doRestart() {
        const r = inc.restart || {};
        const sent = inc.sentOff;
        const done = inc;
        inc = null;
        if (sent) sendOff(sent);
        all().forEach((p) => { p.userData.fallT = 0; p.userData.faceTo = null; });
        if (r.kind === 'free' || r.kind === 'penalty') startFreeKick(r.kind, r.team, r.x, r.z);
        else if (r.kind === 'keeper') goalKick(r.team);
        // the keys that were down during the stoppage don't fire now
        Object.keys(keys).forEach(k => { keys[k] = false; });
        all().forEach((p) => { p.userData.shootHeld = false; p.userData.charging = false; });
        build_view();
        return done;
    }

    // ------------------------------------------------ every tick, whatever happens
    function always() {
        if (!officials) return;
        if (pending && aiTick > pending.until) pending = null;
        if (watch) {
            const k1 = team1Players[0]?.userData.holdingBall, k2 = team2Players[0]?.userData.holdingBall;
            const theirs = (carrier && carrier.team !== watch.team) || (k1 && watch.team !== 1) || (k2 && watch.team !== 2);
            if (theirs || aiTick > watch.until || STATE.setPiece) watch = null;
        }
        if (STATE.setPiece) pending = null;
        if (inc && inc.phase === 'wait') {
            if (++inc.t >= GOAL_WAIT) next('check');
            moveOfficials();
            return;
        }
        if (!inc) moveOfficials();
    }
    // after the normal tick: the replay's memory
    function live() {
        if (!officials) return;
        record();
    }
    function onKickoff() {
        pending = null;
        watch = null;
    }
    function onSetPiece() {
        pending = null;
        watch = null;
    }

    // ------------------------------------------------ where the officials go
    function refTarget() {
        if (inc) {
            if (inc.phase === 'walk' || inc.phase === 'tv' || (inc.phase === 'replay' && inc.varCheck && inc.varCheck.review)
                || (inc.phase === 'decide' && inc.varCheck && inc.varCheck.review && inc.t < 60)) return { x: MONITOR.x, z: MONITOR.z + 3, fast: true };
            if (inc.phase === 'card' && inc.offender) {
                const p = inc.offender;
                const dx = officials.ref.position.x - p.position.x, dz = officials.ref.position.z - p.position.z, d = Math.hypot(dx, dz) || 1;
                return { x: p.position.x + dx / d * 5, z: p.position.z + dz / d * 5, fast: true };
            }
            if (inc.phase === 'whistle' || inc.phase === 'check') return { x: inc.x - dirOf(inc.team) * 10, z: clampTo(inc.z - 8, FIELD_L / 2 - 4) };
        }
        const bx = ball.position.x, bz = ball.position.z;
        // on the diagonal, level with the play, never on top of it
        const x = clampTo(bx * 0.9, FIELD_W * 0.4);
        const z = -x / (FIELD_W / 2) * FIELD_L * 0.3;
        let dx = x - bx, dz = z - bz;
        const d = Math.hypot(dx, dz);
        if (d < 18) {
            if (d < 0.5) { dx = -0.5; dz = -0.85; }
            const l = Math.hypot(dx, dz);
            return { x: clampTo(bx + dx / l * 18, FIELD_W / 2 - 4), z: clampTo(bz + dz / l * 18, FIELD_L / 2 - 4) };
        }
        return { x, z };
    }
    function arTarget(half) {
        // in his half: level with the defending side's second-last man, or the ball if it is further
        const defTeam = half > 0 ? 2 : 1;
        let a = Math.max(secondLast(defTeam), ball.position.x * half);
        if (inc && inc.kind === 'offside' && inc.ar === (half > 0 ? 'arR' : 'arL')) a = inc.x * half;
        a = Math.max(0, Math.min(FIELD_W / 2 - 1, a));
        return { x: a * half, z: half * AR_OUT };
    }
    function moveTo(o, t, top) {
        const u = o.userData;
        const dx = t.x - o.position.x, dz = t.z - o.position.z, d = Math.hypot(dx, dz);
        if (d > 0.8) steer(o, dx / d * Math.min(top, d * 0.07), dz / d * Math.min(top, d * 0.07), RUN_ACCEL * 0.8);
        else steer(o, 0, 0, RUN_BRAKE);
        o.position.x += u.vx;
        o.position.z += u.vz;
    }
    function moveOfficials() {
        if (!officials || !ball) return;
        const replaying = inc && inc.phase === 'replay' && !(inc.varCheck && inc.varCheck.review);
        if (!replaying) {
            const t = refTarget();
            moveTo(officials.ref, t, RUN_SPEED * (t.fast ? 1.2 : 0.78));
        }
        moveTo(officials.arR, arTarget(1), RUN_SPEED * 0.85);
        moveTo(officials.arL, arTarget(-1), RUN_SPEED * 0.85);
        officials.arR.position.z = AR_OUT;
        officials.arL.position.z = -AR_OUT;
    }

    // ------------------------------------------------ drawing the officials, every frame
    function animateOfficial(o, dt) {
        const u = o.userData, rig = u.rig;
        if (!rig) return;
        const dx = o.position.x - (u.lastX ?? o.position.x), dz = o.position.z - (u.lastZ ?? o.position.z);
        u.lastX = o.position.x; u.lastZ = o.position.z;
        const speed = Math.min(80, Math.hypot(dx, dz) / dt);
        let face = null;
        if (u.pose && u.faceTo) face = u.faceTo;
        else if (u.ar) face = speed > 4 ? { x: 0, z: -u.ar } : { x: ball ? ball.position.x - o.position.x : 0, z: -u.ar * 4 };
        else if (speed > 4) face = { x: dx, z: dz };
        else if (ball) face = { x: ball.position.x - o.position.x, z: ball.position.z - o.position.z };
        if (face && (face.x || face.z)) {
            let diff = Math.atan2(face.x, face.z) - rig.body.rotation.y;
            diff = Math.atan2(Math.sin(diff), Math.cos(diff));
            rig.body.rotation.y += diff * Math.min(1, dt * 9);
        }
        const want = Math.min(1, speed / 35);
        u.stride += (want - u.stride) * Math.min(1, dt * 10);
        u.phase = (u.phase || 0) + dt * (6 + speed * 0.22);
        const swing = Math.sin(u.phase) * 0.9 * u.stride;
        rig.legL.rotation.x = swing;
        rig.legR.rotation.x = -swing;
        rig.armL.rotation.x = -swing * 0.8;
        rig.armR.rotation.x = swing * 0.8;
        rig.armL.rotation.z = -0.1;
        rig.armR.rotation.z = 0.1;
        rig.body.position.y = Math.abs(Math.cos(u.phase)) * 0.12 * u.stride;
        rig.body.rotation.x = 0.14 * u.stride;
        u.poseT = u.pose === u.lastPose ? (u.poseT || 0) + dt : 0;
        u.lastPose = u.pose;
        const pt = u.poseT;
        switch (u.pose) {
            case 'flag':   rig.armR.rotation.x = -2.95; rig.armR.rotation.z = 0.05; break;
            case 'whistle': rig.armR.rotation.x = -2.0; rig.armR.rotation.z = 0.75; break;
            case 'point':  rig.armR.rotation.x = -1.55; rig.armR.rotation.z = 0.25; break;
            case 'yellow':
            case 'red':    rig.armR.rotation.x = -2.95; rig.armR.rotation.z = 0.12; break;
            case 'ear':    rig.armR.rotation.x = -2.55; rig.armR.rotation.z = 0.95; rig.armL.rotation.x = -0.4; break;
            case 'tv': {
                // both hands draw the screen in the air: across the top, down, back along the bottom
                const k = (pt % 1.4) / 1.4;
                const top = k < 0.35, down = k >= 0.35 && k < 0.55;
                const spread = top ? k / 0.35 : down ? 1 : 1 - (k - 0.55) / 0.45;
                const lift = top ? -1.85 : down ? -1.85 + (k - 0.35) / 0.2 * 0.75 : -1.1;
                rig.armL.rotation.x = rig.armR.rotation.x = lift;
                rig.armL.rotation.z = -0.15 - spread * 0.65;
                rig.armR.rotation.z = 0.15 + spread * 0.65;
                break;
            }
            case 'watch': rig.armL.rotation.x = -0.25; rig.armR.rotation.x = -0.25; rig.body.rotation.x = 0.12; break;
        }
        if (u.card) {
            const show = u.pose === 'yellow' || u.pose === 'red';
            u.card.visible = show;
            if (show) u.card.material.color.copy(srgb(u.pose === 'red' ? 0xe0203a : 0xffd60a));
        }
    }

    // ------------------------------------------------ what the screens show
    // the host turns the stoppage into a small plain object; the guest gets it in the snapshot
    function build_view() {
        if (!inc) { view = null; return; }
        const v = inc.varCheck;
        const focus = inc.phase === 'replay' && inc.frozen
            ? { x: inc.lines ? inc.lines.a : inc.x, z: inc.z }
            : (inc.phase === 'walk' || inc.phase === 'tv') ? { x: MONITOR.x, z: MONITOR.z } : null;
        view = {
            id: inc.id, k: inc.kind, ph: inc.phase, tm: inc.team, box: inc.inBox ? 1 : 0,
            rs: inc.restart ? inc.restart.kind : '', rt: inc.restart ? inc.restart.team || 0 : 0,
            cd: inc.showAt ? inc.cardColor : null, sec: inc.second ? 1 : 0, who: labelOf(inc.offender),
            vs: v ? v.subject : '', rv: v && v.review ? 1 : 0,
            dec: v ? (v.stands ? v.yes : v.no) : '', dsub: v ? (v.stands ? v.yesSub : v.noSub) : '', st: v && v.stands ? 1 : 0,
            fr: inc.frozen ? 1 : 0,
            ln: inc.lines ? [Math.round(inc.lines.a * 100) / 100, Math.round(inc.lines.d * 100) / 100] : null,
            rg: inc.kind !== 'goalcheck' && inc.kind !== 'offside' ? [Math.round(inc.x * 10) / 10, Math.round(inc.z * 10) / 10] : null,
            fc: focus,
        };
    }
    function camFocus() { return view && view.fc ? view.fc : null; }

    function whistleFor(i) {
        if (i.kind === 'goalcheck') return;
        whistle(i.kind === 'offside' ? 'short' : 'double');
    }
    let actx = null;
    function whistle(pattern) {
        try {
            const AC = typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext);
            if (!AC) return;
            actx = actx || new AC();
            if (actx.state === 'suspended') actx.resume();
            const seq = pattern === 'double' ? [[0, 0.17], [0.26, 0.42]] : pattern === 'long' ? [[0, 0.8]] : [[0, 0.32]];
            seq.forEach(([at, len]) => blow(actx.currentTime + at, len));
        } catch (_) {}
    }
    function blow(t0, len) {
        const o = actx.createOscillator(), trill = actx.createOscillator(), depth = actx.createGain(), g = actx.createGain();
        o.type = 'triangle';
        o.frequency.value = 2700;
        trill.frequency.value = 36;                     // the pea in the whistle
        depth.gain.value = 140;
        trill.connect(depth); depth.connect(o.frequency);
        g.gain.setValueAtTime(0, t0);
        g.gain.linearRampToValueAtTime(0.06, t0 + 0.02);
        g.gain.setValueAtTime(0.06, t0 + len - 0.05);
        g.gain.linearRampToValueAtTime(0, t0 + len);
        o.connect(g); g.connect(actx.destination);
        o.start(t0); trill.start(t0);
        o.stop(t0 + len + 0.03); trill.stop(t0 + len + 0.03);
    }

    function setText(id, text) { const el = $(id); if (el && el.textContent !== text) el.textContent = text; }
    function show(id, on) { const el = $(id); if (el) el.hidden = !on; }
    function paint(v) {
        // the whistle on the guest: a new stoppage, or the goal taken back
        const ear = v ? `${v.id}|${v.ph === 'decide' ? 'd' : ''}` : '';
        if (v && ear !== heard) {
            const isGuest = typeof ONLINE !== 'undefined' && ONLINE.isGuest && ONLINE.isGuest();
            if (isGuest && heard.split('|')[0] !== String(v.id) && v.k !== 'goalcheck') whistle(v.k === 'offside' ? 'short' : 'double');
            if (v.ph === 'decide') whistle(v.k === 'goalcheck' && !v.st ? 'double' : 'short');
            heard = ear;
        }
        // the guest's screen dips too while the players are put in place for the free kick
        const cutKey = v && v.ph === 'restart' ? String(v.id) : cutFor;
        if (cutKey !== cutFor) {
            cutFor = cutKey;
            const isGuest = typeof ONLINE !== 'undefined' && ONLINE.isGuest && ONLINE.isGuest();
            if (isGuest) flashCut();
        }
        const key = v ? JSON.stringify([v.id, v.ph, v.cd, v.fr, v.dec]) : '';
        const gs = $('game-screen');
        if (key === shown) return;
        shown = key;
        if (!v) {
            ['ref-call', 'var-box', 'var-decision', 'replay'].forEach(id => show(id, false));
            if (gs && gs.classList) gs.classList.remove('is-replay');
            if (fx) { fx.atk.visible = fx.def.visible = fx.ring.visible = false; }
            return;
        }
        const codes = typeof hudCodes === 'function' ? hudCodes() : { red: '', blue: '' };
        const code = (t) => (t === 1 ? codes.red : codes.blue);
        const call = $('ref-call');
        // the call itself: offside or a foul, and for whom the free kick is
        const callOn = v.ph === 'whistle' || (v.ph === 'card' && v.cd);
        show('ref-call', callOn);
        if (callOn && call) {
            call.dataset.team = v.tm === 1 ? 'red' : 'blue';
            const card = $('ref-call-card');
            if (v.ph === 'card') {
                if (card) { card.hidden = false; card.dataset.card = v.cd; }
                setText('ref-call-kind', v.cd === 'red' ? (v.sec ? 'Tweede gele kaart' : 'Rode kaart') : 'Gele kaart');
                setText('ref-call-team', code(v.tm));
                setText('ref-call-sub', v.who + (v.cd === 'red' ? ' · van het veld' : ''));
            } else {
                if (card) card.hidden = true;
                setText('ref-call-kind', v.k === 'offside' ? 'Buitenspel' : v.k === 'hands' ? 'Hands' : 'Overtreding');
                setText('ref-call-team', code(v.tm));
                setText('ref-call-sub', v.box ? 'In het strafschopgebied' : `Vrije trap ${code(3 - v.tm)}`);
            }
        }
        // the VAR at work
        const varOn = v.ph === 'check' || v.ph === 'walk' || v.ph === 'tv' || v.ph === 'replay';
        show('var-box', varOn);
        if (varOn) {
            setText('var-state', v.ph === 'check' ? 'Check' : v.ph === 'replay' ? 'Herhaling' : 'Review');
            setText('var-subject', v.ph === 'walk' || v.ph === 'tv' ? 'Scheidsrechter naar het scherm' : v.vs);
        }
        // the replay: bars top and bottom like on television
        show('replay', v.ph === 'replay');
        if (gs && gs.classList) gs.classList.toggle('is-replay', v.ph === 'replay');
        // the decision
        show('var-decision', v.ph === 'decide');
        if (v.ph === 'decide') {
            setText('var-decision-text', v.dec);
            setText('var-decision-sub', v.dsub);
            const box = $('var-decision');
            if (box) {
                // in the colour of the side the call goes for
                const goesTo = v.k === 'goalcheck' ? (v.st ? v.tm : 3 - v.tm) : (v.st ? 3 - v.tm : v.tm);
                box.dataset.team = goesTo === 1 ? 'red' : 'blue';
                box.style.animation = 'none';
                void box.offsetWidth;
                box.style.animation = '';
            }
        }
        // the lines (offside) or the ring (a foul, handball) on the frozen picture
        if (fx) {
            const lines = v.ph === 'replay' && v.fr && v.ln;
            fx.atk.visible = fx.def.visible = !!lines;
            if (lines) {
                fx.atk.position.x = v.ln[0];
                fx.def.position.x = v.ln[1];
                fx.atk.material.color.copy(srgb(v.tm === 1 ? 0xe0203a : 0x1f5dff));
                fx.def.material.color.copy(srgb(v.tm === 1 ? 0x1f5dff : 0xe0203a));
            }
            const ring = v.ph === 'replay' && v.fr && v.rg;
            fx.ring.visible = !!ring;
            if (ring) fx.ring.position.set(v.rg[0], 0.1, v.rg[1]);
        }
    }

    function frame(dt) {
        if (!officials || dt <= 0) return;
        const guest = typeof ONLINE !== 'undefined' && ONLINE.isGuest && ONLINE.isGuest();
        if (guest) {
            // glide to where the host has them
            Object.values(officials).forEach((o) => {
                const t = o.userData.netTo;
                if (!t) return;
                const k = Math.min(1, dt * 12);
                o.position.x += (t.x - o.position.x) * k;
                o.position.z += (t.z - o.position.z) * k;
            });
        }
        Object.values(officials).forEach(o => animateOfficial(o, dt));
        paint(view);
    }

    // ------------------------------------------------ online
    const POSES = [null, 'flag', 'whistle', 'point', 'yellow', 'red', 'ear', 'tv', 'watch'];
    const r1 = (v) => Math.round(v * 10) / 10;
    function snap() {
        if (!officials) return 0;
        const o = ['ref', 'arR', 'arL'].map((k) => {
            const p = officials[k], u = p.userData, f = u.faceTo;
            return [r1(p.position.x), r1(p.position.z), Math.max(0, POSES.indexOf(u.pose || null)), f ? r1(f.x) : 0, f ? r1(f.z) : 0];
        });
        return { o, v: view, x: removed.length ? removed.slice() : 0 };
    }
    function applySnap(rf) {
        if (!officials || !rf) return;
        (rf.o || []).forEach((e, i) => {
            const p = officials[['ref', 'arR', 'arL'][i]];
            if (!p) return;
            const u = p.userData;
            if (!u.netTo) { p.position.x = e[0]; p.position.z = e[1]; }
            u.netTo = { x: e[0], z: e[1] };
            u.pose = POSES[e[2]] || null;
            u.faceTo = e[3] || e[4] ? { x: e[3], z: e[4] } : null;
        });
        // the players the host sent off
        (rf.x || []).forEach((pid) => {
            if (removed.includes(pid)) return;
            const p = byPid(pid);
            removed.push(pid);
            if (!p) return;
            const side = sideOf(p.team), i = side.indexOf(p);
            if (i >= 0) side.splice(i, 1);
            if (scene) scene.remove(p);
            p.userData.offPitch = true;
        });
        view = rf.v || null;
    }

    function teardown() {
        inc = null; view = null; pending = null; watch = null; buffer = [];
        officials = null; monitor = null; fx = null;
        paint(null);
    }

    return {
        build, teardown, always, live, tick, stopped, frame, camFocus,
        onPass, onReceive, onChallenge, onBlock, onGoal, onKickoff, onSetPiece,
        isOffside, lineFor, snap, applySnap,
        force(o) { forced = o; },                    // var-test.html only
        get active() { return inc; },
        get removed() { return removed; },
    };
})();

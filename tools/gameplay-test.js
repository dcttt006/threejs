#!/usr/bin/env node
// =====================================================
// PITCH ROYALE — critical gameplay test
// Runs the real game code (game.core.js, game.ui.js, game.js) without a
// browser: a stand-in for THREE and the page, a virtual clock and a seeded
// random, 60 game ticks a second. Plays many matches with a scripted player
// on a laptop (keyboard: digital keys) and on a phone (the analogue stick and
// the Schiet / Pass buttons), plus matches nobody touches, and reports every
// moment the game misbehaves: a ball lying still that nobody fetches, nobody
// moving, a keeper holding on too long, trembling or standing in a strange
// place, the ball jumping between players, a player who can't get the ball,
// a slide that never ends, a corner or throw-in that is never taken. It also
// counts how many of the player's passes reach his own side (ground and high,
// with the line to the receiver open or not) and the corners and throw-ins.
//
//   node tools/gameplay-test.js            all scenarios
//   node tools/gameplay-test.js --quick    a short run
//   node tools/gameplay-test.js --seed 7 --only touch-medium --verbose
// =====================================================
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = process.env.GAME_ROOT ? path.resolve(process.env.GAME_ROOT) : path.resolve(__dirname, '..');      // GAME_ROOT: test another copy of the game
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf('--' + name); return i < 0 ? dflt : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const QUICK = !!opt('quick', false);
const VERBOSE = !!opt('verbose', false);
const ONLY = opt('only', null);
const SEEDS = opt('seed', null) ? [Number(opt('seed'))] : (QUICK ? [1, 2] : [1, 2, 3, 4]);
const MATCH_SECONDS = Number(opt('seconds', QUICK ? 90 : 180));

// ---------------------------------------------------------------- the stand-in browser
function makeContext(seed) {
    let clock = 1_000_000;                       // virtual ms
    const timers = [];
    let s = seed >>> 0 || 1;
    const rand = () => {                         // mulberry32
        s = (s + 0x6D2B79F5) >>> 0;
        let t = s;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const noop = () => {};
    const classList = () => ({ add: noop, remove: noop, toggle: noop, contains: () => false });
    const ctx2d = new Proxy({}, {
        get: (t, k) => k === 'getImageData' ? (x, y, w, h) => ({ data: new Uint8ClampedArray(Math.max(4, w * h * 4)) })
            : k === 'measureText' ? () => ({ width: 10, actualBoundingBoxAscent: 10 })
            : k in t ? t[k] : noop,
        set: (t, k, v) => { t[k] = v; return true; },
    });
    const el = () => ({
        textContent: '', hidden: true, value: '', disabled: false,
        style: { setProperty: noop, removeProperty: noop }, dataset: {}, classList: classList(),
        addEventListener: noop, removeEventListener: noop, appendChild: noop, append: noop, replaceChildren: noop,
        querySelector: () => el(), querySelectorAll: () => [], setAttribute: noop, focus: noop, blur: noop,
        getContext: () => ctx2d, getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
        scrollIntoView: noop, setPointerCapture: noop, offsetWidth: 0, width: 0, height: 0,
    });
    const elements = new Map();
    const document = {
        addEventListener: noop, removeEventListener: noop,
        documentElement: { classList: classList() },
        getElementById: (id) => { if (!elements.has(id)) elements.set(id, el()); return elements.get(id); },
        createElement: () => el(), querySelector: () => el(), querySelectorAll: () => [], body: el(),
    };

    // THREE: real positions, everything else inert
    class V3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
        set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; } setScalar(v) { this.x = this.y = this.z = v; return this; }
        copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; } clone() { return new V3(this.x, this.y, this.z); } }
    class Obj3D { constructor() { this.position = new V3(); this.rotation = new V3(); this.rotation.order = 'XYZ'; this.scale = new V3(1, 1, 1);
        this.userData = {}; this.children = []; this.visible = true; this.renderOrder = 0; }
        add(...c) { this.children.push(...c); return this; } remove(c) { this.children = this.children.filter(x => x !== c); return this; }
        traverse(f) { f(this); this.children.forEach(c => c.traverse && c.traverse(f)); } lookAt() {} getObjectByName() { return null; } }
    class Mesh extends Obj3D { constructor(geometry, material) { super(); this.geometry = geometry; this.material = material; } }
    class Color { constructor() { this.r = this.g = this.b = 1; } convertSRGBToLinear() { return this; } setRGB() { return this; }
        clone() { return new Color(); } multiplyScalar() { return this; } set() { return this; } }
    class Material { constructor(o = {}) { Object.assign(this, o); this.color = new Color(); } clone() { return new Material(this); } dispose() {} }
    // anything else: an object whose every method does nothing and returns itself
    const inert = () => { const o = {}; const px = new Proxy(o, { get: (t, k) => (k in t ? t[k] : (k === Symbol.toPrimitive || k === 'then' ? undefined : () => px)), set: (t, k, v) => { t[k] = v; return true; } }); return px; };
    function Inert() { return inert(); }
    const special = { Object3D: Obj3D, Group: Obj3D, Scene: Obj3D, Mesh, Vector3: V3, Color };
    const THREE = new Proxy({}, {
        get: (t, k) => special[k] || (/Material$/.test(k) ? Material : (typeof k === 'string' && /^[A-Z][a-z]/.test(k) ? Inert : 0)),
    });

    const M = Object.create(Math);
    M.random = rand;
    const DateShim = class extends Date { static now() { return clock; } };
    const sandbox = {
        THREE, document, Math: M, Date: DateShim, console: { log: noop, warn: noop, error: (...a) => console.error(...a), info: noop },
        navigator: { userAgent: 'node', maxTouchPoints: 0 }, location: { search: '', pathname: '/index.html' },
        history: { pushState: noop, replaceState: noop }, localStorage: { getItem: () => null, setItem: noop },
        matchMedia: () => ({ matches: false, addEventListener: noop }), URLSearchParams,
        performance: { now: () => clock }, requestAnimationFrame: () => 0, cancelAnimationFrame: noop,
        setTimeout: (f, ms) => { timers.push({ at: clock + (ms || 0), f }); return timers.length; }, clearTimeout: noop,
        ResizeObserver: class { observe() {} disconnect() {} }, Image: class { set src(v) {} },
        addEventListener: noop, removeEventListener: noop, innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1,
    };
    sandbox.window = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    sandbox.__advance = (ms) => {
        clock += ms;
        for (let i = 0; i < timers.length; i++) if (timers[i] && timers[i].at <= clock) { const t = timers[i]; timers[i] = null; t.f(); }
    };
    return sandbox;
}

// the game files plus a small bridge to their top-level names, in one script
const BRIDGE = `
;globalThis.__sim = {
    setup(o) {
        scene = new THREE.Scene();
        STATE.mode = o.mode; STATE.difficulty = o.level; STATE.p1.team = 1; STATE.p2.team = 2;
        STATE.kickoffTeam = 1; STATE.score1 = 0; STATE.score2 = 0; STATE.scoring = false; STATE.paused = false;
        STATE.screen = 'playing'; STATE.wkMatch = null; STATE.goldenGoal = false; STATE.gameDuration = 1e9;
        resetMatchStats();
        buildPlayers(); buildBall(); positionForKickoff(); resetBotPerception();
        STATE.inputLocked = false; STATE.gameStartTime = Date.now();
    },
    tick() { gameTick(); animatePlayers(PHYSICS_STEP); },
    get STATE() { return STATE; }, get ball() { return ball; }, get carrier() { return carrier; },
    get team1() { return team1Players; }, get team2() { return team2Players; },
    get p1() { return controlledP1; }, get p2() { return controlledP2; },
    get keys() { return keys; }, get keysPressed() { return keysPressed; }, get touchMove() { return touchMove; },
    setTouchHigh(v) { touchShotHigh = v; }, setTouchPassHigh(v) { touchPassHigh = v; }, get kickoffHold() { return kickoffHold; }, get lastKick() { return lastKick; },
    get MATCH() { return MATCH; }, get passTarget() { return passTarget; },
    get setPiece() { return STATE.setPiece; }, aim(x, z) { return setPieceAim(x, z); },
    C: { FIELD_W, FIELD_L, GOAL_W, GOAL_H, PLAYER_SIZE, BALL_SIZE, CARRY_REACH },
};`;
const SOURCE = ['game.core.js', 'game.ui.js', 'game.js'].map(f => fs.readFileSync(path.join(ROOT, f), 'utf8')).join('\n;\n') + BRIDGE;

// ---------------------------------------------------------------- the scripted human
// Decides like a reasonable player each tick; `device` turns that into keys
// (laptop: digital WASD / arrows, Space, Q, Shift) or into the phone's
// analogue stick and buttons. Reaction time and imperfection included.
function makeHuman(sim, device, rand) {
    const st = { shootHold: 0, shooting: false, tackleCd: 0, passCd: 0, lastWant: [0, 0], react: 0 };
    const keyboard = device === 'keyboard';
    const K = keyboard ? { up: 'KeyW', down: 'KeyS', left: 'KeyA', right: 'KeyD' } : null;
    function press(code) { sim.keys[code] = true; sim.keysPressed[code] = true; }
    function release(code) { sim.keys[code] = false; }
    function move(x, z, sprint) {
        const len = Math.hypot(x, z);
        if (keyboard) {
            ['KeyW', 'KeyS', 'KeyA', 'KeyD'].forEach(c => { sim.keys[c] = false; });
            if (len > 0.001) {
                if (x / len > 0.38) sim.keys[K.right] = true;
                if (x / len < -0.38) sim.keys[K.left] = true;
                if (z / len > 0.38) sim.keys[K.down] = true;
                if (z / len < -0.38) sim.keys[K.up] = true;
            }
        } else {
            const tm = sim.touchMove;
            if (len > 0.001) {
                const mag = 0.6 + 0.4 * rand();                  // a thumb never holds it perfectly
                const wob = (rand() - 0.5) * 0.25;
                const a = Math.atan2(z, x) + wob;
                tm.x = Math.cos(a) * mag; tm.z = Math.sin(a) * mag; tm.active = mag > 0.18;
            } else { tm.active = false; tm.x = tm.z = 0; }
        }
        if (sprint) sim.keys.ShiftLeft = true; else sim.keys.ShiftLeft = false;
    }
    return function act() {
        const me = sim.p1, ball = sim.ball, C = sim.C;
        if (!me || sim.STATE.scoring) { move(0, 0, false); if (st.shooting) { release('Space'); st.shooting = false; } return; }
        // a corner or a throw-in: whoever takes it clicks somewhere sensible, or plays it short
        const sp = sim.setPiece;
        if (sp) {
            if (st.shooting) { release('Space'); st.shooting = false; }
            if (sp.phase === 'ready' && sp.taker === me) {
                move(0, 0, false);
                if (st.spWait === undefined) st.spWait = 20 + Math.floor(rand() * 70);
                if (--st.spWait <= 0) {
                    st.spWait = undefined;
                    if (rand() < 0.65) {
                        const gx = sp.kind === 'corner' ? sp.sx * (C.FIELD_W / 2 - 14 - rand() * 18) : sp.spot.x + (rand() - 0.5) * 50;
                        const gz = sp.kind === 'corner' ? (rand() - 0.5) * 30 : sp.spot.z - sp.sz * (10 + rand() * 30);
                        st.aimed = (st.aimed || 0) + 1;
                        sim.aim(gx, gz);
                    } else press('KeyQ');
                }
                return;
            }
        } else st.spWait = undefined;
        // a ball of ours on its way to me: now and then strike it first time
        const pt = sim.passTarget;
        if (pt && pt.to === me && !sim.carrier && !st.volleyArmed && rand() < 0.02) {
            const gx0 = me.team === 1 ? C.FIELD_W / 2 : -C.FIELD_W / 2;
            if (Math.abs(gx0 - me.position.x) < 45) { press('Space'); st.volleyArmed = true; st.releaseSoon = 3; }
        }
        if (st.releaseSoon > 0 && --st.releaseSoon === 0) release('Space');
        if (!pt) st.volleyArmed = false;
        if (st.tackleCd > 0) st.tackleCd--;
        if (st.passCd > 0) st.passCd--;
        // a human reacts in steps, not every tick
        if (--st.react > 0) { move(st.lastWant[0], st.lastWant[1], st.lastWant[2]); return; }
        st.react = 4 + Math.floor(rand() * 6);
        const goalX = me.team === 1 ? C.FIELD_W / 2 : -C.FIELD_W / 2;
        const carrier = sim.carrier;
        const dxB = ball.position.x - me.position.x, dzB = ball.position.z - me.position.z;
        const dB = Math.hypot(dxB, dzB);
        let want = [0, 0], sprint = false;
        if (st.shooting) {
            // holding Schiet: keep running at goal, let go after the planned charge
            want = [goalX - me.position.x, -me.position.z * 0.5];
            if (--st.shootHold <= 0) {
                if (!keyboard && rand() < 0.25) sim.setTouchHigh(true);
                if (keyboard && rand() < 0.25) sim.keys.KeyW = true;         // a high shot
                release('Space'); st.shooting = false;
            }
        } else if (carrier === me) {
            const toGoal = Math.abs(goalX - me.position.x);
            want = [goalX - me.position.x, (rand() - 0.5) * 20 - me.position.z * 0.3];
            const enemies = (me.team === 1 ? sim.team2 : sim.team1).slice(1);
            const pressure = Math.min(...enemies.map(e => Math.hypot(e.position.x - me.position.x, e.position.z - me.position.z)));
            if (toGoal < 32 && rand() < 0.5) {
                press('Space'); st.shooting = true; st.shootHold = 6 + Math.floor(rand() * 34);
            } else if (pressure < 5 && st.passCd === 0 && rand() < 0.3) {
                press('KeyQ'); st.passCd = 40;
            } else if (pressure > 9 && st.passCd === 0 && rand() < 0.05) {
                // a high pass, over the top: W (or a swipe up over Pass) with it
                if (keyboard) sim.keys.KeyW = true; else sim.setTouchPassHigh(true);
                press('KeyQ'); st.passCd = 40; st.highPassKey = keyboard;
            } else sprint = rand() < 0.3;
        } else if (carrier && carrier.team === me.team) {
            // a teammate has it: run into space ahead, sometimes ask for it
            want = [goalX * 0.55 - me.position.x, -carrier.position.z * 0.8 - me.position.z];
            if (st.passCd === 0 && rand() < 0.08) { press('KeyQ'); st.passCd = 60; }
        } else {
            // loose ball or the other side has it: go for the ball
            want = [dxB + ball.velocity.x * 8, dzB + ball.velocity.z * 8];
            sprint = dB > 15 && rand() < 0.6;
            if (carrier && carrier.team !== me.team && dB < 7 && st.tackleCd === 0 && rand() < 0.35) {
                press('Space'); release('Space'); st.tackleCd = 90;
            }
        }
        st.lastWant = [want[0], want[1], sprint];
        move(want[0], want[1], sprint);
        if (st.highPassKey) { sim.keys.KeyW = true; st.highPassKey = false; }     // held with Q
        if (sim.keys.KeyW && !st.shooting && keyboard) { /* direction keys rebuilt each tick */ }
    };
}

// ---------------------------------------------------------------- one match, watched
function runMatch(scn, seed) {
    const sb = makeContext(seed);
    vm.runInContext(SOURCE, sb, { filename: 'game-bundle.js' });
    const sim = sb.__sim;
    sim.setup({ mode: scn.mode, level: scn.level });
    let rs = (seed * 7919) >>> 0 || 3;
    const rand = () => { rs ^= rs << 13; rs >>>= 0; rs ^= rs >> 17; rs ^= rs << 5; rs >>>= 0; return rs / 4294967296; };
    const human = scn.device === 'idle' ? null : makeHuman(sim, scn.device, rand);
    const C = sim.C;
    const ticks = MATCH_SECONDS * 60;
    const keeperOf = (t) => (t === 1 ? sim.team1 : sim.team2)[0];
    const allPlayers = () => [...sim.team1, ...sim.team2];
    const bots = () => allPlayers().filter(p => p !== sim.p1 && p !== sim.p2 && !p.userData.isKeeper);

    const incidents = [];
    const open = {};                                         // running episodes, by kind
    const stat = { looseTicks: 0, liveTicks: 0, gains: 0, teamSwaps: 0, keeperHolds: 0, parries: 0, goals: [0, 0], shots: [0, 0],
        longestLoose: 0, humanTouches: 0, botStill: 0, botTicks: 0, mateStill: 0, mateTicks: 0,
        dives: 0, divesOnShot: 0, divesOnOwnPass: 0, divesFar: 0, divesBeforeMoving: 0, possTicks: [], curPoss: 0,
        shotLog: [], setPieces: [0, 0], humanPasses: [[], [], [], []], humanLost: { afgepakt: 0, gepasst: 0, geschoten: 0, keeper: 0, los: 0 }, humanCarry: [], humanGain: [], holdTicks: 0, catchFrom: { schot: 0, pass_tegenstander: 0, eigen_pass: 0, losse_bal: 0, van_dribbelaar: 0 } };
    let spSeen = false, spStart = 0, prevLkObj = null, pendingPass = null, prevP1 = sim.p1;
    let prevCarrier = null, prevLastKick = null, shotCount = 0, liveShot = null, humanSince = -1, humanFromX = 0, humanLostAt = -1;
    let lastCarrier = null, lastTeam = 0, carrierSwaps = [], lastHold = [false, false], lastDive = [0, 0], lastParry = [0, 0];
    let keeperFlips = [[], []], keeperLastVz = [0, 0], score = [0, 0];
    let nearestBotDHist = [];
    const trace = []; let traced = false; const swapTrace = []; let swapTraced = false;
    // how long each kind of trouble must last before it counts
    const THRESH = { BAL_LIGT_STIL: 150, NIEMAND_BEWEEGT: 120, NIEMAND_GAAT_NAAR_BAL: 120, BAL_KLEMT_IN_HOEK: 240,
        SPELER_KAN_BAL_NIET_PAKKEN: 90, KEEPER_HOUDT_TE_LANG: 330, KEEPER_TRILT: 30, KEEPER_STAAT_RAAR: 120,
        BAL_SPRINGT_HEEN_EN_WEER: 1, KEEPER_LAAT_BAL_LIGGEN: 90, TEAMGENOOT_STAAT_STIL: 240 };
    const thresh = (kind) => THRESH[kind.replace(/_\d$/, '')] ?? 30;

    const episode = (kind, active, t, info) => {
        if (active) {
            if (!open[kind]) open[kind] = { start: t, info: info() };
            return;
        }
        if (open[kind]) {
            const e = open[kind]; delete open[kind];
            if (t - e.start >= thresh(kind)) incidents.push({ kind, start: e.start, end: t, info: e.info });
        }
    };
    const once = (kind, t, info) => incidents.push({ kind, start: t, end: t, info });
    const describe = () => {
        const b = sim.ball.position;
        const f = (p) => `${p.team}${p.userData.isKeeper ? 'K' : (p === sim.p1 ? 'H' : (p === sim.p2 ? 'H2' : 'B'))}(${p.position.x.toFixed(0)},${p.position.z.toFixed(0)})`;
        const lk = sim.lastKick;
        return `bal (${b.x.toFixed(1)}, ${b.z.toFixed(1)}, h${b.y.toFixed(1)}) v${Math.hypot(sim.ball.velocity.x, sim.ball.velocity.z).toFixed(2)}`
            + `${lk ? ' na ' + lk.kind + ' van ' + lk.team : ''} | ${allPlayers().map(f).join(' ')}`;
    };
    const mate = sim.p1 ? (sim.p1.team === 1 ? sim.team1 : sim.team2).find(p => p !== sim.p1 && !p.userData.isKeeper) : null;

    for (let t = 0; t < ticks; t++) {
        sb.__advance(1000 / 60);
        const ballV0 = { x: sim.ball.velocity.x, z: sim.ball.velocity.z };       // as it was before this tick
        if (human) human();
        try { sim.tick(); } catch (err) { once('CRASH', t, String(err && err.stack || err).split('\n').slice(0, 3).join(' ')); break; }
        const S = sim.STATE, ball = sim.ball, car = sim.carrier;
        const nums = [ball.position.x, ball.position.y, ball.position.z, ...allPlayers().flatMap(p => [p.position.x, p.position.z])];
        if (nums.some(n => !Number.isFinite(n))) { once('NAN', t, describe()); break; }
        if (S.score1 !== score[0] || S.score2 !== score[1]) {
            stat.goals[S.score1 !== score[0] ? 0 : 1]++;
            score = [S.score1, S.score2];
        }
        const shotsNow = sim.MATCH.shots[0] + sim.MATCH.shots[1];
        if (shotsNow > shotCount) {
            const lk = sim.lastKick, team = lk ? lk.team : 0;
            const gx = team === 1 ? C.FIELD_W / 2 : -C.FIELD_W / 2;
            const k = keeperOf(team === 1 ? 2 : 1);
            if (liveShot) stat.shotLog.push({ ...liveShot, out: 'weg' });
            liveShot = { team, dist: Math.abs(gx - ball.position.x), speed: Math.hypot(ball.velocity.x, ball.velocity.z),
                high: !!(lk && lk.high), bot: !(lk && lk.by === sim.p1), kz: k.position.z, bz: ball.position.z,
                aimZ: ball.position.z + ball.velocity.z * Math.abs((gx - ball.position.x) / (ball.velocity.x || 1e-6)), t0: t };
            shotCount = shotsNow;
        }
        if (liveShot) {
            const goalNow = S.score1 + S.score2 > (stat.goals[0] + stat.goals[1]);
            const kHolds = keeperOf(1).userData.holdingBall || keeperOf(2).userData.holdingBall;
            const par = (keeperOf(1).userData.parryT || 0) === 20 || (keeperOf(2).userData.parryT || 0) === 20;
            const sdesc = () => `van ${liveShot.dist.toFixed(0)} snelheid ${liveShot.speed.toFixed(2)} hoog ${liveShot.high} richting z ${liveShot.aimZ.toFixed(1)} keeper z ${liveShot.kz.toFixed(1)}, na ${t - liveShot.t0} ticks: `;
            if (S.scoring) { if (VERBOSE && !liveShot.bot) once('SPELER_SCHOT_GOAL', t, sdesc() + describe()); stat.shotLog.push({ ...liveShot, out: 'goal' }); liveShot = null; }
            else if (kHolds || par) { if (VERBOSE && !liveShot.bot) once('SPELER_SCHOT_GERED', t, sdesc() + describe()); stat.shotLog.push({ ...liveShot, out: 'gered' }); liveShot = null; }
            else if (car) {
                if (VERBOSE && !liveShot.bot) once('SPELER_SCHOT_AFGEPAKT', t, `door ${car.team === liveShot.team ? 'eigen team' : 'tegenstander'} ${car.userData.isKeeper ? 'keeper' : ''}, na ${(t - liveShot.t0)} ticks, schot van ${liveShot.dist.toFixed(0)} snelheid ${liveShot.speed.toFixed(2)} richting z ${liveShot.aimZ.toFixed(1)}: ` + describe());
                stat.shotLog.push({ ...liveShot, out: 'weg' }); liveShot = null;
            }
        }
        // set pieces: how many, and none that hangs
        const spNow = sim.setPiece;
        if (spNow && !spSeen) { stat.setPieces[spNow.kind === 'corner' ? 0 : 1]++; spSeen = true; spStart = t; }
        if (!spNow) spSeen = false;
        if (spNow && t - spStart === 12 * 60) once('SPELHERVATTING_HANGT', t, `${spNow.kind} ${spNow.phase}: ` + describe());
        // the human's passes: does the ball get to one of his own side?
        const lkNow = sim.lastKick;
        if (lkNow && lkNow !== prevLkObj && lkNow.kind === 'pass' && lkNow.by === prevP1 && !lkNow.setPiece) {
            const to = lkNow.to;
            const enemiesL = (lkNow.team === 1 ? sim.team2 : sim.team1).slice(1);
            const ax = prevP1.position.x, az = prevP1.position.z, bx = to.position.x, bz = to.position.z;
            const L2 = (bx - ax) ** 2 + (bz - az) ** 2 || 1;
            const lane = Math.min(...enemiesL.filter(e => Math.hypot(e.position.x - ax, e.position.z - az) > 8).map(e => {
                const k = Math.max(0, Math.min(1, ((e.position.x - ax) * (bx - ax) + (e.position.z - az) * (bz - az)) / L2));
                return Math.hypot(ax + (bx - ax) * k - e.position.x, az + (bz - az) * k - e.position.z);
            }), 99);
            const at0 = new Map(enemiesL.map(e => [e, [e.position.x, e.position.z]]));
            pendingPass = { team: lkNow.team, t, high: !!lkNow.high, to, open: lane >= 3.5, at0, from: [ax, az], dest: [bx, bz], toAt: [to.position.x, to.position.z],
                info: (lkNow.high ? 'HOOG ' : '') + `afstand ${Math.hypot(to.position.x - prevP1.position.x, to.position.z - prevP1.position.z).toFixed(0)} v${Math.hypot(sim.ball.velocity.x, sim.ball.velocity.z).toFixed(2)}`
                    + ` druk ${Math.min(...(lkNow.team === 1 ? sim.team2 : sim.team1).slice(1).map(e => Math.hypot(e.position.x - prevP1.position.x, e.position.z - prevP1.position.z))).toFixed(1)}` };
        }
        prevLkObj = lkNow;
        if (pendingPass) {
            const kh1 = keeperOf(1).userData.holdingBall, kh2 = keeperOf(2).userData.holdingBall;
            let done = null;
            // struck first time by the one it was for: it got there
            if (lkNow && lkNow.kind === 'shot' && lkNow.by === pendingPass.to) done = true;
            else if (car) done = car.team === pendingPass.team;
            else if (kh1 || kh2) done = (kh1 ? 1 : 2) === pendingPass.team;
            else if (spNow || S.scoring || t - pendingPass.t > 240) done = false;
            if (done !== null) {
                stat.humanPasses[pendingPass.high ? 1 : 0].push(done);
                if (!pendingPass.high) stat.humanPasses[pendingPass.open ? 2 : 3].push(done);
                if (!done && VERBOSE) once('PASS_MIS', t, `${pendingPass.info}, na ${t - pendingPass.t} ticks, `
                    + (car ? `onderschept (ontvanger op ${Math.hypot(pendingPass.to.position.x - ball.position.x, pendingPass.to.position.z - ball.position.z).toFixed(1)})` : spNow ? 'uit' : 'anders')
                    + (car && pendingPass.at0.has(car) ? ` door een die stond op (${pendingPass.at0.get(car).map(v => v.toFixed(0))}), pass van (${pendingPass.from.map(v => v.toFixed(0))}) naar (${pendingPass.dest.map(v => v.toFixed(0))})${pendingPass.open ? ' VRIJ' : ''}` : '')
                    + ': ' + describe());
                pendingPass = null;
            }
        }
        prevP1 = sim.p1;
        // a slide that never ends (someone left lying in the slide after a switch)
        allPlayers().forEach((p) => {
            const u = p.userData;
            u.__slideFor = (u.tackleT > 0 || u.getUpT > 0) ? (u.__slideFor || 0) + 1 : 0;
            if (u.__slideFor === 80) once('TACKLE_BLIJFT_HANGEN', t, describe());
        });
        const live = !S.scoring && !S.paused && !sim.kickoffHold && !spNow;
        if (!live) { Object.keys(open).forEach(k => episode(k, false, t)); continue; }
        stat.liveTicks++;
        const holds = [keeperOf(1).userData.holdingBall, keeperOf(2).userData.holdingBall];
        const speed = Math.hypot(ball.velocity.x, ball.velocity.z);
        const loose = !car && !holds[0] && !holds[1];
        if (loose) stat.looseTicks++;
        const bs = bots();

        // a loose ball lying still
        episode('BAL_LIGT_STIL', loose && speed < 0.03 && ball.position.y < C.BALL_SIZE + 0.2, t, describe);
        // a slow loose ball the computer players don't close in on
        const nearBot = bs.length ? Math.min(...bs.map(p => Math.hypot(p.position.x - ball.position.x, p.position.z - ball.position.z))) : 0;
        nearestBotDHist.push(nearBot); if (nearestBotDHist.length > 60) nearestBotDHist.shift();
        episode('NIEMAND_GAAT_NAAR_BAL', loose && speed < 0.6 && nearBot > C.CARRY_REACH + 0.5 && nearestBotDHist.length === 60 && nearestBotDHist[0] - nearBot < 1.0, t, describe);
        // nobody of the computer moving
        const anyMove = [...bs, keeperOf(1), keeperOf(2)].some(p => Math.hypot(p.userData.vx || 0, p.userData.vz || 0) > 0.02);
        episode('NIEMAND_BEWEEGT', !anyMove, t, describe);
        bs.forEach(p => { stat.botTicks++; if (Math.hypot(p.userData.vx || 0, p.userData.vz || 0) < 0.03) stat.botStill++; });
        if (mate) {
            stat.mateTicks++;
            const still = Math.hypot(mate.userData.vx || 0, mate.userData.vz || 0) < 0.03;
            if (still) stat.mateStill++;
            episode('TEAMGENOOT_STAAT_STIL', still && loose, t, describe);
        }
        // the ball pinned at the side or in a corner
        episode('BAL_KLEMT_IN_HOEK', loose && (Math.abs(ball.position.x) > C.FIELD_W / 2 - 1.5 || Math.abs(ball.position.z) > C.FIELD_L / 2 - 1.5) && speed < 0.15, t, describe);
        // the human right at a loose ball but not getting it
        if (sim.p1) {
            const dH = Math.hypot(sim.p1.position.x - ball.position.x, sim.p1.position.z - ball.position.z);
            episode('SPELER_KAN_BAL_NIET_PAKKEN', loose && dH < C.CARRY_REACH + 1.5 && !(sim.p1.userData.cooldown > 0), t, describe);
        }
        // keepers
        for (const team of [1, 2]) {
            const k = keeperOf(team), u = k.userData, i = team - 1;
            const goalX = team === 1 ? -C.FIELD_W / 2 : C.FIELD_W / 2;
            const out = team === 1 ? 1 : -1;
            if (holds[i]) stat.holdTicks++;
            if (holds[i] && !lastHold[i]) {
                stat.keeperHolds++;
                // where the ball he caught came from (as it was the tick before)
                const lk = prevLastKick;
                const src = prevCarrier && prevCarrier.team !== team ? 'van_dribbelaar'
                    : lk && lk.team === team ? 'eigen_pass'
                    : lk && lk.kind === 'shot' ? 'schot'
                    : lk && lk.kind === 'pass' ? 'pass_tegenstander' : 'losse_bal';
                stat.catchFrom[src]++;
                if (src === 'eigen_pass' && VERBOSE) once('KEEPER_VANGT_EIGEN_PASS_' + team, t,
                    `door ${lk.by && lk.by.userData.isKeeper ? 'de keeper zelf' : (lk.by === sim.p1 ? 'de speler' : 'een computerspeler')} (${lk.kind}${lk.to ? ' naar ' + (lk.to.userData.isKeeper ? 'keeper' : lk.to === sim.p1 ? 'speler' : 'computer') : ''}): ` + describe());
            }
            episode('KEEPER_HOUDT_TE_LANG_' + team, holds[i], t, describe);
            lastHold[i] = holds[i];
            if ((u.diveT || 0) > lastDive[i] + 0.3) {
                stat.dives++;
                const lk = sim.lastKick;
                const dist = Math.abs(ball.position.x - k.position.x);
                const kSpeed = Math.hypot(u.vx || 0, u.vz || 0);
                if (lk && lk.kind === 'shot' && lk.team !== team) stat.divesOnShot++;
                if (lk && lk.team === team) { stat.divesOnOwnPass++; once('KEEPER_DUIKT_OP_EIGEN_PASS_' + team, t, describe()); }
                if (dist > 30) { stat.divesFar++; once('KEEPER_DUIKT_VAN_VER_' + team, t, `afstand ${dist.toFixed(0)}: ` + describe()); }
                if (kSpeed < 0.05) stat.divesBeforeMoving++;
                if (-ballV0.x * out < 0.4 && -ball.velocity.x * out < 0.4) once('KEEPER_DUIKT_ZONDER_SCHOT_' + team, t, describe());
            }
            lastDive[i] = u.diveT || 0;
            if ((u.parryT || 0) === 20 && lastParry[i] !== 20) stat.parries++;
            lastParry[i] = u.parryT || 0;
            const vz = u.vz || 0;
            if (Math.sign(vz) !== Math.sign(keeperLastVz[i]) && Math.abs(vz) > 0.03 && Math.abs(keeperLastVz[i]) > 0.03) keeperFlips[i].push(t);
            keeperLastVz[i] = vz;
            keeperFlips[i] = keeperFlips[i].filter(x => t - x < 60);
            episode('KEEPER_TRILT_' + team, keeperFlips[i].length >= 6, t, describe);
            const ballFar = Math.abs(ball.position.x - goalX) > 60;
            episode('KEEPER_STAAT_RAAR_' + team, ballFar && !holds[i] && (Math.abs(k.position.x - goalX) > 7 || Math.abs(k.position.z) > C.GOAL_W / 2 - 1), t, describe);
            // a slow loose ball right by the keeper, in his area, that he leaves lying
            const nearK = Math.hypot(ball.position.x - k.position.x, ball.position.z - k.position.z);
            episode('KEEPER_LAAT_BAL_LIGGEN_' + team, loose && speed < 0.3 && nearK < 6 && Math.abs(ball.position.x - goalX) < 12, t, describe);
        }
        // how the human loses the ball, and how far he gets with it
        if (sim.p1) {
            const goalX1 = sim.p1.team === 1 ? C.FIELD_W / 2 : -C.FIELD_W / 2;
            if (car === sim.p1 && humanSince < 0) { humanSince = t; humanFromX = Math.abs(goalX1 - sim.p1.position.x); }
            if (car !== sim.p1 && humanSince >= 0) {
                const lk = sim.lastKick, kh = keeperOf(1).userData.holdingBall || keeperOf(2).userData.holdingBall;
                const how = lk && lk.by === sim.p1 ? (lk.kind === 'shot' ? 'geschoten' : 'gepasst')
                    : kh ? 'keeper' : car && car.team !== sim.p1.team ? 'afgepakt' : 'los';
                stat.humanLost[how]++;
                stat.humanCarry.push({ ticks: t - humanSince, gained: humanFromX - Math.abs(goalX1 - sim.p1.position.x) });
                humanSince = -1;
            }
        }
        // the ball changing hands
        if (car !== lastCarrier) {
            if (car) {
                stat.gains++;
                if (car === sim.p1) stat.humanTouches++;
                if (lastTeam && car.team !== lastTeam) { stat.teamSwaps++; stat.possTicks.push(stat.curPoss); stat.curPoss = 0; }
                lastTeam = car.team;
            }
            carrierSwaps.push(t);
            lastCarrier = car;
        }
        if (lastTeam) stat.curPoss++;
        prevCarrier = car; prevLastKick = sim.lastKick ? { ...sim.lastKick } : null;
        if (opt('trace', false)) {
            const k2 = keeperOf(2);
            trace.push(`t${t} bal(${ball.position.x.toFixed(2)},${ball.position.z.toFixed(2)},h${ball.position.y.toFixed(2)}) v(${ball.velocity.x.toFixed(2)},${ball.velocity.z.toFixed(2)},${ball.velocity.y.toFixed(2)})`
                + ` K2(${k2.position.x.toFixed(2)},${k2.position.z.toFixed(2)}) hold${k2.userData.holdingBall ? 1 : 0} car:${car ? car.team + (car === sim.p1 ? 'H' : 'B') : '-'} lk:${sim.lastKick ? sim.lastKick.kind + sim.lastKick.team : '-'}`);
            if (trace.length > 24) trace.shift();
            if (incidents.length && incidents[incidents.length - 1].kind.startsWith('KEEPER_VANGT_EIGEN_PASS') && !traced) { traced = true; console.log(trace.join('\n')); }
        }
        carrierSwaps = carrierSwaps.filter(x => t - x < 60);
        if (opt('trace', false)) {
            const lab = (p) => p ? p.team + (p === sim.p1 ? 'H' : p.userData.isKeeper ? 'K' : 'B' + (p === (p.team === 1 ? sim.team1 : sim.team2)[2] ? '2' : '1')) : '-';
            swapTrace.push(`t${t} ${lab(car)} sh${car ? car.userData.shield || 0 : ''} v${speed.toFixed(2)} h${ball.position.y.toFixed(1)} lk:${sim.lastKick ? sim.lastKick.kind + sim.lastKick.team : '-'} tackle:${allPlayers().filter(p => p.userData.tackleT > 0).map(lab).join(',')}`);
            if (swapTrace.length > 70) swapTrace.shift();
            if (carrierSwaps.length >= 7 && !swapTraced) { swapTraced = true; console.log(swapTrace.filter((x, i, a) => i === 0 || x.split(' ')[1] !== a[i - 1].split(' ')[1]).join('\n')); }
        }
        episode('BAL_SPRINGT_HEEN_EN_WEER', carrierSwaps.length >= 7, t, describe);
        if (loose) open.__loose = (open.__loose || 0) + 1; else { stat.longestLoose = Math.max(stat.longestLoose, open.__loose || 0); open.__loose = 0; }
    }
    Object.keys(open).filter(k => !k.startsWith('__')).forEach(k => episode(k, false, ticks));
    stat.shots = [sim.MATCH.shots[0], sim.MATCH.shots[1]];
    stat.passes = [sim.MATCH.passes[0], sim.MATCH.passes[1]];
    return { incidents, stat };
}

// ---------------------------------------------------------------- the scenarios
const SCENARIOS = [
    { id: 'idle-medium', mode: 'cpu', level: 'medium', device: 'idle', label: 'niemand aan de knoppen (gemiddeld)' },
    { id: 'laptop-easy', mode: 'cpu', level: 'easy', device: 'keyboard', label: 'laptop, toetsenbord (makkelijk)' },
    { id: 'laptop-medium', mode: 'cpu', level: 'medium', device: 'keyboard', label: 'laptop, toetsenbord (gemiddeld)' },
    { id: 'laptop-hard', mode: 'cpu', level: 'hard', device: 'keyboard', label: 'laptop, toetsenbord (moeilijk)' },
    { id: 'touch-easy', mode: 'cpu', level: 'easy', device: 'touch', label: 'telefoon, stick + knoppen (makkelijk)' },
    { id: 'touch-medium', mode: 'cpu', level: 'medium', device: 'touch', label: 'telefoon, stick + knoppen (gemiddeld)' },
    { id: 'touch-hard', mode: 'cpu', level: 'hard', device: 'touch', label: 'telefoon, stick + knoppen (moeilijk)' },
    { id: 'duo-idle', mode: 'duo', level: 'medium', device: 'idle', label: 'twee spelers, niemand aan de knoppen' },
].filter(s => !ONLY || s.id === ONLY);

const t0 = Date.now();
const results = [];
for (const scn of SCENARIOS) {
    const agg = { scn, incidents: [], stat: null, runs: 0 };
    for (const seed of SEEDS) {
        const r = runMatch(scn, seed);
        r.incidents.forEach(i => { i.seed = seed; });
        agg.incidents.push(...r.incidents);
        agg.runs++;
        if (!agg.stat) agg.stat = JSON.parse(JSON.stringify(r.stat));
        else for (const k in r.stat) {
            if (k === 'possTicks' || k === 'shotLog' || k === 'humanCarry' || k === 'humanGain') agg.stat[k].push(...r.stat[k]);
            else if (k === 'humanPasses') r.stat[k].forEach((l, i) => agg.stat[k][i].push(...l));
            else if (Array.isArray(r.stat[k])) r.stat[k].forEach((v, i) => { agg.stat[k][i] += v; });
            else if (k === 'longestLoose') agg.stat[k] = Math.max(agg.stat[k], r.stat[k]);
            else if (k === 'curPoss') {}
            else if (k === 'shotLog') agg.stat[k].push(...r.stat[k]);
            else if (k === 'humanCarry' || k === 'humanGain') agg.stat[k].push(...r.stat[k]);
            else if (k === 'humanLost') for (const c in r.stat[k]) agg.stat[k][c] += r.stat[k][c];
            else if (k === 'catchFrom') for (const c in r.stat[k]) agg.stat[k][c] += r.stat[k][c];
            else agg.stat[k] += r.stat[k];
        }
    }
    results.push(agg);
}

// ---------------------------------------------------------------- the report
const mins = MATCH_SECONDS / 60;
const C_GOAL_W = 22;
const pad = (s, n) => String(s).padEnd(n);
console.log(`\nKRITISCHE GAMEPLAY-TEST  —  ${SEEDS.length} wedstrijd(en) van ${MATCH_SECONDS} s per scenario  (${((Date.now() - t0) / 1000).toFixed(1)} s)\n`);
let failing = 0;
for (const r of results) {
    const s = r.stat, n = r.runs;
    const byKind = {};
    r.incidents.forEach(i => { (byKind[i.kind.replace(/_\d$/, '')] = byKind[i.kind.replace(/_\d$/, '')] || []).push(i); });
    const kinds = Object.keys(byKind);
    if (kinds.length) failing++;
    const poss = s.possTicks.slice().sort((x, y) => x - y);
    const med = poss.length ? poss[Math.floor(poss.length / 2)] / 60 : 0;
    console.log(`${kinds.length ? 'FOUT' : ' OK '}  ${r.scn.label}`);
    console.log(`        goals ${s.goals[0]}-${s.goals[1]}   schoten ${s.shots[0]}-${s.shots[1]}   passes ${s.passes[0]}-${s.passes[1]}`
        + `   losse bal ${(100 * s.looseTicks / Math.max(1, s.liveTicks)).toFixed(0)}% (langst ${(s.longestLoose / 60).toFixed(1)} s)`
        + `   balbezit wisselt ${(s.teamSwaps / (mins * n)).toFixed(1)}x/min, mediaan ${med.toFixed(1)} s per bezit`);
    console.log(`        computer staat stil ${(100 * s.botStill / Math.max(1, s.botTicks)).toFixed(0)}%`
        + (s.mateTicks ? `   jouw teamgenoot staat stil ${(100 * s.mateStill / s.mateTicks).toFixed(0)}%` : '')
        + `   keeper vangt ${s.keeperHolds}, tikt weg ${s.parries}, duikt ${s.dives} (op schot ${s.divesOnShot}, op eigen pass ${s.divesOnOwnPass}, van ver ${s.divesFar}, nog stil ${s.divesBeforeMoving})`
        + (r.scn.device !== 'idle' ? `   jij aan de bal ${s.humanTouches}x` : ''));
    {
        const L = s.shotLog, pc = (a) => a.length ? Math.round(100 * a.filter(x => x.out === 'goal').length / a.length) + '%' : '-';
        const bucket = (lo, hi) => L.filter(x => x.dist >= lo && x.dist < hi);
        const onT = L.filter(x => Math.abs(x.aimZ) < C_GOAL_W / 2);
        console.log(`        schoten: ${L.length}, raak ${pc(L)} (op doel gericht ${onT.length}: raak ${pc(onT)}, gered ${onT.filter(x => x.out === 'gered').length})`
            + `   van <15: ${pc(bucket(0, 15))} (${bucket(0, 15).length})  15-25: ${pc(bucket(15, 25))} (${bucket(15, 25).length})  25+: ${pc(bucket(25, 999))} (${bucket(25, 999).length})`
            + `   computer ${pc(L.filter(x => x.bot))}  speler ${pc(L.filter(x => !x.bot))}  hoog ${pc(L.filter(x => x.high))}`);
    }
    {
        const hp = s.humanPasses, rate = (l) => l.length ? Math.round(100 * l.filter(Boolean).length / l.length) + '% (' + l.length + ')' : '-';
        console.log(`        hoekschoppen ${s.setPieces[0]}, inworpen ${s.setPieces[1]}`
            + (r.scn.device !== 'idle' ? `   jouw passes komen aan: ${rate(hp[0])} (vrije lijn ${rate(hp[2])}, dichte lijn ${rate(hp[3])}), hoge passes: ${rate(hp[1])}` : ''));
    }
    if (r.scn.device !== 'idle') {
        const hc = s.humanCarry, avg = (f) => hc.length ? (hc.reduce((a, x) => a + f(x), 0) / hc.length) : 0;
        console.log(`        speler met de bal: gemiddeld ${(avg(x => x.ticks) / 60).toFixed(1)} s, ${avg(x => x.gained).toFixed(0)} units richting doel`
            + `   kwijt door: ${Object.entries(s.humanLost).map(([k, v]) => k + ' ' + v).join(', ')}`);
    }
    console.log(`        bal in keepershanden ${(100 * s.holdTicks / Math.max(1, s.liveTicks)).toFixed(0)}% van de speeltijd`
        + `   gevangen na: ${Object.entries(s.catchFrom).map(([k, v]) => k.replace(/_/g, ' ') + ' ' + v).join(', ')}`);
    for (const k of kinds) {
        const list = byKind[k];
        const total = list.reduce((a, i) => a + (i.end - i.start), 0) / 60;
        console.log(`        ${pad(k, 30)} ${String(list.length).padStart(3)}x  samen ${total.toFixed(1)} s`);
        (VERBOSE ? list : list.slice(0, 2)).forEach(i => console.log(`            seed ${i.seed} t=${(i.start / 60).toFixed(1)}s ${((i.end - i.start) / 60).toFixed(1)}s: ${i.info}`));
    }
}
console.log(`\n${failing ? failing + ' van ' + results.length + ' scenario\'s met fouten' : 'alle scenario\'s zonder fouten'}\n`);
process.exitCode = failing ? 1 : 0;

// Plays penalty shoot-outs (game.pens.js) without a browser: a scripted
// player aims, holds and lets go on his own kicks and picks a corner on the
// others'. Checks every shoot-out ends, with a valid result, and that the
// numbers (goals, saves, misses over the bar) look like football.
//   node tools/pens-test.js [shoot-outs]
const fs = require('fs'), path = require('path'), vm = require('vm');
const N = +process.argv[2] || 300;
const src = fs.readFileSync(path.join(__dirname, '..', 'game.pens.js'), 'utf8');

function run(seed) {
    let clock = 0, s = seed >>> 0 || 1;
    const rand = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const timers = [];
    const listeners = {};
    const el = () => {
        const e = { style: {}, dataset: {}, hidden: false, textContent: '', innerHTML: '', children: [], offsetWidth: 0,
            classList: { add() {}, remove() {}, toggle() {} },
            appendChild(c) { this.children.push(c); return c; }, remove() {},
            addEventListener(type, f) { listeners[type] = f; }, setPointerCapture() {} };
        return e;
    };
    class V3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
        set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; } clone() { return new V3(this.x, this.y, this.z); }
        lerpVectors(a, b, t) { this.x = a.x + (b.x - a.x) * t; this.y = a.y + (b.y - a.y) * t; this.z = a.z + (b.z - a.z) * t; return this; } }
    const GX = 55;
    // the camera's ray: screen x -> across the goal, screen y -> up it
    class Raycaster { constructor() { this.ray = { origin: new V3(), direction: new V3() }; }
        setFromCamera(v) { this.ray.origin.set(GX - 33, 12.5, 0); this.ray.direction.set(33, (5 + v.y * 5) - 12.5, v.x * 11); } }
    const THREE = { Vector3: V3, Vector2: class { constructor(x, y) { this.x = x; this.y = y; } }, Raycaster };
    const mkPlayer = (keeper) => ({ isKeeper: keeper, visible: true, position: new V3(), userData: {} });
    const team1Players = [mkPlayer(false), mkPlayer(true)], team2Players = [mkPlayer(false), mkPlayer(true)];
    const M = Object.create(Math); M.random = rand;
    const sb = {
        THREE, Math: M, FIELD_W: 110, PEN_SPOT: 13, GOAL_W: 22, GOAL_H: 10, BALL_SIZE: 1.05, GOAL_DEPTH: 4.5,
        STATE: { difficulty: 'medium', wkMatch: null }, KIT: { 1: { shirt: '#f36c21' }, 2: { shirt: '#c1272d' } },
        hudCodes: () => ({ red: 'NED', blue: 'MAR' }), IS_TOUCH: false,
        team1Players, team2Players, ball: { position: new V3(), rotation: new V3(), visible: true },
        camera: { position: new V3(), lookAt() {}, updateProjectionMatrix() {} },
        renderer: { domElement: { getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 1000 }) } },
        animatePlayers() {}, updateBallShadow() {}, applyGameplayCamera() {},
        document: { getElementById: () => el(), createElement: () => el() },
        window: { innerWidth: 1280, innerHeight: 720, addEventListener() {} }, innerWidth: 1280, innerHeight: 720,
        location: { search: '' }, URLSearchParams,
        performance: { now: () => clock }, setTimeout: (f, ms) => timers.push({ at: clock + ms, f }),
        console,
    };
    vm.createContext(sb);
    vm.runInContext(src + '\n;globalThis.__P = PENS;', sb);
    const P = sb.__P;
    let result = null;
    P.start((score) => { result = score; });
    const stats = { kicks: 0, goals: 0, myGoals: 0, myKicks: 0, saves: 0, misses: 0 };
    // screen point for a goal spot: z across, y up (inverse of the ray above)
    const at = (z, y) => ({ clientX: 500 + (z / 11) * 500, clientY: 500 - ((y - 5) / 5) * 500, pointerId: 1, preventDefault() {} });
    let plan = null, lastLen = 0;
    for (let f = 0; f < 60 * 400 && !result; f++) {
        clock += 1000 / 60;
        for (const t of timers) if (t && t.at <= clock) { const g = t.f; t.f = null; t.at = Infinity; g && g(); }
        // read the phase off the prompt by trying the listeners at the right moments
        const S = vm.runInContext('PENS', sb);
        P.frame(1 / 60);
        const phase = vm.runInContext('(() => { try { return PENS && PENS.active(); } catch (e) { return false; } })()', sb);
        if (!phase) continue;
        // drive: every 0.3 s try to aim/choose; hold for a planned time then let go
        if (!plan) {
            const z = (rand() < 0.5 ? -1 : 1) * (4 + rand() * 6.5), y = 1.5 + rand() * 6.5;
            plan = { z, y, hold: 500 + rand() * 520, downAt: null };
        }
        if (plan.downAt === null && f % 18 === 0) {
            listeners.pointerdown && listeners.pointerdown(at(plan.z, plan.y));
            plan.downAt = clock;
        } else if (plan.downAt !== null && clock - plan.downAt > plan.hold) {
            listeners.pointerup && listeners.pointerup(at(plan.z, plan.y));
            plan = null;
        }
    }
    return result;
}

let done = 0, bad = 0, wins = 0;
const goalsA = [], goalsB = [];
for (let i = 0; i < N; i++) {
    const r = run(1000 + i * 7919);
    if (!r) { bad++; continue; }
    done++;
    if (r[0] === r[1]) bad++;
    if (r[0] > r[1]) wins++;
    goalsA.push(r[0]); goalsB.push(r[1]);
}
const avg = (a) => (a.reduce((x, y) => x + y, 0) / Math.max(1, a.length)).toFixed(2);
console.log(`${done}/${N} shoot-outs finished, ${bad} wrong; you won ${wins}; average ${avg(goalsA)} - ${avg(goalsB)}`);
process.exit(bad || done < N ? 1 : 0);

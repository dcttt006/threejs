#!/usr/bin/env node
// =====================================================
// PITCH ROYALE — test for Jij bent de VAR (game.var.js)
// Runs the real game code without a browser (tools/sim-context.js) and
//   1. builds every kind of scene many times, at every difficulty and both
//      ways, and checks that what you can see in the replay agrees with the
//      answer the game expects: the offside margin at the moment of the pass,
//      whether the slide touched the ball before the man, whether a defender
//      stood in the corridor to goal, how far the ball was over the line; that
//      the margin in centimetres is the one it shows; that nobody leaves the
//      pitch and the ball stays sensible;
//   2. checks the eight-round plan (every kind twice, once each way);
//   3. plays whole games through the real flow (intro, live, the referee's
//      call, the replay, your answer, the reveal), answering right, wrong and
//      too late, using the replay controls, and checks the score.
//
//   node tools/vargame-test.js            everything
//   node tools/vargame-test.js --quick    fewer scenes
// =====================================================
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { makeContext } = require('./sim-context');

const ROOT = process.env.GAME_ROOT ? path.resolve(process.env.GAME_ROOT) : path.resolve(__dirname, '..');
const QUICK = process.argv.includes('--quick');

const BRIDGE = `
;globalThis.__vg = {
    setup() {
        scene = new THREE.Scene();
        camera = new THREE.Group();
        camera.fov = 30; camera.aspect = 16 / 9; camera.far = 2000; camera.updateProjectionMatrix = () => {};
        STATE.mode = 'cpu'; STATE.difficulty = 'medium'; STATE.p1.team = 1; STATE.p2.team = 2;
        STATE.wkMatch = null; STATE.screen = 'playing'; STATE.paused = false;
        buildPlayers(); buildBall(); positionForKickoff();
        applyGameplayCamera();
    },
    get V() { return VARGAME; },
    get STATE() { return STATE; }, get ball() { return ball; },
    get team1() { return team1Players; }, get team2() { return team2Players; },
    get officials() { return REF.officials; },
    C: { FIELD_W, FIELD_L, GOAL_W, GOAL_H, GOAL_DEPTH, PEN_DEPTH, PEN_WIDTH, BALL_SIZE },
};`;
const SOURCE = ['game.core.js', 'game.ui.js', 'game.players.js', 'game.js', 'game.referee.js', 'game.var.js']
    .map(f => fs.readFileSync(path.join(ROOT, f), 'utf8')).join('\n;\n') + BRIDGE;

function load(seed) {
    const sb = makeContext(seed);
    vm.runInContext(SOURCE, sb, { filename: 'vargame-bundle.js' });
    sb.__vg.setup();
    return sb;
}

const fails = [];
const counts = {};
const fail = (where, msg) => { if (fails.length < 400) fails.push(`${where}: ${msg}`); };
const ang = (x) => Math.abs(Math.atan2(Math.sin(x), Math.cos(x))) * 180 / Math.PI;
const cmIn = (text) => { const m = /(\d+) cm/.exec(text); return m ? parseInt(m[1], 10) : null; };

// ---------------------------------------------------------------- 1. the scenes
function checkScene(sim, kind, seed, d, yes) {
    const X = sim.__vg.V._test, C = sim.__vg.C;
    const GX = C.FIELD_W / 2;
    const where = `${kind} seed ${seed} d ${d.toFixed(2)} ${yes ? 'ja' : 'nee'}`;
    let sc;
    try { sc = X.build(kind, seed, d, yes); } catch (e) { fail(where, 'bouwt niet: ' + e.message); return; }
    counts[kind] = (counts[kind] || 0) + 1;
    // world → the attack's own frame: a towards the goal under attack, b across
    const P = (id, t) => { const p = X.at(sc.act[id].k, t); return [p[0] * sc.g, p[1] * sc.s]; };
    const BA = (t) => { const b = X.ballAt(sc.ball, t); return [b[0] * sc.g, b[1], b[2] * sc.s]; };

    X.IDS.forEach((id) => { if (!sc.act[id] || !sc.act[id].k.length) fail(where, 'geen pad voor ' + id); });
    if (fails.length && fails[fails.length - 1].startsWith(where)) return;
    for (const id in sc.act) {
        const k = sc.act[id].k;
        k.forEach((q, i) => {
            if (!q.every(Number.isFinite)) fail(where, `${id}: geen getal`);
            if (i && q[0] < k[i - 1][0] - 1e-9) fail(where, `${id}: de tijd loopt terug`);
        });
    }
    sc.ball.forEach((q, i) => {
        if (!q.every(Number.isFinite)) fail(where, 'bal: geen getal');
        if (i && q[0] < sc.ball[i - 1][0] - 1e-9) fail(where, 'bal: de tijd loopt terug');
    });
    if (sc.truth !== (yes ? 0 : 1)) fail(where, 'het goede antwoord staat verkeerd');
    if (!(sc.rp[0] >= 0 && sc.tKey > sc.rp[0] && sc.tKey < sc.rp[1] && sc.rp[1] <= sc.T + 1e-9)) fail(where, 'de herhaling klopt niet');
    if (sc.cams.length !== X.KINDS[kind].cams.length) fail(where, 'cameras en namen tellen niet gelijk');
    // everyone on the pitch, the ball sensible, the cameras on our side of the pitch (the near stand is cut away there)
    for (let t = 0; t <= sc.T + 1e-9; t += 0.05) {
        for (const id in sc.act) {
            const p = X.at(sc.act[id].k, t);
            if (Math.abs(p[0]) > GX + 1 || Math.abs(p[1]) > C.FIELD_L / 2 - 0.5) { fail(where, `${id} buiten het veld op t=${t.toFixed(2)}`); break; }
        }
        const b = X.ballAt(sc.ball, t);
        if (Math.abs(b[0]) > GX + C.GOAL_DEPTH || Math.abs(b[2]) > C.FIELD_L / 2 || b[1] < C.BALL_SIZE - 1e-6 || b[1] > 14) {
            fail(where, `bal raar op t=${t.toFixed(2)}`);
            break;
        }
    }
    sc.cams.forEach((c, i) => {
        if (Math.abs(c.pos.x) > GX - 1 || c.pos.z < -C.FIELD_L / 2 || c.pos.y < 2) fail(where, `camera ${i + 1} staat op een rare plek`);
    });
    // nobody on top of anybody at the moment that counts (the contact itself aside)
    const contact = kind === 'penalty' || kind === 'card' ? ['Aatt', 'Ddef'] : [];
    for (let i = 0; i < X.IDS.length; i++) for (let j = i + 1; j < X.IDS.length; j++) {
        const a = X.IDS[i], b = X.IDS[j];
        if (contact.includes(a) && contact.includes(b)) continue;
        const p = P(a, sc.tKey), q = P(b, sc.tKey);
        if (Math.hypot(p[0] - q[0], p[1] - q[1]) < 2) fail(where, `${a} en ${b} staan op elkaar`);
    }

    if (kind === 'offside') {
        const tp = sc.tKey, atk = P('Aatt', tp);
        const ds = ['Dk', 'Datt', 'Dlw', 'Drw', 'Ddef'].map(id => P(id, tp)[0]).sort((x, y) => y - x);
        const margin = atk[0] - ds[1];                       // past their second-last man
        if ((margin > 0) !== (sc.truth === 1)) fail(where, `buitenspel klopt niet (marge ${margin.toFixed(2)})`);
        if (Math.abs(margin) < 0.27) fail(where, `te krap om te zien (${margin.toFixed(2)})`);
        if (Math.abs(margin - sc.margin) > 1e-6) fail(where, 'de marge is niet wat de herhaling toont');
        if (Math.abs(cmIn(sc.detail) - Math.abs(margin) * X.UNIT_CM) > 1) fail(where, `${sc.detail} klopt niet`);
        if (ds[0] < GX - 8) fail(where, 'de keeper is niet de laatste man');
        if (BA(tp)[0] > atk[0] - 5) fail(where, 'de bal is niet achter hem bij de pass');
        if (Math.abs(sc.fx.lines.a * sc.g - atk[0]) > 1e-6 || Math.abs(sc.fx.lines.d * sc.g - ds[1]) > 1e-6) fail(where, 'de lijnen liggen verkeerd');
        // the goal: between the posts, under the bar
        let scored = false;
        for (let t = tp; t <= sc.T; t += 0.005) {
            const b = BA(t);
            if (b[0] >= GX + 0.5) {
                scored = Math.abs(b[2]) < C.GOAL_W / 2 - 0.9 && b[1] < C.GOAL_H - 1;
                break;
            }
        }
        if (!scored) fail(where, 'de goal gaat er niet netjes in');
    }

    if (kind === 'penalty') {
        const tc = sc.tKey, ck = sc.check, att = P('Aatt', tc);
        if (!(att[0] > GX - C.PEN_DEPTH + 1 && Math.abs(att[1]) < C.PEN_WIDTH / 2 - 1)) fail(where, 'het contact is niet in de zestien');
        const u = [ck.slideDir.x * sc.g, ck.slideDir.z * sc.s];
        const foot = (t) => { const p = P('Ddef', t); return [p[0] + u[0] * X.FOOT, p[1] + u[1] * X.FOOT]; };
        const dist = (t) => { const f = foot(t), b = BA(t); return Math.hypot(f[0] - b[0], f[1] - b[2]); };
        const dirAt = (t0, t1) => { const a = BA(t0), b = BA(t1); return Math.atan2(b[2] - a[2], b[0] - a[0]); };
        let minD = Infinity;
        for (let t = ck.tf - 0.3; t <= ck.tf + 0.22; t += 0.004) minD = Math.min(minD, dist(t));
        if (ck.foul) {
            if (minD < 1.25) fail(where, `zijn voet komt te dicht bij de bal (${minD.toFixed(2)})`);
            const f = foot(tc);
            if (Math.hypot(f[0] - att[0], f[1] - att[1]) > 0.3) fail(where, 'zijn voet komt niet bij de man');
            const turn = ang(dirAt(tc - 0.1, tc) - dirAt(tc, tc + 0.3));
            if (turn > 5) fail(where, `de bal verandert van richting zonder dat iemand hem raakt (${turn.toFixed(0)}°)`);
        } else {
            if (dist(ck.tf) > 0.35) fail(where, 'zijn voet komt niet bij de bal');
            if (!(ck.tf < tc - 0.05)) fail(where, 'de bal is niet duidelijk eerst');
            const turn = ang(dirAt(ck.tf - 0.1, ck.tf) - dirAt(ck.tf, ck.tf + 0.2));
            if (turn < 25) fail(where, `de bal verandert te weinig van richting (${turn.toFixed(0)}°)`);
            // and then the man trips over him: the defender lies across his path
            const c = P('Ddef', tc), back = [c[0] - u[0] * 4, c[1] - u[1] * 4];
            const k = Math.max(0, Math.min(1, ((att[0] - c[0]) * (back[0] - c[0]) + (att[1] - c[1]) * (back[1] - c[1])) / 16));
            const off = Math.hypot(att[0] - (c[0] + (back[0] - c[0]) * k), att[1] - (c[1] + (back[1] - c[1]) * k));
            if (off > 1.2) fail(where, `hij struikelt nergens over (${off.toFixed(2)} ernaast)`);
        }
    }

    if (kind === 'card') {
        const tc = sc.tKey, ck = sc.check, att = P('Aatt', tc);
        const kOf = (a) => (a - ck.aC) / (GX - ck.aC), mid = (a) => ck.bC * (1 - kOf(a)), half = (a) => 4 + 11 * kOf(a);
        // > 0: inside the corridor by that much; < 0: outside by that much
        const inLane = (p) => {
            const k = kOf(p[0]);
            if (k < 0) return p[0] - ck.aC;
            if (k > 1) return GX - p[0];
            return half(p[0]) - Math.abs(p[1] - mid(p[0]));
        };
        const cov = inLane(P('Dlw', tc));
        if ((cov > 0) !== (sc.truth === 1)) fail(where, `de dekking klopt niet (${cov.toFixed(2)}, ${ck.how})`);
        if (Math.abs(cov) < 1.4) fail(where, `de dekking is te krap om te zien (${cov.toFixed(2)})`);
        ['Datt', 'Drw'].forEach((id) => { if (inLane(P(id, tc)) > -1.4) fail(where, `${id} staat ook (bijna) in de baan`); });
        if (att[0] > GX - C.PEN_DEPTH - 1) fail(where, 'de overtreding is in de zestien');
        if (P('Ddef', tc)[0] > att[0]) fail(where, 'de overtreder komt niet van achteren');
        if (Math.abs(att[0] - ck.aC) > 1e-6 || Math.abs(att[1] - ck.bC) > 1e-6) fail(where, 'de baan begint niet bij hem');
    }

    if (kind === 'goalline') {
        const tB = sc.tKey, b = BA(tB);
        const e = b[0] - GX - X.BALL_R;                     // its nearest point past the line
        if ((e > 0) !== (sc.truth === 0)) fail(where, `de doellijn klopt niet (${e.toFixed(3)})`);
        if (Math.abs(e) < 0.05) fail(where, `te krap (${e.toFixed(3)})`);
        if (Math.abs(e - sc.margin) > 1e-6) fail(where, 'de marge is niet wat de herhaling toont');
        if (Math.abs(cmIn(sc.detail) - Math.abs(e) * X.UNIT_CM) > 1) fail(where, `${sc.detail} klopt niet`);
        if (Math.abs(b[1] - C.BALL_SIZE) > 1e-6) fail(where, 'de bal is niet op de grond bij de stuit');
        if (Math.abs(b[2]) > C.GOAL_W / 2 - 1.5) fail(where, 'de stuit is niet tussen de palen');
        let deepest = -Infinity, tDeep = 0;
        for (let t = sc.rp[0]; t <= sc.rp[1]; t += 0.002) { const q = BA(t); if (q[0] > deepest) { deepest = q[0]; tDeep = t; } }
        if (Math.abs(tDeep - tB) > 0.01) fail(where, 'de bal komt ergens anders verder dan bij de stuit');
        if (Math.abs(sc.fx.goalLine.x * sc.g - (GX - X.LINE_W / 2)) > 1e-6) fail(where, 'de getekende doellijn ligt verkeerd');
    }
}

// ---------------------------------------------------------------- 2. the plan
function checkPlan(sim) {
    const X = sim.__vg.V._test;
    for (let seed = 1; seed <= 300; seed++) {
        const p = X.plan(seed), where = `plan ${seed}`;
        if (p.length !== X.ROUNDS) { fail(where, `${p.length} rondes`); continue; }
        Object.keys(X.KINDS).forEach((k) => {
            const r = p.filter(x => x.kind === k);
            if (r.length !== 2 || r[0].yes === r[1].yes) fail(where, `${k} niet twee keer, één keer elk antwoord`);
        });
        p.forEach((r, i) => {
            if (i && r.kind === p[i - 1].kind) fail(where, 'twee keer dezelfde soort achter elkaar');
            if (!(r.d >= 0 && r.d <= 1)) fail(where, 'moeilijkheid buiten 0..1');
        });
        if (p[X.ROUNDS - 1].d < p[0].d + 0.6) fail(where, 'wordt niet moeilijker');
    }
}

// ---------------------------------------------------------------- 3. whole games
function playGame(gameSeed, pattern) {
    const sim = load(gameSeed);
    const V = sim.__vg.V, X = V._test;
    const where = `spel ${gameSeed}`;
    V.start({ seed: gameSeed * 7 + 1 });
    const answered = new Set();
    const did = {};
    let frames = 0;
    try {
        while (frames++ < 60 * 60 * 8) {
            sim.__advance(1000 / 60);
            V.frame(1 / 60);
            const st = X.state();
            if (!st) { fail(where, 'het spel is gestopt'); return; }
            if (st.phase === 'done') break;
            const nums = [sim.__vg.ball.position.x, sim.__vg.ball.position.y, sim.__vg.ball.position.z,
                ...[...sim.__vg.team1, ...sim.__vg.team2].flatMap(p => [p.position.x, p.position.z])];
            if (nums.some(n => !Number.isFinite(n))) { fail(where, `geen getal in ronde ${st.i + 1} (${st.phase})`); return; }
            // the replay controls, once
            if (st.phase === 'review' && !did.controls) {
                did.controls = true;
                const rp = st.sc.rp;
                X.step(-100000);
                if (Math.abs(X.state().t - rp[0]) > 1e-9) fail(where, 'terugspoelen stopt niet aan het begin');
                X.step(30);
                if (Math.abs(X.state().t - (rp[0] + 0.5)) > 1e-6) fail(where, '30 frames vooruit is geen halve seconde');
                if (X.state().playing) fail(where, 'spoelen pauzeert de herhaling niet');
                X.togglePlay();
                if (!X.state().playing) fail(where, 'afspelen werkt niet');
                X.nextCam();
                if (X.state().cam !== 1) fail(where, 'van camera wisselen werkt niet');
                X.step(100000);
                if (Math.abs(X.state().t - rp[1]) > 1e-9) fail(where, 'vooruitspoelen stopt niet aan het eind');
                X.togglePlay();
                if (Math.abs(X.state().t - rp[0]) > 1e-9 || !X.state().playing) fail(where, 'afspelen aan het eind begint niet opnieuw');
            }
            if (st.phase === 'review' && !answered.has(st.i) && st.pt > 1.2 + (st.i % 3) * 0.7) {
                const how = pattern[st.i];
                if (how !== 'late') { X.answer(how); answered.add(st.i); }
            }
        }
    } catch (e) {
        fail(where, 'crash: ' + String(e && e.stack || e).split('\n').slice(0, 3).join(' | '));
        return;
    }
    const st = X.state();
    if (!st || st.phase !== 'done') { fail(where, `niet klaar (${st && st.phase}, ronde ${st && st.i + 1})`); return; }
    const res = st.results;
    if (res.length !== X.ROUNDS) fail(where, `${res.length} uitslagen`);
    res.forEach((r, i) => {
        const how = pattern[i];
        if (how === 'right' && !r.right) fail(where, `ronde ${i + 1} goed beantwoord maar fout gerekend`);
        if (how === 'wrong' && (r.right || r.pts)) fail(where, `ronde ${i + 1} fout beantwoord maar goed gerekend`);
        if (how === 'late' && (!r.late || r.right || r.pts)) fail(where, `ronde ${i + 1} te laat maar niet zo gerekend`);
        if (r.right && (r.pts < 100 || r.pts > 175)) fail(where, `ronde ${i + 1}: ${r.pts} punten`);
    });
    const sum = res.reduce((a, r) => a + r.pts, 0);
    if (sum !== st.points) fail(where, `punten tellen niet op (${sum} ≠ ${st.points})`);
    // every round through every step, in order
    for (let i = 0; i < X.ROUNDS; i++) {
        const steps = st.log.filter(x => x.startsWith(i + ':')).map(x => x.split(':')[1]).join('>');
        if (steps !== 'intro>live>call>review>reveal') fail(where, `ronde ${i + 1}: ${steps}`);
    }
    // a quick right answer is worth more than a slow one
    const rights = res.map((r, i) => ({ r, i })).filter(x => x.r.right);
    V.stop();
    if (sim.__vg.STATE.varGame) fail(where, 'stoppen laat de minigame aan');
    return { points: st.points, rights: rights.length };
}

// ---------------------------------------------------------------- run
const t0 = Date.now();
const sim = load(1);
const seeds = QUICK ? 40 : 160;
const levels = [0, 0.25, 0.5, 0.75, 1];
Object.keys(sim.__vg.V._test.KINDS).forEach((kind) => {
    for (let seed = 1; seed <= seeds; seed++) {
        const d = levels[seed % levels.length];
        checkScene(sim, kind, seed, d, true);
        checkScene(sim, kind, seed, d, false);
    }
});
checkPlan(sim);
const games = [
    [3, ['right', 'right', 'wrong', 'right', 'late', 'right', 'wrong', 'right']],
    [8, ['wrong', 'right', 'right', 'right', 'right', 'right', 'right', 'right']],
    [21, ['late', 'late', 'wrong', 'wrong', 'right', 'right', 'right', 'right']],
];
const played = games.map(([s, p]) => playGame(s, p));

console.log(`\nJIJ BENT DE VAR — TEST  (${((Date.now() - t0) / 1000).toFixed(1)} s)\n`);
Object.keys(counts).forEach(k => console.log(`  ${k.padEnd(9)} ${counts[k]} scènes gebouwd en nagekeken`));
console.log(`  plan      300 spellen van ${sim.__vg.V._test.ROUNDS} rondes`);
played.forEach((r, i) => { if (r) console.log(`  spel ${i + 1}    ${r.rights} goed, ${r.points} punten, alle stappen doorlopen`); });
if (fails.length) {
    console.log(`\nFOUT  ${fails.length}${fails.length >= 400 ? '+' : ''} problemen:`);
    fails.slice(0, 40).forEach(f => console.log('  ' + f));
    process.exitCode = 1;
} else console.log('\nalles in orde\n');

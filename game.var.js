// =====================================================
// PITCH ROYALE — Jij bent de VAR
// A minigame on the real pitch, with the real players and officials: eight
// incidents, each played live first, after which the replay is yours. Scrub
// through it frame by frame, switch camera, and decide before the clock runs
// out: goal or offside, penalty or not, red or yellow, over the line or not.
// The answer is checked against what really happened in the scene, shown
// with the lines on the grass and the margin in centimetres. A right call
// scores 100, up to 50 more for a quick one, and 25 extra from three in a row.
//
// The scenes are scripted, not played by the match engine: every player, the
// ball and the officials follow paths in time, so the replay can go back and
// forth to any moment and always shows the same thing. Each game builds eight
// new ones from a random seed, every kind twice (once each way), harder each
// round: an offside from about 1.4 m down to under 20 cm, a ball over the line
// from 50 cm down to a few.
//
//   index.html?test=var           straight in (&seed=7 for the same eight)
//   node tools/vargame-test.js    checks every kind of scene: that what you can
//                                 see in the replay matches the answer it expects
// =====================================================

const VARGAME = (() => {
    const ROUNDS = 8;
    const DECIDE_S = 20;                 // seconds for a decision, from the start of the replay
    const SLOW = 0.35;                   // replay speed
    const INTRO_S = 2.6, CALL_S = 2.2, REVEAL_S = 4.6;
    const UNIT_CM = 10500 / FIELD_W;     // a pitch unit in centimetres (the pitch is 105 m long)
    const GX = FIELD_W / 2;              // the goal line under attack, in the attack's own frame
    const BALL_R = BALL_VISUAL_R;        // the ball as you see it (game.js)
    const AR_OUT = FIELD_L / 2 + 2.6;    // where the assistants run (as in game.referee.js)
    const LINE_W = 0.32;                 // the goal line we draw in the goal-line scene
    const FOOT = 0.6;                    // a sliding player's foot, ahead of his middle
    const BEST_KEY = 'pitchRoyale.varBest';
    const IDS = ['Ak', 'Aatt', 'Alw', 'Arw', 'Adef', 'Dk', 'Datt', 'Dlw', 'Drw', 'Ddef'];

    const KINDS = {
        offside: {
            title: 'Buitenspel?', subject: 'Mogelijk buitenspel', question: 'Telt de goal?',
            answers: ['Goal telt', 'Buitenspel'], moment: 'Moment van de pass',
            rule: 'Stond de aanvaller verder dan de voorlaatste verdediger op het moment van de pass? Dan is het buitenspel.',
            cams: ['Lijncamera', 'Hoofdcamera'],
        },
        penalty: {
            title: 'Strafschop?', subject: 'Mogelijke strafschop', question: 'Is het een strafschop?',
            answers: ['Strafschop', 'Geen strafschop'], moment: 'Moment van het contact',
            rule: 'Speelt de verdediger eerst de bal, dan is het geen strafschop. Raakt hij eerst de man, dan wel.',
            cams: ['Zijkant', 'Bovenaf'],
        },
        card: {
            title: 'Rood of geel?', subject: 'Mogelijke rode kaart', question: 'Welke kaart?',
            answers: ['Rode kaart', 'Gele kaart'], moment: 'Moment van de overtreding',
            rule: 'Staat er niemand meer tussen de aanvaller en het doel (de keeper telt niet mee)? Dan is het rood.',
            cams: ['Overzicht', 'Zijkant'],
        },
        goalline: {
            title: 'Over de lijn?', subject: 'Bal over de lijn?', question: 'Was het een goal?',
            answers: ['Goal', 'Geen goal'], moment: 'Moment van de stuit',
            rule: 'Alleen als de hele bal over de hele lijn is, is het een goal.',
            cams: ['Boven de lijn', 'Laag bij de paal'],
        },
    };

    // ------------------------------------------------ small tools
    function mulberry(seed) {
        let s = seed >>> 0 || 1;
        return () => {
            s = (s + 0x6D2B79F5) >>> 0;
            let t = s;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }
    const lerp = (a, b, k) => a + (b - a) * k;
    const jit = (rand, k) => 1 - k + rand() * 2 * k;            // 1 ± k
    const add = (p, q, k = 1) => [p[0] + q[0] * k, p[1] + q[1] * k];
    const unit = (x, y) => { const l = Math.hypot(x, y) || 1; return [x / l, y / l]; };
    const clampAB = (p) => [Math.max(-GX + 3, Math.min(GX - 3, p[0])), Math.max(-(FIELD_L / 2 - 3), Math.min(FIELD_L / 2 - 3, p[1]))];
    const cm = (u) => Math.max(1, Math.round(Math.abs(u) * UNIT_CM));
    const bk = (t, p, y = BALL_SIZE, h = 0) => [t, p[0], y, p[1], h];
    // the ball's height for a given height of its middle (the mesh sits lower inside the ball: game.js)
    const ballY = (mid) => mid + BALL_SIZE - BALL_R;

    // where a path is at time t: [t, x, z] keys, held before the first and after the last
    function at(keys, t) {
        if (!keys.length) return [0, 0];
        if (t <= keys[0][0]) return [keys[0][1], keys[0][2]];
        for (let i = 1; i < keys.length; i++) {
            const k1 = keys[i];
            if (t <= k1[0]) {
                const k0 = keys[i - 1], f = (t - k0[0]) / ((k1[0] - k0[0]) || 1);
                return [k0[1] + (k1[1] - k0[1]) * f, k0[2] + (k1[2] - k0[2]) * f];
            }
        }
        const l = keys[keys.length - 1];
        return [l[1], l[2]];
    }
    // its speed at time t (the stretch t is in, looking forward), per second
    function vel(keys, t) {
        for (let i = 1; i < keys.length; i++) {
            if (t < keys[i][0]) {
                const k0 = keys[i - 1], k1 = keys[i];
                if (t < k0[0]) return [0, 0];
                const dt = (k1[0] - k0[0]) || 1;
                return [(k1[1] - k0[1]) / dt, (k1[2] - k0[2]) / dt];
            }
        }
        return [0, 0];
    }
    // the way he last moved, at or before t (a man on the ground keeps facing it)
    function heading(keys, t) {
        let i = keys.length - 1;
        while (i > 0 && keys[i - 1][0] > t) i--;
        for (; i > 0; i--) {
            const dx = keys[i][1] - keys[i - 1][1], dz = keys[i][2] - keys[i - 1][2];
            if (Math.hypot(dx, dz) > 0.05) return { x: dx, z: dz };
        }
        return null;
    }
    // the ball: [t, x, y, z, h] keys; h lifts the stretch after that key in an arc
    function ballAt(keys, t) {
        if (t <= keys[0][0]) return [keys[0][1], keys[0][2], keys[0][3]];
        for (let i = 1; i < keys.length; i++) {
            const k1 = keys[i];
            if (t <= k1[0]) {
                const k0 = keys[i - 1], f = (t - k0[0]) / ((k1[0] - k0[0]) || 1);
                return [k0[1] + (k1[1] - k0[1]) * f, k0[2] + (k1[2] - k0[2]) * f + (k0[4] || 0) * 4 * f * (1 - f), k0[3] + (k1[3] - k0[3]) * f];
            }
        }
        const l = keys[keys.length - 1];
        return [l[1], l[2], l[3]];
    }
    const inside = (spans, t) => spans.some(([a, b]) => t >= a && t <= b);
    function lastBefore(times, t) {
        let best = null;
        times.forEach((x) => { if (x <= t && (best === null || x > best)) best = x; });
        return best;
    }

    // ------------------------------------------------ writing a scene
    // Written in the attack's own frame: a towards the goal under attack (its
    // line at a = GX), b across. place() turns it onto the pitch: x = g·a
    // (g: the way the attacking side plays), z = s·b (s: mirrored or not).
    // Ids: A = the attacking side, D = the defending side; k keeper, att, lw,
    // rw, def the roles (game.js: buildPlayers).
    function script(rand) {
        const team = rand() < 0.5 ? 1 : 2;
        return {
            team, g: team === 1 ? 1 : -1, s: rand() < 0.5 ? 1 : -1, act: {}, ball: [],
            off: { ref: { k: [], pose: [] }, arR: { k: [], pose: [] }, arL: { k: [], pose: [] } },
            sounds: [], flashes: [],
        };
    }
    function actor(S, id) {
        return S.act[id] || (S.act[id] = { k: [], slide: [], down: [], fall: [], kick: [], dive: [] });
    }
    function path(S, id, ...keys) {
        const a = actor(S, id);
        a.k.push(...keys);
        return a;
    }
    // the ball at a man's feet from t0 to t1, a little ahead of him, with small touches
    function carry(S, id, t0, t1, ahead) {
        const keys = actor(S, id).k;
        let dir = [1, 0];
        for (let t = t0; ; t += 0.05) {
            const tt = Math.min(t, t1);
            const v = vel(keys, tt), sp = Math.hypot(v[0], v[1]);
            if (sp > 0.5) dir = [v[0] / sp, v[1] / sp];
            const p = at(keys, tt);
            const touch = ahead * (1 + 0.16 * Math.sin(tt * 13));
            S.ball.push([tt, p[0] + dir[0] * touch, BALL_SIZE, p[1] + dir[1] * touch, 0]);
            if (tt >= t1) break;
        }
        return S.ball[S.ball.length - 1];
    }
    // the assistant in the half under attack follows `keys` ([t, a]); the other stands in his own half
    function assistants(S, keys) {
        const atk = S.g > 0 ? 'arR' : 'arL', other = S.g > 0 ? 'arL' : 'arR';
        const bOf = (id) => (id === 'arR' ? AR_OUT : -AR_OUT) * S.s;
        S.off[atk].k = keys.map(([t, a]) => [t, a, bOf(atk)]);
        S.off[other].k = [[0, -22, bOf(other)]];
    }
    const W = (S, a, b) => ({ x: S.g * a, z: S.s * b });
    function place(S, extra) {
        const g = S.g, s = S.s;
        const act = {};
        for (const id in S.act) {
            const a = S.act[id];
            act[id] = {
                k: a.k.map(([t, aa, bb]) => [t, g * aa, s * bb]),
                slide: a.slide, down: a.down, fall: a.fall, kick: a.kick,
                dive: a.dive.map(([t0, t1, side]) => [t0, t1, s * side]),
            };
        }
        const off = {};
        for (const id in S.off) {
            const o = S.off[id];
            off[id] = {
                k: o.k.map(([t, aa, bb]) => [t, g * aa, s * bb]),
                pose: o.pose.map(([t0, t1, p, fa, fb]) => [t0, t1, p, g * (fa || 0), s * (fb || 0)]),
            };
        }
        return Object.assign({
            team: S.team, g, s, act, off, sounds: S.sounds, flashes: S.flashes,
            ball: S.ball.map(([t, a, y, b, h]) => [t, g * a, y, s * b, h]),
        }, extra);
    }

    // ------------------------------------------------ the four kinds of scene
    // Each takes the difficulty d (0 easy … 1 hard) and `yes`: whether the
    // first answer is the right one (the goal stands, a penalty, red, a goal).

    // A ball over the top, the runner on their line; he scores. Offside or not,
    // at the moment of the pass: his middle against their second-last man's.
    function sceneOffside(rand, d, yes) {
        const S = script(rand);
        const off = !yes;
        const mag = lerp(2.6, 0.32, d) * jit(rand, 0.15);
        const m = off ? mag : -mag;                          // how far past the line he is at the pass
        const aL = 52 + rand() * 8;                          // their line (the second-last man) at the pass
        const bR = 12 + rand() * 14, bP = -(8 + rand() * 12);
        const tp = 2.0, tr = tp + 0.62, aR = aL + m;
        const aS = Math.min(aR + 25, GX - 14), bS = bR * 0.35, ts = tr + 0.4, tg = ts + 0.3, T = ts + 1.9;
        // the runner: waits on their line, goes as the pass is played, takes it in his stride, scores
        const run = path(S, 'Aatt', [0, aR - 15, bR + 5], [tp - 0.9, aR - 12, bR + 3], [tp, aR, bR], [tr, aR + 16, bR - 3],
            [ts, aS, bS], [ts + 0.5, aS + 7, bS - 2], [T, aS + 9, bS + 6]);
        run.kick.push(ts - 0.04);
        const passer = path(S, 'Arw', [0, aL - 40, bP], [tp, aL - 27, bP + 2], [tp + 1.2, aL - 18, bP + 4], [T, aL - 10, bP + 5]);
        passer.kick.push(tp - 0.05);
        carry(S, 'Arw', 0, tp, 1.4);
        const rv = vel(run.k, tr - 0.01), rl = Math.hypot(rv[0], rv[1]) || 1;
        S.ball.push(bk(tr, add(at(run.k, tr), [rv[0] / rl, rv[1] / rl], 1.3)));
        carry(S, 'Aatt', tr + 0.05, ts, 1.4);
        const bG = -Math.sign(bS || 1) * (4 + rand() * 4.5), yG = 1.8 + rand() * 3.5;
        S.ball[S.ball.length - 1][4] = 0.6;
        S.ball.push(bk(tg, [GX + 0.8, bG], yG), bk(ts + 0.48, [GX + GOAL_DEPTH - 0.8, bG * 0.96], Math.max(BALL_SIZE, yG * 0.5)),
            bk(ts + 0.85, [GX + GOAL_DEPTH - 1.1, bG * 0.94]));
        // their back line: the last man steps up as the pass goes, the others are higher up
        const bD = bR - (4 + rand() * 9);
        path(S, 'Ddef', [0, aL + 4, bD + 2], [tp, aL, bD], [tp + 0.5, aL + 2.5, bD - 1], [ts, aL + 13, bD * 0.6], [T, aL + 17, bD * 0.5]);
        path(S, 'Dlw', [0, aL - 4, bD - 20], [tp, aL - 7, bD - 22], [ts, aL + 6, bD - 14], [T, aL + 10, bD - 10]);
        path(S, 'Drw', [0, aL - 30, bP + 10], [tp, aL - 25, bP + 5], [T, aL - 16, bP + 3]);
        path(S, 'Datt', [0, aL - 52, -bP], [T, aL - 42, -bP * 0.5]);
        const kp = path(S, 'Dk', [0, GX - 4, 0], [ts, GX - 4.5, bS * 0.25], [ts + 0.5, GX - 4.5, bS * 0.25 - Math.sign(bG) * 2.5]);
        kp.dive.push([ts + 0.08, ts + 0.8, -Math.sign(bG)]);
        path(S, 'Alw', [0, aL - 22, -bR - 6], [T, aL - 4, -bR * 0.6]);
        path(S, 'Adef', [0, aL - 58, 4], [T, aL - 44, 2]);
        path(S, 'Ak', [0, -(GX - 4), 0]);
        S.off.ref.k = [[0, aL - 34, -bR * 0.4 - 12], [ts + 0.4, aS - 28, bS - 18], [T, aS - 25, bS - 16]];
        S.off.ref.pose.push([tg + 0.6, T + 9, 'point', -1, 0]);
        S.sounds.push([tg + 0.6, 'short']);
        S.flashes.push([tg + 0.05, 'Goal']);
        assistants(S, [[0, aL + 4], [tp, aL], [ts, aL + 13], [T, aL + 17]]);
        const xL = S.g * aL, zMid = S.s * (bR + bD) / 2;
        return place(S, {
            kind: 'offside', d, truth: off ? 1 : 0, callIdx: 0, call: 'Goal', T, tKey: tp, rp: [tp - 1.5, tp + 1.0],
            // the line camera stands exactly level with their line, high enough to look over the assistant (who runs on it)
            cams: [
                { pos: { x: xL, y: 30, z: FIELD_L / 2 + 48 }, look: { x: xL, y: 0.5, z: zMid }, fov: 15 },
                { pos: { x: S.g * (aL - 20), y: 36, z: FIELD_L / 2 + 74 }, look: { x: xL, y: -4, z: zMid }, fov: 22 },
            ],
            fx: { lines: { a: S.g * aR, d: xL } },
            margin: m, verdict: off ? 'Buitenspel' : 'Goal telt',
            detail: off ? `${cm(m)} cm buitenspel` : `Geen buitenspel: ${cm(m)} cm erachter`,
        });
    }

    // Into the box, a defender slides in across his path. Did his foot get the
    // ball first (it changes course), or the man (the ball rolls on)?
    function scenePenalty(rand, d, yes) {
        const S = script(rand);
        const foul = yes;
        const aC = 80 + rand() * 6, bC = 5 + rand() * 9;      // where the man is caught, in the box
        const C = [aC, bC];
        const v = 21, tc = 2.3, T = tc + 2.6;
        const dir = unit(26, -(16 + rand() * 6));            // diagonally in, towards goal
        // the slide, across his path (on the side that stays on the pitch): one that gets the
        // ball comes from a little in front of him, a late one from a little behind; the
        // harder, the more both come straight from the side
        const lean = foul ? lerp(0.35, 0.15, d) : -lerp(0.45, 0.15, d);
        const slideFor = (sd) => {
            const p = [-dir[1] * sd, dir[0] * sd];
            return unit(dir[0] * lean + p[0], dir[1] * lean + p[1]);
        };
        const onPitch = (uu) => { const st = add(C, uu, -(15 + FOOT)); return st[0] < GX - 5 && Math.abs(st[1]) < FIELD_L / 2 - 5; };
        let side = rand() < 0.5 ? 1 : -1;
        if (!onPitch(slideFor(side))) side = -side;
        const u = slideFor(side);
        const perp = [-dir[1] * side, dir[0] * side];
        const hA = lerp(4.0, 1.6, d) * jit(rand, 0.1);       // clean: how far ahead the ball is when he gets it
        const dA = lerp(4.5, 2.1, d) * jit(rand, 0.1);       // foul: how far ahead it is when his foot arrives
        const tf = foul ? tc : tc - hA / v;                  // his foot crosses the run at C
        const att = path(S, 'Aatt', [0, ...add(C, dir, -v * tc)], [tc, aC, bC], [tc + 0.35, ...add(C, dir, 3.2)]);
        att.fall.push([tc + 0.06, tc + 1.7]);                // still on his feet at the contact itself
        const cAt = (k) => add(C, u, k - FOOT);              // his middle with his foot k along the slide past C
        const sl = path(S, 'Ddef', [0, ...cAt(-15)], [tf - 0.3, ...cAt(-7)], [tf, ...cAt(0)], [tf + 0.22, ...cAt(2.2)], [tf + 1.4, ...cAt(2.6)]);
        sl.slide.push([tf - 0.3, tf + 0.22]);
        sl.down.push([tf + 0.22, tf + 1.0]);
        let ballEnd;
        if (foul) {
            const tk = tc - lerp(0.35, 0.14, d);             // his last touch, a little long
            carry(S, 'Aatt', 0, tk, 1.5);
            att.kick.push(tk - 0.06);
            ballEnd = add(C, dir, dA + 7.5);
            S.ball.push(bk(tc, add(C, dir, dA)), bk(tc + 0.5, add(C, dir, dA + 5.5)), bk(tc + 1.1, ballEnd));
        } else {
            const t1 = tf - 0.35;
            carry(S, 'Aatt', 0, t1, 1.5);
            att.kick.push(t1 - 0.06);
            const k = lerp(0.95, 0.5, d);                    // harder: it changes course less
            const w = unit(u[0] * k + dir[0] * (1 - k), u[1] * k + dir[1] * (1 - k));
            ballEnd = clampAB(add(C, w, 12.5));
            S.ball.push(bk(tf, C, BALL_SIZE, 1.1), bk(tf + 0.28, add(C, w, 6)), bk(tf + 0.75, add(C, w, 10.5)), bk(tf + 1.35, ballEnd));
        }
        const kp = path(S, 'Dk', [0, GX - 4, 0], [tc - 0.4, GX - 5, bC * 0.3]);
        if (foul) kp.k.push([tc + 1.15, ballEnd[0] + 1.2, ballEnd[1]]);
        else kp.k.push([tc + 1.2, GX - 4.5, bC * 0.4]);
        const pDlw = clampAB(add(add(C, perp, 15), dir, 4));
        path(S, 'Dlw', [0, ...add(pDlw, dir, -8)], [T, ...pDlw]);
        path(S, 'Drw', [0, aC - 30, -bC - 14], [T, aC - 14, -bC - 10]);
        path(S, 'Datt', [0, aC - 50, 12], [T, aC - 38, 8]);
        path(S, 'Alw', [0, aC - 30, -bC - 4], [T, aC - 8, -bC - 6]);
        path(S, 'Arw', [0, aC - 44, bC + 30], [T, aC - 26, bC + 22]);
        path(S, 'Adef', [0, aC - 75, 0], [T, aC - 60, 0]);
        path(S, 'Ak', [0, -(GX - 4), 0]);
        const refEnd = [aC - 16, bC - 22];
        S.off.ref.k = [[0, aC - 42, bC - 30], [tc + 0.9, ...refEnd], [T, ...refEnd]];
        const callPen = rand() < 0.5;
        if (callPen) {
            const spot = [GX - PEN_SPOT, 0];
            S.sounds.push([tc + 0.25, 'double']);
            S.off.ref.pose.push([tc + 0.25, tc + 1.0, 'whistle', 0, 0], [tc + 1.0, T + 9, 'point', spot[0] - refEnd[0], spot[1] - refEnd[1]]);
        }
        assistants(S, [[0, aC + 2], [T, aC + 6]]);
        const Cw = W(S, aC, bC);
        return place(S, {
            kind: 'penalty', d, truth: foul ? 0 : 1, callIdx: callPen ? 0 : 1, call: callPen ? 'Strafschop' : 'Doorspelen',
            T, tKey: tc, rp: [tc - 1.3, tc + 0.9],
            // low from the side; and high from behind his run, where the ball's course reads best
            cams: [
                { pos: { x: Cw.x - S.g * 5, y: 6.5, z: Cw.z + 30 }, look: { x: Cw.x, y: 1.6, z: Cw.z }, fov: 24 },
                { pos: { x: Cw.x - S.g * 9, y: 30, z: Cw.z + 16 }, look: { x: Cw.x + S.g * 2, y: 0, z: Cw.z }, fov: 26 },
            ],
            fx: { ring: Cw },
            margin: foul ? dA : hA, verdict: foul ? 'Strafschop' : 'Geen strafschop',
            detail: foul ? 'Eerst de man: de bal was al voorbij' : 'Eerst de bal: de verdediger speelde hem weg',
            check: { foul, tf, slideDir: { x: S.g * u[0], z: S.s * u[1] }, dir: { x: S.g * dir[0], z: S.s * dir[1] } },
        });
    }

    // Through on goal, tripped from behind outside the box. Red if nobody of
    // theirs is left between him and the goal (the corridor to the posts).
    function sceneCard(rand, d, yes) {
        const S = script(rand);
        const red = yes;
        const aC = 52 + rand() * 9, bC = (rand() - 0.5) * 22;
        const C = [aC, bC];
        const v = 23, tc = 1.7, T = tc + 3.4;
        const dir = unit(GX - aC, -bC * 0.5);
        const att = path(S, 'Aatt', [0, ...add(C, dir, -v * tc)], [tc, aC, bC], [tc + 0.35, ...add(C, dir, 3)]);
        att.fall.push([tc + 0.06, tc + 1.8]);
        carry(S, 'Aatt', 0, tc, 1.5);
        S.ball.push(bk(tc + 0.6, add(C, dir, 8.5)), bk(tc + 1.3, add(C, dir, 11)));
        // the foul: a slide from behind, on his heel
        const sd = rand() < 0.5 ? 1 : -1;
        const perp = [-dir[1] * sd, dir[0] * sd];
        const heel = add(C, dir, -0.8), start = add(add(C, dir, -4.2), perp, 2.8);
        const u = unit(heel[0] - start[0], heel[1] - start[1]);
        const fEnd = add(heel, u, 1.9);
        const fl = path(S, 'Ddef', [0, ...add(add(C, dir, -37), perp, 5)], [tc - 0.3, ...add(start, u, -FOOT)], [tc, ...add(heel, u, -FOOT)],
            [tc + 0.25, ...add(heel, u, 1.6)], [tc + 1.3, ...fEnd]);
        fl.slide.push([tc - 0.3, tc + 0.25]);
        fl.down.push([tc + 0.25, tc + 1.0]);
        // the corridor from him to the posts, and the one defender who may or may not be in it
        const kOf = (a) => (a - aC) / (GX - aC), mid = (a) => bC * (1 - kOf(a)), half = (a) => 4 + 11 * kOf(a);
        let cover, how;
        if (!red) {
            const a1 = aC + lerp(16, 2.5, d) * jit(rand, 0.1);
            cover = [a1, mid(a1) + (rand() * 2 - 1) * Math.max(0, half(a1) - 1.8) * 0.8];
            how = 'between';
        } else if (d < 0.35 || rand() < 0.5) {
            cover = [aC - lerp(12, 2.0, d) * jit(rand, 0.1), bC - sd * (3.5 + rand() * 3)];
            how = 'behind';
        } else {
            const a1 = aC + lerp(16, 6, d) * jit(rand, 0.1);
            const out = half(a1) + lerp(10, 2.2, d) * jit(rand, 0.1);
            let sg = rand() < 0.5 ? 1 : -1;
            if (Math.abs(mid(a1) + sg * out) > FIELD_L / 2 - 5) sg = -sg;
            cover = [a1, mid(a1) + sg * out];
            how = 'wide';
        }
        path(S, 'Dlw', [0, cover[0] - 15, cover[1] + 4], [tc, ...cover], [tc + 0.9, cover[0] + 8, cover[1] - 1], [T, cover[0] + 10, cover[1] - 1]);
        path(S, 'Drw', [0, aC - 45, -bC * 0.5 - 18 * sd], [T, aC - 24, -bC * 0.5 - 14 * sd]);
        path(S, 'Datt', [0, aC - 60, 10], [T, aC - 45, 6]);
        path(S, 'Dk', [0, GX - 4, 0], [tc, GX - 6, bC * 0.2], [T, GX - 7, bC * 0.25]);
        path(S, 'Alw', [0, aC - 42, bC - 18 * sd], [T, aC - 14, bC - 14 * sd]);
        path(S, 'Arw', [0, aC - 55, -bC + 16 * sd], [T, aC - 35, -bC + 12 * sd]);
        path(S, 'Adef', [0, aC - 80, 0], [T, aC - 66, 0]);
        path(S, 'Ak', [0, -(GX - 4), 0]);
        const refEnd = add(fEnd, [-9, -7 * sd]);
        S.off.ref.k = [[0, aC - 46, bC + 20 * sd], [tc + 1.5, ...refEnd], [T, ...refEnd]];
        const callRed = rand() < 0.5;
        S.sounds.push([tc + 0.2, 'double']);
        S.off.ref.pose.push([tc + 0.2, tc + 0.9, 'whistle', 0, 0], [tc + 1.6, T + 9, callRed ? 'red' : 'yellow', fEnd[0] - refEnd[0], fEnd[1] - refEnd[1]]);
        assistants(S, [[0, aC + 5], [T, aC + 10]]);
        const look = W(S, (aC + GX) / 2 - 6, bC * 0.5), Cw = W(S, aC, bC);
        return place(S, {
            kind: 'card', d, truth: red ? 0 : 1, callIdx: callRed ? 0 : 1, call: callRed ? 'Rode kaart' : 'Gele kaart',
            T, tKey: tc, rp: [tc - 1.4, tc + 0.9],
            cams: [
                { pos: { x: look.x, y: 64, z: FIELD_L / 2 + 64 }, look: { x: look.x, y: 0, z: look.z }, fov: 21 },
                { pos: { x: Cw.x - S.g * 4, y: 7, z: Cw.z + 28 }, look: { x: Cw.x, y: 1.6, z: Cw.z }, fov: 26 },
            ],
            fx: { lane: [W(S, aC, bC - 4), W(S, aC, bC + 4), W(S, GX, 15), W(S, GX, -15)], cover: W(S, cover[0], cover[1]), coverIn: !red },
            margin: red ? (how === 'behind' ? aC - cover[0] : Math.abs(cover[1] - mid(cover[0])) - half(cover[0])) : cover[0] - aC,
            verdict: red ? 'Rode kaart' : 'Gele kaart',
            detail: red ? (how === 'wide' ? 'Rood: de laatste verdediger stond te ver weg' : 'Rood: niemand meer tussen hem en het doel')
                : 'Geel: er stond nog een verdediger tussen',
            check: { aC, bC, how },
        });
    }

    // A shot off the underside of the bar, down on the line and out again.
    // A goal only if the whole ball was over the whole line when it came down.
    function sceneGoalLine(rand, d, yes) {
        const S = script(rand);
        const goal = yes;
        const e = lerp(0.9, 0.06, d) * jit(rand, 0.15) * (goal ? 1 : -1);    // its nearest point past the line
        const bb = (rand() - 0.5) * 12;
        const bS = bb * 0.4 + (rand() - 0.5) * 10;
        const tpass = 0.9, trec = 1.45, tsh = 1.75, tbar = tsh + 0.4, tB = tbar + 0.14, T = tB + 2.3;
        const sh = path(S, 'Aatt', [0, 61, bS + 10], [trec, 72, bS + 1], [tsh, 74.5, bS], [tsh + 0.6, 80, bS - 1], [T, 82, bS - 2]);
        sh.kick.push(tsh - 0.04);
        const ps = path(S, 'Arw', [0, 50, bS - 22], [tpass, 55, bS - 20], [T, 62, bS - 16]);
        ps.kick.push(tpass - 0.05);
        carry(S, 'Arw', 0, tpass, 1.4);
        const rv = vel(sh.k, trec - 0.01), rl = Math.hypot(rv[0], rv[1]) || 1;
        S.ball.push(bk(trec, add(at(sh.k, trec), [rv[0] / rl, rv[1] / rl], 1.3)));
        carry(S, 'Aatt', trec + 0.04, tsh, 1.3);
        S.ball[S.ball.length - 1][4] = 1.0;
        const B = [GX + BALL_R + e, bb * 0.96];
        const back = [GX - 11.2, bb * 0.85 + 3.3];
        // off the underside of the bar, never further in than where it comes down
        S.ball.push(bk(tbar, [Math.min(GX - 0.1, B[0] - 0.35), bb], ballY(GOAL_H - 0.24 - BALL_R)), bk(tB, B, BALL_SIZE, 2.4),
            bk(tB + 0.42, [GX - 6, bb * 0.9 + 2], 3.4, 0.5), bk(tB + 0.78, [GX - 9.5, bb * 0.85 + 3]), bk(tB + 1.02, back, BALL_SIZE, 6));
        const clr = clampAB([GX - 42, back[1] + 26 * (bb >= 0 ? 1 : -1)]);
        S.ball.push(bk(tB + 1.75, clr), bk(tB + 2.3, clampAB(add(clr, [-6, 4 * Math.sign(clr[1] || 1)]))));
        const dd = path(S, 'Ddef', [0, 82, bS - 9], [tB + 0.4, GX - 15, bb * 0.85 + 6], [tB + 1.0, back[0] - 1.4, back[1] + 0.3], [T, GX - 18, bb * 0.85 + 8]);
        dd.kick.push(tB + 0.98);
        // the keeper goes the wrong way: away from the near side, where the replay cameras stand
        const ks = -S.s, kb = B[1] + ks * 6.5;
        const kp = path(S, 'Dk', [0, GX - 4, bS * 0.2], [tsh, GX - 4.2, bS * 0.3], [tsh + 0.4, GX - 4.2, kb],
            [tB + 1.6, GX - 4.2, kb], [T, GX - 4, bb * 0.4]);
        kp.dive.push([tsh + 0.06, tsh + 0.85, ks]);
        path(S, 'Dlw', [0, 78, bS + 15], [T, 86, bS + 9]);
        path(S, 'Drw', [0, 66, -bS - 26], [T, 76, -bS - 22]);
        path(S, 'Datt', [0, 30, 4], [T, 40, 8]);
        path(S, 'Alw', [0, 58, -bS - 20], [T, 80, -bS - 22]);
        path(S, 'Adef', [0, 5, 0], [T, 18, 0]);
        path(S, 'Ak', [0, -(GX - 4), 0]);
        S.off.ref.k = [[0, 44, bS - 30], [T, 64, bS - 26]];
        const callGoal = rand() < 0.5;
        if (callGoal) {
            S.sounds.push([tB + 0.5, 'short']);
            S.off.ref.pose.push([tB + 0.6, T + 9, 'point', -1, 0]);
        }
        assistants(S, [[0, 88], [tB, GX - 0.5], [T, GX - 0.5]]);
        const Bw = W(S, B[0], B[1]);
        return place(S, {
            kind: 'goalline', d, truth: goal ? 0 : 1, callIdx: callGoal ? 0 : 1, call: callGoal ? 'Goal' : 'Geen goal',
            T, tKey: tB, rp: [tsh - 0.25, tB + 0.8],
            cams: [
                { pos: { x: S.g * (GX - 12), y: 22, z: Bw.z + 16 }, look: { x: S.g * GX, y: 0.4, z: Bw.z }, fov: 20 },
                { pos: { x: S.g * (GX - 7), y: 3, z: Bw.z + 28 }, look: { x: S.g * (GX + 0.3), y: 0.9, z: Bw.z }, fov: 12 },
            ],
            fx: { goalLine: { x: S.g * (GX - LINE_W / 2) }, foot: Bw },
            margin: e, verdict: goal ? 'Goal' : 'Geen goal',
            detail: goal ? `De bal was ${cm(e)} cm over de lijn` : `Er ontbrak ${cm(e)} cm`,
        });
    }

    const BUILD = { offside: sceneOffside, penalty: scenePenalty, card: sceneCard, goalline: sceneGoalLine };
    function buildScene(kind, seed, d, yes) { return BUILD[kind](mulberry(seed), d, yes); }

    // eight rounds: every kind twice (once each way), never the same kind twice in a row, harder each round
    function plan(rand) {
        const kinds = Object.keys(KINDS);
        let order = [];
        for (let tries = 0; tries < 60; tries++) {
            order = [...kinds, ...kinds];
            for (let i = order.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
            if (order.every((k, i) => i === 0 || k !== order[i - 1])) break;
        }
        const yes = {};
        kinds.forEach((k) => { yes[k] = rand() < 0.5 ? [true, false] : [false, true]; });
        return order.map((kind, i) => ({
            kind, yes: yes[kind].shift(), seed: (rand() * 4294967296) >>> 0,
            d: Math.min(1, i / (ROUNDS - 1) * 0.92 + rand() * 0.08),
        }));
    }

    // ------------------------------------------------ the game
    let G = null;          // the game in progress
    let ui = null;         // its overlay
    let fx = null;         // its marks on the grass
    let keyBound = false;

    function readBest() { try { return Math.max(0, parseInt(localStorage.getItem(BEST_KEY), 10) || 0); } catch (_) { return 0; } }
    function writeBest(v) { try { localStorage.setItem(BEST_KEY, String(v)); } catch (_) {} }

    function start(opts = {}) {
        if (G) stop();
        const seed = Number.isFinite(opts.seed) ? opts.seed : (Date.now() ^ Math.floor(Math.random() * 1e9)) >>> 0;
        const rand = mulberry(seed);
        G = {
            seed, rounds: plan(rand), i: -1, points: 0, streak: 0, results: [],
            phase: 'idle', pt: 0, t: 0, prevT: 0, playing: false, frozeOnce: false, left: DECIDE_S,
            cam: 0, camNow: null, dragging: false, sc: null, cast: null, log: [],
        };
        STATE.varGame = true;
        STATE.inputLocked = true;
        $('game-screen')?.classList.add('is-vargame');
        buildUi();
        buildFx();
        // no arrow, no stamina bar: nobody is yours here
        [...team1Players, ...team2Players].forEach((p) => {
            if (p.userData.arrow) p.userData.arrow.visible = false;
            if (p.userData.staminaBar) p.userData.staminaBar.bar.visible = false;
        });
        if (!keyBound && typeof window !== 'undefined') { window.addEventListener('keydown', onKey); keyBound = true; }
        nextRound();
    }

    function stop() {
        if (G) labels(true);
        if (ui && ui.root && ui.root.remove) ui.root.remove();
        ui = null;
        clearFx();
        if (keyBound && typeof window !== 'undefined') { window.removeEventListener('keydown', onKey); keyBound = false; }
        G = null;
        STATE.varGame = false;
        $('game-screen')?.classList.remove('is-vargame');
        if (typeof camera !== 'undefined' && camera && typeof applyGameplayCamera === 'function') applyGameplayCamera();
    }

    // the players of this scene, by id
    function cast(sc) {
        const A = sc.team === 1 ? team1Players : team2Players, D = sc.team === 1 ? team2Players : team1Players;
        const role = (list, r) => list.find(p => !p.userData.isKeeper && p.userData.role === r);
        return {
            Ak: A[0], Aatt: role(A, 'att'), Alw: role(A, 'lw'), Arw: role(A, 'rw'), Adef: role(A, 'def'),
            Dk: D[0], Datt: role(D, 'att'), Dlw: role(D, 'lw'), Drw: role(D, 'rw'), Ddef: role(D, 'def'),
        };
    }

    function nextRound() {
        if (!G) return;
        G.i++;
        if (G.i >= ROUNDS) { finish(); return; }
        const r = G.rounds[G.i];
        G.sc = buildScene(r.kind, r.seed, r.d, r.yes);
        G.cast = cast(G.sc);
        G.t = 0; G.prevT = 0; G.playing = false; G.cam = 0; G.camNow = null;
        apply(0, 0);
        snap();
        if (typeof applyGameplayCamera === 'function') applyGameplayCamera();
        if (typeof flashCut === 'function' && G.i > 0) flashCut();
        const K = KINDS[G.sc.kind];
        set(ui.cardNum, `Situatie ${G.i + 1} van ${ROUNDS}`);
        set(ui.cardTitle, K.title);
        set(ui.cardRule, K.rule);
        ui.cardLevel.dataset.level = String(1 + Math.round(r.d * 4));
        set(ui.round, `${G.i + 1}/${ROUNDS}`);
        go('intro');
        showFx(false);
    }

    function go(phase) {
        G.phase = phase;
        G.pt = 0;
        G.log.push(`${G.i}:${phase}`);
        if (ui) ui.root.dataset.phase = phase;
        labels(phase !== 'review' && phase !== 'reveal');
        const sc = G.sc, K = KINDS[sc.kind];
        if (phase === 'live') { G.t = 0; G.prevT = 0; }
        if (phase === 'call') {
            G.t = sc.T;
            set(ui.callText, sc.call);
            set(ui.callSub, 'De VAR kijkt mee');
            setState('Check', K.subject);
        }
        if (phase === 'review') {
            if (typeof flashCut === 'function') flashCut();
            G.t = sc.rp[0]; G.prevT = G.t;
            G.playing = true; G.frozeOnce = false; G.left = DECIDE_S; G.cam = 0; G.camNow = null;
            apply(G.t, 0);
            snap();
            showFx(false);
            setState('Review', K.subject);
            set(ui.question, K.question);
            K.answers.forEach((a, i) => set(ui.answerText[i], a));
            ui.range.min = String(sc.rp[0]);
            ui.range.max = String(sc.rp[1]);
            ui.range.step = '0.001';
            ui.mark.style.left = `calc(9px + (100% - 18px) * ${((sc.tKey - sc.rp[0]) / (sc.rp[1] - sc.rp[0])).toFixed(4)})`;
            ui.mark.title = K.moment;
            camLabel();
        }
    }

    // a star's name under his feet: fine in the live play, in the way of a close replay camera
    function labels(on) {
        [...team1Players, ...team2Players].forEach((p) => (p.children || []).forEach((c) => { if (c.isSprite) c.visible = on; }));
    }

    // ------------------------------------------------ your decision
    function decide(i) {
        if (!G || G.phase !== 'review') return;
        const sc = G.sc, K = KINDS[sc.kind];
        const right = i === sc.truth, late = i < 0;
        const quick = Math.max(0, G.left) / DECIDE_S;
        G.streak = right ? G.streak + 1 : 0;
        const pts = right ? 100 + Math.round(50 * quick) + (G.streak >= 3 ? 25 : 0) : 0;
        G.points += pts;
        const refRight = sc.callIdx === sc.truth;
        G.results.push({ kind: sc.kind, right, late, pts, verdict: sc.verdict, detail: sc.detail, answer: i, truth: sc.truth });
        G.t = sc.tKey;
        G.playing = false;
        ui.verdict.dataset.result = right ? 'right' : late ? 'late' : 'wrong';
        set(ui.vTitle, right ? 'Goed' : late ? 'Te laat' : 'Fout');
        set(ui.vAnswer, sc.verdict);
        set(ui.vDetail, sc.detail);
        set(ui.vPoints, right ? `+${pts}` + (G.streak >= 3 ? ' · reeks' : '') : '+0');
        set(ui.vRef, `Scheidsrechter: ${sc.call.toLowerCase()} · ${refRight ? 'blijft staan' : 'teruggedraaid'}`);
        set(ui.points, String(G.points));
        set(ui.next, G.i + 1 >= ROUNDS ? 'Uitslag' : 'Volgende');
        go('reveal');
        showFx(true);
    }

    function finish() {
        G.phase = 'done';
        G.log.push('done');
        if (ui) ui.root.dataset.phase = 'done';
        showFx(false);
        const right = G.results.filter(r => r.right).length;
        const best = readBest(), record = G.points > best;
        if (record) writeBest(G.points);
        set(ui.endPoints, String(G.points));
        set(ui.endScore, `${right} van de ${ROUNDS} goed`);
        set(ui.endRating, rating(right));
        set(ui.endBest, record ? (best ? `Nieuw record! (was ${best})` : 'Je eerste record') : `Record: ${best}`);
        if (ui.endList.replaceChildren) ui.endList.replaceChildren();
        G.results.forEach((r, i) => {
            const li = h('li', 'vg-end__row', ui.endList);
            li.dataset.result = r.right ? 'right' : r.late ? 'late' : 'wrong';
            h('span', 'vg-end__n', li, String(i + 1));
            h('span', 'vg-end__kind', li, KINDS[r.kind].title);
            h('span', 'vg-end__what', li, r.detail);
            h('span', 'vg-end__pts', li, r.right ? `+${r.pts}` : r.late ? 'te laat' : 'fout');
        });
        launchLabel();
    }
    function rating(n) {
        if (n === ROUNDS) return 'Foutloos. De KNVB belt je morgen.';
        if (n >= 7) return 'Topniveau: bijna niets gemist.';
        if (n >= 5) return 'Prima VAR, een paar twijfelgevallen.';
        if (n >= 3) return 'Nog even oefenen in de VAR-kamer.';
        return 'Tijd voor een nieuwe bril.';
    }

    // ------------------------------------------------ the replay controls
    function togglePlay() {
        if (!G || G.phase !== 'review') return;
        if (!G.playing && G.t >= G.sc.rp[1] - 1e-3) G.t = G.sc.rp[0];
        G.playing = !G.playing;
    }
    function step(frames) {
        if (!G || G.phase !== 'review') return;
        G.playing = false;
        G.t = Math.max(G.sc.rp[0], Math.min(G.sc.rp[1], G.t + frames / 60));
    }
    function nextCam() {
        if (!G || (G.phase !== 'review' && G.phase !== 'reveal')) return;
        G.cam = (G.cam + 1) % G.sc.cams.length;
        camLabel();
    }
    function camLabel() { set(ui.camText, KINDS[G.sc.kind].cams[G.cam]); }

    function onKey(e) {
        if (!G || STATE.paused || STATE.screen !== 'playing') return;
        const c = e.code;
        if (G.phase === 'review') {
            if (c === 'Digit1' || c === 'Numpad1') { e.preventDefault(); decide(0); return; }
            if (c === 'Digit2' || c === 'Numpad2') { e.preventDefault(); decide(1); return; }
            if (c === 'ArrowLeft' || c === 'ArrowRight') { e.preventDefault(); step((c === 'ArrowLeft' ? -1 : 1) * (e.shiftKey ? 15 : 1)); return; }
            if (c === 'Space' && !e.repeat) { e.preventDefault(); togglePlay(); return; }
            if (c === 'KeyC' && !e.repeat) { e.preventDefault(); nextCam(); return; }
            return;
        }
        if (c === 'KeyC' && !e.repeat && G.phase === 'reveal') { e.preventDefault(); nextCam(); return; }
        if ((c === 'Space' || c === 'Enter' || c === 'NumpadEnter') && !e.repeat) {
            e.preventDefault();
            if (G.phase === 'intro') go('live');
            else if (G.phase === 'call') go('review');
            else if (G.phase === 'reveal') nextRound();
            else if (G.phase === 'done' && c !== 'Space') start();
        }
    }

    // ------------------------------------------------ every frame
    function frame(dt) {
        if (!G || !G.sc) return;
        // a phone held upright: everything waits until it is turned (the rotate hint shows)
        if (typeof IS_TOUCH !== 'undefined' && IS_TOUCH && typeof isPortrait === 'function' && isPortrait()) return;
        const sc = G.sc;
        G.pt += dt;
        switch (G.phase) {
            case 'intro':
                if (G.pt >= INTRO_S) go('live');
                break;
            case 'live': {
                const before = G.t;
                G.t = Math.min(sc.T, G.t + dt);
                sc.sounds.forEach(([t, pat]) => { if (t > before && t <= G.t && typeof REF !== 'undefined' && REF.whistle) REF.whistle(pat); });
                sc.flashes.forEach(([t, text]) => { if (t > before && t <= G.t) flash(text); });
                if (G.t >= sc.T) go('call');
                break;
            }
            case 'call':
                if (G.pt >= CALL_S) go('review');
                break;
            case 'review': {
                G.left -= dt;
                if (G.left <= 0) { decide(-1); break; }
                if (G.playing) {
                    const before = G.t;
                    G.t += dt * SLOW;
                    // the first time through it stops at the moment that counts
                    if (!G.frozeOnce && before < sc.tKey && G.t >= sc.tKey) { G.t = sc.tKey; G.playing = false; G.frozeOnce = true; }
                    if (G.t >= sc.rp[1]) { G.t = sc.rp[1]; G.playing = false; }
                }
                break;
            }
            case 'reveal':
                if (G.pt >= REVEAL_S) nextRound();
                break;
        }
        if (!G || G.phase === 'done' || !G.sc) return;
        const sdt = Math.abs(G.t - G.prevT);
        G.prevT = G.t;
        apply(G.t, sdt);
        // standing about before and after (intro, the call): limbs settle in real time
        const anim = G.phase === 'intro' || G.phase === 'call' ? dt : sdt;
        if (typeof animatePlayers === 'function') animatePlayers(anim);
        if (typeof REF !== 'undefined') REF.frame(anim);
        if (typeof updateBallShadow === 'function') updateBallShadow();
        if (G.phase === 'review' || G.phase === 'reveal') shotCam(dt);
        else if (typeof updateCamera === 'function') updateCamera(dt);
        paintPanel();
    }

    // puts everybody and the ball where the scene has them at time t
    function apply(t, sdt) {
        const sc = G.sc;
        for (const id in sc.act) {
            const p = G.cast[id];
            if (!p) continue;
            const a = sc.act[id], u = p.userData;
            const q = at(a.k, t);
            p.position.x = q[0];
            p.position.z = q[1];
            const v = vel(a.k, t), sp = Math.hypot(v[0], v[1]);
            const sliding = inside(a.slide, t), down = inside(a.down, t), fallen = inside(a.fall, t);
            u.tackleT = sliding ? 1 : 0;
            u.getUpT = down ? 1 : 0;
            u.fallT = fallen ? 1 : 0;
            u.callT = 0;
            u.throwPose = false;
            u.faceTo = u.isKeeper ? null : sp > 2.5 ? { x: v[0], z: v[1] } : (sliding || down || fallen) ? heading(a.k, t) : null;
            const kt = lastBefore(a.kick, t);
            u.kickT = kt !== null && t - kt < 0.28 ? 0.28 - (t - kt) + sdt : 0;
            const dv = a.dive.find(([t0, t1]) => t >= t0 && t <= t1);
            if (dv) { u.diveT = Math.min(0.9, dv[1] - t) + sdt; u.diveX = 0; u.diveZ = dv[2]; } else u.diveT = 0;
        }
        const b = ballAt(sc.ball, t);
        const mesh = ball.userData && ball.userData.mesh;
        if (mesh) {
            mesh.rotation.z -= (b[0] - ball.position.x) / BALL_R;
            mesh.rotation.x += (b[2] - ball.position.z) / BALL_R;
        }
        ball.position.set(b[0], b[1], b[2]);
        const off = typeof REF !== 'undefined' ? REF.officials : null;
        if (off) ['ref', 'arR', 'arL'].forEach((id) => {
            const o = off[id], s = sc.off[id];
            if (!o || !s || !s.k.length) return;
            const q = at(s.k, t);
            o.position.x = q[0];
            o.position.z = q[1];
            const ps = s.pose.find(([t0, t1]) => t >= t0 && t <= t1);
            o.userData.pose = ps ? ps[2] : null;
            o.userData.faceTo = ps && (ps[3] || ps[4]) ? { x: ps[3], z: ps[4] } : null;
        });
    }

    // after a jump in time: nobody runs or spins to get to where he now is,
    // and everybody is in his pose for that moment straight away
    function snap() {
        [...team1Players, ...team2Players].forEach((p) => {
            const u = p.userData;
            u.lastX = p.position.x; u.lastZ = p.position.z;
            u.slide = u.tackleT > 0 || u.getUpT > 0 ? 1 : 0;
            u.fall = u.fallT > 0 ? 1 : 0;
            u.roll = 0;
            u.stride = 0;
            const f = u.faceTo || (ball ? { x: ball.position.x - p.position.x, z: ball.position.z - p.position.z } : null);
            if (f && u.rig && (f.x || f.z)) u.rig.body.rotation.y = Math.atan2(f.x, f.z);
        });
        const off = typeof REF !== 'undefined' ? REF.officials : null;
        if (off) Object.values(off).forEach((o) => { o.userData.lastX = o.position.x; o.userData.lastZ = o.position.z; });
        // one tiny step so the limbs take the pose now, not only once time moves
        if (typeof animatePlayers === 'function') animatePlayers(1e-3);
        if (typeof REF !== 'undefined') REF.frame(1e-3);
    }

    // a test hook (index.html?test=var&round=3&at=review): straight to a round and a step
    function jump(round, at, cam) {
        if (!G) return;
        G.i = Math.max(0, Math.min(ROUNDS - 1, (round || 1) - 1)) - 1;
        nextRound();
        if (at === 'done') {
            // every round answered at once (every third one wrong), straight to the end
            while (G && G.phase !== 'done') {
                if (G.phase !== 'review') go('review');
                decide(G.i % 3 === 2 ? 1 - G.sc.truth : G.sc.truth);
                nextRound();
            }
            return;
        }
        if (at === 'live') go('live');
        else if (at === 'call') go('call');
        else if (at === 'review' || at === 'reveal') {
            go('review');
            G.t = G.prevT = G.sc.tKey;
            G.playing = false;
            G.frozeOnce = true;
            apply(G.t, 0);
            snap();
            if (cam) { G.cam = Math.max(0, Math.min(G.sc.cams.length - 1, cam - 1)); G.camNow = null; camLabel(); }
            if (at === 'reveal') decide(G.sc.truth);
        }
    }

    // ------------------------------------------------ the replay cameras
    function fovFor(f) {
        const asp = window.innerWidth / window.innerHeight;
        return asp >= 1.6 ? f : Math.min(62, f * 1.6 / asp);
    }
    function shotCam(dt) {
        const s = G.sc.cams[G.cam];
        if (!G.camNow) G.camNow = { pos: { ...s.pos }, look: { ...s.look }, fov: s.fov };
        const c = G.camNow, k = 1 - Math.exp(-dt * 6);
        ['x', 'y', 'z'].forEach((a) => { c.pos[a] += (s.pos[a] - c.pos[a]) * k; c.look[a] += (s.look[a] - c.look[a]) * k; });
        c.fov += (s.fov - c.fov) * k;
        camera.position.set(c.pos.x, c.pos.y, c.pos.z);
        camera.lookAt(c.look.x, c.look.y, c.look.z);
        const f = fovFor(c.fov);
        if (Math.abs(camera.fov - f) > 1e-3) { camera.fov = f; camera.updateProjectionMatrix(); }
    }

    // ------------------------------------------------ marks on the grass
    function buildFx() {
        clearFx();
        if (typeof scene === 'undefined' || !scene) return;
        const mat = (hex, op, depth) => new THREE.MeshBasicMaterial({
            color: srgb(hex), transparent: true, opacity: op, depthWrite: false, depthTest: depth, side: THREE.DoubleSide,
        });
        const flat = (geo, m, y, order) => {
            const o = new THREE.Mesh(geo, m);
            o.rotation.x = -Math.PI / 2;
            o.position.y = y;
            o.renderOrder = order;
            o.visible = false;
            scene.add(o);
            return o;
        };
        const ring = () => {
            const g = new THREE.Group();
            [[3.4, 5.4, 0x121512], [3.8, 5.0, 0xffd60a]].forEach(([r0, r1, c], i) => {
                const o = new THREE.Mesh(new THREE.RingGeometry(r0, r1, 48), mat(c, 1, false));
                o.rotation.x = -Math.PI / 2;
                o.renderOrder = 21 + i;
                g.add(o);
            });
            g.position.y = 0.1;
            g.visible = false;
            scene.add(g);
            return g;
        };
        const lineMat = mat(0xfff3b0, 1, true);
        lineMat.polygonOffset = true; lineMat.polygonOffsetFactor = -2; lineMat.polygonOffsetUnits = -2;
        fx = {
            atk: flat(new THREE.PlaneGeometry(0.55, FIELD_L), mat(0xe0203a, 0.95, false), 0.12, 20),
            def: flat(new THREE.PlaneGeometry(0.55, FIELD_L), mat(0x1f5dff, 0.95, false), 0.12, 20),
            ring: ring(),
            cover: ring(),
            goal: flat(new THREE.PlaneGeometry(LINE_W, GOAL_W + 0.6), lineMat, 0.07, 5),
            foot: flat(new THREE.CircleGeometry(BALL_R, 32), mat(0x3fbf63, 0.6, false), 0.09, 22),
            lane: null,
        };
    }
    function clearFx() {
        if (!fx) return;
        const drop = (o) => {
            if (!o) return;
            if (o.parent) o.parent.remove(o);
            (o.children && o.children.length ? o.children : [o]).forEach((m) => {
                if (m.geometry && m.geometry.dispose) m.geometry.dispose();
                if (m.material && m.material.dispose) m.material.dispose();
            });
        };
        Object.values(fx).forEach(drop);
        fx = null;
    }
    const teamHex = (team) => (typeof KIT !== 'undefined' && KIT[team] && typeof KIT[team].shirt === 'number' ? KIT[team].shirt : team === 1 ? 0xe0203a : 0x1f5dff);
    function showFx(on) {
        if (!fx || !G || !G.sc) return;
        const f = G.sc.fx || {}, sc = G.sc;
        const lines = on && !!f.lines;
        fx.atk.visible = fx.def.visible = lines;
        if (lines) {
            fx.atk.position.x = f.lines.a;
            fx.def.position.x = f.lines.d;
            fx.atk.material.color.copy(srgb(teamHex(sc.team)));
            fx.def.material.color.copy(srgb(teamHex(3 - sc.team)));
        }
        fx.ring.visible = on && !!f.ring;
        if (f.ring) { fx.ring.position.set(f.ring.x, 0.1, f.ring.z); fx.ring.scale.setScalar(0.62); }   // small: the cameras are close
        fx.cover.visible = on && !!f.cover;
        if (f.cover) {
            fx.cover.position.set(f.cover.x, 0.1, f.cover.z);
            fx.cover.scale.setScalar(0.8);
            const c = fx.cover.children[1];
            if (c && c.material) c.material.color.copy(srgb(f.coverIn ? 0x3fbf63 : 0xe0203a));
        }
        if (fx.lane && fx.lane.parent) fx.lane.parent.remove(fx.lane);
        fx.lane = null;
        if (on && f.lane && typeof scene !== 'undefined' && scene) {
            const sh = new THREE.Shape();
            sh.moveTo(f.lane[0].x, -f.lane[0].z);
            for (let i = 1; i < f.lane.length; i++) sh.lineTo(f.lane[i].x, -f.lane[i].z);
            sh.closePath();
            fx.lane = new THREE.Mesh(new THREE.ShapeGeometry(sh), new THREE.MeshBasicMaterial({
                color: srgb(0xffd60a), transparent: true, opacity: 0.26, depthWrite: false, depthTest: false, side: THREE.DoubleSide,
            }));
            fx.lane.rotation.x = -Math.PI / 2;
            fx.lane.position.y = 0.11;
            fx.lane.renderOrder = 19;
            scene.add(fx.lane);
        }
        // the goal line is drawn through the whole replay, the ball's footprint only with the answer
        fx.goal.visible = !!f.goalLine && (G.phase === 'review' || G.phase === 'reveal');
        if (f.goalLine) fx.goal.position.set(f.goalLine.x, 0.07, 0);
        fx.foot.visible = on && !!f.foot;
        if (f.foot) {
            fx.foot.position.set(f.foot.x, 0.09, f.foot.z);
            fx.foot.material.color.copy(srgb(sc.truth === 0 ? 0x3fbf63 : 0xe0203a));
        }
    }

    // ------------------------------------------------ the overlay
    function h(tag, cls, parent, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined) e.textContent = text;
        if (parent && parent.appendChild) parent.appendChild(e);
        return e;
    }
    function set(el, text) { if (el && el.textContent !== text) el.textContent = text; }
    function setState(state, subject) { set(ui.stateTxt, state); set(ui.subject, subject); }
    function button(cls, parent, label, onClick) {
        const b = h('button', cls, parent);
        b.type = 'button';
        b.tabIndex = -1;
        if (label) b.innerHTML = label;
        b.addEventListener('click', (e) => { e.preventDefault(); if (b.blur) b.blur(); onClick(); });
        return b;
    }
    const ICON = {
        back: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5v14M18 5l-9 7 9 7z" fill="currentColor"/></svg>',
        fwd: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 5v14M6 5l9 7-9 7z" fill="currentColor"/></svg>',
        play: '<svg class="vg-i-play" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4l13 8-13 8z" fill="currentColor"/></svg>'
            + '<svg class="vg-i-pause" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h4v16H6zM14 4h4v16h-4z" fill="currentColor"/></svg>',
        cam: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h12v10H3zM15 10l6-3v10l-6-3z" fill="currentColor"/></svg>',
    };
    function buildUi() {
        const host = $('game-screen');
        const root = h('div', 'vg', host);
        root.dataset.phase = 'idle';
        ui = { root };
        // the replay's bars
        const bars = h('div', 'vg-bars', root);
        h('span', 'vg-bars__tag', bars, 'Herhaling');
        // top left: who you are, the round, the points
        const top = h('div', 'vg-top', root);
        h('span', 'vg-top__mark', top, 'VAR');
        h('span', 'vg-top__name', top, 'Jij bent de VAR');
        ui.round = h('span', 'vg-top__round', top, `1/${ROUNDS}`);
        const pts = h('span', 'vg-top__points', top);
        ui.points = h('b', '', pts, '0');
        h('span', '', pts, ' pt');
        // top middle: the VAR at work
        const st = h('div', 'vg-state', root);
        h('span', 'vg-state__mark', st, 'VAR');
        ui.stateTxt = h('span', 'vg-state__state', st, 'Check');
        ui.subject = h('span', 'vg-state__subject', st, '');
        // the round's card
        const card = h('div', 'vg-card', root);
        ui.cardNum = h('span', 'vg-card__num', card, '');
        ui.cardTitle = h('span', 'vg-card__title', card, '');
        ui.cardRule = h('span', 'vg-card__rule', card, '');
        const lvl = h('span', 'vg-card__level', card);
        h('span', 'vg-card__level-label', lvl, 'Moeilijkheid');
        ui.cardLevel = h('span', 'vg-card__dots', lvl);
        for (let i = 0; i < 5; i++) h('i', '', ui.cardLevel);
        // the referee's call
        const call = h('div', 'vg-call', root);
        h('span', 'vg-call__who', call, 'Scheidsrechter');
        ui.callText = h('span', 'vg-call__text', call, '');
        ui.callSub = h('span', 'vg-call__sub', call, '');
        // a goal in the live play
        ui.flash = h('div', 'vg-flash', root);
        ui.flash.hidden = true;
        // the panel: clock, replay controls, your answer
        const panel = h('div', 'vg-panel', root);
        const clock = h('div', 'vg-clock', panel);
        const bar = h('span', 'vg-clock__bar', clock);
        ui.clockFill = h('span', 'vg-clock__fill', bar);
        ui.clockNum = h('span', 'vg-clock__num', clock, String(DECIDE_S));
        const tools = h('div', 'vg-tools', panel);
        button('vg-tool', tools, ICON.back, () => step(-1)).title = 'Frame terug (←)';
        ui.play = button('vg-tool vg-tool--play', tools, ICON.play, togglePlay);
        ui.play.title = 'Afspelen / pauze (spatie)';
        button('vg-tool', tools, ICON.fwd, () => step(1)).title = 'Frame vooruit (→)';
        const scrub = h('div', 'vg-scrub', tools);
        ui.range = h('input', 'vg-scrub__range', scrub);
        ui.range.type = 'range';
        ui.range.tabIndex = -1;
        ui.range.setAttribute && ui.range.setAttribute('aria-label', 'Herhaling');
        ui.mark = h('span', 'vg-scrub__mark', scrub);
        ui.time = h('span', 'vg-tools__time', tools, '');
        const camBtn = button('vg-tool vg-tool--cam', tools, ICON.cam, nextCam);
        camBtn.title = 'Andere camera (C)';
        ui.camText = h('span', 'vg-tool__cam', camBtn, '');
        ui.range.addEventListener('pointerdown', () => { if (G) { G.dragging = true; G.playing = false; } });
        ui.range.addEventListener('input', () => {
            if (!G || G.phase !== 'review') return;
            G.playing = false;
            G.t = Math.max(G.sc.rp[0], Math.min(G.sc.rp[1], +ui.range.value));
        });
        const endDrag = () => { if (G) G.dragging = false; if (ui && ui.range.blur) ui.range.blur(); };
        ui.range.addEventListener('pointerup', endDrag);
        ui.range.addEventListener('pointercancel', endDrag);
        ui.range.addEventListener('change', endDrag);
        const ask = h('div', 'vg-ask', panel);
        ui.question = h('span', 'vg-ask__q', ask, '');
        ui.answerText = [];
        [0, 1].forEach((i) => {
            const b = button('vg-answer', ask, '', () => decide(i));
            h('kbd', '', b, String(i + 1));
            ui.answerText.push(h('span', 'vg-answer__text', b, ''));
        });
        // the answer
        ui.verdict = h('div', 'vg-verdict', root);
        ui.vTitle = h('span', 'vg-verdict__title', ui.verdict, '');
        const body = h('div', 'vg-verdict__body', ui.verdict);
        ui.vAnswer = h('span', 'vg-verdict__answer', body, '');
        ui.vDetail = h('span', 'vg-verdict__detail', body, '');
        ui.vRef = h('span', 'vg-verdict__ref', body, '');
        const foot = h('div', 'vg-verdict__foot', ui.verdict);
        ui.vPoints = h('span', 'vg-verdict__points', foot, '');
        ui.next = button('vg-verdict__next', foot, '', () => { if (G && G.phase === 'reveal') nextRound(); });
        // the end
        const end = h('div', 'vg-end', root);
        const endCard = h('div', 'vg-end__card', end);
        h('span', 'vg-end__label', endCard, 'Jij bent de VAR · uitslag');
        ui.endPoints = h('span', 'vg-end__points', endCard, '0');
        ui.endScore = h('span', 'vg-end__score', endCard, '');
        ui.endRating = h('span', 'vg-end__rating', endCard, '');
        ui.endBest = h('span', 'vg-end__best', endCard, '');
        ui.endList = h('ol', 'vg-end__list', endCard);
        const btns = h('div', 'vg-end__btns', endCard);
        button('vg-end__btn vg-end__btn--gold', btns, 'Nog een keer', () => start());
        button('vg-end__btn', btns, 'Naar het menu', () => { if (typeof gotoScreen === 'function') gotoScreen('launch', { replace: true }); });
    }
    function flash(text) {
        if (!ui) return;
        set(ui.flash, text);
        ui.flash.hidden = false;
        ui.flash.style.animation = 'none';
        void ui.flash.offsetWidth;
        ui.flash.style.animation = '';
        clearTimeout(flash.timer);
        flash.timer = setTimeout(() => { if (ui) ui.flash.hidden = true; }, 1500);
    }
    function paintPanel() {
        if (!ui || G.phase !== 'review') return;
        const sc = G.sc;
        if (!G.dragging) ui.range.value = String(G.t);
        ui.play.classList.toggle('is-playing', G.playing);
        const dtk = G.t - sc.tKey;
        set(ui.time, Math.abs(dtk) < 0.5 / 60 ? KINDS[sc.kind].moment : `${dtk < 0 ? '−' : '+'}${Math.abs(dtk).toFixed(2)} s`);
        const left = Math.max(0, G.left);
        ui.clockFill.style.transform = `scaleX(${(left / DECIDE_S).toFixed(4)})`;
        ui.clockFill.classList.toggle('is-low', left < 5);
        set(ui.clockNum, String(Math.ceil(left)));
    }

    function launchLabel() {
        const el = typeof document !== 'undefined' ? document.getElementById('launch-var-meta') : null;
        if (!el) return;
        const best = readBest();
        el.textContent = best > 0 ? `Record ${best}` : 'Minigame';
    }

    return {
        start, stop, frame, launchLabel, jump,
        active: () => !!G,
        best: readBest,
        // tools/vargame-test.js
        _test: {
            KINDS, ROUNDS, DECIDE_S, UNIT_CM, FOOT, BALL_R, LINE_W, IDS,
            build: buildScene, plan: (seed) => plan(mulberry(seed)), at, vel, ballAt,
            state: () => G && { phase: G.phase, i: G.i, t: G.t, pt: G.pt, left: G.left, points: G.points, results: G.results.slice(),
                playing: G.playing, cam: G.cam, sc: G.sc, log: G.log.slice() },
            answer: (how) => { if (G && G.sc) decide(how === 'right' ? G.sc.truth : 1 - G.sc.truth); },
            step, togglePlay, nextCam,
        },
    };
})();

// From the start screen: the pitch of the chosen stadium, no match, the minigame on it.
function startVarGame(opts) {
    STATE.mode = 'cpu';
    STATE.wkMatch = null;
    STATE.wkStarting = false;
    STATE.goldenGoal = false;
    STATE.kickoffTeam = 1;
    STATE.score1 = 0;
    STATE.score2 = 0;
    if (typeof wkApply === 'function') wkApply();
    STATE.paused = false;
    STATE.scoring = false;
    STATE.setPiece = null;
    if (typeof resetTouch === 'function') resetTouch();
    gotoScreen('playing');
    if (typeof paintHud === 'function') paintHud();
    initThree();
    STATE.inputLocked = true;
    VARGAME.start(opts || {});
}

(function wireVarGame() {
    if (typeof document === 'undefined') return;
    const btn = document.getElementById('launch-var');
    if (btn && btn.addEventListener) btn.addEventListener('click', () => startVarGame());
    VARGAME.launchLabel();
    if (typeof location !== 'undefined' && typeof URLSearchParams !== 'undefined') {
        const q = new URLSearchParams(location.search);
        if (q.get('test') === 'var' && typeof window !== 'undefined' && window.addEventListener) {
            const seed = q.has('seed') ? Number(q.get('seed')) : undefined;
            window.addEventListener('load', () => setTimeout(() => {
                startVarGame({ seed });
                if (q.has('round') || q.has('at')) VARGAME.jump(Number(q.get('round')) || 1, q.get('at') || 'intro', Number(q.get('cam')) || 0);
            }, 400));
        }
    }
})();

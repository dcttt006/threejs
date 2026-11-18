// =====================================================
// PITCH ROYALE — penalty shoot-out
// A WK knockout level after extra time ends in penalties, as in real football:
// the two teams take turns, five each, then one each until one misses. Only
// the taker and the keeper stay on the pitch, the camera stands behind the
// taker (as on TV), the score of the shoot-out sits on top.
//   Your penalty: point at the goal (mouse or finger), press and hold, let go.
//     The bar shows the power: too short is weak, in the green is right,
//     too long and it goes over the bar.
//   Their penalty: click (tap) the corner you dive to: left, middle or right.
// Online (game.online.js) both sides are people: the taker aims and the
// keeper picks a corner at the same time, without seeing each other's choice.
// The host's browser decides how the kick ends and sends that to the other,
// so both see the same shoot-out.
// Test page: index.html?test=pens goes straight to a shoot-out.
// =====================================================

const PENS = (() => {
    const GX = FIELD_W / 2;                       // the goal they shoot at (the right-hand one)
    const SPOT_X = GX - PEN_SPOT;
    const POWER_FULL_MS = 1000;                   // hold this long for a full bar
    const POWER_OVER = 1.0;                       // past this the shot rises over the bar
    const POWER_CAP = 1.35;
    const ZONE = GOAL_W / 6;                      // |z| over this: a corner
    const NET_KEEPER_MS = 8000;                   // online: the keeper has this long to pick a corner
    const NET_TAKER_MS = 12000;                   // and the taker this long to shoot
    let S = null;                                 // the shoot-out in progress
    let layer = null;                             // the overlay: board, bar, prompts
    const ray = new THREE.Raycaster();

    // ---------------------------------------------------------------- overlay
    function el(tag, cls, parent, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined) e.textContent = text;
        if (parent) parent.appendChild(e);
        return e;
    }
    function buildLayer() {
        layer = el('div', 'pens', document.getElementById('game-screen'));
        const board = el('div', 'pens-board', layer);
        S.rows = [1, 2].map(team => {
            const row = el('div', 'pens-row', board);
            const t = S.teams[team];
            if (t.flag) { const im = el('img', 'pens-flag', row); im.src = t.flag; im.alt = ''; }
            const dot = el('span', 'pens-dot', row); dot.style.background = t.color;
            el('span', 'pens-code', row, t.code);
            const total = el('span', 'pens-total', row, '0');
            el('span', 'pens-sep', row);
            const slots = el('span', 'pens-slots', row);
            return { total, slots };
        });
        S.prompt = el('div', 'pens-prompt', layer);
        S.flash = el('div', 'pens-flash', layer);
        S.flash.hidden = true;
        const bar = el('div', 'pens-power', layer);
        el('span', 'pens-power__over', bar);
        S.barFill = el('span', 'pens-power__fill', bar);
        S.bar = bar; bar.hidden = true;
        S.reticle = el('div', 'pens-reticle', layer); S.reticle.hidden = true;
        layer.addEventListener('pointerdown', onDown);
        layer.addEventListener('pointermove', onMove);
        layer.addEventListener('pointerup', onUp);
        layer.addEventListener('pointercancel', onUp);
        layer.addEventListener('contextmenu', (e) => e.preventDefault());
    }
    function renderBoard() {
        [1, 2].forEach((team, i) => {
            const kicks = S.kicks[team];
            S.rows[i].total.textContent = kicks.filter(Boolean).length;
            const shown = Math.max(5, Math.min(kicks.length + (S.turn === team ? 1 : 0), 99));
            const first = Math.max(0, shown - 5);              // sudden death: the last five
            S.rows[i].slots.innerHTML = '';
            for (let k = first; k < first + 5; k++) {
                const s = el('span', 'pens-slot', S.rows[i].slots);
                if (k < kicks.length) { s.classList.add(kicks[k] ? 'is-in' : 'is-out'); s.textContent = kicks[k] ? 'O' : 'X'; }
                else s.textContent = k + 1;
            }
        });
    }
    function say(text) { S.prompt.textContent = text; S.prompt.hidden = !text; }
    function flash(text, kind) {
        S.flash.textContent = text;
        S.flash.dataset.kind = kind;
        S.flash.hidden = false;
        S.flash.style.animation = 'none'; void S.flash.offsetWidth; S.flash.style.animation = '';
    }

    // ---------------------------------------------------------------- pointer
    function goalPoint(e) {
        // where on the goal mouth the pointer is: { z, y }, or null off it
        const r = renderer.domElement.getBoundingClientRect();
        const v = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
        ray.setFromCamera(v, camera);
        const o = ray.ray.origin, d = ray.ray.direction;
        if (Math.abs(d.x) < 1e-6) return null;
        const t = (GX - o.x) / d.x;
        if (t <= 0) return null;
        return { z: o.z + d.z * t, y: o.y + d.y * t };
    }
    function showReticle(e) {
        S.reticle.hidden = false;
        S.reticle.style.left = e.clientX + 'px';
        S.reticle.style.top = e.clientY + 'px';
    }
    function onMove(e) {
        if (!S || S.phase !== 'aim' && S.phase !== 'charge') return;
        showReticle(e);
        const p = goalPoint(e);
        if (p) S.aim = p;
    }
    function onDown(e) {
        if (!S) return;
        e.preventDefault();
        if (S.phase === 'aim') {
            showReticle(e);
            const p = goalPoint(e);
            if (p) S.aim = p;
            S.phase = 'charge';
            S.chargeStart = performance.now();
            S.bar.hidden = false;
            try { layer.setPointerCapture(e.pointerId); } catch (_) {}
        } else if (S.phase === 'choose') {
            const p = goalPoint(e);
            S.dive = !p ? 0 : (p.z < -ZONE ? -1 : p.z > ZONE ? 1 : 0);
            say('');
            if (S.net) submit({ dive: S.dive });
            else startRunup();
        }
    }
    function onUp() {
        if (!S || S.phase !== 'charge') return;
        S.power = Math.min(POWER_CAP, (performance.now() - S.chargeStart) / POWER_FULL_MS);
        S.reticle.hidden = true;
        say('');
        if (S.net) { S.bar.hidden = true; submit({ shot: { z: S.aim.z, y: S.aim.y, p: S.power } }); }
        else startRunup();
    }

    // ---------------------------------------------------------------- online
    // Your choice for this kick: the host keeps it, the guest sends it over.
    function submit(c) {
        c.k = S.k;
        S.phase = 'wait';
        const keeperDone = c.dive !== undefined;
        say(keeperDone ? 'Wachten op de schutter…' : 'Wachten op de keeper…');
        if (S.net.host) take(c);
        else S.net.send({ t: 'pkc', ...c });
    }
    // host: both choices in, then decide the kick and tell the guest
    function take(c) {
        if (!S || !S.net || !S.net.host) return;
        if (c.k !== S.k) { if (c.k > S.k) (S.inbox[c.k] = S.inbox[c.k] || []).push(c); return; }
        if (c.shot) S.choice.shot = c.shot;
        if (c.dive !== undefined) S.choice.dive = c.dive;
        if (!S.choice.shot || S.choice.dive === null || S.outcome) return;
        const o = resolve(+S.choice.shot.z || 0, +S.choice.shot.y || 0, Math.max(0, Math.min(POWER_CAP, +S.choice.shot.p || 0)), true, () => S.choice.dive);
        o.k = S.k;
        S.net.send({ t: 'pko', ...o });
        play(o);
    }
    // both: play out a kick the host decided
    function play(o) {
        if (!S || o.k !== S.k) return;
        S.outcome = o;
        S.aim = { z: o.z, y: o.y };
        S.power = o.p;
        S.dive = o.dive;
        say('');
        startRunup();
    }

    // ---------------------------------------------------------------- the kicks
    function players(team) {
        const list = team === 1 ? team1Players : team2Players;
        return { taker: list.find(p => !p.isKeeper), keeper: list.find(p => p.isKeeper) };
    }
    function setupKick() {
        const other = S.turn === 1 ? 2 : 1;
        S.taker = players(S.turn).taker;
        S.keeper = players(other).keeper;
        [...team1Players, ...team2Players].forEach(p => { p.visible = p === S.taker || p === S.keeper; });
        S.taker.position.set(SPOT_X - 5.5, 0, -2.6);
        S.keeper.position.set(GX - 0.9, 0, 0);
        Object.assign(S.keeper.userData, { diveT: 0, roll: 0 });
        ball.position.set(SPOT_X, BALL_SIZE, 0);
        ball.visible = true;
        S.flight = null;
        S.kicked = false;
        S.power = 0;
        [...team1Players, ...team2Players].forEach(p => {
            if (p.userData.arrow) p.userData.arrow.visible = false;            // no arrow, no stamina bar: only the kick
            if (p.userData.staminaBar) p.userData.staminaBar.bar.visible = false;
        });
        S.dive = 0;
        S.t = 0;
        S.k = (S.k ?? -1) + 1;
        S.aim = { z: 0, y: 2 };
        S.choice = { shot: null, dive: null };
        S.outcome = null;
        renderBoard();
        if (S.net && S.net.host) (S.inbox[S.k] || []).forEach(c => take(c));    // came in before we got here
        if (S.human === S.turn) {
            S.phase = 'aim';
            S.aimUntil = performance.now() + NET_TAKER_MS;
            say(IS_TOUCH ? 'Houd je vinger op het doel en laat los om te schieten' : 'Richt met je muis, houd ingedrukt en laat los om te schieten');
        } else {
            S.phase = 'choose';
            say(IS_TOUCH ? 'Tik waar je duikt: links, midden of rechts' : 'Klik waar je duikt: links, midden of rechts');
            S.chooseUntil = performance.now() + (S.net ? NET_KEEPER_MS : 4500);   // too slow: you stay in the middle
        }
    }
    function startRunup() {
        S.phase = 'runup';
        S.bar.hidden = S.human !== S.turn;
        S.t = 0;
        if (S.human !== S.turn && !S.net) {
            // the computer picks its spot; now and then it misses
            const side = Math.random();
            const z = side < 0.4 ? -1 : side < 0.8 ? 1 : 0;
            const miss = Math.random() < 0.08;
            S.aim = { z: z * (ZONE + Math.random() * (GOAL_W / 2 - ZONE - 1.2)) + (z ? 0 : (Math.random() - 0.5) * 3),
                      y: 1.0 + Math.random() * (GOAL_H - 2.8) };
            if (miss) { if (Math.random() < 0.5) S.aim.y = GOAL_H + 1.5; else S.aim.z = (z || 1) * (GOAL_W / 2 + 1.5); }
            S.power = 0.55 + Math.random() * 0.3;
        }
    }
    const zoneOf = (zz) => (zz < -ZONE ? -1 : zz > ZONE ? 1 : 0);
    // How a kick ends: where it goes (a person's kick spreads a little, more
    // when hit hard; past the green it rises over the bar), whether it is on
    // target, and whether the keeper, diving to diveOf(where it goes), saves it.
    function resolve(z, y, p, human, diveOf) {
        if (human) {
            const spread = 0.35 + Math.max(0, p - 0.85) * 2.5;
            z += (Math.random() - 0.5) * spread * 2;
            y += (Math.random() - 0.5) * spread;
            if (p > POWER_OVER) y += (p - POWER_OVER) * 30;          // over the bar
            if (p < 0.3) y = Math.min(y, 2.5);                        // a weak one rolls along the grass
        }
        y = Math.max(BALL_SIZE, y);
        const onTarget = Math.abs(z) < GOAL_W / 2 - 0.4 && y < GOAL_H - 0.4;
        const dive = diveOf(z);
        let saved = false;
        if (onTarget && zoneOf(z) === dive) {
            const topCorner = dive !== 0 && Math.abs(z) > GOAL_W / 2 - 3.2 && y > GOAL_H - 3.2;
            let chance = dive === 0 ? 0.85 : 0.72;
            if (topCorner) chance -= 0.45;
            if (p > 0.85 && p <= POWER_OVER) chance -= 0.15;
            if (p < 0.35) chance += 0.2;
            saved = Math.random() < chance;
        }
        const r2 = (v) => Math.round(v * 100) / 100;
        return { z: r2(z), y: r2(y), p: r2(p), dive, onTarget, saved };
    }
    function kick() {
        // online the host already decided; against the computer it is decided now:
        // you chose your dive, or the computer guesses (better on harder levels)
        const o = S.outcome || resolve(S.aim.z, S.aim.y, S.power, S.human === S.turn, (z) => {
            if (S.human !== S.turn) return S.dive;
            const read = { easy: 0.25, medium: 0.33, hard: 0.42 }[STATE.difficulty] ?? 0.33;
            const right = zoneOf(z);
            const others = [-1, 0, 1].filter(v => v !== right);
            return Math.random() < read ? right : others[Math.floor(Math.random() * others.length)];
        });
        const { z, y, p, dive, onTarget, saved } = o;
        const speed = 45 + Math.min(1, p) * 60;                       // units a second
        const dist = Math.hypot(GX - SPOT_X, z);
        S.flight = { from: ball.position.clone(), to: new THREE.Vector3(GX + 0.2, y, z), t: 0, T: dist / speed, onTarget, saved, z, y };
        S.keeper.userData.diveT = dive ? 0.9 : 0;
        S.keeper.userData.diveX = 0;
        S.keeper.userData.diveZ = dive;
        S.diveTo = dive * Math.min(GOAL_W / 2 - 2.5, Math.max(ZONE + 1, Math.abs(z)));
        S.phase = 'flight';
        S.bar.hidden = true;
    }
    function finishKick(scored) {
        S.kicks[S.turn].push(scored);
        flash(scored ? 'GOAL' : (S.flight.onTarget ? 'GERED' : 'MIS'), scored ? 'in' : 'out');
        S.phase = 'result';
        S.t = 0;
        renderBoard();
    }
    function decided() {
        const a = S.kicks[1], b = S.kicks[2];
        const ga = a.filter(Boolean).length, gb = b.filter(Boolean).length;
        if (a.length <= 5 && b.length <= 5) {
            const ra = 5 - a.length, rb = 5 - b.length;
            if (ga > gb + rb || gb > ga + ra) return true;
            if (a.length < 5 || b.length < 5) return false;
        }
        return a.length === b.length && ga !== gb;                       // sudden death: after each pair
    }
    function next() {
        if (decided()) { done(); return; }
        S.turn = S.turn === 1 ? 2 : 1;
        setupKick();
    }
    function done() {
        const ga = S.kicks[1].filter(Boolean).length, gb = S.kicks[2].filter(Boolean).length;
        S.phase = 'done';
        const winner = ga > gb ? S.teams[1].code : S.teams[2].code;
        say(`${winner} wint de strafschoppen (${Math.max(ga, gb)}-${Math.min(ga, gb)})`);
        const cb = S.onDone, mine = S;
        setTimeout(() => { if (S !== mine) return; stop(); cb && cb([ga, gb]); }, 2600);
    }

    // ---------------------------------------------------------------- every frame
    function frame(dt) {
        if (!S) return;
        S.t += dt;
        // the camera behind the taker, a little above, looking at the goal
        const aspect = window.innerWidth / window.innerHeight;
        camera.fov = aspect >= 1.6 ? 30 : Math.min(55, 30 * 1.6 / aspect);
        camera.updateProjectionMatrix();
        camera.position.set(SPOT_X - 52, 21, 0);
        camera.lookAt(GX - 10, 1.5, 0);

        if (S.phase === 'charge') {
            const p = Math.min(POWER_CAP, (performance.now() - S.chargeStart) / POWER_FULL_MS);
            S.barFill.style.width = (p / POWER_CAP * 100).toFixed(1) + '%';
            S.bar.classList.toggle('is-over', p > POWER_OVER);
        }
        if (S.phase === 'choose' && performance.now() > S.chooseUntil) {
            S.dive = 0; say('');
            if (S.net) submit({ dive: 0 }); else startRunup();
        }
        // online, a taker who waits too long: a soft one down the middle
        if (S.net && S.phase === 'aim' && performance.now() > S.aimUntil) {
            S.reticle.hidden = true; say('');
            S.power = 0.5;
            submit({ shot: { z: 0, y: 2, p: 0.5 } });
        }
        if (S.phase === 'runup') {
            // a few steps to the ball, then the kick
            const T = 0.75, k = Math.min(1, S.t / T);
            S.taker.position.set(SPOT_X - 5.5 + 4.4 * k, 0, -2.6 + 1.9 * k);
            if (k >= 1 && !S.kicked) { S.taker.userData.kickT = 0.28; S.kicked = true; S.kickAt = S.t + 0.12; }
            if (S.kicked && S.t >= S.kickAt) { S.kicked = false; kick(); }
        }
        if (S.phase === 'flight') {
            const f = S.flight;
            f.t += dt;
            const s = Math.min(1, f.t / f.T);
            // the keeper goes the way he chose, from the moment of the kick
            const kz = S.keeper.position.z;
            S.keeper.position.z = kz + (S.diveTo - kz) * Math.min(1, dt * 7);
            if (f.saved === true && s >= 0.92) {
                // palmed away: back out and wide
                f.saved = 'done';
                f.from = ball.position.clone();
                f.to = new THREE.Vector3(GX - 9, 1.2, f.z + Math.sign(f.z || 1) * 9);
                f.t = 0; f.T = 0.6;
                return;
            }
            ball.position.lerpVectors(f.from, f.to, s);
            if (f.saved !== 'done') ball.position.y += Math.sin(s * Math.PI) * 0.9;   // a little arc
            ball.rotation.x += dt * 18; ball.rotation.z += dt * 9;
            if (s >= 1) {
                if (f.saved === 'done') finishKick(false);
                else if (f.onTarget) {
                    // into the net: on to the back of it and down
                    f.from = ball.position.clone();
                    f.to = new THREE.Vector3(GX + GOAL_DEPTH - 0.8, Math.max(BALL_SIZE, f.y * 0.6), f.z * 0.95);
                    f.t = 0; f.T = 0.25; f.onTarget = 'in';
                    finishKick(true);
                    S.phase = 'net';
                } else finishKick(false);
            }
        }
        if (S.phase === 'net') {
            const f = S.flight;
            f.t += dt;
            ball.position.lerpVectors(f.from, f.to, Math.min(1, f.t / f.T));
            if (f.t > f.T) S.phase = 'result';
        }
        if (S.phase === 'result' && S.t > 1.6) {
            S.flash.hidden = true;
            next();
        }
        animatePlayers(dt);
        if (typeof updateBallShadow === 'function') updateBallShadow();
    }

    // ---------------------------------------------------------------- start / stop
    function teamInfo(team) {
        const kit = KIT[team];
        const color = typeof kit.shirt === 'number' ? '#' + kit.shirt.toString(16).padStart(6, '0') : kit.shirt;
        const m = STATE.wkMatch;
        const code = m ? (team === 1 ? m.me : m.opp) : (typeof hudCodes === 'function' ? hudCodes()[team === 1 ? 'red' : 'blue'] : 'T' + team);
        const flag = m && typeof wkFlagSrc === 'function' ? wkFlagSrc(code) : null;
        return { code, color, flag };
    }
    // opts (online): { me: your team, turn: who kicks first, net: { host, send } }
    function start(onDone, opts = {}) {
        if (S) stop();
        S = { teams: { 1: teamInfo(1), 2: teamInfo(2) }, kicks: { 1: [], 2: [] }, human: opts.me || 1, onDone, phase: 'idle', t: 0,
              net: opts.net || null, inbox: {} };
        S.turn = opts.turn || (Math.random() < 0.5 ? 1 : 2);   // the toss
        STATE.pens = true;
        STATE.inputLocked = true;
        document.getElementById('game-screen')?.classList.add('is-pens');
        buildLayer();
        flash('STRAFSCHOPPEN', 'title');
        setTimeout(() => { if (S) { S.flash.hidden = true; setupKick(); } }, 1600);
        renderBoard();
    }
    function stop() {
        if (layer) layer.remove();
        layer = null;
        S = null;
        STATE.pens = false;
        document.getElementById('game-screen')?.classList.remove('is-pens');
        [...(typeof team1Players !== 'undefined' ? team1Players : []), ...(typeof team2Players !== 'undefined' ? team2Players : [])].forEach(p => {
            p.visible = true;
            if (p.userData.arrow) p.userData.arrow.visible = true;
        });
        if (typeof applyGameplayCamera === 'function') applyGameplayCamera();
    }

    // ---------------------------------------------------------------- test page
    // index.html?test=pens: Nederland - Marokko, level after extra time, penalties
    function testShootout() {
        STATE.mode = 'cpu';
        STATE.difficulty = 'medium';
        STATE.p1.name = WK_TEAMS.NED.name; STATE.p1.team = 1;
        STATE.p2.name = WK_TEAMS.MAR.name; STATE.p2.team = 2;
        STATE.gameDuration = 9999;
        STATE.wkMatch = { f: { kind: 'ko', round: 'r16' }, me: 'NED', opp: 'MAR', knockout: true, city: null, extra: true, test: true };
        STATE.wkStarting = true;
        startGame();
        STATE.wkStarting = false;
        if (typeof wkDecorateHud === 'function') wkDecorateHud();
        STATE.score1 = 1; STATE.score2 = 1;
        $('hud-s1').textContent = '1'; $('hud-s2').textContent = '1';
        const go = () => {
            if (STATE.screen !== 'playing' || !team1Players.length) { setTimeout(go, 300); return; }
            start((score) => {
                const again = document.createElement('button');
                again.className = 'pens-again';
                again.textContent = `Klaar (${score[0]}-${score[1]}) · nog een keer`;
                again.onclick = () => location.reload();
                document.getElementById('game-screen').appendChild(again);
            });
        };
        setTimeout(go, 4200);                                  // after the kick-off countdown
    }
    if (typeof location !== 'undefined' && new URLSearchParams(location.search).get('test') === 'pens') {
        window.addEventListener('load', () => setTimeout(testShootout, 400));
    }

    return {
        start, stop, frame,
        active: () => !!S,
        phase: () => S && S.phase,
        // online messages (game.online.js)
        netChoice: (c) => take(c),
        netOutcome: (o) => play(o),
    };
})();

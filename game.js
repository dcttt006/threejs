// =====================================================
// PITCH ROYALE — Stadium Nightfall
// Feature + gameplay logic
// =====================================================


function initThree() {
    if (!scene) {
        scene = new THREE.Scene();

        camera = new THREE.PerspectiveCamera(CAM.fov, window.innerWidth / window.innerHeight, 1, 2000);

        renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
        // cap pixel ratio harder — Retina at 2× quadruples GPU work for marginal gain
        // a phone's screen is small and dense: at 1.5 the stadium (and the
        // text on its screens) came out soft, so touch devices get 2
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, (typeof IS_TOUCH !== 'undefined' && IS_TOUCH) ? 2 : 1.5));
        renderer.setSize(window.innerWidth, window.innerHeight);
        // Real-time shadows are intentionally OFF. With them on, the corner
        // spotlight projects player + stadium-mesh silhouettes onto the pitch
        // at a low angle, and from the gameplay camera those projections read
        // as fighter-jet outlines on the grass (verified empirically: turning
        // shadowMap on/off flips them on/off). We compensate with a flat dark
        // round shadow blob mounted under each player in makePlayer().
        renderer.shadowMap.enabled = false;
        // Per-material clipping planes: dressStadium() cuts the pitch column
        // and the camera side out of every imported model.
        renderer.localClippingEnabled = true;
        renderer.outputEncoding = THREE.sRGBEncoding;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.05;
        $('game-screen').appendChild(renderer.domElement);

        window.addEventListener('resize', onResize);
        // capture: true so focused buttons / iframes can't swallow the keystroke first
        window.addEventListener('keydown', onKeyDown, { capture: true });
        window.addEventListener('keyup', onKeyUp, { capture: true });
        // if the window loses focus, drop all held keys so the player doesn't drift
        window.addEventListener('blur', clearAllKeys);
        // tab visibility flip ALSO clears, so a held arrow doesn't get stuck on
        // the way back from a switched tab
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) clearAllKeys();
        });
        // any time a button steals keyboard focus during play, blur it so arrow
        // keys + space go straight to the game instead of activating the button
        document.addEventListener('focusin', (e) => {
            if (STATE.screen !== 'playing') return;
            const tgt = e.target;
            if (tgt && tgt.tagName === 'BUTTON') tgt.blur();
        });
    }

    // clear previous scene contents
    while (scene.children.length) scene.remove(scene.children[0]);

    const viewOf = ((!STATE.wkMatch || matchStadium().screen === 'wk') && matchStadium().view) || {};
    camLookShift = viewOf.lookZ || 0;

    buildSky();
    buildLights();
    buildField();
    buildGoals();
    buildBoards();
    buildStadium();        // imports the .glb of the selected stadium as scenery
    buildPlayers();
    buildBall();
    positionForKickoff();

    applyGameplayCamera();

    // reset fixed-step bookkeeping
    physicsAccum = 0;
    lastFrameTime = 0;
    // wipe any stale held keys
    clearAllKeys();
    // sync the bot's perception to the real ball at kickoff
    resetBotPerception();

    if (animationId) cancelAnimationFrame(animationId);
    animationId = requestAnimationFrame(animate);
}

// ----------- camera -----------
// The camera chosen in Instellingen (game.core.js: CAMERA_VIEWS), one for a
// laptop and one for a phone: on the long side, tracking the ball sideways
// like a TV main camera; 'Dynamisch' also moves in and out with it.
let CAM = cameraFor(typeof IS_TOUCH !== 'undefined' && IS_TOUCH ? 'phone' : 'laptop');
let camX = 0, camZ = 0;
let camLookShift = 0;      // per stadium (catalog view.lookZ): aim a little further out, e.g. to keep a big screen in frame

// what the camera follows: the ball, or what the referee (and the VAR) look at
function cameraFocus() {
    const f = typeof REF !== 'undefined' ? REF.camFocus() : null;
    return f || (ball ? ball.position : null);
}
function cameraTargetX() {
    const f = cameraFocus();
    if (!f) return 0;
    return Math.max(-CAM.maxX, Math.min(CAM.maxX, f.x * CAM.follow));
}
function cameraTargetZ() {
    const f = cameraFocus();
    return f && CAM.followZ ? f.z * CAM.followZ : 0;
}
function placeCamera() {
    camera.position.set(camX, CAM.height, CAM.back + camZ);
    camera.lookAt(camX, 0, CAM.lookZ + camLookShift * CAM.shift + camZ);
}
function applyGameplayCamera() {
    CAM = cameraFor(typeof IS_TOUCH !== 'undefined' && IS_TOUCH ? 'phone' : 'laptop');
    const aspect = window.innerWidth / window.innerHeight;
    camera.aspect = aspect;
    // widen the lens on narrow windows so both touchlines stay in frame
    camera.fov = aspect >= 1.6 ? CAM.fov : Math.min(62, CAM.fov * 1.6 / aspect);
    camera.far = Math.max(2000, CAM.back * 12);
    camera.updateProjectionMatrix();
    camX = cameraTargetX();
    camZ = cameraTargetZ();
    placeCamera();
}
function updateCamera(dt) {
    camX += (cameraTargetX() - camX) * Math.min(1, dt * 3);
    camZ += (cameraTargetZ() - camZ) * Math.min(1, dt * 2);
    placeCamera();
}

// sRGB hex -> the linear colour the renderer expects (it re-encodes to sRGB
// on output; without this every flat colour comes out washed and pastel)
function srgb(hex) {
    return new THREE.Color(hex).convertSRGBToLinear();
}
function litMat(hex) {
    return new THREE.MeshLambertMaterial({ color: srgb(hex) });
}

function buildSky() {
    // night blue, or the day sky of a stadium with the sun baked in (game.stadium.js)
    scene.add(stadiumSkyMesh(matchStadium(), 900));
}

function buildLights() {
    // even floodlight wash: bright from above, soft green bounce from the grass
    scene.add(new THREE.HemisphereLight(0xffffff, 0x4c7a4c, 0.52));
    scene.add(new THREE.AmbientLight(0xffffff, 0.12));
    const key = new THREE.DirectionalLight(0xfff6e6, 0.42);
    key.position.set(-40, 120, 60);
    scene.add(key);
}

// ----------- pitch -----------
// A drawn pitch at the gameplay dimensions. It is the stand-in for stadiums
// without a usable pitch of their own; otherwise the match is played on the
// model's grass and this one is hidden (see buildStadium).
const PITCH_MARGIN = 10;          // grass apron outside the lines
const PEN_DEPTH = 18 * PITCH_SCALE, PEN_WIDTH = 46 * PITCH_SCALE;
const BOX_DEPTH = 7 * PITCH_SCALE,  BOX_WIDTH = 30 * PITCH_SCALE;
const PEN_SPOT = 13 * PITCH_SCALE,  CIRCLE_R = 10 * PITCH_SCALE;

function makePitchTexture() {
    const PX = 16;                                  // pixels per world unit
    const w = (FIELD_W + PITCH_MARGIN * 2) * PX;
    const h = (FIELD_L + PITCH_MARGIN * 2) * PX;
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const ctx = c.getContext('2d');

    // mowing stripes across the length of the pitch, apron included
    const bands = 14;
    const bandW = FIELD_W / bands * PX;
    ctx.fillStyle = '#4c9440';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#43853a';
    for (let i = -2; i < bands + 2; i += 2) {
        ctx.fillRect(PITCH_MARGIN * PX + i * bandW, 0, bandW, h);
    }

    // fine grain so the grass isn't a flat fill
    const img = ctx.getImageData(0, 0, w, h);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
        const n = (Math.random() - 0.5) * 16;
        d[i] += n; d[i + 1] += n; d[i + 2] += n * 0.6;
    }
    ctx.putImageData(img, 0, 0);

    // markings, in world units with the origin on the centre spot
    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.scale(PX, PX);
    ctx.strokeStyle = '#f4f6f2';
    ctx.fillStyle = '#f4f6f2';
    ctx.lineWidth = 0.42;
    const W2 = FIELD_W / 2, L2 = FIELD_L / 2;

    ctx.strokeRect(-W2, -L2, FIELD_W, FIELD_L);
    ctx.beginPath(); ctx.moveTo(0, -L2); ctx.lineTo(0, L2); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, CIRCLE_R, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, 0.55, 0, Math.PI * 2); ctx.fill();

    [-1, 1].forEach(side => {
        const gx = side * W2;                       // goal line
        ctx.strokeRect(Math.min(gx, gx - side * PEN_DEPTH), -PEN_WIDTH / 2, PEN_DEPTH, PEN_WIDTH);
        ctx.strokeRect(Math.min(gx, gx - side * BOX_DEPTH), -BOX_WIDTH / 2, BOX_DEPTH, BOX_WIDTH);
        const sx = gx - side * PEN_SPOT;
        ctx.beginPath(); ctx.arc(sx, 0, 0.5, 0, Math.PI * 2); ctx.fill();
        // the "D": only the part of the circle outside the penalty area
        const a = Math.acos((PEN_DEPTH - PEN_SPOT) / CIRCLE_R);
        ctx.beginPath();
        if (side < 0) ctx.arc(sx, 0, CIRCLE_R, -a, a);
        else          ctx.arc(sx, 0, CIRCLE_R, Math.PI - a, Math.PI + a);
        ctx.stroke();
    });
    // corner arcs
    [[-W2, -L2, 0], [W2, -L2, Math.PI / 2], [W2, L2, Math.PI], [-W2, L2, -Math.PI / 2]].forEach(([x, y, start]) => {
        ctx.beginPath(); ctx.arc(x, y, 1.6, start, start + Math.PI / 2); ctx.stroke();
    });
    ctx.restore();

    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return tex;
}

function buildField() {
    const pitch = new THREE.Mesh(
        new THREE.PlaneGeometry(FIELD_W + PITCH_MARGIN * 2, FIELD_L + PITCH_MARGIN * 2),
        new THREE.MeshLambertMaterial({ map: makePitchTexture() })
    );
    pitch.rotation.x = -Math.PI / 2;
    pitch.name = 'own-pitch';                 // hidden when the stadium brings its own
    scene.add(pitch);

    // plain grass just under the stadium's pitch: scans have cracks and holes
    const under = new THREE.Mesh(
        new THREE.PlaneGeometry(FIELD_W + PITCH_MARGIN * 2, FIELD_L + PITCH_MARGIN * 2),
        new THREE.MeshLambertMaterial({ color: srgb(0x3a6a2c) })
    );
    under.rotation.x = -Math.PI / 2;
    under.position.y = -0.12;
    scene.add(under);

    // plain turf far beyond the stadium so gaps in a model never show a void
    const outer = new THREE.Mesh(
        new THREE.PlaneGeometry(3000, 3000),
        new THREE.MeshLambertMaterial({ color: srgb(0x1c2a1f) })
    );
    outer.rotation.x = -Math.PI / 2;
    outer.position.y = -1.2;
    scene.add(outer);
}

// ----------- goals -----------
const GOAL_DEPTH = 4.5;

function makeNetTexture() {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const ctx = c.getContext('2d');
    ctx.strokeStyle = 'rgba(255,255,255,0.95)';
    ctx.lineWidth = 5;
    ctx.strokeRect(0, 0, 64, 64);
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.encoding = THREE.sRGBEncoding;
    return tex;
}

// A stadium can colour the nets (catalog nets: [left, right], as seen from the
// pitch looking into the goal; De Kuip: red | white). Otherwise they are white.
function buildGoals() {
    const postMat = litMat(0xffffff);
    const baseNet = makeNetTexture();
    const st = typeof matchStadium === 'function' ? matchStadium() : null;
    const colours = (st && st.nets) || null;
    const netPanel = (wUnits, hUnits, colour) => {
        const tex = baseNet.clone();
        tex.needsUpdate = true;
        tex.repeat.set(wUnits / 0.9, hUnits / 0.9);   // one mesh square ≈ 0.9 units
        return new THREE.Mesh(
            new THREE.PlaneGeometry(wUnits, hUnits),
            new THREE.MeshBasicMaterial({ map: tex, color: srgb(colour || 0xffffff), transparent: true,
                opacity: colour ? 0.85 : 0.6, side: THREE.DoubleSide, depthWrite: false })
        );
    };
    const R = 0.24;

    [-1, 1].forEach(side => {
        const x = side * FIELD_W / 2;
        const back = x + side * GOAL_DEPTH;
        // looking into this goal from the pitch, your left hand is at z = leftZ
        const leftZ = side > 0 ? -1 : 1;
        const colourAt = (zs) => colours ? colours[zs === leftZ ? 0 : 1] : null;

        [-1, 1].forEach(zs => {
            const post = new THREE.Mesh(new THREE.CylinderGeometry(R, R, GOAL_H, 12), postMat);
            post.position.set(x, GOAL_H / 2, zs * GOAL_W / 2);
            scene.add(post);
        });
        const bar = new THREE.Mesh(new THREE.CylinderGeometry(R, R, GOAL_W + R * 2, 12), postMat);
        bar.rotation.x = Math.PI / 2;
        bar.position.set(x, GOAL_H, 0);
        scene.add(bar);

        // rear and roof in two halves, one per colour; each side panel in its half's colour
        [-1, 1].forEach(zs => {
            const rear = netPanel(GOAL_W / 2, GOAL_H, colourAt(zs));
            rear.rotation.y = Math.PI / 2;
            rear.position.set(back, GOAL_H / 2, zs * GOAL_W / 4);
            scene.add(rear);

            const roof = netPanel(GOAL_DEPTH, GOAL_W / 2, colourAt(zs));
            roof.rotation.x = -Math.PI / 2;                    // depth along x, width along z
            roof.position.set(x + side * GOAL_DEPTH / 2, GOAL_H, zs * GOAL_W / 4);
            scene.add(roof);

            const flank = netPanel(GOAL_DEPTH, GOAL_H, colourAt(zs));
            flank.position.set(x + side * GOAL_DEPTH / 2, GOAL_H / 2, zs * GOAL_W / 2);
            scene.add(flank);
        });
    });
}

// ----------- advertising boards -----------
const SHOW_BOARDS = false;
// Far touchline and behind both goals; the camera side stays open.
function makeBoardTexture(lines) {
    const c = document.createElement('canvas');
    c.width = 1024; c.height = 64;
    const ctx = c.getContext('2d');
    const panelW = c.width / lines.length;
    lines.forEach((text, i) => {
        const dark = i % 2 === 0;
        ctx.fillStyle = dark ? '#121512' : '#ffffff';
        ctx.fillRect(i * panelW, 0, panelW, 64);
        ctx.fillStyle = dark ? '#ffffff' : '#121512';
        ctx.font = '800 44px "Barlow Condensed", "Arial Narrow", Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text.toUpperCase(), i * panelW + panelW / 2, 35, panelW - 40);
    });
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = THREE.RepeatWrapping;
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return tex;
}

function buildBoards() {
    // No advertising boards in any stadium (also not in the WK): they didn't
    // line up with the models. The code stays for when they come back.
    if (!SHOW_BOARDS) return;
    const stadium = getSelectedStadium();
    // in a WK match the boards say WK 2026 and where it is played
    const texts = STATE.wkMatch ? wkBoardText() : ['Pitch Royale', stadium.name];
    const base = makeBoardTexture(texts);
    const H = 1.9, T = 0.5;
    const blank = new THREE.MeshLambertMaterial({ color: srgb(0x1a1d1a) });
    // One panel of print keeps its shape on the canvas (1024 / texts x 64);
    // every board shows a whole number of panels, so no name is cut off.
    const PANEL = H * (1024 / texts.length) / 64;
    const board = (length) => {
        const tex = base.clone();
        tex.needsUpdate = true;
        const panels = Math.max(2, Math.round(length / PANEL));
        tex.repeat.x = panels / texts.length;
        const face = new THREE.MeshBasicMaterial({ map: tex });
        // BoxGeometry faces: +x, -x, +y, -y, +z, -z — only +z carries the print
        return new THREE.Mesh(new THREE.BoxGeometry(length, H, T), [blank, blank, blank, blank, face, blank]);
    };

    // A U around the pitch: the far touchline and both goal ends, meeting in
    // the corners. The camera side stays open; the end boards stop at the
    // near touchline.
    const xEnd = FIELD_W / 2 + GOAL_DEPTH + 3.5;     // behind the goals
    const zFar = FIELD_L / 2 + 4.5;                  // behind the far touchline
    const zNear = FIELD_L / 2 + 2;

    const far = board(2 * xEnd - T);                 // between the inner faces of the end boards
    far.position.set(0, H / 2, -zFar);
    scene.add(far);

    const endLen = zFar + T / 2 + zNear;             // from the far board's back to the near touchline
    [-1, 1].forEach(side => {
        const end = board(endLen);
        end.rotation.y = -side * Math.PI / 2;        // printed face towards the pitch
        end.position.set(side * xEnd, H / 2, (zNear - zFar - T / 2) / 2);
        scene.add(end);
    });
}

// ----------- players -----------
const KIT = {
    1: { shirt: COLORS.team1, shorts: 0xffffff, socks: COLORS.team1, keeper: 0xf2c230 },
    2: { shirt: COLORS.team2, shorts: 0x10214f, socks: COLORS.team2, keeper: 0x2fb463 },
};
// A footballer for this side (game.players.js builds him): `look` a number
// for an ordinary look, or a look from playerLook()
function makePlayer(team, isKeeper, controlled, look, role, star) {
    const lk = typeof look === 'object' && look ? look : playerLook(team, isKeeper, role, look || 0, star);
    return makeFootballer(team, isKeeper, lk);
}

function buildPlayers() {
    team1Players = [];
    team2Players = [];

    // Five a side: a keeper and four outfield players in a diamond, each
    // with a role (ROLES): 'att' up front, 'lw' and 'rw' on the flanks,
    // 'def' at the back. A human plays one of the four at a time and takes
    // over whoever gets the ball or is nearest to it (see setControlled).
    // Hot-Seat (duo) and online: a human on each side; against the computer
    // only P1's side has one.
    const isCpu = STATE.mode === 'cpu';
    // the stars play up front (game.players.js: matchStars)
    const stars = matchStars();
    const add = (team, isKeeper, role, x, z, look) => {
        const p = makePlayer(team, isKeeper, false, look, role, role === 'att' ? stars[team] : null);
        p.position.set(x, 0, z);
        p.team = team;
        p.isKeeper = isKeeper;
        p.homePosition = { x, z };
        p.userData.role = role;
        if (!isKeeper) p.userData.isBot = true;
        scene.add(p);
        (team === 1 ? team1Players : team2Players).push(p);
        return p;
    };
    const mains = {};
    [1, 2].forEach((team) => {
        const side = team === 1 ? -1 : 1;
        const look = team === 1 ? 0 : 2;
        add(team, true, 'keeper', side * (FIELD_W / 2 - 5), 0, look);
        // the order matters: [keeper, att (where a human starts), lw, rw, def]
        ['att', 'lw', 'rw', 'def'].forEach((role, i) => {
            const at = ROLE_KICKOFF[role](false);
            const p = add(team, false, role, side * -at.a, side * -at.b, look + 1 + i);
            if (role === 'att') mains[team] = p;
        });
    });

    controlledP1 = null;
    controlledP2 = null;
    // with a star of your own you play him, and only him, the whole match
    lockedSlot[1] = !!stars[STATE.p1.team];
    lockedSlot[2] = false;
    setControlled(1, mains[STATE.p1.team]);
    if (!isCpu) setControlled(2, mains[STATE.p2.team]);
    // the referee and his assistants (game.referee.js)
    if (typeof REF !== 'undefined') REF.build();
}

// ----------- who you play -----------
// The arrow and the stamina bar belong to the human slot (1 or 2) and move
// with it: to the teammate who gets the ball (a pass, a keeper's throw, a
// ball won), to the one nearest the ball when the other side has it, or to
// the one nearest it when you press Pass without the ball.
const SWITCH_GAP = 700;            // ms between two automatic switches
const switchAt = { 1: 0, 2: 0 };
// A locked slot plays one man all match (your star, against the computer and
// as player 1 in Hot-Seat): no switching, his teammates are all the computer.
// Only a red card (force) moves it to someone else.
const lockedSlot = { 1: false, 2: false };
function setControlled(slot, p, force) {
    const old = slot === 1 ? controlledP1 : controlledP2;
    if (!p || old === p || p.userData.isKeeper) return;
    if (old && lockedSlot[slot] && !force) return;
    if (old) {
        const ou = old.userData;
        if (ou.arrow) { old.remove(ou.arrow); p.add(ou.arrow); p.userData.arrow = ou.arrow; ou.arrow = null; }
        if (ou.staminaBar) { old.remove(ou.staminaBar.bar); p.add(ou.staminaBar.bar); p.userData.staminaBar = ou.staminaBar; ou.staminaBar = null; }
        p.userData.remoteStick = ou.remoteStick || null;    // online: the opponent's stick
        ou.remoteStick = null;
        ou.charging = false; ou.chargeStart = 0; ou.shootHeld = false;
        ou.isBot = true;
        ou.drift = Math.random() * 6.28;
    } else {
        if (typeof scene !== 'undefined' && scene) {
            addStaminaBar(p);
            addPlayerArrow(p, slot === 1 ? ARROW_P1 : ARROW_P2);
        }
    }
    p.userData.isBot = false;
    p.userData.runT = 0;
    if (slot === 1) controlledP1 = p; else controlledP2 = p;
    switchAt[slot] = performance.now();
}
function slotOf(team) {
    if (controlledP1 && controlledP1.team === team) return 1;
    if (controlledP2 && controlledP2.team === team) return 2;
    return 0;
}
// the teammate nearest to where the ball is going, not counting `but`
function nearestMateToBall(team, but) {
    const side = (team === 1 ? team1Players : team2Players).filter(m => !m.userData.isKeeper && m !== but);
    const tx = ball.position.x + ball.velocity.x * 8, tz = ball.position.z + ball.velocity.z * 8;
    return nearestTo(side, tx, tz);
}
function autoSwitch(slot) {
    const me = slot === 1 ? controlledP1 : controlledP2;
    if (!me || lockedSlot[slot]) return;
    // a teammate has the ball: play him
    if (carrier && carrier.team === me.team && carrier !== me) { setControlled(slot, carrier); return; }
    if (me.userData.tackleT > 0) return;                                 // not in the middle of your slide
    if (carrier === me) return;
    if (passTarget && passTarget.to.team === me.team) return;            // the ball is coming to one of us
    const keeper = (me.team === 1 ? team1Players : team2Players)[0];
    if (keeper && keeper.userData.holdingBall) return;
    if (performance.now() - switchAt[slot] < SWITCH_GAP) return;
    // the other side has it, or it is loose: the one of us nearest to it, if clearly nearer
    const tx = ball.position.x + ball.velocity.x * 8, tz = ball.position.z + ball.velocity.z * 8;
    const dMe = Math.hypot(me.position.x - tx, me.position.z - tz);
    const best = nearestMateToBall(me.team, me);
    if (best.p && best.d < dMe - 9 && best.d < dMe * 0.65) setControlled(slot, best.p);
}

// ----------- sprint and stamina -----------
// Sprinting is 35% faster and empties the stamina bar in about three seconds;
// it refills in five. Run it dry and you have to wait for a quarter of it.
const SPRINT_MULT   = 1.35;
const STAMINA_DRAIN = 1 / (3.2 * 60);
const STAMINA_REGEN = 1 / (5 * 60);
const STAMINA_MIN   = 0.25;

// Returns whether p sprints this tick, and spends or refills his stamina.
function sprintFor(p, wanted) {
    const u = p.userData;
    if (u.stamina === undefined) u.stamina = 1;
    if (u.tired && u.stamina >= STAMINA_MIN) u.tired = false;
    const on = !!wanted && !u.tired && u.stamina > 0;
    if (on) {
        u.stamina = Math.max(0, u.stamina - STAMINA_DRAIN);
        if (u.stamina === 0) u.tired = true;
    } else {
        u.stamina = Math.min(1, u.stamina + STAMINA_REGEN);
    }
    u.sprinting = on;
    return on;
}

// A small bar over the head of each human player; shown while it isn't full.
function addStaminaBar(p) {
    const flat = (hex, opacity) => new THREE.MeshBasicMaterial({
        // both transparent, so renderOrder puts the fill over the background
        color: srgb(hex), transparent: true, opacity, depthTest: false, depthWrite: false,
    });
    const bar = new THREE.Group();
    const bg = new THREE.Mesh(new THREE.PlaneGeometry(5.6, 0.95), flat(0x121512, 0.85));
    const fgGeo = new THREE.PlaneGeometry(5.0, 0.5);
    fgGeo.translate(2.5, 0, 0);                       // grows from its left end
    const fg = new THREE.Mesh(fgGeo, flat(0xffd60a, 1));
    fg.position.set(-2.5, 0, 0.01);
    bg.renderOrder = 20;
    fg.renderOrder = 21;
    bar.add(bg, fg);
    bar.position.y = 9.3;
    bar.visible = false;
    p.add(bar);
    p.userData.staminaBar = { bar, fg };
}
// A flat arrow over the head of each human player, pointing down at him, so you
// always see which one is yours: yellow for player 1, light blue for player 2.
// It sits above the stamina bar and is drawn over everything else.
const ARROW_P1 = 0xffd60a, ARROW_P2 = 0x3cc8ff;
function addPlayerArrow(p, hex) {
    const tri = (w, h) => {
        const sh = new THREE.Shape();
        sh.moveTo(-w / 2, h / 2); sh.lineTo(w / 2, h / 2); sh.lineTo(0, -h / 2); sh.closePath();
        return new THREE.ShapeGeometry(sh);
    };
    const flat = (c) => new THREE.MeshBasicMaterial({ color: srgb(c), transparent: true, depthTest: false, depthWrite: false });
    const arrow = new THREE.Group();
    const edge = new THREE.Mesh(tri(3.1, 2.6), flat(0x121512));     // a dark edge: readable on grass and stands alike
    const fill = new THREE.Mesh(tri(2.3, 1.9), flat(hex));
    fill.position.set(0, 0.12, 0.01);
    edge.renderOrder = 22;
    fill.renderOrder = 23;
    arrow.add(edge, fill);
    arrow.position.y = ARROW_Y;
    p.add(arrow);
    p.userData.arrow = arrow;
}
const ARROW_Y = 11.5;                 // clear of the stamina bar (9.3)
const STAMINA_COLOR = srgb(0xffd60a);
const TIRED_COLOR   = srgb(0xd91e36);

function updateStaminaBars() {
    [controlledP1, controlledP2].forEach(p => {
        const ar = p && p.userData.arrow;
        if (ar) {
            ar.quaternion.copy(camera.quaternion);       // always face the camera
            ar.position.y = ARROW_Y + Math.sin(performance.now() / 260) * 0.25;   // a slow bob
        }
        const sb = p && p.userData.staminaBar;
        if (!sb) return;
        const st = p.userData.stamina ?? 1;
        sb.bar.visible = st < 0.995 && !p.userData.throwPose;     // not over the ball in a throw-in
        sb.fg.scale.x = Math.max(0.001, st);
        sb.fg.material.color.copy(p.userData.tired ? TIRED_COLOR : STAMINA_COLOR);
        sb.bar.quaternion.copy(camera.quaternion);   // always face the camera
    });
    // the Sprint button on phones shows the same stamina as a ring
    const btn = typeof IS_TOUCH !== 'undefined' && IS_TOUCH ? $('touch-sprint') : null;
    if (btn && controlledP1) {
        btn.style.setProperty('--stamina', (controlledP1.userData.stamina ?? 1).toFixed(3));
        btn.classList.toggle('is-tired', !!controlledP1.userData.tired);
        // with the ball: Schiet and Pass; without it: Tackle and Wissel (Vraag when your keeper has it)
        const own = hasBall(controlledP1);
        const myKeeper = (controlledP1.team === 1 ? team1Players : team2Players)[0];
        const shoot = $('touch-shoot'), pass = $('touch-pass');
        // a ball of ours on its way to you: Schiet strikes it first time; a set piece you take: Pass plays it short
        const coming = !own && passTarget && passTarget.to === controlledP1 && !carrier;
        const shootText = coming ? 'Volley' : !own ? 'Tackle'
            : shoot && shoot.classList.contains('is-high') ? 'Hoog'
            : shoot && shoot.classList.contains('is-power') ? 'Power' : 'Schiet';
        const passText = aimingHere() ? 'Kort' : own ? (pass && pass.classList.contains('is-high') ? 'Hoog' : 'Pass')
            : (lockedSlot[1] || (myKeeper && myKeeper.userData.holdingBall) ? 'Vraag' : 'Wissel');
        if (shoot && shoot.textContent !== shootText) shoot.textContent = shootText;
        if (pass && pass.textContent !== passText) pass.textContent = passText;
        shoot?.classList.toggle('is-tackle', !own && !coming);
        pass?.classList.toggle('is-ball', own && !STATE.setPiece);
        shoot?.classList.toggle('is-resting', !own && controlledP1.userData.tackleCd > 0);
    }
}

// Turn each figure towards where it is running and swing its limbs.
// Purely cosmetic: reads positions, never writes them.
function animatePlayers(dt) {
    if (dt <= 0) return;
    [...team1Players, ...team2Players].forEach(p => {
        const u = p.userData;
        const rig = u.rig;
        if (!rig) return;
        const dx = p.position.x - (u.lastX ?? p.position.x);
        const dz = p.position.z - (u.lastZ ?? p.position.z);
        u.lastX = p.position.x;
        u.lastZ = p.position.z;
        const speed = Math.min(80, Math.hypot(dx, dz) / dt);     // units per second

        // heading: direction of travel, or towards the ball when standing
        let target = null;
        // keepers shuffle sideways facing the ball; outfield players face where they run
        if (u.faceTo) target = Math.atan2(u.faceTo.x, u.faceTo.z);        // at the ball for a set piece
        else if (speed > 4 && !u.isKeeper) target = Math.atan2(dx, dz);
        else if (ball) target = Math.atan2(ball.position.x - p.position.x, ball.position.z - p.position.z);
        if (target !== null) {
            let diff = target - rig.body.rotation.y;
            diff = Math.atan2(Math.sin(diff), Math.cos(diff));   // shortest way round
            rig.body.rotation.y += diff * Math.min(1, dt * (speed > 4 ? 14 : 5));
        }

        // stride: ease in and out so stopping doesn't snap the legs straight
        const want = Math.min(1, speed / 35);
        u.stride += (want - u.stride) * Math.min(1, dt * 10);
        u.phase = (u.phase || 0) + dt * (6 + speed * 0.22);
        const swing = Math.sin(u.phase) * 0.95 * u.stride;
        rig.legL.rotation.x = swing;
        rig.legR.rotation.x = -swing;
        rig.armL.rotation.x = -swing * 0.8;
        rig.armR.rotation.x = swing * 0.8;
        rig.body.position.y = Math.abs(Math.cos(u.phase)) * 0.12 * u.stride;
        rig.body.rotation.x = 0.16 * u.stride;                    // lean into the run

        // a kick: the right leg swings back, then through the ball
        if (u.kickT > 0) {
            u.kickT = Math.max(0, u.kickT - dt);
            const k = 1 - u.kickT / 0.28;                         // 0 → 1
            rig.legR.rotation.x = k < 0.35 ? (k / 0.35) * 0.9 : 0.9 - (k - 0.35) / 0.65 * 2.1;
            rig.armL.rotation.x = -0.6 * Math.sin(k * Math.PI);
        }

        // asking for the ball: the right arm straight up
        if (u.callT > 0) {
            u.callT = Math.max(0, u.callT - dt);
            rig.armR.rotation.x = -2.9;
        }
        // a throw-in: both arms up, the ball over his head
        if (u.throwPose) {
            rig.armL.rotation.x = -2.9;
            rig.armR.rotation.x = -2.9;
        }

        // a sliding tackle: leaning back, low over the grass, the leading leg out
        const sliding = u.tackleT > 0 || u.getUpT > 0;
        u.slide = (u.slide || 0) + ((sliding ? 1 : 0) - (u.slide || 0)) * Math.min(1, dt * (sliding ? 20 : 8));
        if (u.slide > 0.01) {
            rig.body.rotation.x = rig.body.rotation.x * (1 - u.slide) - 1.05 * u.slide;
            rig.legR.rotation.x = rig.legR.rotation.x * (1 - u.slide) - 1.3 * u.slide;
            rig.legL.rotation.x = rig.legL.rotation.x * (1 - u.slide) + 0.4 * u.slide;
            rig.armL.rotation.x = rig.armL.rotation.x * (1 - u.slide) - 1.2 * u.slide;
        }

        // a keeper's dive: the whole body tips over towards the ball and drops
        rig.body.rotation.order = 'YXZ';
        let rollWant = 0;
        if (u.diveT > 0) {
            u.diveT = Math.max(0, u.diveT - dt);
            const yaw = rig.body.rotation.y;
            const side = Math.sign(-Math.cos(yaw) * (u.diveX || 0) + Math.sin(yaw) * (u.diveZ || 0)) || 1;
            rollWant = side * 1.3 * Math.min(1, u.diveT / 0.18);
            rig.armL.rotation.x = rig.armR.rotation.x = -2.6;     // both arms up and out
        }
        // quick to go down, slower to get back up
        u.roll = (u.roll || 0) + (rollWant - (u.roll || 0)) * Math.min(1, dt * (rollWant ? 18 : 7));
        rig.body.rotation.z = u.roll;
        rig.body.position.y -= Math.abs(u.roll) * 0.9 + (u.slide || 0) * 1.1;

        // fouled: face down on the grass for a moment, then back up
        if (u.fallT > 0) u.fallT = Math.max(0, u.fallT - dt);
        u.fall = (u.fall || 0) + ((u.fallT > 0 ? 1 : 0) - (u.fall || 0)) * Math.min(1, dt * (u.fallT > 0 ? 12 : 4));
        if (u.fall > 0.01) {
            rig.body.rotation.x = rig.body.rotation.x * (1 - u.fall) + 1.4 * u.fall;
            rig.armL.rotation.x = rig.armR.rotation.x = -2.2 * u.fall;
            rig.legL.rotation.x = rig.legR.rotation.x = 0;
            rig.body.position.y -= 0.35 * u.fall;
        }
    });
}

// ----------- ball -----------
const BALL_VISUAL_R = 0.78;      // drawn smaller than the physics radius (BALL_SIZE)

function makeBallTexture() {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 128;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 256, 128);
    ctx.fillStyle = '#1a1a1a';
    // staggered dark patches so you can see the ball roll
    for (let row = 0; row < 3; row++) {
        for (let col = 0; col < 6; col++) {
            const x = (col + (row % 2 ? 0.5 : 0)) * (256 / 6);
            const y = 24 + row * 40;
            ctx.beginPath();
            ctx.ellipse(x, y, 12, 11, 0, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    return tex;
}

function buildBall() {
    // `ball` carries position + velocity for the physics; the visible sphere
    // sits lower inside it so it rests on the grass instead of hovering.
    ball = new THREE.Group();
    const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(BALL_VISUAL_R, 24, 16),
        new THREE.MeshLambertMaterial({ map: STATE.wkMatch ? wkBallTexture() : makeBallTexture() })
    );
    mesh.position.y = BALL_VISUAL_R - BALL_SIZE;
    ball.add(mesh);
    ball.userData.mesh = mesh;

    const blob = new THREE.Mesh(
        new THREE.CircleGeometry(BALL_VISUAL_R * 1.05, 20),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.3, depthWrite: false })
    );
    blob.rotation.x = -Math.PI / 2;
    ball.userData.shadow = blob;
    scene.add(blob);

    ball.position.set(0, BALL_SIZE, 0);
    ball.velocity = { x: 0, y: 0, z: 0 };
    scene.add(ball);
}

// keep the ball's ground shadow under it; it shrinks as the ball rises
function updateBallShadow() {
    const blob = ball && ball.userData.shadow;
    if (!blob) return;
    const lift = Math.max(0, ball.position.y - BALL_SIZE);
    blob.position.set(ball.position.x, 0.06, ball.position.z);
    blob.scale.setScalar(Math.max(0.45, 1 - lift * 0.07));
    blob.material.opacity = Math.max(0.1, 0.3 - lift * 0.02);
}

function positionForKickoff() {
    ballCall = null;
    if (typeof REF !== 'undefined') REF.onKickoff();
    if (STATE.setPiece) endSetPiece(null);
    lastTouch = 0;
    ball.position.set(0, BALL_SIZE, 0);
    ball.velocity = { x: 0, y: 0, z: 0 };

    // clear any in-flight keeper holds and player charges
    [...team1Players, ...team2Players].forEach(p => {
        p.userData.holdingBall = false;
        p.userData.holdStart = 0;
        p.userData.charging = false;
        p.userData.chargeStart = 0;
        p.userData.shootHeld = false;
        p.userData.vx = 0;
        p.userData.vz = 0;
        p.userData.cooldown = 0;
        p.userData.diveT = 0;
        p.userData.react = 0;
        p.userData.tackleT = p.userData.getUpT = p.userData.tackleCd = 0;
        p.userData.callT = 0;
        p.userData.calledBy = null;
        p.userData.aimX = p.team === 1 ? 1 : -1;      // facing the other goal
        p.userData.aimZ = 0;
        p.userData.stamina = 1;
        p.userData.tired = false;
        p.userData.sprinting = false;
    });
    carrier = null;
    passTarget = null;
    curl = null;
    lastKick = null;

    [...team1Players, ...team2Players].forEach(p => {
        const at = kickoffSpot(p);
        p.position.set(at.x, 0, at.z);
    });
    kickoffHold = { team: STATE.kickoffTeam, ticks: KICKOFF_WAIT };
}

// ----------- kick-off -----------
// Everybody in his own half; the side kicking off has its main player at the
// ball. Until the ball has been played the other side stays outside the centre
// circle and in its own half (or for four seconds at most, so nobody can stall).
const KICKOFF_WAIT = 240;          // ticks
const RESTART_TICKS = 180;         // three seconds from goal to kick-off
let kickoffHold = null;            // { team, ticks } until the kick-off is taken

// where each role lines up, in its own half: a = towards the other goal
// (negative: own half), b = across. The side kicking off has its striker at the ball.
const ROLE_KICKOFF = {
    att: (kicking) => ({ a: kicking ? -3 : -18 * PITCH_SCALE, b: 0 }),
    lw:  (kicking) => ({ a: (kicking ? -10 : -16) * PITCH_SCALE, b: -20 * PITCH_SCALE }),
    rw:  (kicking) => ({ a: (kicking ? -10 : -16) * PITCH_SCALE, b: 20 * PITCH_SCALE }),
    def: () => ({ a: -32 * PITCH_SCALE, b: 0 }),
};
function kickoffSpot(p) {
    const side = p.team === 1 ? 1 : -1;                 // the way this side attacks
    if (p.userData.isKeeper) return { x: -side * (FIELD_W / 2 - 5), z: 0 };
    const kicking = p.team === STATE.kickoffTeam;
    const at = (ROLE_KICKOFF[p.userData.role] || ROLE_KICKOFF.def)(kicking);
    // the one a human plays at kick-off stands where his role does
    return { x: side * at.a, z: side * at.b };
}

function keepOutForKickoff() {
    if (!kickoffHold) return;
    const moved = Math.hypot(ball.position.x, ball.position.z) > 2.5;
    if (lastKick || moved || --kickoffHold.ticks <= 0) { kickoffHold = null; return; }
    [...team1Players, ...team2Players].forEach(p => {
        if (p.team === kickoffHold.team || p.userData.isKeeper) return;
        const side = p.team === 1 ? -1 : 1;
        if (p.position.x * side < 1) p.position.x = side;           // own half
        const d = Math.hypot(p.position.x, p.position.z);
        const r = CIRCLE_R + 1.5;
        if (d < r) {                                                 // outside the circle
            const k = r / (d || 1);
            p.position.x = d ? p.position.x * k : side * r;
            p.position.z *= d ? k : 0;
        }
    });
}

// After a goal: the ball stays in the net, everybody jogs back to his
// kick-off spot for three seconds, then play restarts.
function walkBack() {
    STATE.restartTicks--;
    [...team1Players, ...team2Players].forEach(p => {
        // a slide when the goal went in: finished (and up again) before he walks back
        if (!p.userData.isKeeper && (p.userData.tackleT > 0 || p.userData.getUpT > 0) && slideTackle(p)) return;
        const at = kickoffSpot(p);
        const dx = at.x - p.position.x, dz = at.z - p.position.z;
        const d = Math.hypot(dx, dz);
        const want = Math.min(RUN_SPEED * 0.8, d * 0.08);
        if (d > 0.3) steer(p, dx / d * want, dz / d * want, RUN_ACCEL);
        else steer(p, 0, 0, RUN_BRAKE);
        p.position.x += p.userData.vx || 0;
        p.position.z += p.userData.vz || 0;
        p.userData.aimX = p.team === 1 ? 1 : -1;
        p.userData.aimZ = 0;
        sprintFor(p, false);                                         // catch their breath
    });
    separatePlayers();
    if (STATE.restartTicks === 50) {                                 // the ball goes back on the spot
        ball.position.set(0, BALL_SIZE, 0);
        ball.velocity = { x: 0, y: 0, z: 0 };
    }
    if (STATE.restartTicks <= 0) {
        positionForKickoff();
        Object.keys(keys).forEach(k => keys[k] = false);   // a held button doesn't fire on restart
        STATE.scoring = false;
        STATE.inputLocked = false;
    }
}

function onResize() {
    if (!camera || !renderer) return;
    applyGameplayCamera();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// ----------- input -----------
// keys[]        : currently held (level-triggered, used for movement)
// keysPressed[] : just-pressed this tick (edge-triggered, used for shooting)
const keysPressed = {};
const GAME_KEYS = new Set([
    'KeyW','KeyA','KeyS','KeyD',
    'ArrowUp','ArrowDown','ArrowLeft','ArrowRight',
    'Space','Enter',
    'KeyQ','ShiftRight','ShiftLeft',     // pass (Q, right Shift) and sprint (left Shift)
    'AltRight','Slash',                  // player 2 sprints with right Alt/Option or /
]);
// Numpad fallback — when NumLock is off some laptops fire Numpad codes for arrows.
// We map them onto the canonical Arrow* code so movement code only checks one name.
const KEY_ALIASES = {
    'Numpad8': 'ArrowUp',
    'Numpad2': 'ArrowDown',
    'Numpad4': 'ArrowLeft',
    'Numpad6': 'ArrowRight',
};
// e.key fallback for legacy / odd browsers that fail to populate e.code (rare,
// but seen on some virtual keyboards / Bluetooth dongles)
const KEY_FROM_EKEY = {
    'ArrowUp': 'ArrowUp', 'ArrowDown': 'ArrowDown',
    'ArrowLeft': 'ArrowLeft', 'ArrowRight': 'ArrowRight',
    ' ': 'Space', 'Enter': 'Enter',
    'w': 'KeyW', 'W': 'KeyW',
    'a': 'KeyA', 'A': 'KeyA',
    's': 'KeyS', 'S': 'KeyS',
    'd': 'KeyD', 'D': 'KeyD',
    'q': 'KeyQ', 'Q': 'KeyQ',
};
function resolveKeyCode(e) {
    if (e.code && KEY_ALIASES[e.code]) return KEY_ALIASES[e.code];
    if (e.code && GAME_KEYS.has(e.code)) return e.code;
    if (e.key && KEY_FROM_EKEY[e.key]) return KEY_FROM_EKEY[e.key];
    if (e.key === 'Shift') return e.location === 2 ? 'ShiftRight' : 'ShiftLeft';
    return null;
}
function onKeyDown(e) {
    // gate by screen so name inputs / page navigation aren't hijacked
    if (STATE.screen !== 'playing') return;
    const code = resolveKeyCode(e);
    if (!code) return;
    keys[code] = true;
    if (!e.repeat) keysPressed[code] = true;
    e.preventDefault();
}
function onKeyUp(e) {
    // releases always fire — otherwise a key held when leaving the screen
    // would stay 'pressed' forever
    const code = resolveKeyCode(e);
    if (!code) return;
    keys[code] = false;
}
function clearAllKeys() {
    Object.keys(keys).forEach(k => keys[k] = false);
    Object.keys(keysPressed).forEach(k => keysPressed[k] = false);
}


// ----------- fixed-step game loop -----------
// Render runs at the display rate; game logic ticks at exactly 60 Hz so the
// game feels identical on a 60 Hz, 144 Hz or 240 Hz monitor.
const PHYSICS_HZ = 60;
const PHYSICS_STEP = 1 / PHYSICS_HZ;
let physicsAccum = 0;
let lastFrameTime = 0;

// The bot uses a *delayed, smoothed* version of the ball position for strategic
// decisions, so it can't react instantly to the user's input — eliminates the
// "the CPU mirrors me" feel.
// One per side: each follows the ball as quickly as its players read the
// game (levelFor: your computer teammates quicker than a weak opponent).
const botPerception = { x: 0, z: 0, init: false, 1: { x: 0, z: 0, vx: 0, vz: 0 }, 2: { x: 0, z: 0, vx: 0, vz: 0 } };
function resetBotPerception() {
    botPerception.x = ball ? ball.position.x : 0;
    botPerception.z = ball ? ball.position.z : 0;
    [1, 2].forEach(t => { Object.assign(botPerception[t], { x: botPerception.x, z: botPerception.z, vx: 0, vz: 0 }); });
    botPerception.init = true;
}
function perceptionOf(team) { return botPerception[team] || botPerception; }

function animate(now) {
    if (STATE.screen !== 'playing') return;
    animationId = requestAnimationFrame(animate);

    if (lastFrameTime === 0) lastFrameTime = now;
    let frameDt = (now - lastFrameTime) / 1000;
    lastFrameTime = now;
    if (!Number.isFinite(frameDt) || frameDt < 0) frameDt = PHYSICS_STEP;
    if (frameDt > 0.25) frameDt = 0.25;     // tab/sleep recovery cap

    // a penalty shoot-out runs its own scene (game.pens.js)
    if (STATE.pens && typeof PENS !== 'undefined' && PENS.active()) {
        PENS.frame(frameDt);
        renderer.render(scene, camera);
        return;
    }
    // Jij bent de VAR plays its own scripted scenes, no match (game.var.js)
    if (STATE.varGame && typeof VARGAME !== 'undefined' && VARGAME.active()) {
        if (!STATE.paused) VARGAME.frame(frameDt);
        renderer.render(scene, camera);
        return;
    }

    // online, the guest doesn't play the match itself: it shows the host's (game.online.js)
    const guest = typeof ONLINE !== 'undefined' && ONLINE.isGuest();
    const host = typeof ONLINE !== 'undefined' && ONLINE.isHost();
    if (guest) {
        if (!STATE.paused) ONLINE.guestFrame();
    } else if (!STATE.paused) {
        physicsAccum += frameDt;
        let safety = 5;
        while (physicsAccum >= PHYSICS_STEP && safety-- > 0) {
            physicsAccum -= PHYSICS_STEP;
            if (host) ONLINE.step(); else gameTick();
        }
        if (safety <= 0) physicsAccum = 0;       // dropped frames — don't spiral
    } else {
        physicsAccum = 0;                          // no catch-up on resume
    }

    if (!STATE.paused) animatePlayers(frameDt);
    if (!STATE.paused && typeof REF !== 'undefined') REF.frame(frameDt);
    updateBallShadow();
    updateCamera(frameDt);
    updateChargeFx();
    updateStaminaBars();
    updateSetPieceUI();
    updateTimer();
    renderer.render(scene, camera);
}

// Charge feedback on the arrow over the head of the one you play: it grows
// while a shot charges and turns red once a power shot is ready (held long).
const ARROW_COLORS = [srgb(ARROW_P1), srgb(ARROW_P2)];
const POWER_COLOR = srgb(0xe0203a);
function updateChargeFx() {
    [controlledP1, controlledP2].forEach((p, i) => {
        if (!p) return;
        const u = p.userData;
        let t = 0, power = false;
        if (u.charging) {
            const ms = performance.now() - (u.chargeStart || performance.now());
            t = Math.min(1, Math.max(0, (ms - CHARGE_MIN_MS) / (CHARGE_MAX_MS - CHARGE_MIN_MS)));
            power = ms >= POWER_SHOT_MS;
        }
        const ar = u.arrow;
        if (ar) {
            const target = 1 + t * 0.3 + (power ? 0.2 : 0);
            ar.scale.setScalar(ar.scale.x + (target - ar.scale.x) * 0.35);
            const fill = ar.children[1];
            if (fill && fill.material && fill.material.color) fill.material.color.copy(power ? POWER_COLOR : ARROW_COLORS[i]);
        }
        const ring = u.ring;
        if (ring) {
            const target = 1 + t * 0.55;
            ring.scale.setScalar(ring.scale.x + (target - ring.scale.x) * 0.35);
            ring.material.opacity = 0.7 + t * 0.3;
        }
    });
}

function gameTick() {
    if (STATE.paused) return;
    // the referee: play stopped for offside, a foul or the VAR (game.referee.js)
    if (typeof REF !== 'undefined') {
        REF.always();
        if (REF.stopped()) {
            REF.tick();
            for (const k in keysPressed) keysPressed[k] = false;
            return;
        }
    }
    if (STATE.scoring) {
        walkBack();
        for (const k in keysPressed) keysPressed[k] = false;
        return;
    }
    if (!STATE.inputLocked && !STATE.scoring) {
        if (!STATE.setPiece) {
            autoSwitch(1);
            autoSwitch(2);
        }
        controls().forEach((c) => {
            if (!c.p) return;
            const sp = STATE.setPiece;
            if (sp) {
                // a corner or a throw-in: whoever takes it stands at the ball
                // (Pass plays it short, a click or tap puts it anywhere: setPieceAim);
                // everyone else can move, but there is no ball to play yet
                if (sp.taker === c.p) {
                    if (sp.phase === 'ready' && pressedOnce(c.pass)) takeSetPiece(null);
                    // a free kick or a penalty: Schiet goes at goal (up or down: that corner)
                    else if (sp.phase === 'ready' && (sp.kind === 'free' || sp.kind === 'penalty') && pressedOnce(c.shoot)) shootSetPiece(aimZFor(c));
                } else {
                    // your star doesn't take it, a teammate does: you still say where it goes
                    // (a click, or Pass for short) while you find a spot
                    const lockedHere = (c.p === controlledP1 && lockedSlot[1]) || (c.p === controlledP2 && lockedSlot[2]);
                    if (lockedHere && sp.phase === 'ready' && sp.team === c.p.team && pressedOnce(c.pass)) takeSetPiece(null);
                    movePlayer(c.p, c.move);
                    keepAway(c.p, sp);
                }
                c.p.userData.shootHeld = pressed(c.shoot);
                c.p.userData.charging = false;
                return;
            }
            movePlayer(c.p, c.move);
            handleShoot(c.p, c.shoot, c.up);
            handlePass(c.p, c.pass, c.up);
        });
    }

    updateSetPiece();
    updateAI();
    separatePlayers();
    keepOutForKickoff();
    updateCarry();
    applyCurl();
    updateBall();
    countPossession();
    if (typeof REF !== 'undefined') REF.live();

    // Update the bot's perception of the ball: smoothed lerp with ~150 ms lag.
    // Bot AI uses this for strategy, not the raw ball position.
    if (!botPerception.init) resetBotPerception();
    const read = aiLevel().read;
    botPerception.x += (ball.position.x - botPerception.x) * read;
    botPerception.z += (ball.position.z - botPerception.z) * read;
    [1, 2].forEach(t => {
        const per = botPerception[t];
        const r = levelFor((t === 1 ? team1Players : team2Players)[1]).read;
        per.x += (ball.position.x - per.x) * r;
        per.z += (ball.position.z - per.z) * r;
        // where it is going is read as late: a pass is seen a moment after it is played
        per.vx += (ball.velocity.x - per.vx) * r;
        per.vz += (ball.velocity.z - per.vz) * r;
    });

    // consume edge-triggered presses so a held key only fires once
    for (const k in keysPressed) keysPressed[k] = false;
}

function pressedOnce(arr) { return arr.some(k => keysPressed[k]); }

// Who plays with which keys. Online: you, on this keyboard or phone, and your
// opponent's keys as they arrive over the network (game.online.js writes them
// as R_...). Against the computer: WASD or the arrows. Two on one keyboard:
// WASD and the arrows each. `up` held as Schiet or Pass goes: high.
function controls() {
    const both = {
        up: ['KeyW', 'ArrowUp'], down: ['KeyS', 'ArrowDown'], left: ['KeyA', 'ArrowLeft'], right: ['KeyD', 'ArrowRight'],
        sprint: ['ShiftLeft', 'ShiftRight'],
    };
    if (STATE.mode === 'online') return [
        { p: controlledP1, move: both, shoot: ['Space', 'Enter'], up: ['KeyW', 'ArrowUp'], pass: ['KeyQ'] },
        { p: controlledP2, move: { up: ['R_up'], down: ['R_down'], left: ['R_left'], right: ['R_right'], sprint: ['R_sprint'] },
            shoot: ['R_shoot'], up: ['R_up', 'R_high'], pass: ['R_pass'] },
    ];
    if (STATE.mode === 'cpu') return [
        { p: controlledP1, move: both, shoot: ['Space'], up: ['KeyW', 'ArrowUp'], pass: ['KeyQ'] },
    ];
    return [
        { p: controlledP1, move: { up: ['KeyW'], down: ['KeyS'], left: ['KeyA'], right: ['KeyD'], sprint: ['ShiftLeft'] },
            shoot: ['Space'], up: ['KeyW'], pass: ['KeyQ'] },
        { p: controlledP2, move: { up: ['ArrowUp'], down: ['ArrowDown'], left: ['ArrowLeft'], right: ['ArrowRight'], sprint: ['AltRight', 'Slash'] },
            shoot: ['Enter'], up: ['ArrowUp'], pass: ['ShiftRight'] },
    ];
}

// Push overlapping players apart so they can't lock into a single tile.
// Each pair finds the overlap and shoves them along the connecting axis.
function separatePlayers() {
    const all = [...team1Players, ...team2Players];
    const minDist = PLAYER_SIZE * 1.2;        // tighter contact — less wall-feeling
    const minDist2 = minDist * minDist;
    for (let i = 0; i < all.length; i++) {
        const a = all[i];
        for (let j = i + 1; j < all.length; j++) {
            const b = all[j];
            const dx = a.position.x - b.position.x;
            const dz = a.position.z - b.position.z;
            const d2 = dx*dx + dz*dz;
            if (d2 >= minDist2) continue;

            // exact overlap — nudge with a deterministic direction
            let nx, nz, d;
            if (d2 < 0.01) {
                nx = 1; nz = 0; d = 0;
            } else {
                d = Math.sqrt(d2);
                nx = dx / d; nz = dz / d;
            }
            const overlap = (minDist - d) * 0.5 + 0.02;
            // shove rules:
            //   keeper vs field player → only the field player moves
            //   human  vs bot          → bot does most of the dance (90/10)
            //   else                   → 50/50
            // a keeper, or whoever stands at the ball for a corner or a throw-in, isn't pushed
            const aIsKeeper = a.userData && (a.userData.isKeeper || a.userData.setPieceTaker);
            const bIsKeeper = b.userData && (b.userData.isKeeper || b.userData.setPieceTaker);
            const aIsHuman = (a === controlledP1 || a === controlledP2);
            const bIsHuman = (b === controlledP1 || b === controlledP2);
            let aShove, bShove;
            if (aIsKeeper && !bIsKeeper)        { aShove = 0;    bShove = 1; }
            else if (bIsKeeper && !aIsKeeper)   { aShove = 1;    bShove = 0; }
            else if (aIsHuman && !bIsHuman)     { aShove = 0.1;  bShove = 0.9; }
            else if (bIsHuman && !aIsHuman)     { aShove = 0.9;  bShove = 0.1; }
            else                                { aShove = 0.5;  bShove = 0.5; }
            a.position.x += nx * overlap * (aShove * 2);
            a.position.z += nz * overlap * (aShove * 2);
            b.position.x -= nx * overlap * (bShove * 2);
            b.position.z -= nz * overlap * (bShove * 2);

            // clamp both to pitch bounds (the taker of a set piece stands outside them)
            [a, b].forEach((q) => {
                if (q.userData.setPieceTaker) return;
                q.position.x = Math.max(-FIELD_W/2 + PLAYER_SIZE/2, Math.min(FIELD_W/2 - PLAYER_SIZE/2, q.position.x));
                q.position.z = Math.max(-FIELD_L/2 + PLAYER_SIZE/2, Math.min(FIELD_L/2 - PLAYER_SIZE/2, q.position.z));
            });
        }
    }
}

function pressed(arr) { return arr.some(k => keys[k]); }

// ----------- movement -----------
// Everything below is in world units per physics tick (60 per second).
// Players have a velocity that eases towards where the stick points, so they
// start, turn and stop like footballers instead of teleporting a step a frame.
const RUN_SPEED     = 0.50;   // ~30 units/s: the pitch (110) in under four seconds
const DRIBBLE_SPEED = 0.43;   // a touch slower with the ball at your feet
const RUN_ACCEL     = 0.065;  // full speed in about a sixth of a second
const RUN_BRAKE     = 0.09;

// Ease a player's velocity towards (wantX, wantZ), at most `rate` per tick.
function steer(p, wantX, wantZ, rate) {
    const u = p.userData;
    u.vx = u.vx || 0;
    u.vz = u.vz || 0;
    const dx = wantX - u.vx, dz = wantZ - u.vz;
    const d = Math.hypot(dx, dz);
    if (d <= rate) { u.vx = wantX; u.vz = wantZ; }
    else { u.vx += dx / d * rate; u.vz += dz / d * rate; }
}

function movePlayer(player, k) {
    if (!player) return;
    if (slideTackle(player)) return;
    if (receivePass(player)) return;

    // collect raw input direction
    let inX = 0, inZ = 0;
    if (pressed(k.up))    inZ -= 1;
    if (pressed(k.down))  inZ += 1;
    if (pressed(k.left))  inX -= 1;
    if (pressed(k.right)) inX += 1;

    // the on-screen stick (phones) is analogue: a small push walks, a full one runs
    // (online the opponent's stick comes over the network: remoteStick)
    let analog = 1;
    const stick = player === controlledP1 ? (typeof touchMove !== 'undefined' ? touchMove : null) : player.userData.remoteStick;
    if (stick && stick.active) {
        inX = stick.x;
        inZ = stick.z;
        analog = Math.min(1, Math.max(0.4, (Math.hypot(inX, inZ) - 0.18) / 0.55));
    }

    const inLen = Math.hypot(inX, inZ);
    // up/down as it is held right now, for curling a shot after it is hit
    player.userData.inZ = Math.abs(inZ) > 0.35 ? Math.sign(inZ) : 0;
    let top = (carrier === player ? DRIBBLE_SPEED : RUN_SPEED) * analog;
    if (sprintFor(player, pressed(k.sprint || []) && inLen > 0)) top *= SPRINT_MULT;
    if (player.userData.charging && carrier === player) top *= 0.4;   // set yourself for the shot (you don't run on into the keeper)
    if (inLen > 0) {
        // remember the direction faced, for dribbling and aiming
        player.userData.aimX = inX / inLen;
        player.userData.aimZ = inZ / inLen;
        steer(player, inX / inLen * top, inZ / inLen * top, RUN_ACCEL);
    } else {
        steer(player, 0, 0, RUN_BRAKE);
    }
    let mx = player.userData.vx;
    let mz = player.userData.vz;
    if (mx === 0 && mz === 0) return;

    // Slide-along-defender: project velocity onto the contact tangent so the
    // player slips around opponents instead of jittering between canX / canZ.
    // The human keeps a small fraction of inward velocity so they can muscle
    // the bot back instead of feeling stuck against a wall.
    const all = [...team1Players, ...team2Players];
    const minDist = PLAYER_SIZE * 1.2;
    const minDist2 = minDist * minDist;
    // Only cancel inward velocity vs the keeper (hard wall — no walking through
    // him into the goal). Vs field players we let the human plough through at
    // full speed; separatePlayers shoves the bot aside afterwards. Result: the
    // arrows always translate to motion, no sticky / laggy feel during a press.
    for (const other of all) {
        if (other === player) continue;
        const otherIsKeeper = other.userData && other.userData.isKeeper;
        if (!otherIsKeeper) continue;
        const ndx = (player.position.x + mx) - other.position.x;
        const ndz = (player.position.z + mz) - other.position.z;
        const nd2 = ndx*ndx + ndz*ndz;
        if (nd2 >= minDist2) continue;
        const nd = Math.sqrt(nd2) || 0.001;
        const nx = ndx / nd;
        const nz = ndz / nd;
        const dot = mx * nx + mz * nz;
        if (dot < 0) {
            mx -= dot * nx;
            mz -= dot * nz;
        }
    }
    // the wall check above may have taken some speed off
    player.userData.vx = mx;
    player.userData.vz = mz;
    player.position.x += mx;
    player.position.z += mz;

    // pitch bounds
    player.position.x = Math.max(-FIELD_W/2 + PLAYER_SIZE/2, Math.min(FIELD_W/2 - PLAYER_SIZE/2, player.position.x));
    player.position.z = Math.max(-FIELD_L/2 + PLAYER_SIZE/2, Math.min(FIELD_L/2 - PLAYER_SIZE/2, player.position.z));
}

// A pass (or a cross, a throw) on its way to the player you control: he goes to
// meet it by himself, as in FIFA, so a pass arrives; the stick takes over the
// moment he has it. True while that takes over from the stick.
function receivePass(player) {
    if (!passTarget || passTarget.to !== player || carrier || player.userData.isKeeper) return false;
    const ip = interceptPoint(player, RUN_SPEED);
    const dx = ip.x - player.position.x, dz = ip.z - player.position.z;
    const d = Math.hypot(dx, dz);
    const u = player.userData;
    if (d > 0.6) {
        // a high ball he sprints for sooner: someone else can get under it too
        const top = RUN_SPEED * (d > (lastKick && lastKick.high ? 5 : 14) && sprintFor(player, true) ? SPRINT_MULT : 1);
        steer(player, dx / d * Math.min(top, d * 0.25), dz / d * Math.min(top, d * 0.25), RUN_ACCEL * 1.5);
    } else {
        sprintFor(player, false);
        steer(player, 0, 0, RUN_BRAKE);
    }
    // face the way the ball comes from, so it is taken in front of him
    const bx = ball.position.x - player.position.x, bz = ball.position.z - player.position.z;
    const bd = Math.hypot(bx, bz);
    if (bd > 1) { u.aimX = bx / bd; u.aimZ = bz / bd; }
    player.position.x += u.vx;
    player.position.z += u.vz;
    player.position.x = Math.max(-FIELD_W/2 + PLAYER_SIZE/2, Math.min(FIELD_W/2 - PLAYER_SIZE/2, player.position.x));
    player.position.z = Math.max(-FIELD_L/2 + PLAYER_SIZE/2, Math.min(FIELD_L/2 - PLAYER_SIZE/2, player.position.z));
    return true;
}

// Where p can first get to the ball, as it rolls or flies on from (fromX,
// fromZ) (the real ball, or where his side thinks it is): the same steps as
// updateBall, without other players. A ball in the air counts only where it
// is low enough to take. { x, z, t } with t in ticks; where the ball stops
// or goes out if he can't get there sooner.
function interceptPoint(p, speed, fromX, fromZ, fromVx, fromVz) {
    let x = fromX ?? ball.position.x, y = ball.position.y, z = fromZ ?? ball.position.z;
    let vx = fromVx ?? ball.velocity.x, vy = ball.velocity.y, vz = fromVz ?? ball.velocity.z;
    const reach = CARRY_REACH - 0.8;
    const px = p.position.x, pz = p.position.z;
    if (carrier || (Math.hypot(vx, vz) < 0.02 && y <= BALL_SIZE + 0.05)) return { x, z, t: 0 };
    for (let t = 1; t <= 150; t++) {
        vy -= 0.022;
        if (y > BALL_SIZE + 0.05) { vx *= 0.996; vz *= 0.996; }
        x += vx; y += vy; z += vz;
        if (y > 16) { y = 16; vy = Math.min(vy, 0); }
        if (y <= BALL_SIZE) {
            const hard = vy < -0.08;
            y = BALL_SIZE;
            vy = hard ? Math.abs(vy) * 0.22 : 0;
            const f = hard ? 0.85 : 0.985;
            vx *= f; vz *= f;
            if (Math.abs(vx) < 0.012) vx = 0;
            if (Math.abs(vz) < 0.012) vz = 0;
        }
        if (Math.abs(x) > FIELD_W / 2 || Math.abs(z) > FIELD_L / 2) {
            return { x: Math.max(-FIELD_W / 2 + 2, Math.min(FIELD_W / 2 - 2, x)), z: Math.max(-FIELD_L / 2 + 2, Math.min(FIELD_L / 2 - 2, z)), t, out: true };
        }
        if (y >= BALL_SIZE + 1.4) continue;
        if (Math.hypot(x - px, z - pz) - reach <= speed * t) return { x, z, t };
        if (vx === 0 && vz === 0 && vy === 0) return { x, z, t };
    }
    return { x, z, t: 150 };
}

// ----------- the ball at your feet -----------
// One field player at a time carries the ball. It rolls just in front of him,
// in the direction he faces, and keeps its speed when he passes or shoots.
let carrier = null;
let lastCarrierSeen = null;        // to note the moment someone gets the ball
const CARRY_REACH = PLAYER_SIZE / 2 + BALL_SIZE + 1.1;   // how close you must get to take it
const CARRY_DIST  = PLAYER_SIZE / 2 + BALL_SIZE + 0.45;  // where it sits in front of you
const STEAL_REACH = PLAYER_SIZE / 2 + BALL_SIZE + 0.5;   // a challenger this close takes it
const CONTROL_SHIELD = 24;        // ticks a player who picks up a loose ball can't be robbed
const INTERCEPT_SPEED = 1.9;      // a ball slower than this a player in its path can cut out
const HEADER_TOP = 9.8;           // the highest a player gets his head to the ball
let lastTouch = 0;                // the side that touched the ball last: who gets the throw-in, corner or goal kick

function facingOf(p) {
    const u = p.userData;
    if (u.aimX !== undefined && (u.aimX || u.aimZ)) return { x: u.aimX, z: u.aimZ };
    return { x: p.team === 1 ? 1 : -1, z: 0 };
}
function ballDistTo(p) {
    return Math.hypot(ball.position.x - p.position.x, ball.position.z - p.position.z);
}
function knockBall(dirX, dirZ, power, lift) {
    ball.velocity.x = dirX * power;
    ball.velocity.z = dirZ * power;
    ball.velocity.y = lift;
}

function updateCarry() {
    const field = [...team1Players, ...team2Players].filter(p => !p.userData.isKeeper);
    if (passTarget && --passTarget.t <= 0) passTarget = null;
    field.forEach(p => {
        if (p.userData.cooldown > 0) p.userData.cooldown--;
        if (p.userData.shield > 0) p.userData.shield--;
    });

    const keeperHolds = team1Players[0]?.userData.holdingBall || team2Players[0]?.userData.holdingBall;
    // nobody has the ball while it is out of play for a set piece
    if (keeperHolds || STATE.scoring || STATE.setPiece) { carrier = null; return; }

    const low = ball.position.y < BALL_SIZE + 1.4;
    const free = (p) => !(p.userData.cooldown > 0);

    // a challenger from the other side who keeps his foot in takes it: on
    // average after about a fifth of a second of contact, and never straight
    // back from someone who has only just won it
    if (carrier && !(carrier.userData.shield > 0)) {
        for (const rival of field) {
            if (rival.team === carrier.team || !free(rival) || ballDistTo(rival) >= STEAL_REACH) continue;
            const human = rival === controlledP1 || rival === controlledP2;
            if (Math.random() < (human ? 0.07 : levelFor(rival).steal)) {
                if (typeof REF !== 'undefined' && REF.onChallenge(rival, carrier, false)) return;   // a foul: the whistle
                carrier.userData.cooldown = 36;
                carrier = rival;
                rival.userData.shield = 45;
                break;
            }
        }
    }

    // keep the ball, unless it got away (a shot, a block, a tackle)
    if (carrier && (!free(carrier) || !low || ballDistTo(carrier) > CARRY_REACH + 0.8)) carrier = null;

    // a first-time shot: Schiet pressed while a ball of ours was on its way to
    // him. Struck the moment it is there, off the foot low down, a header up high.
    if (!carrier && passTarget) {
        const p = passTarget.to, v = p.userData.volley;
        if (v && !p.userData.isKeeper && free(p) && ball.position.y < HEADER_TOP && ballDistTo(p) < CARRY_REACH + 0.9) {
            p.userData.volley = null;
            if (typeof REF !== 'undefined' && REF.onReceive(p)) return;         // offside: the flag goes up
            const header = ball.position.y > BALL_SIZE + 2.4;
            const charge = header ? 0.5 : 0.8;
            fireShot(p, POWER_MIN + (POWER_MAX - POWER_MIN) * charge, charge, false, { fromY: ball.position.y, header });
            return;
        }
    }

    // a loose ball goes to whoever reaches it first. A ball travelling fast
    // has to come close to be controlled; a shot can't be stopped by the
    // shooter's own teammate, and a pass is easiest for the one it is meant for:
    // he reaches a little further for it, and a pass you play is hard to cut out
    if (!carrier && low) {
        const fast = Math.hypot(ball.velocity.x, ball.velocity.z) > 1.2;
        let best = null, bestD = Infinity;
        const ballSpeed = Math.hypot(ball.velocity.x, ball.velocity.z);
        const byHuman = !!(lastKick && lastKick.kind === 'pass' && lastKick.byHuman);
        const past = lastKick && lastKick.past && aiTick < lastKick.until ? lastKick.past : null;
        field.forEach(p => {
            if (!free(p)) return;
            if (past && past.includes(p)) return;
            let reach = CARRY_REACH;
            if (lastKick && lastKick.kind === 'pass' && lastKick.to === p) reach = CARRY_REACH + 1.2;
            else if (lastKick && (fast || (byHuman && ballSpeed > 0.5))) {
                if (lastKick.kind === 'shot' && p.team === lastKick.team) return;
                // someone the ball wasn't meant for has to be close to it; a pass
                // that runs into him he can still cut out (it doesn't bounce off
                // him like a wall), a hard shot he can only block
                const slow = byHuman ? ballSpeed < 0.9 : ballSpeed < INTERCEPT_SPEED;
                reach = slow ? Math.max(CARRY_REACH * 0.6, PLAYER_SIZE / 2 + BALL_SIZE + 0.3) : CARRY_REACH * 0.6;
            }
            const d = ballDistTo(p);
            if (d < reach && d < bestD) { bestD = d; best = p; }
        });
        carrier = best;
        if (carrier && typeof REF !== 'undefined' && REF.onReceive(carrier)) return;   // offside: the flag goes up
        if (carrier) {
            passTarget = null; lastKick = null; shotLive = null;
            field.forEach(p => { p.userData.volley = null; });
            // a moment to get it under control before anyone can take it off him
            carrier.userData.shield = Math.max(carrier.userData.shield || 0, CONTROL_SHIELD);
        }
    }
    if (carrier) lastTouch = carrier.team;

    if (carrier && carrier !== lastCarrierSeen) carrier.userData.gotAt = performance.now();
    lastCarrierSeen = carrier;
    updateBallCall();                 // a teammate who was asked for it plays it now
    if (!carrier) return;
    const f = facingOf(carrier);
    const tx = carrier.position.x + f.x * CARRY_DIST;
    const tz = carrier.position.z + f.z * CARRY_DIST;
    // glide to the spot in front, so turning swings the ball round smoothly
    ball.position.x += (tx - ball.position.x) * 0.35;
    ball.position.z += (tz - ball.position.z) * 0.35;
    ball.position.y = BALL_SIZE;
    ball.velocity.x = carrier.userData.vx || 0;
    ball.velocity.z = carrier.userData.vz || 0;
    ball.velocity.y = 0;
}

// charge-shot tuning
const CHARGE_MIN_MS = 0;        // any press counts, even a flick fires
const CHARGE_MAX_MS = 650;      // hold this long for a full-power shot
const POWER_MIN = 1.35;         // a tap: a pass or a placed shot (~80 units/s)
const POWER_MAX = 2.55;         // full charge: hard, but a keeper can still get there
// keep holding on: a power shot. Flat and much harder, into a corner, but
// you are slowed down all the while you wind it up (a defender can get there)
const POWER_SHOT_MS = 1150;
const POWER_SHOT = 3.25;

// The shoot key: low, or high when up is held as it is let go (W or the up
// arrow; on a phone a swipe up over Schiet). Held long: a power shot. Without
// the ball: a tackle, or with a ball of ours on its way to you, a first-time
// shot (a volley or a header) the moment it gets there.
function handleShoot(player, key, upKeys) {
    if (!player) return;

    // charge mechanic: press starts a timer, release fires with scaled power
    const isHeld = pressed(key);
    const wasHeld = !!player.userData.shootHeld;

    if (isHeld && !wasHeld) {
        if (!hasBall(player)) {
            player.userData.charging = false;
            player.userData.shootHeld = isHeld;
            if (passTarget && passTarget.to === player && !carrier) { player.userData.volley = { at: performance.now() }; return; }
            // without the ball the same key is a sliding tackle
            startTackle(player);
            return;
        }
        player.userData.charging = true;
        player.userData.chargeStart = performance.now();
    }

    if (!isHeld && wasHeld && player.userData.charging) {
        // released: fire, if the ball is at your feet
        const heldMs = performance.now() - (player.userData.chargeStart || 0);
        const clamped = Math.min(CHARGE_MAX_MS, Math.max(CHARGE_MIN_MS, heldMs));
        const t = (clamped - CHARGE_MIN_MS) / (CHARGE_MAX_MS - CHARGE_MIN_MS);
        const power = POWER_MIN + (POWER_MAX - POWER_MIN) * t;
        player.userData.charging = false;
        player.userData.chargeStart = 0;
        const high = (upKeys && pressed(upKeys))
            || (player === controlledP1 && typeof touchShotHigh !== 'undefined' && touchShotHigh);
        if (typeof touchShotHigh !== 'undefined' && player === controlledP1) touchShotHigh = false;
        const powerShot = !high && heldMs >= POWER_SHOT_MS;
        if (carrier === player || ballDistTo(player) < CARRY_REACH + 0.6) fireShot(player, power, t, high, powerShot ? { power: true } : null);
    }

    player.userData.shootHeld = isHeld;
}

// Every shot goes at the other goal, wherever you face. Up or down (held, or
// the last way you ran) picks that corner; otherwise it goes low towards the
// middle, on your side of it.
// High shots: the height at the goal line it is struck for, short press ..
// full charge (the bar is at 10, a full one may go over), and the least height
// it must have where the keeper stands, about 6 units off his line.
const HIGH_LOW = 8.4, HIGH_TOP = 9.6, HIGH_OVER_KEEPER = 7.7, KEEPER_LINE = 6;
// [height where the keeper stands, height at the line] for a ball struck this
// far at this speed and lift, run through the same steps as updateBall
function highFlight(dist, speed, lift) {
    let x = 0, y = BALL_SIZE + 0.2, vx = speed, vy = lift, atKeeper = null;
    for (let t = 0; t < 600; t++) {
        vy -= 0.022;
        if (y > BALL_SIZE + 0.05) vx *= 0.996;
        x += vx; y += vy;
        if (y > 16) { y = 16; vy = Math.min(vy, 0); }
        if (atKeeper === null && x >= dist - KEEPER_LINE) atKeeper = y;
        if (x >= dist) return [atKeeper ?? y, y];
        if (y <= BALL_SIZE && t > 3) return [atKeeper ?? y, -1];      // lands short
    }
    return [atKeeper ?? y, y];
}
// the lift that crosses the line at `want`, raised if that would leave it
// low enough for the keeper to take in front of his goal
function highLift(dist, speed, want) {
    const search = (ok) => {
        let lo = 0.05, hi = 1.6;
        for (let i = 0; i < 22; i++) { const m = (lo + hi) / 2; if (ok(m)) hi = m; else lo = m; }
        return (lo + hi) / 2;
    };
    let lift = search(m => highFlight(dist, speed, m)[1] >= want);
    if (highFlight(dist, speed, lift)[0] < HIGH_OVER_KEEPER) {
        lift = search(m => highFlight(dist, speed, m)[0] >= HIGH_OVER_KEEPER);
    }
    return lift;
}
// opts: { power } a power shot; { header, fromY } struck first time, off the
// head or the foot, where the ball is
function fireShot(player, power, charge01, high, opts) {
    opts = opts || {};
    const f = facingOf(player);
    const goalX = player.team === 1 ? FIELD_W / 2 : -FIELD_W / 2;
    const reach = GOAL_W * 0.45;                               // just inside the post
    // the keeper right in front of you and no corner picked: round him, into
    // the side of the goal he isn't covering (a shot into his chest from two
    // yards used to be the only option)
    const keeper = (player.team === 1 ? team2Players : team1Players)[0];
    const kClose = keeper && Math.hypot(keeper.position.x - ball.position.x, keeper.position.z - ball.position.z) < 9
        && Math.abs(keeper.position.x - goalX) < Math.abs(ball.position.x - goalX);
    let aimZ = Math.abs(f.z) > 0.3
        ? Math.sign(f.z) * reach
        : kClose ? (keeper.position.z > 0 ? -reach : reach)
        : Math.max(-reach * 0.5, Math.min(reach * 0.5, ball.position.z * 0.5));
    // a power shot goes for a corner (the one you aim at, else the one the
    // keeper isn't covering), hit so hard it can fly a little wide
    if (opts.power) {
        const side = Math.abs(f.z) > 0.3 ? Math.sign(f.z) : (keeper && keeper.position.z > 0 ? -1 : 1);
        aimZ = side * reach * 0.92 + (Math.random() - 0.5) * GOAL_W * 0.22;
    }
    // a header or a volley isn't placed as well as a shot you set yourself for
    if (opts.header || opts.fromY !== undefined) aimZ += (Math.random() - 0.5) * GOAL_W * (opts.header ? 0.5 : 0.3);
    const dx = goalX - ball.position.x, dz = aimZ - ball.position.z;
    const len = Math.hypot(dx, dz) || 1;
    const nx = dx / len, nz = dz / len;

    if (opts.power) {
        knockBall(nx, nz, POWER_SHOT, 0.05);
    } else if (opts.header) {
        // nodded at goal: down from head height, so it bounces on the way
        knockBall(nx, nz, power, -0.12);
    } else if (high) {
        // pick the height it should cross the line at, and the lift that gets it
        // there over this distance (a full one may go over: a little spread)
        const speed = power * 0.88;
        const want = HIGH_LOW + (HIGH_TOP - HIGH_LOW) * charge01 + (Math.random() - 0.5) * 1.4 * charge01;
        knockBall(nx, nz, speed, highLift(len, speed, want));
    } else {
        // a tap lifts a little, a full shot stays low and flat
        knockBall(nx, nz, power, 0.2 - charge01 * 0.12);
    }
    ball.position.x = player.position.x + nx * CARRY_DIST;
    ball.position.z = player.position.z + nz * CARRY_DIST;
    ball.position.y = opts.fromY !== undefined ? Math.max(BALL_SIZE + 0.2, opts.fromY) : BALL_SIZE + 0.2;
    player.userData.cooldown = 14;          // don't take it straight back off your own boot
    player.userData.kickT = opts.header ? 0 : 0.28;   // swing the leg (animatePlayers)
    player.userData.volley = null;
    if (carrier === player) carrier = null;
    passTarget = null;
    lastTouch = player.team;
    lastKick = { by: player, team: player.team, kind: 'shot', high: !!high, power: !!opts.power, at: performance.now() };
    shotTaken(player.team);
    // aftertouch: what is held now aimed the shot, a fresh up/down curls it
    curl = { by: player, t: CURL_TICKS, z0: player.userData.inZ || 0, curled: false };
}

// ----------- sliding tackle -----------
// The shoot key without the ball: a slide along the ground, towards the ball
// when it is close. Reaching the man on the ball wins it most of the time,
// otherwise it is knocked loose. A missed slide leaves you on the grass for
// a moment, and you can't slide again straight away.
const TACKLE_TICKS = 24;          // the slide, 0.4 s
const TACKLE_SPEED = 0.85;        // faster than a sprint at the start, slowing down
const TACKLE_GETUP_MISS = 26;     // on the ground after a miss
const TACKLE_GETUP_WIN = 8;
const TACKLE_COOLDOWN = 80;       // before the next slide
const TACKLE_AIM_RANGE = 10;      // within this distance the slide goes for the ball

function hasBall(p) {
    return carrier === p || (!carrier && ballDistTo(p) < CARRY_REACH + 0.6);
}

function startTackle(p) {
    const u = p.userData;
    if (u.tackleT > 0 || u.getUpT > 0 || u.tackleCd > 0) return;
    let dir = facingOf(p);
    const bx = ball.position.x - p.position.x, bz = ball.position.z - p.position.z;
    const bd = Math.hypot(bx, bz);
    if (bd > 0.5 && bd < TACKLE_AIM_RANGE) dir = { x: bx / bd, z: bz / bd };
    u.tvx = dir.x * TACKLE_SPEED;
    u.tvz = dir.z * TACKLE_SPEED;
    u.aimX = dir.x; u.aimZ = dir.z;
    u.tackleT = TACKLE_TICKS;
    u.tackleWon = false;
    u.tackleCd = TACKLE_COOLDOWN;
}

// The computer slides in too (teammates and opponents alike): the one pressing
// the man on the ball, a few steps from it, from the front or the side (from
// behind is a foul: game.referee.js), now and then, more often at a higher
// level (LEVELS.slide), and seldom in his own box, where a foul is a penalty.
const BOT_SLIDE_MIN = 2.2, BOT_SLIDE_MAX = 7;
function botWantsSlide(p, owner, lvl, ownGoalX) {
    const u = p.userData;
    if (!owner || owner.team === p.team || !lvl.slide || u.tackleCd > 0 || u.cooldown > 0) return false;
    if (owner.userData.shield > 0) return false;                 // he has only just won it
    const bx = ball.position.x - p.position.x, bz = ball.position.z - p.position.z, bd = Math.hypot(bx, bz);
    if (bd < BOT_SLIDE_MIN || bd > BOT_SLIDE_MAX) return false;
    // not from behind him: where he goes, the slider must be ahead of or beside him
    const ov = Math.hypot(owner.userData.vx || 0, owner.userData.vz || 0);
    if (ov > 0.05) {
        const dot = ((owner.userData.vx || 0) * -bx + (owner.userData.vz || 0) * -bz) / (ov * bd);
        if (dot < -0.35) return false;
    }
    const inOwnBox = Math.abs(owner.position.x - ownGoalX) < PEN_DEPTH && Math.abs(owner.position.z) < PEN_WIDTH / 2;
    return Math.random() < lvl.slide * (inOwnBox ? 0.25 : 1);
}

// Moves a sliding (or getting up) player; true while that takes over from the
// stick. Runs for every outfield player each tick, the one you play and the
// computer's alike: a slide carries on to the end (and he gets up again) even
// when you have switched to someone else meanwhile (that used to leave him
// stuck in the slide, running about lying down).
function slideTackle(p) {
    const u = p.userData;
    if (u.tackleCd > 0) u.tackleCd--;
    if (u.tackleT > 0) {
        u.tackleT--;
        p.position.x += u.tvx;
        p.position.z += u.tvz;
        u.vx = u.tvx; u.vz = u.tvz;
        u.tvx *= 0.93; u.tvz *= 0.93;
        p.position.x = Math.max(-FIELD_W/2 + PLAYER_SIZE/2, Math.min(FIELD_W/2 - PLAYER_SIZE/2, p.position.x));
        p.position.z = Math.max(-FIELD_L/2 + PLAYER_SIZE/2, Math.min(FIELD_L/2 - PLAYER_SIZE/2, p.position.z));

        if (!u.tackleWon && ballDistTo(p) < STEAL_REACH + 0.7) {
            if (carrier && carrier.team !== p.team && typeof REF !== 'undefined' && REF.onChallenge(p, carrier, true)) {
                u.tackleWon = true;                       // a foul: the whistle (game.referee.js)
                u.tackleT = 0;
                u.getUpT = TACKLE_GETUP_MISS;
                return true;
            }
            if (carrier && carrier.team !== p.team) {
                carrier.userData.cooldown = 50;
                carrier.userData.shield = 0;
                if (Math.random() < 0.7) {
                    carrier = p;                          // clean: the ball is yours
                    u.shield = 45;
                } else {
                    carrier = null;                       // poked away
                    knockBall(u.tvx / TACKLE_SPEED, u.tvz / TACKLE_SPEED, 0.75, 0.05);
                    lastTouch = p.team;
                }
                u.tackleWon = true;
            } else if (!carrier) {
                u.tackleWon = true;                       // a loose ball: just take it
            }
        }
        if (u.tackleT === 0) u.getUpT = u.tackleWon ? TACKLE_GETUP_WIN : TACKLE_GETUP_MISS;
        return true;
    }
    if (u.getUpT > 0) {
        u.getUpT--;
        steer(p, 0, 0, RUN_BRAKE);
        return true;
    }
    return false;
}

// ----------- asking for the ball -----------
// The pass key without the ball: the arm goes up and whoever of your side has
// it (your computer teammate, or your keeper once he has held it a moment)
// plays it to you.
const CALL_DELAY = 12;            // a teammate's reaction, 0.2 s
let ballCall = null;              // { from, to, t }

function callForBall(player) {
    player.userData.callT = 0.7;                          // arm up (animatePlayers)
    const side = player.team === 1 ? team1Players : team2Players;
    const keeper = side[0];
    if (keeper && keeper.userData.holdingBall) { keeper.userData.calledBy = player; return; }
    if (carrier && carrier !== player && carrier.team === player.team) {
        ballCall = { from: carrier, to: player, t: CALL_DELAY };
    }
}
function updateBallCall() {
    if (!ballCall) return;
    if (carrier !== ballCall.from) { ballCall = null; return; }   // lost it, or already played it
    if (--ballCall.t > 0) return;
    passBall(ballCall.from, ballCall.to);
    ballCall = null;
}

// ----------- curl (aftertouch) -----------
// Right after your shot, press up or down (W/S, the arrows, or the stick) and
// the ball bends towards that corner of the goal; it stops bending once it is
// heading for the corner, so holding longer never takes it wide. The direction
// you were already holding when you shot only aims; let go and press again to
// curl that way too. A keeper who has already dived can't follow it.
const CURL_TICKS = 40;
const CURL_RATE = 0.065;         // most the flight turns per tick (radians)
let curl = null;

function applyCurl() {
    if (!curl) return;
    const held = team1Players[0]?.userData.holdingBall || team2Players[0]?.userData.holdingBall;
    if (carrier || held || STATE.scoring || curl.t <= 0) { curl = null; return; }
    curl.t--;
    const s = curl.by.userData.inZ || 0;
    if (s === 0) { curl.z0 = 0; return; }        // released: the next press curls
    if (s === curl.z0) return;                   // still the key that aimed it
    const vx = ball.velocity.x, vz = ball.velocity.z;
    if (Math.hypot(vx, vz) < 0.6) return;
    // turn towards the pressed corner of the goal being shot at, no further
    const goalX = curl.by.team === 1 ? FIELD_W / 2 : -FIELD_W / 2;
    const want = Math.atan2(s * GOAL_W * 0.42 - ball.position.z, goalX - ball.position.x);
    let diff = want - Math.atan2(vz, vx);
    diff = Math.atan2(Math.sin(diff), Math.cos(diff));
    if (Math.abs(diff) < 0.004) return;
    const a = Math.sign(diff) * Math.min(Math.abs(diff), CURL_RATE);
    const c = Math.cos(a), sn = Math.sin(a);
    ball.velocity.x = vx * c - vz * sn;
    ball.velocity.z = vx * sn + vz * c;
    curl.curled = true;
    curl.spin = s;
}

// ----------- passing -----------
// The pass key (Q, right Shift, or Pass on a phone):
//   * your keeper has the ball → he gives it to you
//   * you have it → to the teammate you are facing who is free: the line to
//     him clear of opponents, the further forward the better; your keeper
//     only when you face your own goal
//   * nobody of yours has it → you switch to the teammate nearest the ball
// A pass is weighted for the distance and played into the receiver's run,
// and you play on with the one who receives it.
let passTarget = null;           // { to, t }: the receiver moves to meet the ball
let lastKick = null;             // { by, team, kind: 'shot' | 'pass' }

// how close the nearest opponent comes to the line from (ax, az) to (bx, bz)
function laneRoom(team, ax, az, bx, bz) {
    const enemies = (team === 1 ? team2Players : team1Players).filter(e => !e.userData.isKeeper);
    const dx = bx - ax, dz = bz - az, L2 = dx * dx + dz * dz || 1;
    let room = Infinity;
    enemies.forEach((e) => {
        const t = Math.max(0, Math.min(1, ((e.position.x - ax) * dx + (e.position.z - az) * dz) / L2));
        room = Math.min(room, Math.hypot(ax + dx * t - e.position.x, az + dz * t - e.position.z));
    });
    return room;
}
// how free a teammate is to be passed to: room round him and on the way to him,
// how far it takes the ball forward, not too short, not too long
function passValue(from, m) {
    const goalSign = from.team === 1 ? 1 : -1;
    const enemies = (from.team === 1 ? team2Players : team1Players).filter(e => !e.userData.isKeeper);
    const d = Math.hypot(m.position.x - from.position.x, m.position.z - from.position.z);
    const open = Math.min(14, nearestTo(enemies, m.position.x, m.position.z).d);
    const lane = Math.min(8, laneRoom(from.team, from.position.x, from.position.z, m.position.x, m.position.z));
    const adv = (m.position.x - from.position.x) * goalSign;
    return adv * 0.05 + open * 0.07 + lane * 0.13 - Math.max(0, d - 42 * PITCH_SCALE) * 0.05 - (d < 10 ? (10 - d) * 0.12 : 0) - (lane < 3 ? 1 : 0);
}

// Pass, or with up held (W or the up arrow; on a phone a swipe up over Pass)
// a high pass: lofted over the defenders, so it comes down at his feet.
function handlePass(player, keyArr, upKeys) {
    if (!player) return;
    if (!pressedOnce(keyArr)) return;

    const side = player.team === 1 ? team1Players : team2Players;
    // without the ball: ask your keeper for it, or switch to whoever is nearest it
    if (!hasBall(player)) {
        const keeper = side[0];
        if ((keeper && keeper.userData.holdingBall) || (carrier && carrier.team === player.team)) { callForBall(player); return; }
        const slot = player === controlledP1 ? 1 : player === controlledP2 ? 2 : 0;
        if (lockedSlot[slot]) return;                   // you play your star, nobody else
        const best = nearestMateToBall(player.team, player);
        if (slot && best.p) setControlled(slot, best.p);
        return;
    }
    const touchHigh = player === controlledP1 && typeof touchPassHigh !== 'undefined' && touchPassHigh;
    if (touchHigh) touchPassHigh = false;
    const keyHigh = !!(upKeys && pressed(upKeys));
    const high = keyHigh || touchHigh;
    let f = facingOf(player);
    // up on the keyboard says "high", not "that way": what counts is left or
    // right (with neither: forward). A phone's stick still aims all round.
    const stick = player === controlledP1 ? (typeof touchMove !== 'undefined' && touchMove.active) : !!(player.userData.remoteStick && player.userData.remoteStick.active);
    if (keyHigh && !stick && f.z < 0) {
        f = Math.abs(f.x) > 0.2 ? { x: Math.sign(f.x), z: 0 } : { x: player.team === 1 ? 1 : -1, z: 0 };
    }
    const goalSign = player.team === 1 ? 1 : -1;
    const enemies = (player.team === 1 ? team2Players : team1Players).filter(e => !e.userData.isKeeper);
    let best = null, bestScore = -Infinity;
    side.forEach(m => {
        if (m === player) return;
        const dx = m.position.x - player.position.x, dz = m.position.z - player.position.z;
        const d = Math.hypot(dx, dz) || 1;
        // mostly where you face; among those the freest
        const facing = (dx * f.x + dz * f.z) / d;
        let score;
        if (high) {
            // over the top: the further forward and the more room round him the
            // better; a short one hangs in the air too long to be any use
            if (m.userData.isKeeper) return;
            const open = Math.min(16, nearestTo(enemies, m.position.x, m.position.z).d);
            score = facing * 1.4 + dx * goalSign * 0.012 + open * 0.08 + Math.min(d, 110) / 160 - (d < 30 ? 2 : 0);
        } else {
            const lane = laneRoom(player.team, player.position.x, player.position.z, m.position.x, m.position.z);
            score = facing * 1.6 + (m.userData.isKeeper ? -0.9 : passValue(player, m) * 0.5) - d / 160 - (lane < 3.5 ? 1.0 : 0);
        }
        // between two about the same, the one who is onside (where you aim still counts most)
        if (typeof REF !== 'undefined' && REF.isOffside(m)) score -= 0.5;
        if (score > bestScore) { bestScore = score; best = m; }
    });
    if (best) passBall(player, best, high);
    if (player.userData.charging) {
        player.userData.charging = false;
        player.userData.chargeStart = 0;
    }
}

// A ground pass is weighted to arrive at an easy pace (ROLL: what the grass
// leaves of its speed each tick, as in updateBall); a lofted ball goes up and
// comes down at the spot in a time set by the distance.
const ROLL = 0.985;
const PASS_ARRIVE = 0.9;           // units a tick when it gets to him (~55 a second)
const PASS_MAX = 2.4;
function groundPassSpeed(d) { return Math.min(PASS_MAX, PASS_ARRIVE + d * (1 - ROLL)); }
function groundPassTicks(d) {
    const v0 = groundPassSpeed(d), va = Math.max(0.2, v0 - d * (1 - ROLL));
    return Math.ceil(Math.log(va / v0) / Math.log(ROLL));
}
function loftTicks(d, kind) {
    if (kind === 'throw') return Math.round(Math.min(46, 16 + d * 0.45));
    if (kind === 'cross') return Math.round(Math.min(72, 32 + d * 0.3));
    return Math.round(Math.min(70, 23 + d * 0.3));
}
// Plays the ball from where it lies to (tx, tz): along the ground (high false)
// or lofted to come down there (high true, or 'cross' / 'throw' for the arc
// of a corner or a throw-in). Returns how many ticks it takes.
function playBallTo(tx, tz, high) {
    const dx = tx - ball.position.x, dz = tz - ball.position.z;
    const d = Math.hypot(dx, dz) || 1;
    if (!high) {
        ball.position.y = BALL_SIZE;
        knockBall(dx / d, dz / d, groundPassSpeed(d), 0);
        return groundPassTicks(d);
    }
    const T = loftTicks(d, high);
    const g = 0.022, y0 = ball.position.y;
    // up and down in T ticks: vy is taken off before each step (updateBall)
    const vy = (BALL_SIZE - y0 + g * T * (T + 1) / 2) / T;
    // and across the distance with the air drag on the way (0.996 a tick)
    const v = d * 0.004 / (0.996 * (1 - Math.pow(0.996, T)));
    knockBall(dx / d, dz / d, v, vy);
    return T;
}

function passBall(from, to, high) {
    MATCH.passes[from.team - 1]++;
    const fromKeeper = !!from.userData.isKeeper;
    const byHuman = from === controlledP1 || from === controlledP2;
    const startX = from.position.x, startZ = from.position.z;
    let tx = to.position.x, tz = to.position.z;
    const d0 = Math.hypot(tx - startX, tz - startZ);
    // the computer doesn't put every pass on a sixpence: a little off, less at a higher level
    if (!byHuman && !fromKeeper) {
        const err = levelFor(from).miss * 0.3 * Math.min(1, d0 / 30);
        tx += (Math.random() - 0.5) * 2 * err;
        tz += (Math.random() - 0.5) * 2 * err;
    }
    // into his stride: where he will be when it gets there (he goes to meet it
    // as well, so not all the way); but if he is running towards his marker,
    // to his feet: of the three the one with the most room on the way
    const ticks = fromKeeper ? d0 / 1.6 : high ? loftTicks(d0) : groundPassTicks(d0);
    const lead = Math.min(ticks, 50) * 0.55;
    if (high) {
        // a high ball comes down in front of him, away from his marker, so he
        // runs onto it and the man marking him is behind him
        const enemies = (from.team === 1 ? team2Players : team1Players).filter(e => !e.userData.isKeeper);
        const mk = nearestTo(enemies, tx, tz);
        if (mk.p && mk.d < 14) {
            const ax = tx - mk.p.position.x, az = tz - mk.p.position.z, al = Math.hypot(ax, az) || 1;
            tx += ax / al * 5;
            tz += az / al * 5;
        }
        tx += (from.team === 1 ? 1 : -1) * 5;
    }
    let bestRoom = -Infinity, bx = tx, bz = tz;
    [1, 0.5, 0].forEach((k) => {
        const cx = Math.max(-FIELD_W / 2 + 2, Math.min(FIELD_W / 2 - 2, tx + (to.userData.vx || 0) * lead * k));
        const cz = Math.max(-FIELD_L / 2 + 2, Math.min(FIELD_L / 2 - 2, tz + (to.userData.vz || 0) * lead * k));
        const room = high ? 8 : Math.min(8, laneRoom(from.team, startX, startZ, cx, cz)) + k * 0.6;
        if (room > bestRoom) { bestRoom = room; bx = cx; bz = cz; }
    });
    tx = bx;
    tz = bz;
    const dx = tx - startX, dz = tz - startZ;
    const d = Math.hypot(dx, dz) || 1;
    const off = fromKeeper ? PLAYER_SIZE / 2 + BALL_SIZE + 0.9 : CARRY_DIST;
    ball.position.x = startX + dx / d * off;
    ball.position.z = startZ + dz / d * off;
    ball.position.y = BALL_SIZE + 0.2;
    let T;
    if (fromKeeper) {
        const power = Math.min(2.3, 0.85 + d0 * 0.022);
        knockBall(dx / d, dz / d, power, 0.28);
        T = Math.round(d / power) + 20;
    } else {
        T = playBallTo(tx, tz, !!high);
    }
    if (fromKeeper) {
        from.userData.holdingBall = false;
        from.userData.holdStart = 0;
    } else {
        from.userData.cooldown = 14;
        from.userData.kickT = 0.28;
    }
    if (carrier === from) carrier = null;
    lastTouch = from.team;
    passTarget = { to, t: T + 45 };
    // a pass you play goes past the man pressing you (it is played round his
    // legs, not into them): for its first moments he can't block or take it
    const pressing = byHuman ? (from.team === 1 ? team2Players : team1Players)
        .filter(e => !e.userData.isKeeper && Math.hypot(e.position.x - startX, e.position.z - startZ) < 8) : [];
    lastKick = { by: from, team: from.team, kind: 'pass', to, high: !!high, byHuman, past: pressing, until: aiTick + 14 };
    curl = null;
    if (typeof REF !== 'undefined') REF.onPass(from, to, 'pass');      // who stood offside when it was played
    // a human plays on with the one he passed to (who goes to meet it: receivePass)
    const slot = slotOf(to.team);
    if (slot && !to.userData.isKeeper) setControlled(slot, to);
    // the passer goes on: into space ahead for the return (a one-two)
    if (!fromKeeper) startRun(from);
}

// ----------- AI -----------
function updateAI() {
    aiTick++;
    [...team1Players, ...team2Players].forEach(p => {
        if (p === controlledP1 || p === controlledP2) return;
        if (p.userData.isKeeper) updateKeeper(p);
        else if (slideTackle(p)) return;                 // a slide you started, finished after a switch
        else if (p.userData.isBot) updateBotFieldPlayer(p);
    });
}

// Keeper tuning, in units per tick. A keeper always stands between the ball and
// the middle of his goal and shuffles along with it. When a shot comes he
// reads where it will cross his line, reacts after a beat and dives for it:
// soft and medium shots are saved, a hard one into a corner goes in.
// How quick, far and fast he goes comes from LEVELS (game.core.js): the
// computer's keeper plays at the chosen level, every other keeper at medium.
const KEEPER_REACH = PLAYER_SIZE / 2 + BALL_SIZE + 0.2;   // hands, standing
// How long he holds it before he plays it out. While he has it the game
// waits, so it is short: a saved shot a little longer, a loose ball he picks
// up or takes off an attacker's foot is played on almost at once.
const KEEPER_HOLD_MIN = 900;      // ms, after a save
const KEEPER_HOLD_MAX = 1600;
const KEEPER_QUICK_MIN = 450;     // ms, a loose ball or a ball taken off an attacker
const KEEPER_QUICK_MAX = 850;
const KEEPER_CALL_MIN = 500;      // asked for it: never sooner than this
const KEEPER_DIVE_TICKS = 26;     // he only goes down for a ball that is this close to arriving

function keeperSkill(k) {
    const cpuSide = STATE.mode === 'cpu' && k.team !== STATE.p1.team;
    return (cpuSide ? getLevel() : LEVELS.medium).keeper;
}

function updateKeeper(k) {
    const u = k.userData;
    const skill = keeperSkill(k);
    const isTeam1 = k.team === 1;
    const goalLineX = isTeam1 ? -FIELD_W/2 : FIELD_W/2;
    const out = isTeam1 ? 1 : -1;                     // direction from the goal into the pitch
    const lineX = goalLineX + out * 3.5;

    if (u.holdingBall) {
        // with the ball in his hands he takes a few steps out of his goal
        steer(k, out * 0.07, -k.position.z * 0.004, 0.01);
    } else {
        // 1 — is a shot coming? where will it cross my line, and when?
        // A ball his own side played (a pass back) is no shot: he just collects it.
        const vx = ball.velocity.x, vz = ball.velocity.z;
        const ownBall = !!(lastKick && lastKick.team === k.team);
        const incoming = -vx * out > 0.6 && carrier === null && !ownBall;
        let shotZ = null, arrive = Infinity;
        if (incoming) {
            const t = (k.position.x - ball.position.x) / vx;
            if (t > 0 && t < 70) { shotZ = ball.position.z + vz * t; arrive = t; }
        }

        let targetX, targetZ, top;
        if (shotZ !== null && Math.abs(shotZ) < GOAL_W / 2 + 3) {
            u.react = (u.react || 0) + 1;
            // no keeper reads every shot equally well: a tick quicker or up to
            // two slower than his level, decided when he first sees it
            // a high shot is harder to read and to get across to: later, and slower
            const highShot = !!(lastKick && lastKick.kind === 'shot' && lastKick.high);
            // and a power shot is on him before he has read it
            const powerShot = !!(lastKick && lastKick.kind === 'shot' && lastKick.power);
            if (u.react === 1) u.reactAt = skill.react - 1 + Math.floor(Math.random() * 4) + (highShot ? 3 : 0) + (powerShot ? 2 : 0);
            targetX = k.position.x;
            // once he has dived he is committed: a ball that curls late beats him
            targetZ = u.diveT > 0 && u.diveAt !== undefined ? u.diveAt : shotZ;
            const moving = u.react > u.reactAt;
            // a ball still far off: he gets across into its line, no lunge yet
            top = !moving ? 0 : arrive > 40 ? skill.shuffle * 1.3 : skill.lunge * (highShot ? 0.85 : 1);
            // he goes down for anything that isn't straight at him, once he is
            // moving and the ball is nearly there; whether he gets there depends
            // on his level
            const gap = shotZ - k.position.z;
            if (moving && arrive < KEEPER_DIVE_TICKS && Math.abs(ball.position.x - k.position.x) < 24 && Math.abs(gap) > 1.4 && !(u.diveT > 0)) {
                u.diveT = 0.6;
                u.diveAt = shotZ;
                u.diveX = 0;
                u.diveZ = Math.sign(gap);
            }
        } else {
            u.react = 0;
            // 2 — narrow the angle: on the line between ball and goal centre,
            // further across and a little further out as the ball gets closer
            const dist = Math.abs(ball.position.x - goalLineX);
            const near = Math.max(0, Math.min(1, 1 - (dist - 10) / 45));
            targetZ = ball.position.z * (0.2 + 0.4 * near);
            targetX = lineX + out * 3 * near;
            top = skill.shuffle;
        }
        // positioning stays inside the posts; only a dive goes past them
        const lim = top === skill.shuffle ? GOAL_W / 2 - 1.5 : GOAL_W / 2 + 1;
        targetZ = Math.max(-lim, Math.min(lim, targetZ));

        const dx = targetX - k.position.x, dz = targetZ - k.position.z;
        const d = Math.hypot(dx, dz);
        // slow into the spot instead of overshooting it
        const want = Math.min(top, d * 0.25);
        if (d > 0.05) steer(k, dx / d * want, dz / d * want, top === skill.lunge ? 0.2 : 0.05);
        else steer(k, 0, 0, 0.05);
    }

    k.position.x += u.vx || 0;
    k.position.z += u.vz || 0;

    // he stays in his own six-yard area
    const minX = isTeam1 ? goalLineX + 1.2 : goalLineX - 9;
    const maxX = isTeam1 ? goalLineX + 9 : goalLineX - 1.2;
    k.position.x = Math.max(minX, Math.min(maxX, k.position.x));
    k.position.z = Math.max(-GOAL_W / 2 - 1, Math.min(GOAL_W / 2 + 1, k.position.z));

    // catch → hold → release (only when pressured, or after a safety timeout)
    const dx = ball.position.x - k.position.x;
    const dz = ball.position.z - k.position.z;
    const d2 = dx*dx + dz*dz;
    // a dive stretches the reach; an attacker dribbling in close is only
    // robbed when he walks right into the keeper, and one winding up a shot
    // only when the ball all but touches him (he used to take it off the foot
    // of anyone charging a shot near the goal, before the shot was hit)
    const reach = carrier
        ? KEEPER_REACH * (carrier.userData.charging ? 0.35 : 0.5)
        : KEEPER_REACH + (u.diveT > 0 && u.react > u.reactAt ? skill.dive : 0);
    const speed = Math.hypot(ball.velocity.x, ball.velocity.z);
    // a high ball (a high shot): held when it comes straight at him, tipped away
    // when he has to stretch for it; his reach up there is shorter than low down,
    // so a high shot into the top corner beats him more often than a low one
    const highBall = !carrier && ball.position.y >= GOAL_H * 0.75 && ball.position.y < GOAL_H + 0.6;
    // up there a dive gains him a bit over half as much as low down
    const highReach = KEEPER_REACH + (u.diveT > 0 && u.react > u.reactAt ? skill.dive * 0.58 : 0);
    // a ball already past him and moving away can't be gathered any more
    const goingAway = !carrier && speed > 0.4 && (ball.velocity.x * dx + ball.velocity.z * dz) > 0;
    const catchable = !goingAway && (ball.position.y < GOAL_H * 0.75
        || (highBall && d2 < KEEPER_REACH * KEEPER_REACH && speed < 1.6));

    // a shot struck from right in front of him: it is a block or it is past him,
    // he has no time to gather it. Straight at him he gets a body to it and it
    // rebounds; a yard to the side and it is by him (only a dive can reach it)
    const freshShot = !carrier && !u.holdingBall && lastKick && lastKick.kind === 'shot' && lastKick.team !== k.team
        && performance.now() - (lastKick.at || 0) < 170 && speed > 0.8;
    if (freshShot && d2 < reach * reach && ball.position.y < GOAL_H * 0.75) {
        const lat = Math.abs(-dx * ball.velocity.z / speed + dz * ball.velocity.x / speed);
        if (lat < 1.3) {
            knockBall(out * 0.5, (Math.sign(dz) || 1) * 0.85, Math.min(1.0, speed * 0.4), 0.25);
            ball.position.x = k.position.x + out * 1.8;
            u.parryT = 20;
            lastTouch = k.team;
            curl = null;
            lastKick = null;
            shotSaved(k.team);
            return;
        }
        if (!(u.diveT > 0 && u.react > u.reactAt)) return;      // past him
    }

    // a hard shot taken at full stretch is pushed away, not held
    const stretchedLow = catchable && !highBall && d2 < reach * reach && d2 > KEEPER_REACH * KEEPER_REACH && speed > 1.7;
    const stretchedHigh = highBall && !goingAway && !catchable && d2 < highReach * highReach;
    if (!carrier && !u.holdingBall && (stretchedLow || stretchedHigh)) {
        const side = Math.sign(dz) || 1;
        knockBall(out * 0.35, side * 0.9, Math.min(1.2, speed * 0.45), stretchedHigh ? 0.1 : 0.3);
        ball.position.x = k.position.x + out * 1.5;
        u.parryT = 20;
        lastTouch = k.team;
        curl = null;
        lastKick = null;
        shotSaved(k.team);
        return;
    }
    if (u.parryT > 0) { u.parryT--; return; }      // let the parried ball get away

    // begin holding the moment the ball touches the keeper
    if (catchable && d2 < reach * reach && !u.holdingBall) {
        const saved = !carrier && !!(lastKick && lastKick.kind === 'shot' && lastKick.team !== k.team);
        if (carrier) carrier.userData.cooldown = 40;
        carrier = null;
        shotSaved(k.team);
        u.holdingBall = true;
        lastTouch = k.team;
        u.holdStart = performance.now();
        // a save: a moment to gather himself; anything else he plays on quickly
        u.holdFor = saved
            ? KEEPER_HOLD_MIN + Math.random() * (KEEPER_HOLD_MAX - KEEPER_HOLD_MIN)
            : KEEPER_QUICK_MIN + Math.random() * (KEEPER_QUICK_MAX - KEEPER_QUICK_MIN);
        u.calledBy = null;
    }

    if (k.userData.holdingBall) {
        // sticky to keeper — bal is in zijn handen
        ball.position.x = k.position.x;
        ball.position.z = k.position.z;
        ball.position.y = BALL_SIZE + 1.6;
        ball.velocity.x = 0;
        ball.velocity.y = 0;
        ball.velocity.z = 0;

        const enemies = (isTeam1 ? team2Players : team1Players).filter(p => !p.userData.isKeeper);
        const heldMs = performance.now() - (k.userData.holdStart || performance.now());

        // asked for it (pass key): to you, once he has held it a moment
        if (u.calledBy && heldMs > KEEPER_CALL_MIN) {
            const to = u.calledBy;
            u.calledBy = null;
            passBall(k, to);
            return;
        }

        // nobody can take it out of his hands, so there is no hurry
        if (heldMs > (u.holdFor || KEEPER_HOLD_MIN)) {
            // to the teammate with the most room; a human gets it when he is free
            const mates = (isTeam1 ? team1Players : team2Players).filter(p => !p.userData.isKeeper);
            let best = null, bestRoom = -Infinity;
            mates.forEach(m => {
                const human = m === controlledP1 || m === controlledP2;
                const room = nearestTo(enemies, m.position.x, m.position.z).d + (human ? 6 : 0);
                if (room > bestRoom) { bestRoom = room; best = m; }
            });
            if (best) { passBall(k, best); return; }
            k.userData.holdingBall = false;
            k.userData.holdStart = 0;
        }
    }
}

// ----------- computer outfield players -----------
// Five a side, in a diamond (ROLE_KICKOFF). Every outfield player nobody is
// playing thinks for himself each tick, but as part of his side (planFor):
//   * a loose ball: the one of his side who is nearest goes for it, human or not
//   * the other side has it: the nearest presses the man on the ball; the
//     others each pick up an opponent near our goal, from his goal side, or
//     hold their place in the side's shape, which moves up and down with the ball
//   * his side has it: to his place in the attacking shape (the flanks wide,
//     the striker high and away from the ball, the defender behind it), and
//     from there into the nearest space where the line to the ball is free
//   * after a pass he runs on for the return: a one-two (startRun)
//   * with the ball: shoots in range, sooner with a way through; passes to the
//     freest teammate when that is better than running on, and almost always
//     when pressed; otherwise dribbles at goal, round the man in front of him
// How fast, sharp and clever he is comes from aiLevel() (game.core.js).

function nearestTo(list, x, z) {
    let best = null, d = Infinity;
    list.forEach(p => {
        const dd = Math.hypot(p.position.x - x, p.position.z - z);
        if (dd < d) { d = dd; best = p; }
    });
    return { p: best, d };
}

let aiTick = 0;
const teamPlan = { 1: null, 2: null };          // per side, worked out once a tick
const clampX = (x) => Math.max(-FIELD_W / 2 + 3, Math.min(FIELD_W / 2 - 3, x));
const clampZ = (z) => Math.max(-FIELD_L / 2 + 3, Math.min(FIELD_L / 2 - 3, z));

// a player's place in his side's shape, which follows the ball up and down
// the pitch. Worked out in his side's own frame: a towards the other goal, b
// across (the left flank negative), then turned the right way round.
function roleSpot(p, attacking) {
    const g = p.team === 1 ? 1 : -1;
    // in units of the 110 x 70 pitch, scaled back at the end
    const ba = ball.position.x * g / PITCH_SCALE, bz = ball.position.z * g / PITCH_SCALE;
    const anchor = Math.max(-34, Math.min(34, ba));
    const lean = bz * 0.3;
    let a, b;
    switch (p.userData.role) {
        case 'att': a = attacking ? Math.min(anchor + 22, 44) : anchor + 6; b = attacking ? -Math.sign(bz || 1) * 8 + lean * 0.5 : lean; break;
        case 'lw':  a = attacking ? anchor + 6 : anchor - 10; b = attacking ? -24 : -15 + lean; break;
        case 'rw':  a = attacking ? anchor + 6 : anchor - 10; b = attacking ? 24 : 15 + lean; break;
        default:    a = attacking ? Math.max(anchor - 22, -42) : Math.max(anchor - 20, -46); b = lean;
    }
    a = Math.max(-48, Math.min(46, a)) * PITCH_SCALE;
    b *= PITCH_SCALE;
    return { x: clampX(a * g), z: clampZ(b * g) };
}
// the best spot near `spot` to be passed to: away from opponents, the line
// from the ball clear, not too far from where he should be
function freeSpot(p, spot, owner) {
    const enemies = (p.team === 1 ? team2Players : team1Players).filter(e => !e.userData.isKeeper);
    // apart from his teammates: two of them in the same space is one option less
    const mates = (p.team === 1 ? team1Players : team2Players).filter(m => m !== p && m !== owner && !m.userData.isKeeper);
    const step = 5 * PITCH_SCALE;
    let best = spot, bestV = -Infinity;
    for (let i = -2; i <= 2; i++) {
        for (let j = -2; j <= 2; j++) {
            if (Math.abs(i) + Math.abs(j) > 3) continue;
            const x = clampX(spot.x + i * step), z = clampZ(spot.z + j * step);
            const open = Math.min(14, nearestTo(enemies, x, z).d);
            const lane = owner ? Math.min(8, laneRoom(p.team, owner.position.x, owner.position.z, x, z)) : 8;
            const room = Math.min(18, nearestTo(mates, x, z).d);
            // not so close to the man on the ball that one defender covers both
            const near = owner ? Math.hypot(x - owner.position.x, z - owner.position.z) : 40;
            const v = open * 0.1 + lane * 0.15 + room * 0.035 - Math.hypot(i, j) * 0.09 - (near < 16 ? (16 - near) * 0.07 : 0);
            if (v > bestV) { bestV = v; best = { x, z }; }
        }
    }
    return best;
}
// who of a side goes for the ball, and who picks up whom
function planFor(team) {
    const plan = teamPlan[team];
    if (plan && plan.tick === aiTick) return plan;
    const side = (team === 1 ? team1Players : team2Players).filter(m => !m.userData.isKeeper);
    const enemies = (team === 1 ? team2Players : team1Players).filter(m => !m.userData.isKeeper);
    const per = perceptionOf(team);
    const human = (m) => m === controlledP1 || m === controlledP2;
    const loose = !carrier && !team1Players[0]?.userData.holdingBall && !team2Players[0]?.userData.holdingBall;
    let presser = null, chase = null;
    // the one of the side who gets to a ball first, and where he meets it
    const first = (list) => {
        let best = null, bestIp = null;
        list.forEach((m) => {
            if (m.userData.tackleT > 0 || m.userData.getUpT > 0) return;
            const ip = interceptPoint(m, RUN_SPEED * levelFor(m).run * 1.15, per.x, per.z, per.vx, per.vz);
            if (!bestIp || ip.t < bestIp.t) { best = m; bestIp = ip; }
        });
        return { p: best, ip: bestIp };
    };
    if (loose && passTarget && passTarget.to.team === team && !passTarget.to.userData.isKeeper) {
        // our pass on its way: only the one it is meant for goes to it
        presser = passTarget.to;
    } else if (loose) {
        // a loose ball, or their pass on its way: whoever of us gets there first
        // goes for it, to where he meets it (cutting a pass out on the way)
        ({ p: presser, ip: chase } = first(side));
        if (presser && human(presser)) {
            const d = Math.hypot(chase.x - presser.position.x, chase.z - presser.position.z);
            const toward = ((presser.userData.vx || 0) * (chase.x - presser.position.x) + (presser.userData.vz || 0) * (chase.z - presser.position.z)) / (d || 1);
            if (d > 7 && toward < 0.12) {
                const alt = first(side.filter(m => !human(m)));
                if (alt.p) { presser = alt.p; chase = alt.ip; }
            }
        }
    } else {
        const tx = per.x + ball.velocity.x * 6, tz = per.z + ball.velocity.z * 6;
        presser = nearestTo(side, tx, tz).p;
        // a human who is nearest but not going for it himself: the nearest of the rest goes
        if (presser && human(presser)) {
            const d = Math.hypot(tx - presser.position.x, tz - presser.position.z);
            const toward = ((presser.userData.vx || 0) * (tx - presser.position.x) + (presser.userData.vz || 0) * (tz - presser.position.z)) / (d || 1);
            if (d > 7 && toward < 0.12) presser = nearestTo(side.filter(m => !human(m)), tx, tz).p || presser;
        }
    }
    const ownGoalX = team === 1 ? -FIELD_W / 2 : FIELD_W / 2;
    const markers = side.filter(m => m !== presser && !human(m));
    const danger = enemies.filter(e => e !== carrier && Math.abs(e.position.x - ownGoalX) < 70 * PITCH_SCALE)
        .sort((a, b) => Math.abs(a.position.x - ownGoalX) - Math.abs(b.position.x - ownGoalX));
    const marks = new Map();
    danger.forEach((e) => {
        const free = markers.filter(m => !marks.has(m));
        if (!free.length) return;
        marks.set(nearestTo(free, e.position.x, e.position.z).p, e);
    });
    teamPlan[team] = { tick: aiTick, presser, chase, marks };
    return teamPlan[team];
}
// after a pass: on into space ahead, for the return
function startRun(p) {
    if (p === controlledP1 || p === controlledP2 || p.userData.isKeeper) return;
    const g = p.team === 1 ? 1 : -1;
    const u = p.userData;
    const enemies = (p.team === 1 ? team2Players : team1Players).filter(e => !e.userData.isKeeper);
    const x = clampX(Math.min(FIELD_W / 2 - 12, Math.max(-FIELD_W / 2 + 12, p.position.x + g * 18 * PITCH_SCALE)));
    const near = nearestTo(enemies, x, p.position.z).p;
    const z = clampZ(p.position.z * 0.6 + (near ? Math.sign(p.position.z - near.position.z || 1) * 5 : 0));
    u.runTo = { x, z };
    u.runT = 75;
    u.behindRun = false;            // a run for the return stays onside
}

function updateBotFieldPlayer(p) {
    if (STATE.inputLocked) return;
    const lvl = levelFor(p);
    const u = p.userData;
    if (u.setPieceTaker) { u.vx = 0; u.vz = 0; return; }    // at the ball for a corner or a throw-in
    if (u.behindCd > 0) u.behindCd--;

    const goalSign = p.team === 1 ? 1 : -1;
    const ownGoalX = -goalSign * FIELD_W / 2;
    const enemyGoalX = -ownGoalX;
    const per = perceptionOf(p.team);
    const perX = per.x;
    const perZ = per.z;

    const side = p.team === 1 ? team1Players : team2Players;
    const mates = side.filter(m => m !== p && !m.userData.isKeeper);
    const enemies = (p.team === 1 ? team2Players : team1Players).filter(m => !m.userData.isKeeper);

    const owner = carrier;
    const haveBall = owner === p;
    const mateHasBall = owner && owner !== p && owner.team === p.team;
    const enemyHasBall = owner && owner.team !== p.team;
    const keeperHolds = team1Players[0]?.userData.holdingBall ? 1 : team2Players[0]?.userData.holdingBall ? 2 : 0;
    const myD = Math.hypot(perX - p.position.x, perZ - p.position.z);
    if (u.runT > 0) u.runT--;
    // a new place to stand only now and then, so nobody twitches between two
    const fresh = (aiTick + side.indexOf(p) * 3) % 12 === 0 || !u.spot;
    const spotFor = (attacking, ownerForLane) => {
        if (fresh || u.spotAttack !== attacking) {
            const base = roleSpot(p, attacking);
            u.spot = attacking ? freeSpot(p, base, ownerForLane) : base;
            u.spotAttack = attacking;
        }
        return u.spot;
    };

    let targetX, targetZ, chasing = false, running = false;
    let blocker = null;

    if (STATE.setPiece) {
        // a corner or a throw-in: to his place for it (setPieceSpot)
        ({ x: targetX, z: targetZ } = setPieceSpot(p, STATE.setPiece));
    } else if (keeperHolds && keeperHolds !== p.team) {
        // their keeper has it: back into shape
        ({ x: targetX, z: targetZ } = spotFor(false));
    } else if (keeperHolds) {
        // our keeper has it: get free for his throw
        ({ x: targetX, z: targetZ } = spotFor(true, side[0]));
    } else if (passTarget && passTarget.to === p) {
        // a pass is on its way to me: to where I can meet it
        const ip = interceptPoint(p, RUN_SPEED * lvl.run);
        targetX = ip.x;
        targetZ = ip.z;
        chasing = true;
    } else if (haveBall) {
        // dribble at goal; a man in front: go round him, on the side away from him
        targetX = enemyGoalX;
        targetZ = ball.position.z * 0.6;
        enemies.forEach((e) => {
            const ex = (e.position.x - p.position.x) * goalSign, ez = e.position.z - p.position.z;
            if (ex > 0 && ex < 10 && Math.abs(ez) < 6 && (!blocker || ex < (blocker.position.x - p.position.x) * goalSign)) blocker = e;
        });
        if (blocker) {
            const away = Math.sign(p.position.z - blocker.position.z) || (p.position.z > 0 ? -1 : 1);
            targetX = p.position.x + goalSign * 10;
            targetZ = clampZ(p.position.z + away * 12);
        }
    } else if (u.runT > 0 && u.runTo && !enemyHasBall) {
        // the run after my pass
        targetX = u.runTo.x;
        targetZ = u.runTo.z;
        running = true;
    } else if (mateHasBall) {
        // now and then the striker (or a winger) goes in behind their last man,
        // when the man on the ball faces forward: for a ball through or over the top
        const f = facingOf(owner);
        const deepest = Math.max(...enemies.map(e => e.position.x * goalSign));
        const myA = p.position.x * goalSign;
        const runner = u.role === 'att' || ((u.role === 'lw' || u.role === 'rw') && Math.random() < 0.004);
        if (runner && !(u.behindCd > 0) && f.x * goalSign > 0.4 && owner.position.x * goalSign > -FIELD_W * 0.3
            && deepest - myA < 30 && deepest < FIELD_W / 2 - 16 && Math.random() < 0.05) {
            u.runTo = { x: clampX(Math.min(FIELD_W / 2 - 12, deepest + 14) * goalSign), z: clampZ(p.position.z * 0.7) };
            u.runT = 80;
            u.behindRun = true;         // in behind on purpose: the pass has to come in time
            u.behindCd = 300;
            targetX = u.runTo.x;
            targetZ = u.runTo.z;
            running = true;
        } else ({ x: targetX, z: targetZ } = spotFor(true, owner));
    } else {
        const plan = planFor(p.team);
        if (plan.presser === p) {
            if (enemyHasBall) {
                const inOurDefendingThird = Math.abs(perX - ownGoalX) < FIELD_W * 0.30;
                if (myD < lvl.press) {
                    // close enough to win it: get goal-side of the ball and put a foot in
                    targetX = perX - 1.5 * goalSign;
                    targetZ = perZ;
                    chasing = true;
                    if (botWantsSlide(p, owner, lvl, ownGoalX)) { startTackle(p); return; }
                } else if (inOurDefendingThird) {
                    // between the ball and our goal, moving across with it
                    targetX = ownGoalX + (perX - ownGoalX) * 0.45;
                    targetZ = perZ * 0.6;
                } else {
                    targetX = perX - 8 * goalSign;
                    targetZ = perZ;
                }
            } else if (plan.chase) {
                // loose ball (or their pass): to where I get to it first
                targetX = plan.chase.x;
                targetZ = plan.chase.z;
                chasing = true;
            } else {
                targetX = perX + ball.velocity.x * 4;
                targetZ = perZ + ball.velocity.z * 4;
                chasing = true;
            }
        } else if (enemyHasBall && plan.marks.has(p)) {
            // pick up my man: goal-side of him, leaning towards the ball
            // (and in the way of a pass to him: part of the way to the ball, by level)
            const e = plan.marks.get(p);
            targetX = e.position.x + (ownGoalX - e.position.x) * 0.12 + (perX - e.position.x) * lvl.lane;
            targetZ = e.position.z * (1 - lvl.lane) + perZ * lvl.lane;
        } else {
            ({ x: targetX, z: targetZ } = spotFor(!enemyHasBall && possTeam === p.team, null));
        }
    }

    // with the ball on our side, stay onside: never further forward than their
    // second-last man (or the ball), unless on a run in behind (game.referee.js)
    if (typeof REF !== 'undefined' && !chasing && !haveBall && !(running && u.behindRun) && !STATE.setPiece && (mateHasBall || keeperHolds === p.team || running)) {
        const limit = Math.max(REF.lineFor(p.team) - 1.6, ball.position.x * goalSign, 0);
        if (targetX * goalSign > limit) targetX = limit * goalSign;
    }

    // nobody stands quite still: off the ball he keeps adjusting a little
    if (!chasing && !haveBall && !running) {
        u.drift = (u.drift || Math.random() * 6.28) + 0.018;
        targetX += Math.sin(u.drift) * 1.6;
        targetZ += Math.cos(u.drift * 0.77) * 1.6;
    }

    const tdx = targetX - p.position.x;
    const tdz = targetZ - p.position.z;
    const tdist = Math.sqrt(tdx*tdx + tdz*tdz);
    let top = lvl.run * (haveBall ? DRIBBLE_SPEED * 0.92 : ((enemyHasBall || chasing || running) ? RUN_SPEED * 0.96 : RUN_SPEED * 0.85));
    // sprint after the ball, on a run, or back into shape from far away, if the level allows it
    if (sprintFor(p, lvl.sprint > 0 && ((chasing && tdist > 9) || running || tdist > 22))) top *= 1 + 0.35 * lvl.sprint;
    if (tdist > 0.5) {
        const want = Math.min(top, tdist * 0.2);
        steer(p, tdx / tdist * want, tdz / tdist * want, RUN_ACCEL);
        u.aimX = tdx / tdist;
        u.aimZ = tdz / tdist;
    } else {
        steer(p, 0, 0, RUN_BRAKE);
    }
    if (u.vx || u.vz) {
        // slide-along collision (same projection trick as the human player)
        let mx = u.vx;
        let mz = u.vz;
        const all = [...team1Players, ...team2Players];
        const minDist = PLAYER_SIZE * 1.2;
        const minDist2 = minDist * minDist;
        for (let pass = 0; pass < 2; pass++) {
            for (const o of all) {
                if (o === p) continue;
                const ndx = (p.position.x + mx) - o.position.x;
                const ndz = (p.position.z + mz) - o.position.z;
                const nd2 = ndx*ndx + ndz*ndz;
                if (nd2 >= minDist2) continue;
                const nd = Math.sqrt(nd2) || 0.001;
                const nx = ndx / nd;
                const nz = ndz / nd;
                const dot = mx * nx + mz * nz;
                if (dot < 0) {
                    mx -= dot * nx;
                    mz -= dot * nz;
                }
            }
        }
        u.vx = mx;
        u.vz = mz;
        p.position.x += mx;
        p.position.z += mz;
    }

    // pitch bounds
    p.position.x = Math.max(-FIELD_W/2 + PLAYER_SIZE/2, Math.min(FIELD_W/2 - PLAYER_SIZE/2, p.position.x));
    p.position.z = Math.max(-FIELD_L/2 + PLAYER_SIZE/2, Math.min(FIELD_L/2 - PLAYER_SIZE/2, p.position.z));

    if (!haveBall) return;

    // shoot when in range; close in, always, before running into the keeper
    const shootRange = Math.abs(enemyGoalX - p.position.x);
    // a way through to goal makes him shoot sooner; a man right in front, later
    const shotLane = laneRoom(p.team, p.position.x, p.position.z, enemyGoalX, 0);
    const shootNow = Math.random() < lvl.shootChance * (shotLane > 3 ? 1.5 : 0.4);
    // a rebound is controlled first too (0.2 s): no shot straight off the first touch
    const settled = performance.now() - (u.gotAt || 0) > 200;
    // close in he always shoots, unless a man stands right in the way
    if (settled && shootRange < lvl.shootFrom && (shootNow || (shootRange < 15 && shotLane > 1.6))) {
        const keeper = (p.team === 1 ? team2Players[0] : team1Players[0]);
        // aim for the side the keeper isn't, with a human-sized miss
        const sideZ = keeper ? Math.sign(-keeper.position.z || (Math.random() - 0.5)) : 1;
        const aimZ = sideZ * GOAL_W * lvl.aim + (Math.random() - 0.5) * lvl.miss;
        const tx = enemyGoalX - ball.position.x;
        const tz = aimZ - ball.position.z;
        const len = Math.hypot(tx, tz) || 1;
        u.aimX = tx / len;
        u.aimZ = tz / len;
        const power = POWER_MIN + (POWER_MAX - POWER_MIN) * (lvl.power[0] + Math.random() * (lvl.power[1] - lvl.power[0]));
        knockBall(tx / len, tz / len, power, 0.14);
        ball.position.x = p.position.x + (tx / len) * CARRY_DIST;
        ball.position.z = p.position.z + (tz / len) * CARRY_DIST;
        ball.position.y = BALL_SIZE + 0.2;
        u.cooldown = 14;
        u.kickT = 0.28;
        carrier = null;
        passTarget = null;
        curl = null;
        lastKick = { by: p, team: p.team, kind: 'shot', at: performance.now() };
        lastTouch = p.team;
        shotTaken(p.team);                                   // the full-time statistics
        return;
    }

    // pass, after taking the ball under control first (0.4 s at least, or a
    // touch sooner when someone is on top of him), looking up a few times a
    // second: to the freest teammate when that beats running on
    const held = performance.now() - (u.gotAt || 0);
    const close = nearestTo(enemies, p.position.x, p.position.z).d;
    if (held < (close < 4 ? 250 : 400)) return;
    if ((aiTick + side.indexOf(p)) % 6) return;
    const pressure = nearestTo(enemies, p.position.x, p.position.z).d;
    let best = null, bestV = -Infinity;
    // a man in an offside position is left out, nearly always (a weaker side misses one now and then)
    // (decided once each time he gets the ball, not every look up)
    if (u.blindFor !== u.gotAt) { u.blindFor = u.gotAt; u.blind = Math.random() > (lvl === LEVELS.easy ? 0.8 : lvl === LEVELS.medium ? 0.9 : 0.97); }
    mates.forEach((m) => {
        if (typeof REF !== 'undefined' && !u.blind && REF.isOffside(m)) return;
        const v = passValue(p, m) + (m === controlledP1 || m === controlledP2 ? 0.3 : 0);
        if (v > bestV) { bestV = v; best = m; }
    });
    const keepIt = 0.9 + (pressure > 8 ? 0.6 : 0) - (pressure < 4 ? 0.9 : 0) - (blocker ? 0.5 : 0);
    if (best && bestV > keepIt && Math.random() < Math.min(1, lvl.pass * 30)) passBall(p, best);
}

// who has the ball: the carrier, else nobody
function getBallOwner() {
    return carrier;
}

// ----------- match statistics (the full-time screen) -----------
// Per side, index 0 = team 1 (red, left on the scoreboard), 1 = team 2 (blue):
//   poss      ticks the side had the ball (a loose ball stays with the side
//             that had it last; the keeper holding it counts for his side)
//   shots     every shot, low or high
//   onTarget  shots that went in or that the keeper had to stop
//   passes    every pass, the keeper's throws and kicks included
const MATCH = { poss: [0, 0], shots: [0, 0], onTarget: [0, 0], passes: [0, 0], fouls: [0, 0], offsides: [0, 0], yellows: [0, 0], reds: [0, 0] };
const MATCH_KEYS = Object.keys(MATCH);
let possTeam = 0;
let shotLive = null;            // { team }: a shot on its way, not yet decided
function resetMatchStats() {
    MATCH_KEYS.forEach(k => { MATCH[k][0] = 0; MATCH[k][1] = 0; });
    possTeam = 0;
    shotLive = null;
}
function countPossession() {
    if (STATE.scoring || STATE.inputLocked || STATE.paused) return;
    let t = carrier ? carrier.team : 0;
    if (!t && team1Players[0] && team1Players[0].userData.holdingBall) t = 1;
    if (!t && team2Players[0] && team2Players[0].userData.holdingBall) t = 2;
    if (t) possTeam = t;
    if (possTeam) MATCH.poss[possTeam - 1]++;
}
function shotTaken(team) {
    MATCH.shots[team - 1]++;
    shotLive = { team };
}
// the keeper of keeperTeam stops a shot: it was on target
function shotSaved(keeperTeam) {
    if (shotLive && shotLive.team !== keeperTeam) MATCH.onTarget[shotLive.team - 1]++;
    shotLive = null;
}
// the side's share of the ball, in whole percents that add up to 100
function possessionShare() {
    const total = MATCH.poss[0] + MATCH.poss[1];
    const red = total ? Math.round((MATCH.poss[0] / total) * 100) : 50;
    return [red, 100 - red];
}
// Shown under the final score: red on the left, blue on the right, like the
// scoreboard. "8 (5)" = eight shots, five of them on target.
function renderMatchStats() {
    const box = $('over-stats');
    if (!box) return;
    const [pr, pb] = possessionShare();
    const rows = [
        { label: 'Balbezit', red: `${pr}%`, blue: `${pb}%`, split: [pr, pb] },
        { label: 'Schoten (op doel)', red: `${MATCH.shots[0]} (${MATCH.onTarget[0]})`, blue: `${MATCH.shots[1]} (${MATCH.onTarget[1]})` },
        { label: 'Passes', red: String(MATCH.passes[0]), blue: String(MATCH.passes[1]) },
        { label: 'Overtredingen', red: String(MATCH.fouls[0]), blue: String(MATCH.fouls[1]) },
        { label: 'Buitenspel', red: String(MATCH.offsides[0]), blue: String(MATCH.offsides[1]) },
    ];
    if (MATCH.yellows[0] + MATCH.yellows[1] + MATCH.reds[0] + MATCH.reds[1] > 0) {
        rows.push({ label: 'Gele kaarten', red: String(MATCH.yellows[0]), blue: String(MATCH.yellows[1]) });
        rows.push({ label: 'Rode kaarten', red: String(MATCH.reds[0]), blue: String(MATCH.reds[1]) });
    }
    box.replaceChildren(...rows.map(r => {
        const row = document.createElement('div');
        row.className = 'match-stats__row';
        const cell = (cls, text) => { const s = document.createElement('span'); s.className = cls; s.textContent = text; return s; };
        row.append(cell('match-stats__value match-stats__value--red', r.red),
                   cell('match-stats__label', r.label),
                   cell('match-stats__value match-stats__value--blue', r.blue));
        if (r.split) {
            const bar = document.createElement('span');
            bar.className = 'match-stats__bar';
            bar.setAttribute('aria-hidden', 'true');
            const a = cell('match-stats__bar-red', ''), b = cell('match-stats__bar-blue', '');
            a.style.flexGrow = String(Math.max(1, r.split[0]));
            b.style.flexGrow = String(Math.max(1, r.split[1]));
            bar.append(a, b);
            row.appendChild(bar);
        }
        return row;
    }));
}

// A ball over the bar (or high over the line): the keeper of that goal takes
// it for a goal kick, and plays it out after his usual wait.
function goalKick(team) {
    const k = (team === 1 ? team1Players : team2Players)[0];
    shotLive = null;
    if (!k) return;
    carrier = null;
    curl = null;
    passTarget = null;
    lastKick = null;
    ballCall = null;
    const u = k.userData;
    u.holdingBall = true;
    lastTouch = team;
    u.holdStart = performance.now();
    u.holdFor = KEEPER_HOLD_MIN + Math.random() * (KEEPER_HOLD_MAX - KEEPER_HOLD_MIN);
    u.calledBy = null;
    ball.velocity = { x: 0, y: 0, z: 0 };
    ball.position.set(k.position.x, BALL_SIZE + 1.6, k.position.z);
}

// ----------- corners and throw-ins -----------
// The ball over a touchline: a throw-in for the side that didn't touch it
// last. Over the goal line off a defender: a corner (off an attacker: a goal
// kick, above). The ball rolls out, the screen dips for a moment and the
// taker stands at the ball; for a corner both sides are in the box by then.
// Whoever plays the side taking it:
//   * clicks (taps) where the ball should go: a cross that comes down there,
//     or a throw (as far as a throw goes); the teammate nearest it goes for it,
//     and Schiet while it is on its way strikes it first time (a header, a volley)
//   * or presses Pass: short, to the freest teammate
// The computer takes its own after a moment, and yours if you leave it ten
// seconds. Online the guest's click comes over the network (game.online.js).
const SP_OUT_TICKS = 42;          // the ball rolls out, then the cut
const SP_CUT_LEAD = 14;           // the dip starts this long before the players are put in place
const SP_CPU_TICKS = 80;          // the computer takes its own after about this long
const SP_AUTO_TICKS = 600;        // a human who doesn't: taken for him
const THROW_MAX = 60;             // as far as a throw goes
const clampTo = (v, lim) => Math.max(-lim, Math.min(lim, v));

function startSetPiece(kind, team, x, z) {
    let sx = Math.sign(x) || 1, sz = Math.sign(z) || 1;
    let spot;
    if (kind === 'corner') spot = { x: sx * (FIELD_W / 2 - 0.9), z: sz * (FIELD_L / 2 - 0.9) };
    else if (kind === 'throw') spot = { x: clampTo(x, FIELD_W / 2 - 3), z: sz * (FIELD_L / 2 - 0.4) };
    else {
        // a free kick where it happened, a penalty on the spot; sx is the way the side attacks
        sx = team === 1 ? 1 : -1;
        spot = kind === 'penalty' ? { x: sx * (FIELD_W / 2 - PEN_SPOT), z: 0 } : { x: clampTo(x, FIELD_W / 2 - 2), z: clampTo(z, FIELD_L / 2 - 2) };
    }
    if (typeof REF !== 'undefined') REF.onSetPiece();
    STATE.setPiece = { kind, team, spot, sx, sz, phase: 'out', t: 0, taker: null, wait: SP_CPU_TICKS + Math.floor(Math.random() * 40) };
    carrier = null;
    passTarget = null;
    curl = null;
    lastKick = null;
    ballCall = null;
    [...team1Players, ...team2Players].forEach(p => { p.userData.volley = null; p.userData.charging = false; });
}

function updateSetPiece() {
    const sp = STATE.setPiece;
    if (!sp || STATE.scoring) return;
    sp.t++;
    if (sp.phase === 'out') {
        if (sp.t === SP_OUT_TICKS - SP_CUT_LEAD) flashCut();
        if (sp.t >= SP_OUT_TICKS) placeSetPiece(sp);
        return;
    }
    const human = !!slotOf(sp.team);
    if (sp.t < (human ? SP_AUTO_TICKS : sp.wait)) return;
    // a penalty, or a free kick within range: the computer goes for goal
    if (sp.kind === 'penalty' || (!human && sp.kind === 'free' && sp.shootable && Math.random() < 0.7)) {
        shootSetPiece(Math.random() < 0.5 ? -1 : 1);
        return;
    }
    takeSetPiece(human ? null : cpuSetPieceAim(sp));
}

// put someone somewhere at once (behind the cut), standing still
function placeAt(p, x, z) {
    const u = p.userData;
    p.position.x = x;
    p.position.z = z;
    u.vx = 0; u.vz = 0;
    u.lastX = x; u.lastZ = z;
    u.runT = 0;
    u.spot = null;
}

function placeSetPiece(sp) {
    sp.phase = 'ready';
    sp.t = 0;
    const side = (sp.team === 1 ? team1Players : team2Players).filter(p => !p.userData.isKeeper);
    // a penalty is for the striker (the star), anything else for the nearest man;
    // a side whose human plays only his star: he takes their free kicks and penalties
    const slot0 = slotOf(sp.team);
    const own = slot0 && lockedSlot[slot0] ? (slot0 === 1 ? controlledP1 : controlledP2) : null;
    const star = own && side.includes(own) && (sp.kind === 'free' || sp.kind === 'penalty') ? own : null;
    const taker = star || (sp.kind === 'penalty' && side.find(p => p.userData.role === 'att')) || nearestTo(side, sp.spot.x, sp.spot.z).p;
    if (!taker) { STATE.setPiece = null; return; }
    sp.taker = taker;
    const u = taker.userData;
    u.setPieceTaker = true;
    u.tackleT = 0; u.getUpT = 0; u.charging = false; u.volley = null;
    if (sp.kind === 'corner') {
        // behind the ball at the corner flag, facing the box
        placeAt(taker, sp.sx * (FIELD_W / 2 + 0.6), sp.sz * (FIELD_L / 2 + 0.6));
        const ax = -sp.sx, az = -sp.sz * 0.7, al = Math.hypot(ax, az);
        u.aimX = ax / al; u.aimZ = az / al;
        arrangeCorner(sp);
    } else if (sp.kind === 'free' || sp.kind === 'penalty') {
        // a few steps behind the ball, facing the goal
        const gx = sp.sx * FIELD_W / 2 - sp.spot.x, gz = -sp.spot.z, gl = Math.hypot(gx, gz) || 1;
        const ax = sp.kind === 'penalty' ? sp.sx : gx / gl, az = sp.kind === 'penalty' ? 0 : gz / gl;
        placeAt(taker, sp.spot.x - ax * 2.6, sp.spot.z - az * 2.6);
        u.aimX = ax; u.aimZ = az;
        arrangeFreeKick(sp, gl);
    } else {
        // on the line, the ball over his head
        placeAt(taker, sp.spot.x, sp.sz * (FIELD_L / 2 + 0.2));
        u.aimX = 0; u.aimZ = -sp.sz;
        u.throwPose = true;
        // nobody of the other side right on top of him
        (sp.team === 1 ? team2Players : team1Players).forEach((p) => {
            if (p.userData.isKeeper) return;
            const dx = p.position.x - sp.spot.x, dz = p.position.z - sp.spot.z, d = Math.hypot(dx, dz);
            if (d < 9) placeAt(p, clampX(sp.spot.x + (dx || 1) / (d || 1) * 9), clampZ(sp.spot.z - sp.sz * 9));
        });
    }
    u.faceTo = { x: u.aimX, z: u.aimZ };
    const slot = slotOf(sp.team);
    if (slot) setControlled(slot, taker);
    setPieceBall(sp);
}

// A corner: the attackers on the near post, the penalty spot and the far post
// (and one on the edge of the box), each picked up goal side by a defender;
// the defender left over guards the near post, the keeper is on his line.
function arrangeCorner(sp) {
    const gx = sp.sx * FIELD_W / 2, ix = -sp.sx, sz = sp.sz;
    const at = (a, b) => ({ x: gx + ix * a, z: b });
    const spots = [at(PEN_SPOT - 2, -sz * 2), at(9, sz * 8), at(11, -sz * 12), at(PEN_DEPTH + 6, sz * 6)];
    const order = ['att', 'rw', 'lw', 'def'];
    const byRole = (list) => list.slice().sort((a, b) => order.indexOf(a.userData.role) - order.indexOf(b.userData.role));
    const atk = byRole((sp.team === 1 ? team1Players : team2Players).filter(p => !p.userData.isKeeper && p !== sp.taker));
    const def = byRole((sp.team === 1 ? team2Players : team1Players).filter(p => !p.userData.isKeeper));
    atk.forEach((p, i) => { const s = spots[i]; placeAt(p, s.x, s.z); p.userData.spSpot = s; });
    def.forEach((p, i) => {
        const m = atk[i];
        const s = m ? { x: m.position.x + sp.sx * 3.8, z: m.position.z + sz * 1.5 } : at(5, sz * (GOAL_W / 2 + 2));
        placeAt(p, s.x, s.z);
        p.userData.spSpot = s;
    });
    const k = (sp.team === 1 ? team2Players : team1Players)[0];
    if (k) placeAt(k, gx + ix * 2, sz * 2);
}

// A free kick: the other side 9.15 m (FREE_GAP) from the ball, and close to
// goal a wall of two or three between the ball and the goal. A penalty:
// everybody but the taker and the keeper outside the box, the keeper on his line.
const FREE_GAP = 17;
function inBoxOf(sp, x, z) {
    const gx = sp.sx * FIELD_W / 2;
    return Math.abs(x - gx) < PEN_DEPTH + 1 && Math.abs(z) < PEN_WIDTH / 2 + 1;
}
function arrangeFreeKick(sp, toGoal) {
    const opp = sp.team === 1 ? team2Players : team1Players;
    const own = sp.team === 1 ? team1Players : team2Players;
    const gx = sp.sx * FIELD_W / 2;
    sp.wall = 0;
    sp.shootable = sp.kind === 'penalty' || (toGoal < 62 && Math.abs(sp.spot.z) < 40);
    if (sp.kind === 'penalty') {
        const edge = gx - sp.sx * (PEN_DEPTH + 4);
        [...own, ...opp].filter(p => !p.userData.isKeeper && p !== sp.taker).forEach((p, i) => {
            const s = { x: edge - sp.sx * (i % 2) * 3, z: (i % 2 ? 1 : -1) * (6 + Math.floor(i / 2) * 8) };
            placeAt(p, s.x, s.z);
            p.userData.spSpot = s;
        });
        const k = opp[0];
        if (k && k.userData.isKeeper) placeAt(k, gx - sp.sx * 1.2, 0);
        return;
    }
    const dx = (gx - sp.spot.x) / toGoal, dz = -sp.spot.z / toGoal;
    const defs = opp.filter(p => !p.userData.isKeeper);
    if (toGoal < 80) {
        const n = Math.min(defs.length - 1, toGoal < 50 ? 3 : 2);
        const wall = defs.slice().sort((a, b) => Math.hypot(a.position.x - sp.spot.x, a.position.z - sp.spot.z) - Math.hypot(b.position.x - sp.spot.x, b.position.z - sp.spot.z)).slice(0, Math.max(0, n));
        const cx = sp.spot.x + dx * FREE_GAP, cz = sp.spot.z + dz * FREE_GAP;
        wall.forEach((p, i) => {
            const k = (i - (wall.length - 1) / 2) * 3.7;
            const s = { x: clampX(cx - dz * k), z: clampZ(cz + dx * k) };
            placeAt(p, s.x, s.z);
            p.userData.spSpot = s;
            p.userData.faceTo = { x: -dx, z: -dz };
        });
        sp.wall = wall.length;
    }
    // nobody of theirs closer than 9.15 m
    defs.forEach((p) => {
        if (p.userData.spSpot) return;
        const ex = p.position.x - sp.spot.x, ez = p.position.z - sp.spot.z, d = Math.hypot(ex, ez);
        if (d < FREE_GAP + 1) placeAt(p, clampX(sp.spot.x + (d ? ex / d : -dx) * (FREE_GAP + 1)), clampZ(sp.spot.z + (d ? ez / d : -dz) * (FREE_GAP + 1)));
    });
}
// a human player of the other side (or anyone but the taker, for a penalty)
// can't walk up to the ball while it is being taken
function keepAway(p, sp) {
    if (!p || !sp || sp.phase !== 'ready' || (sp.kind !== 'free' && sp.kind !== 'penalty') || p === sp.taker) return;
    if (sp.kind === 'penalty' && inBoxOf(sp, p.position.x, p.position.z)) p.position.x = sp.sx * (FIELD_W / 2 - PEN_DEPTH - 2);
    if (p.team === sp.team && sp.kind !== 'penalty') return;
    const ex = p.position.x - sp.spot.x, ez = p.position.z - sp.spot.z, d = Math.hypot(ex, ez);
    if (d < FREE_GAP && d > 0.01) {
        p.position.x = sp.spot.x + ex / d * FREE_GAP;
        p.position.z = sp.spot.z + ez / d * FREE_GAP;
    }
}
// up or down held by whoever takes it: that corner (-1 top, 1 bottom, 0 the middle)
function aimZFor(c) {
    let z = (pressed(c.move.down) ? 1 : 0) - (pressed(c.move.up) ? 1 : 0);
    const stick = c.p === controlledP1 ? (typeof touchMove !== 'undefined' ? touchMove : null) : c.p.userData.remoteStick;
    if (stick && stick.active) z = stick.z;
    return z;
}
// play stopped by the referee: the free kick or the penalty is taken from where it happened
function startFreeKick(kind, team, x, z) {
    startSetPiece(kind, team, x, z);
    if (STATE.setPiece) placeSetPiece(STATE.setPiece);
}
// a free kick or a penalty struck at goal; zAim picks the corner
function shootSetPiece(zAim) {
    const sp = STATE.setPiece;
    if (!sp || sp.phase !== 'ready' || !sp.taker || (sp.kind !== 'free' && sp.kind !== 'penalty')) return;
    const taker = sp.taker, u = taker.userData;
    endSetPiece(sp);
    ball.position.set(sp.spot.x, BALL_SIZE, sp.spot.z);
    ball.velocity = { x: 0, y: 0, z: 0 };
    u.aimX = sp.sx;
    u.aimZ = zAim > 0.3 ? 0.8 : zAim < -0.3 ? -0.8 : 0;
    // over the wall when there is one; a penalty low and firm
    const high = sp.kind === 'free' && sp.wall > 0;
    const charge = sp.kind === 'penalty' ? 0.75 : high ? 0.5 : 0.85;
    fireShot(taker, POWER_MIN + (POWER_MAX - POWER_MIN) * charge, charge, high);
}

// the ball while it is out of play: rolling to a stop out there, then at the
// corner flag or in the thrower's hands
function setPieceBall(sp) {
    if (sp.phase === 'out') {
        ball.velocity.y -= 0.022;
        ball.position.x += ball.velocity.x;
        ball.position.y += ball.velocity.y;
        ball.position.z += ball.velocity.z;
        if (ball.position.y <= BALL_SIZE) {
            ball.position.y = BALL_SIZE;
            ball.velocity.y = 0;
            ball.velocity.x *= 0.88;
            ball.velocity.z *= 0.88;
        }
        return;
    }
    ball.velocity.x = 0; ball.velocity.y = 0; ball.velocity.z = 0;
    if (sp.kind === 'throw' && sp.taker) ball.position.set(sp.taker.position.x, 9.4, sp.taker.position.z);
    else ball.position.set(sp.spot.x, BALL_SIZE, sp.spot.z);
}

// where a computer player goes while a set piece is being taken: his place in
// the box for a corner; for a throw-in his place in the shape (the thrower's
// side finding room to be thrown to), never right on top of the ball
function setPieceSpot(p, sp) {
    const u = p.userData;
    if (u.spSpot) return u.spSpot;
    if (u.spCache && u.spT-- > 0) return u.spCache;
    const own = p.team === sp.team;
    let s = roleSpot(p, own);
    if (own && sp.phase === 'ready' && sp.taker) s = freeSpot(p, s, sp.taker);
    const dx = s.x - sp.spot.x, dz = s.z - sp.spot.z, d = Math.hypot(dx, dz);
    const free = sp.kind === 'free' || sp.kind === 'penalty';
    const gap = free && !own ? FREE_GAP + 1 : 9;
    if (d < gap) s = free
        ? { x: clampX(sp.spot.x + (d ? dx / d : -sp.sx) * gap), z: clampZ(sp.spot.z + (d ? dz / d : 0) * gap) }
        : { x: clampX(sp.spot.x + (dx || 1) / (d || 1) * 9), z: clampZ(sp.spot.z - sp.sz * 9) };
    u.spCache = s;
    u.spT = 12;
    return s;
}

// the computer's corner: at one of its men in the box, not quite on his head
function cpuSetPieceAim(sp) {
    if (sp.kind !== 'corner') return null;
    const atk = (sp.team === 1 ? team1Players : team2Players).filter(p => !p.userData.isKeeper && p !== sp.taker && p.userData.spSpot);
    if (!atk.length) return null;
    const m = atk[Math.floor(Math.random() * Math.min(3, atk.length))];
    return { x: m.position.x + (Math.random() - 0.5) * 6, z: m.position.z + (Math.random() - 0.5) * 6 };
}

// Takes the set piece: to `aim` (a spot, from a click or the computer), or
// with no aim short to the freest teammate.
function takeSetPiece(aim) {
    const sp = STATE.setPiece;
    if (!sp || sp.phase !== 'ready' || !sp.taker) return;
    // a penalty: a click picks the corner
    if (sp.kind === 'penalty') { shootSetPiece(aim ? clampTo(aim.z / 6, 1) : 0); return; }
    const taker = sp.taker, team = sp.team;
    const mates = (team === 1 ? team1Players : team2Players).filter(m => !m.userData.isKeeper && m !== taker);
    let to = null, tx = 0, tz = 0;
    if (aim) {
        tx = clampTo(aim.x, FIELD_W / 2 - 2);
        tz = clampTo(aim.z, FIELD_L / 2 - 2);
        if (sp.kind === 'throw') {
            const dx = tx - sp.spot.x, dz = tz - sp.spot.z, d = Math.hypot(dx, dz);
            if (d > THROW_MAX) { tx = sp.spot.x + dx / d * THROW_MAX; tz = sp.spot.z + dz / d * THROW_MAX; }
        }
        to = nearestTo(mates, tx, tz).p;
    } else {
        let bestV = -Infinity;
        mates.forEach((m) => {
            if (sp.kind === 'free' && typeof REF !== 'undefined' && REF.isOffside(m)) return;   // not to a man offside
            const d = Math.hypot(m.position.x - sp.spot.x, m.position.z - sp.spot.z);
            const v = passValue(taker, m) - (sp.kind === 'throw' && d > THROW_MAX ? 3 : 0);
            if (v > bestV) { bestV = v; to = m; }
        });
        // everybody offside: back to the one nearest a spot behind the ball
        if (!to && sp.kind === 'free') to = nearestTo(mates, sp.spot.x - sp.sx * 12, sp.spot.z).p;
        if (to) { tx = to.position.x; tz = to.position.z; }
    }
    if (!to) return;
    endSetPiece(sp);
    // back into play from inside the line: a throw from over his head, a corner off the grass
    ball.position.set(sp.spot.x, sp.kind === 'throw' ? 8.6 : BALL_SIZE + 0.2, sp.spot.z);
    const far = Math.hypot(tx - sp.spot.x, tz - sp.spot.z) > 45;
    const how = sp.kind === 'throw' ? 'throw' : aim && (sp.kind === 'corner' || far) ? 'cross' : false;
    const T = playBallTo(tx, tz, how);
    const u = taker.userData;
    u.cooldown = 24;
    if (sp.kind === 'corner') u.kickT = 0.28;
    lastTouch = team;
    MATCH.passes[team - 1]++;
    const slot = slotOf(team);
    passTarget = { to, t: T + 45 };
    lastKick = { by: taker, team, kind: 'pass', to, high: !!how, byHuman: !!slot, setPiece: sp.kind };
    // offside counts from a free kick (not from a corner or a throw-in)
    if (sp.kind === 'free' && typeof REF !== 'undefined') REF.onPass(taker, to, 'free');
    if (slot) setControlled(slot, to);
    // the computer heads or volleys a corner now and then, more often at a higher level
    else if (sp.kind === 'corner' && aim && Math.random() < 0.3 + levelFor(to).aim) to.userData.volley = { at: performance.now() };
}

function endSetPiece(sp) {
    STATE.setPiece = null;
    [...team1Players, ...team2Players].forEach((p) => {
        const u = p.userData;
        u.setPieceTaker = false; u.faceTo = null; u.spSpot = null; u.spCache = null; u.throwPose = false;
    });
    // the taker steps back onto the pitch
    const t = sp && sp.taker;
    if (t) {
        t.position.x = clampTo(t.position.x, FIELD_W / 2 - PLAYER_SIZE / 2);
        t.position.z = clampTo(t.position.z, FIELD_L / 2 - PLAYER_SIZE / 2);
    }
}

// a click or a tap on the pitch while you take a set piece (or the guest's,
// over the network: game.online.js)
function setPieceAim(x, z) {
    const sp = STATE.setPiece;
    if (!sp || sp.phase !== 'ready') return false;
    if (typeof ONLINE !== 'undefined' && ONLINE.isGuest()) { ONLINE.sendAim(x, z); return true; }
    takeSetPiece({ x, z });
    return true;
}
// whether the one in front of this screen takes the set piece now
function aimingHere() {
    const sp = STATE.setPiece;
    if (!sp || sp.phase !== 'ready') return false;
    if (typeof ONLINE !== 'undefined' && ONLINE.isGuest()) return !!controlledP1 && sp.team === controlledP1.team;
    const slot = slotOf(sp.team);
    return STATE.mode === 'online' ? slot === 1 : !!slot;
}

// The screen dips to black for a moment while the players are put in place.
function flashCut() {
    const el = typeof document !== 'undefined' ? document.getElementById('cut') : null;
    if (!el || !el.classList) return;
    el.hidden = false;
    el.classList.remove('is-on');
    void el.offsetWidth;
    el.classList.add('is-on');
    clearTimeout(flashCut.timer);
    flashCut.timer = setTimeout(() => { el.hidden = true; el.classList.remove('is-on'); }, 620);
}

// The strip under the scoreboard (what it is, for whom, and for the taker how
// to take it), the layer that catches the click or tap, and the ring on the
// grass where the ball will go. Every frame, from animate().
let spUiKey = '';
let aimRing = null;
function groundPoint(e) {
    const r = renderer.domElement.getBoundingClientRect();
    const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
    const ny = -((e.clientY - r.top) / r.height) * 2 + 1;
    const v = new THREE.Vector3(nx, ny, 0.5).unproject(camera).sub(camera.position).normalize();
    if (v.y > -0.001) return null;
    const t = -camera.position.y / v.y;
    return { x: camera.position.x + v.x * t, z: camera.position.z + v.z * t };
}
let aimBound = false;
function bindAimLayer() {
    const layer = $('aim-layer');
    if (aimBound || !layer || !layer.addEventListener) return;
    aimBound = true;
    layer.addEventListener('pointermove', (e) => {
        const g = groundPoint(e);
        if (g && aimRing) aimRing.position.set(clampTo(g.x, FIELD_W / 2 - 2), 0.09, clampTo(g.z, FIELD_L / 2 - 2));
    });
    layer.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        const g = groundPoint(e);
        if (!g) return;
        if (aimRing) aimRing.position.set(clampTo(g.x, FIELD_W / 2 - 2), 0.09, clampTo(g.z, FIELD_L / 2 - 2));
        setPieceAim(g.x, g.z);
    });
    layer.addEventListener('contextmenu', (e) => e.preventDefault());
}
function updateSetPieceUI() {
    const box = $('setpiece');
    if (!box) return;
    const sp = STATE.setPiece;
    const aiming = aimingHere();
    if (aiming && (!aimRing || aimRing.parent !== scene)) {
        // a yellow ring with a dot, flat on the grass, drawn over the players' feet
        const mat = (c) => new THREE.MeshBasicMaterial({ color: srgb(c), transparent: true, side: THREE.DoubleSide, depthWrite: false, depthTest: false });
        aimRing = new THREE.Group();
        const edge = new THREE.Mesh(new THREE.RingGeometry(2.6, 4.6, 48), mat(0x121512));
        const ring = new THREE.Mesh(new THREE.RingGeometry(3.0, 4.2, 48), mat(0xffd60a));
        const dot = new THREE.Mesh(new THREE.CircleGeometry(0.8, 20), mat(0xffd60a));
        [edge, ring, dot].forEach((m, i) => { m.rotation.x = -Math.PI / 2; m.renderOrder = 18 + i; aimRing.add(m); });
        scene.add(aimRing);
    }
    if (aimRing) aimRing.visible = aiming;
    if (aimRing && sp && sp.kind === 'penalty') aimRing.visible = false;
    const key = sp ? `${sp.kind}|${sp.team}|${sp.phase}|${aiming}` : '';
    if (key === spUiKey) return;
    spUiKey = key;
    box.hidden = !sp;
    const layer = $('aim-layer');
    if (layer) layer.hidden = !aiming;
    $('game-screen').classList.toggle('is-aiming', aiming);
    // a free kick or a penalty can be struck at goal: Schiet stays on a phone
    $('game-screen').classList.toggle('can-shoot', aiming && !!sp && (sp.kind === 'free' || sp.kind === 'penalty'));
    if (!sp) return;
    bindAimLayer();
    const codes = typeof hudCodes === 'function' ? hudCodes() : { red: '', blue: '' };
    box.dataset.team = sp.team === 1 ? 'red' : 'blue';
    $('setpiece-kind').textContent = { corner: 'Hoekschop', throw: 'Inworp', free: 'Vrije trap', penalty: 'Strafschop' }[sp.kind] || '';
    $('setpiece-team').textContent = sp.team === 1 ? codes.red : codes.blue;
    const hint = $('setpiece-hint');
    const touch = typeof IS_TOUCH !== 'undefined' && IS_TOUCH;
    const second = STATE.mode === 'duo' && slotOf(sp.team) === 2;
    const passKey = touch ? 'Pass' : (second ? 'Shift' : 'Q');
    const shootKey = touch ? 'Schiet' : (second ? 'Enter' : 'Spatie');
    const upDown = touch ? 'stick omhoog/omlaag' : (second ? '↑/↓' : 'W/S');
    let text = `${touch ? 'Tik' : 'Klik'} waar de bal moet komen · ${passKey}: kort`;
    if (sp.kind === 'free') text += ` · ${shootKey}: op doel`;
    if (sp.kind === 'penalty') text = `${shootKey}: schieten · ${upDown}: hoek kiezen`;
    hint.textContent = aiming ? text : '';
    hint.hidden = !aiming;
    // the ring starts where a good ball would go: the penalty spot, or a teammate for a throw
    if (aiming && aimRing) {
        let ax, az;
        if (sp.kind === 'corner' || sp.kind === 'penalty') { ax = sp.sx * (FIELD_W / 2 - PEN_SPOT); az = 0; }
        else {
            const m = nearestTo((sp.team === 1 ? team1Players : team2Players).filter(q => !q.userData.isKeeper && q !== sp.taker), sp.spot.x, sp.spot.z - sp.sz * 20).p;
            ax = m ? m.position.x : sp.spot.x; az = m ? m.position.z : sp.spot.z - sp.sz * 20;
        }
        aimRing.position.set(ax, 0.09, az);
    }
}

// ----------- ball physics -----------
function updateBall() {
    // freeze the ball during goal celebrations
    if (STATE.scoring) return;
    // a corner or a throw-in: out of play (setPieceBall)
    if (STATE.setPiece) { setPieceBall(STATE.setPiece); return; }
    // any keeper holding the ball? skip all physics — bal zit in z'n handen
    if (team1Players[0] && team1Players[0].userData.holdingBall) return;
    if (team2Players[0] && team2Players[0].userData.holdingBall) return;

    // gravity (skip if sticky)
    const sticky = isSticky();
    if (!sticky) {
        ball.velocity.y -= 0.022;
        // mild air drag so a hard shot doesn't fly forever and ricochet around
        if (ball.position.y > BALL_SIZE + 0.05) {
            ball.velocity.x *= 0.996;
            ball.velocity.z *= 0.996;
        }
        ball.position.x += ball.velocity.x;
        ball.position.y += ball.velocity.y;
        ball.position.z += ball.velocity.z;
    }

    // ceiling: high enough for a high shot to clear the bar (10)
    if (ball.position.y > 16) {
        ball.position.y = 16;
        ball.velocity.y = Math.min(ball.velocity.y, 0);
    }

    // ground
    if (ball.position.y <= BALL_SIZE) {
        ball.position.y = BALL_SIZE;
        const hardLanding = ball.velocity.y < -0.08;
        // less bouncy — ball settles into a roll instead of pogo-sticking
        if (hardLanding) ball.velocity.y = Math.abs(ball.velocity.y) * 0.22;
        else ball.velocity.y = 0;
        // heavy friction on real impact (kills bouncing skips), light friction
        // on rolling so a flat shot keeps travelling toward the goal
        const fric = hardLanding ? 0.85 : 0.985;
        ball.velocity.x *= fric;
        ball.velocity.z *= fric;
        if (Math.abs(ball.velocity.x) < 0.012) ball.velocity.x = 0;
        if (Math.abs(ball.velocity.z) < 0.012) ball.velocity.z = 0;
    }

    // over a line: a goal, or out of play. Over the goal line a corner when
    // the defending side touched it last, else a goal kick; over a touchline
    // a throw-in for the side that didn't touch it last
    if (Math.abs(ball.position.x) > FIELD_W/2) {
        if (Math.abs(ball.position.z) < GOAL_W/2 && ball.position.y < GOAL_H) {
            scoreGoal(ball.position.x > 0 ? 1 : 2);
            return;
        }
        shotLive = null;                                   // wide or over: the shot missed
        const defending = ball.position.x > 0 ? 2 : 1;
        if (lastTouch === defending) startSetPiece('corner', 3 - defending, ball.position.x, ball.position.z);
        else goalKick(defending);
        return;
    }
    if (Math.abs(ball.position.z) > FIELD_L/2) {
        const touched = lastTouch || possTeam || 2;
        startSetPiece('throw', 3 - touched, ball.position.x, ball.position.z);
        return;
    }

    // player collisions — skip the ball owner; only bounce on approach.
    // Lobs above PLAYER_SIZE * 1.5 fly over a player's head (defense can be jumped).
    const owner = getBallOwner();
    const ballOverHead = ball.position.y > PLAYER_SIZE * 1.5;
    // a carried ball is handled by updateCarry (tackles included)
    const past = lastKick && lastKick.past && aiTick < lastKick.until ? lastKick.past : null;
    const assisted = !!(lastKick && lastKick.kind === 'pass' && lastKick.byHuman && Math.hypot(ball.velocity.x, ball.velocity.z) > 1.0);
    let whistled = false;
    if (!sticky) [...team1Players, ...team2Players].forEach(p => {
        if (whistled || p === owner) return;
        if (ballOverHead) return;
        if (past && past.includes(p)) return;

        const dx = ball.position.x - p.position.x;
        const dz = ball.position.z - p.position.z;
        const d2 = dx*dx + dz*dz;
        // a firm pass you play has to go right at an opponent to come off him
        const slim = assisted && p.team !== lastKick.team;
        const r = (slim ? PLAYER_SIZE * 0.35 : PLAYER_SIZE / 2) + BALL_SIZE;
        if (d2 >= r*r) return;

        const d = Math.sqrt(d2) || 0.001;
        const overlap = r - d + 0.02;
        ball.position.x += (dx / d) * overlap;
        ball.position.z += (dz / d) * overlap;
        const touchedBefore = lastTouch;
        lastTouch = p.team;                                // off him: his side touched it last
        // off his arm: handball (game.referee.js)
        if (typeof REF !== 'undefined' && REF.onBlock(p, touchedBefore)) { whistled = true; return; }

        const ballSpeed = Math.hypot(ball.velocity.x, ball.velocity.z);
        const airborne = ball.position.y > BALL_SIZE + 0.6;

        // TACKLE: if the ball is currently sticking to an enemy (low speed),
        // a collision with this defender is a clean tackle — strong push away
        const tackling = owner && owner.team !== p.team && ballSpeed < 0.35;
        if (tackling) {
            ball.velocity.x = (dx / d) * 1.1;
            ball.velocity.z = (dz / d) * 1.1;
            // airborne tackle = bring ball down; ground tackle = small bump
            ball.velocity.y = airborne ? -0.12 : 0.18;
            return;
        }

        // BLOCK: only when moving toward this player. The ball comes off him like
        // off a body: a glancing ball carries on, one that hits him square drops
        // near his feet (it used to fly back half as fast as it came, and pinball
        // around the box)
        const nx = dx / d, nz = dz / d;
        const vn = ball.velocity.x * nx + ball.velocity.z * nz;
        if (vn < 0) {
            curl = null;
            const RESTITUTION = 0.3, KEEP = 0.75;
            ball.velocity.x = (ball.velocity.x - (1 + RESTITUTION) * vn * nx) * KEEP;
            ball.velocity.z = (ball.velocity.z - (1 + RESTITUTION) * vn * nz) * KEEP;
            // only pull DOWN floaty/slow airborne balls — fast shots keep their arc
            if (airborne && ballSpeed < 1.2) {
                ball.velocity.y = Math.min(ball.velocity.y, -0.15);
            }
        }
    });

    if (whistled) return;

    // Anti-float safety: if the ball is hovering high without horizontal
    // momentum (stuck mid-air after a chain of collisions), pull it down hard.
    const horiz = Math.hypot(ball.velocity.x, ball.velocity.z);
    if (ball.position.y > BALL_SIZE + 1.5 && horiz < 0.15 && ball.velocity.y > -0.05) {
        ball.velocity.y -= 0.08;
    }

    // visual rotation
    const ballMesh = ball.userData.mesh;
    ballMesh.rotation.x += ball.velocity.z * 0.16;
    ballMesh.rotation.z -= ball.velocity.x * 0.16;
    if (curl && curl.curled) ballMesh.rotation.y += 0.45 * (curl.spin || 0);   // side spin
}

// the carried ball is placed by updateCarry, not by the physics
function isSticky() {
    return carrier !== null;
}

function scoreGoal(scoringTeam) {
    if (STATE.scoring) return;       // already counted, ignore re-entry
    STATE.scoring = true;
    STATE.inputLocked = true;

    if (scoringTeam === 1) STATE.score1++;
    else STATE.score2++;
    if (shotLive && shotLive.team === scoringTeam) MATCH.onTarget[scoringTeam - 1]++;
    shotLive = null;

    // the ball comes to rest in the net
    const net = scoringTeam === 1 ? 1 : -1;               // red scores in the right-hand goal
    ball.position.x = net * (FIELD_W / 2 + 2.5);
    ball.position.y = BALL_SIZE;
    ball.velocity.x = 0;
    ball.velocity.y = 0;
    ball.velocity.z = 0;
    carrier = null;
    curl = null;
    passTarget = null;
    lastKick = null;
    kickoffHold = null;

    showGoalFlash(scoringTeam);
    if (STATE.mode === 'online') ONLINE.hostGoal(scoringTeam);

    // golden goal in WK extra time: the first goal ends the match
    if (STATE.goldenGoal) {
        setTimeout(() => { if (STATE.screen === 'playing') endGame(); }, 1900);
        return;
    }

    // the side that conceded kicks off, after everybody has jogged back (walkBack)
    STATE.kickoffTeam = scoringTeam === 1 ? 2 : 1;
    STATE.restartTicks = RESTART_TICKS;
    // a tight offside before it: the VAR has a look (game.referee.js)
    if (typeof REF !== 'undefined') REF.onGoal(scoringTeam);
}

// The word GOAL in the scorer's colour and the new score. Online the guest
// shows it when the host says a goal went in.
function showGoalFlash(scoringTeam) {
    $('hud-s1').textContent = STATE.score1;
    $('hud-s2').textContent = STATE.score2;
    const scorer = STATE.p1.team === scoringTeam ? STATE.p1 : STATE.p2;
    $('goal-flash-sub').textContent = scorer.name;
    const codes = hudCodes();
    $('goal-flash-red').textContent = codes.red;
    $('goal-flash-blue').textContent = codes.blue;
    $('goal-flash-s1').textContent = STATE.score1;
    $('goal-flash-s2').textContent = STATE.score2;

    const flash = $('goal-flash');
    flash.dataset.team = scoringTeam === 1 ? 'red' : 'blue';   // band takes the scorer's colour
    flash.hidden = false;
    flash.style.animation = 'none';
    void flash.offsetWidth;
    flash.style.animation = '';

    setTimeout(() => { flash.hidden = true; }, 1700);
}

function updateTimer() {
    if (STATE.paused) return;
    // online guest: the host's clock, and the host decides when it is full time
    if (typeof ONLINE !== 'undefined' && ONLINE.isGuest()) {
        const shown = Math.min(STATE.onlineElapsed || 0, STATE.gameDuration);
        const clock = formatClock(shown);
        $('hud-timer').textContent = clock;
        if (typeof STADIUM_SCREEN !== 'undefined') STADIUM_SCREEN.update(clock, STATE.score1, STATE.score2);
        const left = STATE.gameDuration - shown;
        $('hud-timer').classList.toggle('warning', left <= 10 && left > 0);
        return;
    }
    if (!STATE.gameStartTime) {
        $('hud-timer').textContent = formatClock(0);
        if (typeof STADIUM_SCREEN !== 'undefined') STADIUM_SCREEN.update(formatClock(0), STATE.score1, STATE.score2);
        return;
    }
    const elapsed = Math.floor((Date.now() - STATE.gameStartTime) / 1000);
    const remaining = Math.max(0, STATE.gameDuration - elapsed);
    // the clock counts up, like on TV: 00:00 to 01:30 (02:00 after extra time)
    const clock = formatClock(Math.min(elapsed, STATE.gameDuration));
    $('hud-timer').textContent = clock;
    // the big screens in the stadium show the same (game.screen.js)
    if (typeof STADIUM_SCREEN !== 'undefined') STADIUM_SCREEN.update(clock, STATE.score1, STATE.score2);
    $('hud-timer').classList.toggle('warning', remaining <= 10 && remaining > 0);
    if (remaining === 0 && STATE.screen === 'playing') {
        endGame();
    }
}
function formatClock(s) {
    const m = Math.floor(s / 60);
    return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}
function formatTime(s) {
    if (!Number.isFinite(s)) return '∞';
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${r.toString().padStart(2,'0')}`;
}

function endGame() {
    // a WK knockout level at full time goes to extra time instead
    if (typeof wkBeforeEnd === 'function' && wkBeforeEnd()) return;
    STATE.inputLocked = true;

    // populate over screen
    const redPlayer  = STATE.p1.team === 1 ? STATE.p1 : STATE.p2;
    const bluePlayer = STATE.p1.team === 2 ? STATE.p1 : STATE.p2;
    $('over-p1-name').textContent = redPlayer.name;
    $('over-p2-name').textContent = bluePlayer.name;
    $('over-s1').textContent = STATE.score1;
    $('over-s2').textContent = STATE.score2;

    let winner;
    if (STATE.score1 > STATE.score2) winner = `${redPlayer.name} wint`;
    else if (STATE.score2 > STATE.score1) winner = `${bluePlayer.name} wint`;
    else winner = 'Gelijkspel';
    $('over-winner').textContent = winner;
    renderMatchStats();
    // a WK match: record it, and the result screen leads back to the tournament
    if (typeof wkAfterMatch === 'function') wkAfterMatch();
    if (typeof PR_STATS !== 'undefined') PR_STATS.matchEnd(true);       // statistics (game.stats.js)
    // online: the host sends the result to the guest and keeps it (game.online.js)
    if (STATE.mode === 'online') ONLINE.onEnd();

    gotoScreen('over');
}

function teardownGame() {
    // left before full time (back button, menu): counted as a match not finished
    if (typeof PR_STATS !== 'undefined') PR_STATS.matchEnd(false);
    if (typeof ONLINE !== 'undefined') ONLINE.onTeardown();
    if (typeof PENS !== 'undefined' && PENS.active()) PENS.stop();       // left during a shoot-out
    if (typeof VARGAME !== 'undefined' && VARGAME.active()) VARGAME.stop();   // left the VAR minigame
    if (animationId) cancelAnimationFrame(animationId);
    animationId = null;
    STATE.gameStartTime = null;
    STATE.inputLocked = true;
    STATE.paused = false;
    STATE.setPiece = null;
    if (typeof REF !== 'undefined') REF.teardown();
    pauseFreezeStart = 0;
    const overlay = $('pause-overlay');
    if (overlay) overlay.hidden = true;
    $('hud-s1').textContent = '0';
    $('hud-s2').textContent = '0';
    $('hud-timer').textContent = formatClock(0);
    $('hud-timer').classList.remove('warning');
}

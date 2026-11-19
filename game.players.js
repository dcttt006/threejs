// =====================================================
// PITCH ROYALE — the footballers
// Every player on the pitch, built from smooth turned shapes: boots with a
// sole, socks with the calf, knees, shorts, a shirt broader at the chest with
// a collar and trim, arms, a head with a painted face, ears and a nose, and a
// haircut. The stars (STARS, game.core.js) have their own skin, cut, beard,
// boots, name and number; everyone else an ordinary look and a number.
// The rig is the one animatePlayers() (game.js) swings: legs and arms hang
// from pivots at the hip and the shoulder, the figure faces local +z.
// =====================================================

const SKIN_TONES = [0xe2c39a, 0xc68e5e, 0x8a5a3b, 0xf0d2b0, 0xa8754e];
const HAIR_TONES = [0x1c1612, 0x4a2f1b, 0x111111, 0xb08a4a, 0x2e2018];
const HAIR_CUTS  = ['short', 'crop', 'buzz', 'fringe', 'curls'];
const ROLE_NUMBER = { keeper: 1, def: 4, lw: 11, rw: 7, att: 9 };

const hexNum = (c) => typeof c === 'number' ? c : parseInt(String(c).replace('#', ''), 16) || 0;
const hexStr = (n) => '#' + (hexNum(n) & 0xffffff).toString(16).padStart(6, '0');
// a colour mixed towards another (k 0..1), as a number
function mixHex(a, b, k) {
    a = hexNum(a); b = hexNum(b);
    const ch = (s) => Math.round(((a >> s) & 255) * (1 - k) + ((b >> s) & 255) * k) << s;
    return ch(16) | ch(8) | ch(0);
}
const lightness = (c) => { c = hexNum(c); return (((c >> 16) & 255) * 0.3 + ((c >> 8) & 255) * 0.59 + (c & 255) * 0.11) / 255; };

// The face, painted round the head: the front of the sphere is u = 0.25 of the texture
function faceTexture(skin, brow) {
    const c = document.createElement('canvas');
    c.width = 512; c.height = 256;
    const g = c.getContext('2d');
    g.scale(0.5, 0.5);
    g.fillStyle = hexStr(skin);
    g.fillRect(0, 0, 1024, 512);
    const cx = 256, ex = 48, ey = 262;
    g.fillStyle = hexStr(brow);
    [-1, 1].forEach((s) => {
        g.save(); g.translate(cx + s * ex, ey - 30); g.rotate(s * -0.12);
        g.beginPath(); g.ellipse(0, 0, 26, 8, 0, 0, Math.PI * 2); g.fill(); g.restore();
    });
    [-1, 1].forEach((s) => {
        g.fillStyle = '#f4f1ea';
        g.beginPath(); g.ellipse(cx + s * ex, ey, 19, 13, 0, 0, Math.PI * 2); g.fill();
        g.fillStyle = '#4a3220';
        g.beginPath(); g.arc(cx + s * ex + s * 2, ey + 1, 8.5, 0, Math.PI * 2); g.fill();
        g.fillStyle = '#111';
        g.beginPath(); g.arc(cx + s * ex + s * 2, ey + 1, 4.2, 0, Math.PI * 2); g.fill();
        g.fillStyle = 'rgba(255,255,255,.85)';
        g.beginPath(); g.arc(cx + s * ex + s * 2 - 3, ey - 3, 2.2, 0, Math.PI * 2); g.fill();
    });
    g.strokeStyle = hexStr(mixHex(skin, 0x000000, 0.45));
    g.lineWidth = 5; g.lineCap = 'round';
    g.beginPath(); g.moveTo(cx - 20, ey + 78); g.quadraticCurveTo(cx, ey + 86, cx + 20, ey + 78); g.stroke();
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    return tex;
}

// a name and number (on the back), or just the number (on the chest)
function shirtPrint(top, num, size, color) {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 256;
    const g = c.getContext('2d');
    g.fillStyle = color;
    g.textAlign = 'center';
    if (top) {
        let fs = 44;
        g.font = `800 ${fs}px "Barlow Condensed", "Arial Narrow", sans-serif`;
        while (g.measureText(top).width > 210 && fs > 20) { fs -= 2; g.font = `800 ${fs}px "Barlow Condensed", "Arial Narrow", sans-serif`; }
        g.fillText(top, 128, 56);
    }
    g.font = `800 ${size}px "Barlow Condensed", "Arial Narrow", sans-serif`;
    g.fillText(String(num), 128, top ? 226 : 200);
    const t = new THREE.CanvasTexture(c);
    t.encoding = THREE.sRGBEncoding;
    return t;
}

const lathe = (pts, mat, seg = 18) => new THREE.Mesh(new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), seg), mat);
const orb = (r, mat, seg = 16) => new THREE.Mesh(new THREE.SphereGeometry(r, seg, Math.round(seg * 0.7)), mat);

// a point on a sphere of radius r: th from the top, ph round (ph = pi/2 is the front)
function onSphere(r, th, ph) { return [-Math.cos(ph) * Math.sin(th) * r, Math.cos(th) * r, Math.sin(ph) * Math.sin(th) * r]; }

// The haircut, on a head of radius R (its centre is the head's origin)
function addHair(head, cut, hairHex, R) {
    const hair = litMat(hairHex);
    const TAU = Math.PI * 2;
    const cap = (r, cover, tilt, mat) => {
        const m = new THREE.Mesh(new THREE.SphereGeometry(r, 32, 18, 0, TAU, 0, Math.PI * cover), mat || hair);
        m.rotation.x = -tilt;            // tipped back: the hairline higher at the front
        head.add(m);
        return m;
    };
    const blob = (r, x, y, z, sx = 1, sy = 1, sz = 1) => {
        const m = orb(r, hair, 12);
        m.position.set(x, y, z);
        m.scale.set(sx, sy, sz);
        head.add(m);
        return m;
    };
    switch (cut) {
        case 'buzz':
            cap(R * 1.008, 0.48, 0.32, litMat(mixHex(hairHex, 0x6a4a36, 0.3)));
            break;
        case 'short': {
            cap(R * 1.06, 0.52, 0.32);
            const [x, y, z] = onSphere(R * 0.62, 0.12 * Math.PI, Math.PI / 2);
            blob(R * 0.55, x, y, z, 1.5, 0.55, 1.5);
            break;
        }
        case 'quiff':
            cap(R * 1.025, 0.5, 0.32);
            blob(R * 0.42, 0, R * 0.78, R * 0.5, 1.35, 0.55, 1.0).rotation.x = 0.55;
            break;
        case 'curls':
            cap(R * 1.04, 0.5, 0.3);
            for (let i = 0; i < 26; i++) {
                const [x, y, z] = onSphere(R * 1.05, (0.04 + (i % 3) * 0.13) * Math.PI, i * 2.4);
                blob(R * 0.24, x, y + R * 0.06, z - R * 0.06);
            }
            break;
        case 'twists':
            cap(R * 1.04, 0.5, 0.3);
            for (let i = 0; i < 34; i++) {
                const th = (0.03 + (i % 4) * 0.1) * Math.PI, ph = i * 2.4;
                // mostly up, a little outward
                const lean = Math.min(0.5, th);
                const [x, y, z] = onSphere(R * 1.08, th, ph);
                const t = new THREE.Mesh(new THREE.CylinderGeometry(R * 0.09, R * 0.12, R * 0.4, 7), hair);
                t.position.set(x, y + R * 0.1, z - R * 0.05);
                t.rotation.set(Math.sin(ph) * lean * 0.8, 0, Math.cos(ph) * lean * 0.8);
                head.add(t);
                blob(R * 0.1, x * 1.06, y + R * 0.3, z * 1.06 - R * 0.05);
            }
            break;
        case 'crop':
            cap(R * 1.035, 0.5, 0.32);
            blob(R * 0.75, 0, R * 0.72, -R * 0.02, 1.15, 0.42, 1.12);
            break;
        case 'fringe':
            cap(R * 1.07, 0.53, 0.26);
            blob(R * 0.5, R * 0.18, R * 0.7, R * 0.5, 1.3, 0.42, 0.8).rotation.z = 0.3;
            break;
    }
}

// The look of a player: a star's, or an ordinary one from `seed`
function playerLook(team, isKeeper, role, seed, star) {
    if (star && !isKeeper) return { skin: star.skin, hair: star.hair, cut: star.style, beard: star.beard, boots: star.boots, number: star.number, back: star.back, star };
    return {
        skin: SKIN_TONES[seed % SKIN_TONES.length],
        hair: HAIR_TONES[(seed * 3 + 1) % HAIR_TONES.length],
        cut: HAIR_CUTS[(seed * 2 + team) % HAIR_CUTS.length],
        beard: !isKeeper && seed % 7 === 3,
        boots: 0x141414,
        number: ROLE_NUMBER[isKeeper ? 'keeper' : role] || 9,
        back: '',
    };
}

function makeFootballer(team, isKeeper, look) {
    const kit = KIT[team];
    const shirtHex = isKeeper ? kit.keeper : kit.shirt;
    const light = lightness(shirtHex) > 0.72;
    const shirt  = litMat(shirtHex);
    const trim   = litMat(light ? 0x10214f : 0xffffff);          // collar, cuffs, hem: white, or navy on a light shirt
    const shorts = litMat(isKeeper ? 0x161616 : kit.shorts);
    const socks  = litMat(isKeeper ? shirtHex : kit.socks);
    const skin   = litMat(look.skin);
    const boot   = litMat(look.boots || 0x141414);
    const sole   = litMat(0xf2f2f2);

    const group = new THREE.Group();
    const body = new THREE.Group();
    group.add(body);
    const HIP = 2.75, SHOULDER = 5.05;

    const makeLeg = (x) => {
        const pivot = new THREE.Group();
        pivot.position.set(x, HIP, 0);
        pivot.add(lathe([[0.001, 0.05], [0.44, 0.04], [0.44, -0.3], [0.42, -0.72], [0.001, -0.72]], shorts));
        pivot.add(lathe([[0.001, -0.6], [0.36, -0.62], [0.33, -1.05], [0.26, -1.42], [0.001, -1.45]], skin));
        const knee = orb(0.25, skin, 12); knee.position.set(0, -1.42, 0.02); pivot.add(knee);
        pivot.add(lathe([[0.001, -1.48], [0.27, -1.5], [0.31, -1.82], [0.24, -2.2], [0.18, -2.5], [0.001, -2.52]], socks));
        const band = new THREE.Mesh(new THREE.CylinderGeometry(0.275, 0.275, 0.09, 16, 1, true), trim);
        band.position.y = -1.58; pivot.add(band);
        const up = orb(0.3, boot, 16); up.scale.set(0.72, 0.6, 1.55); up.position.set(0, -2.55, 0.16); pivot.add(up);
        const so = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.07, 0.98), sole); so.position.set(0, -2.71, 0.17); pivot.add(so);
        body.add(pivot);
        return pivot;
    };
    const legL = makeLeg(-0.4), legR = makeLeg(0.4);

    const seat = lathe([[0.001, HIP - 0.22], [0.74, HIP - 0.2], [0.8, HIP + 0.2], [0.78, HIP + 0.55], [0.001, HIP + 0.55]], shorts);
    seat.scale.z = 0.66; body.add(seat);
    const torso = lathe([[0.001, HIP + 0.4], [0.76, HIP + 0.42], [0.82, HIP + 1.0], [0.96, HIP + 1.75], [0.98, HIP + 2.05],
        [0.82, HIP + 2.28], [0.46, HIP + 2.42], [0.001, HIP + 2.44]], shirt, 22);
    torso.scale.z = 0.6; body.add(torso);
    const collar = new THREE.Mesh(new THREE.TorusGeometry(0.29, 0.055, 8, 20), trim);
    collar.rotation.x = Math.PI / 2; collar.scale.y = 0.7; collar.position.y = HIP + 2.4; body.add(collar);
    const hem = new THREE.Mesh(new THREE.CylinderGeometry(0.765, 0.765, 0.08, 22, 1, true), trim);
    hem.scale.z = 0.6; hem.position.y = HIP + 0.46; body.add(hem);

    const makeArm = (x) => {
        const pivot = new THREE.Group();
        pivot.position.set(x, SHOULDER - 0.08, 0);
        pivot.add(lathe([[0.001, 0.2], [0.18, 0.18], [0.29, 0.06], [0.31, -0.1], [0.31, -0.55], [0.29, -0.82], [0.001, -0.84]], shirt));
        const cuff = new THREE.Mesh(new THREE.CylinderGeometry(0.295, 0.295, 0.07, 14, 1, true), trim);
        cuff.position.y = -0.8; pivot.add(cuff);
        pivot.add(lathe([[0.001, -0.7], [0.21, -0.72], [0.2, -1.2], [0.17, -1.6], [0.14, -1.95], [0.001, -1.97]], skin));
        const hand = orb(0.17, isKeeper ? litMat(0xf4f4f4) : skin, 12);
        hand.scale.set(isKeeper ? 1.4 : 0.85, 1.15, isKeeper ? 1.2 : 0.7); hand.position.y = -2.1; pivot.add(hand);
        pivot.rotation.z = x < 0 ? -0.1 : 0.1;
        body.add(pivot);
        return pivot;
    };
    const armL = makeArm(-1.02), armR = makeArm(1.02);

    body.add(lathe([[0.001, SHOULDER + 0.05], [0.24, SHOULDER + 0.05], [0.22, SHOULDER + 0.55], [0.001, SHOULDER + 0.55]], skin, 14));
    const R = 0.58;
    const head = new THREE.Mesh(new THREE.SphereGeometry(R, 32, 22), new THREE.MeshLambertMaterial({ map: faceTexture(look.skin, look.hair) }));
    head.scale.set(0.94, 1.06, 0.98);
    head.position.y = SHOULDER + 1.0;
    body.add(head);
    [-1, 1].forEach((s) => { const e = orb(0.13, skin, 10); e.scale.set(0.45, 1, 0.75); e.position.set(s * R * 0.97, -0.02, 0); head.add(e); });
    const nose = orb(0.085, skin, 10); nose.scale.set(0.85, 1.1, 1.0); nose.position.set(0, -0.06, R * 0.98); head.add(nose);
    if (look.beard) {
        const bm = litMat(look.hair);
        head.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.02, 28, 14, Math.PI / 2 - 1.25, 2.5, Math.PI * 0.6, Math.PI * 0.3), bm));
        const tache = orb(0.07, bm, 10); tache.scale.set(2.6, 0.6, 0.8); tache.position.set(0, -0.16, R * 0.96); head.add(tache);
    }
    addHair(head, look.cut, look.hair, R);

    // name and number on the back, the number on the chest
    if (!isKeeper && look.number) {
        const ink = light ? '#10214f' : '#ffffff';
        const back = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 1.25),
            new THREE.MeshLambertMaterial({ map: shirtPrint(look.back || '', look.number, 170, ink), transparent: true, depthWrite: false }));
        back.position.set(0, HIP + 1.55, -0.565); back.rotation.set(0.05, Math.PI, 0); body.add(back);
        const front = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.42),
            new THREE.MeshLambertMaterial({ map: shirtPrint('', look.number, 200, ink), transparent: true, depthWrite: false }));
        front.position.set(0.32, HIP + 1.75, 0.575); front.rotation.x = -0.05; body.add(front);
    }

    // soft contact shadow; real shadow maps are off (see initThree)
    const shadowBlob = new THREE.Mesh(new THREE.CircleGeometry(2.0, 24),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.32, depthWrite: false }));
    shadowBlob.rotation.x = -Math.PI / 2;
    shadowBlob.position.y = 0.05;
    group.add(shadowBlob);

    // a star's name under his feet, as in FC Mobile
    if (look.star) group.add(starNameLabel(look.star.back, team));

    body.scale.setScalar(1.25);          // a little larger than life so they read from the stand
    group.userData.isKeeper = isKeeper;
    group.userData.rig = { body, legL, legR, armL, armR };
    group.userData.stride = 0;
    group.userData.star = look.star || null;
    body.rotation.y = team === 1 ? Math.PI / 2 : -Math.PI / 2;   // face the opponent's goal
    return group;
}

function starNameLabel(text, team) {
    const c = document.createElement('canvas');
    c.width = 512; c.height = 96;
    const g = c.getContext('2d');
    g.font = '800 64px "Barlow Condensed", "Arial Narrow", sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.lineJoin = 'round';
    g.lineWidth = 10;
    g.strokeStyle = 'rgba(18,21,18,.85)';
    g.strokeText(text, 256, 50);
    g.fillStyle = '#ffffff';
    g.fillText(text, 256, 50);
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, depthWrite: false, transparent: true }));
    sp.scale.set(14, 2.6, 1);
    sp.position.set(0, -0.8, 3.4);
    sp.renderOrder = 24;
    return sp;
}

// Who plays as a star this match, per side. Against the computer: your pick
// for your side and another star for the computer's (not in a World Cup
// match, where it is a country). Two on one keyboard: player 1's pick.
// Online: no stars for now (both browsers would have to agree).
function matchStars() {
    const out = { 1: null, 2: null };
    if (STATE.mode === 'online') return out;
    const mine = getSelectedStar();
    out[STATE.p1.team] = mine;
    if (STATE.mode === 'cpu' && !STATE.wkMatch) {
        const others = STARS.filter(s => s.id !== mine.id);
        out[STATE.p1.team === 1 ? 2 : 1] = others[Math.floor(Math.random() * others.length)];
    }
    return out;
}

// ----------- Speler kiezen -----------
// Laid out as Stadion kiezen: the star on the left (drag to turn him round),
// the seven on the right with his speed, shot, dribble and passing under them.
// Arrow keys move through the list, Enter picks, Esc goes back.
const STAR_PICKER = (() => {
    let idx = 1, renderer = null, scene3 = null, cam = null, controls = null, figure = null, raf = 0;
    const el = (id) => document.getElementById(id);
    const flag = (s) => `<img class="flag" src="media/flags/${s.flag}.svg" alt="">`;
    const LABELS = ['Snelheid', 'Schot', 'Dribbel', 'Passen'];
    const statsHtml = (s) => LABELS.map((l, i) => `<div class="star__stat"><span>${l}</span><span class="star__bar">${[0, 1, 2, 3, 4].map(k => `<i class="${k < s.stats[i] ? 'on' : ''}"></i>`).join('')}</span></div>`).join('')
        + `<div class="star__extra"><b>Extra</b>${s.extra}</div>`;

    function updateLaunchLabel() {
        const lbl = el('launch-star-name');
        if (lbl) lbl.textContent = getSelectedStar().name;
    }

    function ensure3D() {
        const box = el('star-viewer');
        if (renderer || !box || typeof THREE === 'undefined') return;
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.outputEncoding = THREE.sRGBEncoding;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.05;
        box.appendChild(renderer.domElement);
        scene3 = new THREE.Scene();
        scene3.add(new THREE.HemisphereLight(0xffffff, 0x4c7a4c, 0.62));
        scene3.add(new THREE.AmbientLight(0xffffff, 0.16));
        const key = new THREE.DirectionalLight(0xfff6e6, 0.55);
        key.position.set(-30, 60, 60);
        scene3.add(key);
        const disc = new THREE.Mesh(new THREE.CircleGeometry(4.2, 48), new THREE.MeshBasicMaterial({ color: srgb(0x16243a) }));
        disc.rotation.x = -Math.PI / 2;
        scene3.add(disc);
        cam = new THREE.PerspectiveCamera(26, 1, 0.5, 200);
        cam.position.set(4, 6.8, 23);
        if (THREE.OrbitControls) {
            controls = new THREE.OrbitControls(cam, renderer.domElement);
            controls.target.set(0, 4.7, 0);
            controls.enablePan = false;
            controls.enableZoom = false;
            controls.minPolarAngle = Math.PI * 0.32;
            controls.maxPolarAngle = Math.PI * 0.52;
            controls.enableDamping = true;
        } else cam.lookAt(0, 4.7, 0);
    }
    function size() {
        const box = el('star-viewer');
        if (!renderer || !box) return;
        const w = box.clientWidth || 1, h = box.clientHeight || 1;
        renderer.setSize(w, h, false);
        cam.aspect = w / h;
        // with the bars beside him (a phone on its side) he stands left of the middle
        const over = el('star-stats-over');
        const side = over && getComputedStyle(over).display !== 'none';
        if (side) cam.setViewOffset(w * 1.44, h, w * 0.44, 0, w, h); else cam.clearViewOffset();
        cam.updateProjectionMatrix();
    }
    function loop() {
        if (STATE.screen !== 'star') { raf = 0; return; }
        raf = requestAnimationFrame(loop);
        size();
        if (controls) controls.update();
        renderer.render(scene3, cam);
    }
    function show(i) {
        idx = (i + STARS.length) % STARS.length;
        const s = STARS[idx];
        el('star-name').textContent = s.name;
        el('star-land').innerHTML = `${flag(s)}${s.country}`;
        el('star-cap').textContent = `Rugnummer ${s.number}`;
        el('star-num').textContent = s.number;
        el('star-stats').innerHTML = statsHtml(s);
        el('star-stats-over').innerHTML = statsHtml(s);
        const chosen = getSelectedStar().id === s.id;
        el('star-confirm').textContent = chosen ? 'Deze speler houden' : 'Deze speler kiezen';
        [...el('star-list').children].forEach((row, k) => {
            row.classList.toggle('is-active', k === idx);
            row.classList.toggle('is-chosen', STARS[k].id === getSelectedStar().id);
            row.setAttribute('aria-pressed', k === idx ? 'true' : 'false');
        });
        if (scene3) {
            if (figure) scene3.remove(figure);
            figure = makeFootballer(STATE.p1 && STATE.p1.team === 2 ? 2 : 1, false, playerLook(1, false, 'att', 0, s));
            figure.userData.rig.body.rotation.y = 0;
            figure.children.forEach((c) => { if (c.isSprite || (c.geometry && c.geometry.type === 'CircleGeometry')) c.visible = false; });
            scene3.add(figure);
        }
    }
    function open() {
        idx = Math.max(0, STARS.findIndex(s => s.id === getSelectedStar().id));
        gotoScreen('star');
        const list = el('star-list');
        if (list && !list.children.length) {
            STARS.forEach((s, k) => {
                const row = document.createElement('button');
                row.type = 'button';
                row.className = 'stadium-row';
                row.innerHTML = `<span class="stadium-row__num">${s.number}</span><span class="stadium-row__name">${s.name}</span>`
                    + `<span class="stadium-row__tag">gekozen</span><span class="stadium-row__cap">${flag(s)}</span>`;
                row.addEventListener('click', () => show(k));
                list.appendChild(row);
            });
        }
        ensure3D();
        show(idx);
        if (renderer && !raf) loop();
    }
    function confirm() {
        setSelectedStar(STARS[idx].id);
        updateLaunchLabel();
        history.back();
    }
    document.addEventListener('DOMContentLoaded', () => {
        updateLaunchLabel();
        el('launch-star-pick')?.addEventListener('click', open);
        el('star-back')?.addEventListener('click', () => history.back());
        el('star-confirm')?.addEventListener('click', confirm);
        document.addEventListener('keydown', (e) => {
            if (STATE.screen !== 'star') return;
            const onButton = e.target instanceof Element && !!e.target.closest('button');
            if (e.code === 'ArrowUp' || e.code === 'ArrowLeft') { e.preventDefault(); show(idx - 1); }
            else if (e.code === 'ArrowDown' || e.code === 'ArrowRight') { e.preventDefault(); show(idx + 1); }
            else if (e.code === 'Escape') { e.preventDefault(); history.back(); }
            else if (e.code === 'Enter' && !onButton) { e.preventDefault(); confirm(); }
        });
    });
    return { open, updateLaunchLabel };
})();

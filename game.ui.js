// =====================================================
// PITCH ROYALE — UI systems
// Launch, setup, coin, pause, over and HUD bindings
// =====================================================

// ----------- TOUCH DEVICES -----------
// Phones and tablets get on-screen controls and play against the computer
// (there is no second keyboard). ?touch in the URL forces it on a desktop.
// Recognised by any of:
//   * a coarse main pointer (a finger). Not "hover: none" as well: some
//     Android phones, Samsung's above all (S Pen, mouse support), claim to hover
//   * a touch screen on a phone or tablet system (Android, iPhone, iPad)
//   * an iPad that asks for the desktop site (says Macintosh, has touch)
// And should all of that miss one, the first touch of a finger switches the
// controls on after all (switchToTouch, below).
const UA = navigator.userAgent || '';
const mq = (q) => !!(window.matchMedia && matchMedia(q).matches);
let IS_TOUCH = mq('(pointer: coarse)')
    || (navigator.maxTouchPoints > 0 && /Android|iPhone|iPad|iPod|Mobile|Tablet/i.test(UA))
    || (/Macintosh/.test(UA) && navigator.maxTouchPoints > 1)
    || new URLSearchParams(location.search).has('touch');
if (IS_TOUCH) touchMode();

function touchMode() {
    document.documentElement.classList.add('is-touch');
    // A double tap or pinch zooms Safari in, and in the match (which takes
    // every touch for the controls) there is no way back out. Block both.
    ['gesturestart', 'gesturechange', 'gestureend'].forEach(t =>
        document.addEventListener(t, (e) => e.preventDefault(), { passive: false }));
    document.addEventListener('dblclick', (e) => e.preventDefault(), { passive: false });
    let lastTouchEnd = 0;
    document.addEventListener('touchend', (e) => {
        const now = Date.now();
        if (now - lastTouchEnd < 320 && !e.target.closest?.('input')) e.preventDefault();
        lastTouchEnd = now;
    }, { passive: false });
}

// The safety net: a finger touches the screen on a device that wasn't
// recognised. From then on it is a touch device: controls on, no two-player
// option, and a match already running gets its buttons straight away.
function switchToTouch(e) {
    if (IS_TOUCH || e.pointerType !== 'touch') return;
    IS_TOUCH = true;
    touchMode();
    if (typeof setMode === 'function' && STATE.screen !== 'playing' && STATE.mode !== 'online') setMode('cpu');
    if (typeof bindTouch === 'function') bindTouch();
    document.removeEventListener('pointerdown', switchToTouch, true);
}
if (!IS_TOUCH) document.addEventListener('pointerdown', switchToTouch, true);

// ----------- LAUNCH -----------
function bindLaunch() {
    if (IS_TOUCH) setMode('cpu');
    $('launch-cta').addEventListener('click', () => { setMode('duo'); goToSetup(); });
    $('launch-cpu').addEventListener('click', () => { setMode('cpu'); goToSetup(); });
    $('launch-stadium-pick').addEventListener('click', openStadiumPicker);
    $('launch-settings').addEventListener('click', openSettings);
    updateLaunchSettingsLabel();
    bindSettings();
    // the Online button is wired in game.online.js
    updateLaunchLevelLabel();

    // "Terug" in the top bar of the setup and toss screens
    document.querySelectorAll('[data-back]').forEach(btn => {
        btn.addEventListener('click', () => history.back());
    });
}
// ----------- SETTINGS: the match camera -----------
// A camera per device (game.core.js: CAMERA_VIEWS): the tabs pick which one
// you are setting, this device first. Every change is kept at once.
let settingsDevice = 'laptop';
function thisDevice() { return IS_TOUCH ? 'phone' : 'laptop'; }
function updateLaunchSettingsLabel() {
    const lbl = $('launch-settings-name');
    const set = getCameraSettings()[thisDevice()];
    if (lbl) lbl.textContent = 'Camera: ' + CAMERA_VIEWS.find(c => c.id === set.view).name;
}
function openSettings() {
    settingsDevice = thisDevice();
    gotoScreen('settings');
    renderSettings();
}
addEventListener('resize', () => { if (STATE.screen === 'settings') renderSettings(); });
function bindSettings() {
    const list = $('set-views');
    if (!list) return;
    CAMERA_VIEWS.forEach((v) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'set__view';
        b.dataset.view = v.id;
        b.setAttribute('role', 'radio');
        b.innerHTML = `<span class="set__view-name">${v.name}</span><span class="set__view-meta">${v.meta}</span>`;
        b.addEventListener('click', () => { setCameraSettings(settingsDevice, { view: v.id }); renderSettings(); });
        list.appendChild(b);
    });
    document.querySelectorAll('.set-device').forEach(b => b.addEventListener('click', () => {
        settingsDevice = b.dataset.device;
        renderSettings();
    }));
    ['height', 'zoom'].forEach((k) => {
        $('set-' + k).addEventListener('input', (e) => {
            setCameraSettings(settingsDevice, { [k]: +e.target.value });
            renderSettings();
        });
    });
    $('set-reset').addEventListener('click', (e) => {
        e.currentTarget.blur();
        setCameraSettings(settingsDevice, CAMERA_DEFAULT);
        renderSettings();
    });
}
function renderSettings() {
    const set = getCameraSettings()[settingsDevice];
    document.querySelectorAll('.set-device').forEach((b) => {
        const on = b.dataset.device === settingsDevice;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on);
    });
    document.querySelectorAll('.set__view').forEach((b) => {
        const on = b.dataset.view === set.view;
        b.classList.toggle('active', on);
        b.setAttribute('aria-checked', on);
    });
    ['height', 'zoom'].forEach((k) => { $('set-' + k).value = set[k]; $('set-' + k + '-out').textContent = set[k]; });
    const mine = settingsDevice === thisDevice();
    $('set-note').textContent = settingsDevice === 'phone'
        ? (mine ? 'Geldt voor deze telefoon.' : 'Geldt als je op een telefoon speelt.') + ' De laptop heeft zijn eigen camera.'
        : (mine ? 'Geldt voor deze laptop.' : 'Geldt als je op een laptop speelt.') + ' De telefoon heeft zijn eigen camera.';
    SETTINGS_PREVIEW.show(settingsDevice);
    updateLaunchSettingsLabel();
}
// The chosen stadium as the match camera sees it: the model placed on the
// pitch and cut open exactly as in a match (game.stadium.js), our pitch and
// goals where the model has none, the camera where the setting puts it.
// The box has the device's shape: 16:9 for a laptop, a phone on its side.
const SETTINGS_PREVIEW = (() => {
    let r = null, sc = null, cam = null, rig = null, rigId = null, raf = 0, token = 0;
    function ensure() {
        if (r) return;
        r = new THREE.WebGLRenderer({ antialias: true });
        r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        r.outputEncoding = THREE.sRGBEncoding;
        r.toneMapping = THREE.ACESFilmicToneMapping;
        r.toneMappingExposure = 1.05;
        r.localClippingEnabled = true;                   // dressStadium cuts the near stand away
        r.setClearColor(0x0b1220);
        sc = new THREE.Scene();
        sc.add(new THREE.HemisphereLight(0xffffff, 0x4c7a4c, 0.52));
        sc.add(new THREE.AmbientLight(0xffffff, 0.12));
        const key = new THREE.DirectionalLight(0xfff6e6, 0.42);
        key.position.set(-40, 120, 60);
        sc.add(key);
        // our pitch and goals, under the model's own grass where it has some
        const grass = new THREE.Mesh(new THREE.PlaneGeometry(FIELD_W + 16, FIELD_L + 12), new THREE.MeshLambertMaterial({ color: new THREE.Color(0x2f7d32).convertSRGBToLinear() }));
        grass.rotation.x = -Math.PI / 2; grass.name = 'set-grass';
        sc.add(grass);
        const white = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const line = (w, l, x, z) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, l), white); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.05, z); m.name = 'set-line'; sc.add(m); };
        line(FIELD_W, 0.4, 0, -FIELD_L / 2); line(FIELD_W, 0.4, 0, FIELD_L / 2);
        line(0.4, FIELD_L, -FIELD_W / 2, 0); line(0.4, FIELD_L, FIELD_W / 2, 0); line(0.4, FIELD_L, 0, 0);
        const post = new THREE.MeshLambertMaterial({ color: 0xffffff });
        [-1, 1].forEach((sx) => {
            [-1, 1].forEach((sz) => {
                const p = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, GOAL_H, 8), post);
                p.position.set(sx * FIELD_W / 2, GOAL_H / 2, sz * GOAL_W / 2);
                sc.add(p);
            });
            const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, GOAL_W, 8), post);
            bar.rotation.x = Math.PI / 2; bar.position.set(sx * FIELD_W / 2, GOAL_H, 0);
            sc.add(bar);
        });
        cam = new THREE.PerspectiveCamera(38, 16 / 9, 1, 4000);
    }
    function loop() {
        raf = 0;
        if (!r || STATE.screen !== 'settings') return;
        r.render(sc, cam);
        raf = requestAnimationFrame(loop);
    }
    function loadStadium() {
        const stadium = getSelectedStadium();
        if (rigId === stadium.id) return;
        const mine = ++token;
        if (rig) { sc.remove(rig); rig = null; }
        rigId = stadium.id;
        const wait = $('set-preview-wait');
        const ownGrass = (show) => sc.children.forEach(c => { if (c.name === 'set-grass' || c.name === 'set-line') c.visible = show; });
        ownGrass(true);
        if (!stadium.file || !stadium.pitch || typeof THREE.GLTFLoader !== 'function') { if (wait) wait.hidden = true; return; }
        if (wait) wait.hidden = false;
        loadStadiumModel(stadium).then((gltf) => {
            if (mine !== token) return;
            const goals = gltf.scene.getObjectByName('StadiumGoals');
            if (goals) goals.parent.remove(goals);
            if (typeof STADIUM_SCREEN !== 'undefined' && STADIUM_SCREEN.attach(gltf.scene, stadium.screen, stadium.screenLogo)) STADIUM_SCREEN.update('00:00', 0, 0);
            rig = fitStadiumToPitch(gltf.scene, stadium);
            if (!stadium.pitch.own) levelStadiumPitch(rig, stadium);
            dressStadium(rig, stadium);
            sc.add(rig);
            ownGrass(!usesStadiumPitch(stadium));
            if (wait) wait.hidden = true;
        }).catch(() => { if (wait) wait.hidden = true; });
    }
    function show(device) {
        const host = $('set-preview');
        if (!host) return;
        ensure();
        if (r.domElement.parentNode !== host) host.prepend(r.domElement);
        host.dataset.device = device;
        loadStadium();
        // the shape of the screen it is for, the width the box gets
        const aspect = device === 'phone' ? 19.5 / 9 : 16 / 9;
        const w = Math.max(1, Math.floor(host.clientWidth)), h = Math.max(1, Math.round(w / aspect));
        r.setSize(w, h, false);
        // the camera as applyGameplayCamera (game.js) puts it, the ball on the centre spot
        const c = cameraFor(device), view = getSelectedStadium().view || {};
        cam.aspect = aspect;
        cam.fov = c.fov;
        cam.far = Math.max(2000, c.back * 12);
        cam.updateProjectionMatrix();
        cam.position.set(0, c.height, c.back);
        cam.lookAt(0, 0, (c.lookZ || 0) + (view.lookZ || 0) * c.shift);
        if (!raf) raf = requestAnimationFrame(loop);
    }
    return { show };
})();

function updateLaunchStadiumLabel() {
    const lbl = $('launch-stadium-name');
    if (lbl) lbl.textContent = getSelectedStadium().name;
}
function updateLaunchLevelLabel() {
    const lbl = $('launch-cpu-level');
    if (lbl) lbl.textContent = getLevel().label;
}
function goToSetup() {
    gotoScreen('setup');
}


// ----------- SETUP -----------
function bindSetup() {
    const p1Input = $('p1-name');
    const p2Input = $('p2-name');
    const submit = $('to-coin');

    // mode toggle ---------------------------------------
    document.querySelectorAll('.mode-tab').forEach(btn => {
        btn.addEventListener('click', () => setMode(btn.dataset.mode));
    });
    renderLevels();

    $('swap-teams').addEventListener('click', () => {
        const tmp = STATE.p1.team;
        STATE.p1.team = STATE.p2.team;
        STATE.p2.team = tmp;
        renderRosterColors();
    });

    // Enter in a name field continues to the toss
    [p1Input, p2Input].forEach(inp => {
        inp.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') submit.click();
        });
    });

    // no toss without a name: the button waits until every player has one
    [p1Input, p2Input].forEach(inp => inp.addEventListener('input', checkNames));

    submit.addEventListener('click', () => {
        if (missingNames().length) { checkNames(); missingNames()[0].focus(); return; }
        STATE.p1.name = p1Input.value.trim().slice(0, 14);
        if (STATE.mode === 'cpu') {
            STATE.p2.name = 'Computer';
        } else {
            STATE.p2.name = p2Input.value.trim().slice(0, 14);
        }
        // CPU never wins the toss randomly — keep it human-friendly: human always calls
        STATE.callerSide = STATE.mode === 'cpu' ? 'p1' : (Math.random() < 0.5 ? 'p1' : 'p2');
        goToCoin();
    });

    $('level-list')?.addEventListener('keydown', (e) => {
        const ids = Object.keys(LEVELS);
        const step = (e.key === 'ArrowDown' || e.key === 'ArrowRight') ? 1 : (e.key === 'ArrowUp' || e.key === 'ArrowLeft') ? -1 : 0;
        if (!step) return;
        e.preventDefault();
        const next = ids[(ids.indexOf(STATE.difficulty) + step + ids.length) % ids.length];
        setLevel(next);
        renderLevels();
        updateLaunchLevelLabel();
        $('level-list').querySelector(`[data-level="${next}"]`)?.focus();
    });

    renderRosterColors();
    applyMode();
}

// Two players or against the computer: from the start screen or the tabs.
function setMode(mode) {
    STATE.mode = mode === 'cpu' ? 'cpu' : 'duo';
    document.querySelectorAll('.mode-tab').forEach(b => {
        const on = b.dataset.mode === STATE.mode;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    applyMode();
}

// The three levels, one row each, built once from LEVELS and then re-flagged.
function renderLevels() {
    const list = $('level-list');
    if (!list) return;
    if (!list.children.length) {
        Object.entries(LEVELS).forEach(([id, lvl]) => {
            const row = document.createElement('button');
            row.type = 'button';
            row.className = 'level__btn';
            row.dataset.level = id;
            row.setAttribute('role', 'radio');
            const name = document.createElement('span');
            name.className = 'level__name';
            name.textContent = lvl.label;
            const desc = document.createElement('span');
            desc.className = 'level__desc';
            desc.textContent = lvl.desc;
            row.append(name, desc);
            row.addEventListener('click', () => {
                setLevel(id);
                renderLevels();
                updateLaunchLevelLabel();
            });
            list.appendChild(row);
        });
    }
    [...list.children].forEach(row => {
        const on = row.dataset.level === STATE.difficulty;
        row.setAttribute('aria-checked', on ? 'true' : 'false');
        row.tabIndex = on ? 0 : -1;
    });
}

function applyMode() {
    const cpu = STATE.mode === 'cpu';
    const human = $('p2-human');
    const bot = $('p2-cpu');
    const p2Input = $('p2-name');
    const p1Alt = $('p1-keys-alt');
    if (human) human.hidden = cpu;
    if (bot) bot.hidden = !cpu;
    if (p2Input) p2Input.disabled = cpu;
    if (p1Alt) p1Alt.hidden = !cpu;
    checkNames();
}

// The name fields that are still empty (player 2 only counts with two players).
function missingNames() {
    const fields = [$('p1-name')];
    if (STATE.mode !== 'cpu') fields.push($('p2-name'));
    return fields.filter(f => f && !f.value.trim());
}
function checkNames() {
    const submit = $('to-coin');
    if (!submit) return;
    const missing = missingNames();
    submit.disabled = missing.length > 0;
    submit.textContent = !missing.length ? 'Naar de toss'
        : STATE.mode !== 'cpu' && missing.length === 2 ? 'Vul jullie namen in'
        : 'Vul je naam in';
}

function renderRosterColors() {
    // P1 is always the left card, P2 the right one; only the colours swap
    [['card-p1', STATE.p1], ['card-p2', STATE.p2]].forEach(([id, player]) => {
        const card = $(id);
        if (!card) return;
        const red = player.team === 1;
        card.dataset.team = red ? 'red' : 'blue';
        const side = card.querySelector('.team-card__side');
        const color = card.querySelector('.team-card__color');
        if (side) side.textContent = red ? 'Thuis' : 'Uit';
        if (color) color.textContent = red ? 'Rood' : 'Blauw';
    });
}

// ----------- COIN -----------
// must match the coin-toss animation duration in styles.css
const COIN_FLIP_MS = 2400;

function bindCoin() {
    $('pick-heads').addEventListener('click', () => callCoin('heads'));
    $('pick-tails').addEventListener('click', () => callCoin('tails'));
    $('kickoff-btn').addEventListener('click', (e) => { e.currentTarget.blur(); startGame(); });
}

function goToCoin() {
    // reset coin UI
    const callerEl = $('coin-caller-name');
    callerEl.textContent = STATE.callerSide === 'p1' ? STATE.p1.name : STATE.p2.name;

    const coin = $('coin3d');
    coin.classList.remove('flipping','land-heads','land-tails');
    coin.style.removeProperty('--final-rot');
    $('coin-result').classList.remove('show');
    $('coin-result').querySelector('.coin-result__line').textContent = '';
    $('coin-result').querySelector('.coin-result__text').textContent = '';
    $('kickoff-btn').hidden = true;
    document.querySelectorAll('.pick-btn').forEach(b => {
        b.disabled = false;
        b.classList.remove('chosen');
    });

    gotoScreen('coin');
}

function tossCoin() {
    // Use crypto when available — every flip is a fresh, unbiased bit.
    if (window.crypto && window.crypto.getRandomValues) {
        const buf = new Uint8Array(1);
        window.crypto.getRandomValues(buf);
        return (buf[0] & 1) === 0 ? 'heads' : 'tails';
    }
    return Math.random() < 0.5 ? 'heads' : 'tails';
}

function callCoin(choice) {
    const result = tossCoin();
    const won = choice === result;

    const buttons = document.querySelectorAll('.pick-btn');
    buttons.forEach(b => b.disabled = true);
    document.getElementById(choice === 'heads' ? 'pick-heads' : 'pick-tails').classList.add('chosen');

    const coin = $('coin3d');
    coin.style.setProperty('--final-rot', result === 'heads' ? '3600deg' : '3780deg');
    coin.classList.add('flipping');

    setTimeout(() => {
        coin.classList.remove('flipping');
        coin.classList.add(result === 'heads' ? 'land-heads' : 'land-tails');

        const resultEl = $('coin-result');
        const callerName = STATE.callerSide === 'p1' ? STATE.p1.name : STATE.p2.name;
        const otherName  = STATE.callerSide === 'p1' ? STATE.p2.name : STATE.p1.name;
        const winnerName = won ? callerName : otherName;
        const choiceLabel = choice === 'heads' ? 'kop' : 'munt';
        const resultLabel = result === 'heads' ? 'kop' : 'munt';

        resultEl.querySelector('.coin-result__line').textContent =
            `Gekozen: ${choiceLabel}. Het is ${resultLabel}.`;
        resultEl.querySelector('.coin-result__text').textContent =
            `${winnerName} trapt af`;
        resultEl.classList.add('show');

        if (won) {
            STATE.kickoffTeam = STATE.callerSide === 'p1' ? STATE.p1.team : STATE.p2.team;
        } else {
            STATE.kickoffTeam = STATE.callerSide === 'p1' ? STATE.p2.team : STATE.p1.team;
        }

        $('kickoff-btn').hidden = false;
        // on a short phone on its side the button can sit just below the edge
        $('kickoff-btn').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }, COIN_FLIP_MS);
}

// ----------- GAME OVER -----------
function bindOver() {
    $('play-again').addEventListener('click', (e) => {
        e.currentTarget.blur();
        // online: ask your opponent for a rematch (game.online.js)
        if (STATE.mode === 'online') { ONLINE.wantAgain(); return; }
        teardownGame();
        STATE.score1 = 0; STATE.score2 = 0;
        STATE.callerSide = STATE.mode === 'cpu' ? 'p1' : (Math.random() < 0.5 ? 'p1' : 'p2');
        goToCoin();
    });
    $('back-home').addEventListener('click', (e) => {
        e.currentTarget.blur();
        if (STATE.mode === 'online') { ONLINE.quitToLobby(); return; }
        teardownGame();
        STATE.score1 = 0; STATE.score2 = 0;
        // collapse the history stack — going back from launch leaves the page
        gotoScreen('launch', { replace: true });
    });
}

// =====================================================
// THREE.JS GAME
// =====================================================
let scene, camera, renderer, animationId;
let team1Players = [], team2Players = [];
let ball;
let controlledP1, controlledP2;     // human-controlled veldspelers
const keys = {};

function startGame() {
    // WK kits and colours for a WK match, the normal ones otherwise (game.wk.js)
    if (typeof wkApply === 'function') wkApply();
    STATE.paused = false;
    STATE.scoring = false;          // a match that ended mid-celebration
    resetTouch();
    if (typeof resetMatchStats === 'function') resetMatchStats();
    gotoScreen('playing');

    // hud names + colors
    paintHud();

    initThree();
    runKickoffCountdown(() => {
        STATE.gameStartTime = Date.now();
        STATE.inputLocked = false;
        if (typeof PR_STATS !== 'undefined') PR_STATS.matchStart();     // statistics (game.stats.js)
        // started with the phone upright: wait until it is turned
        // (online the match can't wait: the turn-your-phone notice is enough)
        if (IS_TOUCH && isPortrait() && STATE.mode !== 'online') togglePause(true);
    });
}

// Straight to a penalty shoot-out, no match first (online, game.online.js).
// A WK one: set STATE.wkMatch and STATE.wkStarting before calling.
function startShootout(opts) {
    if (typeof wkApply === 'function') wkApply();
    STATE.paused = false;
    STATE.scoring = false;
    resetTouch();
    gotoScreen('playing');
    paintHud();
    if (STATE.wkMatch && typeof wkDecorateHud === 'function') wkDecorateHud();
    initThree();
    STATE.inputLocked = true;
    PENS.start(opts.onDone, opts);
}

// ----------- pause -----------
let pauseFreezeStart = 0;
function togglePause(force) {
    if (STATE.screen !== 'playing') return;
    // online there is no pause: the panel offers to leave instead (game.online.js)
    if (STATE.mode === 'online') { ONLINE.togglePanel(force); return; }
    const quitBtn = $('pause-quit');
    if (quitBtn) quitBtn.hidden = false;
    const next = (force === undefined) ? !STATE.paused : !!force;
    if (next === STATE.paused) return;

    STATE.paused = next;
    const overlay = $('pause-overlay');
    if (overlay) overlay.hidden = !next;

    if (next) {
        // remember when we paused so the game timer can be paused too
        pauseFreezeStart = Date.now();
        // wipe held keys so they don't auto-fire on resume
        clearAllKeys();
    } else {
        // shift the start time forward by the paused duration
        if (STATE.gameStartTime && pauseFreezeStart) {
            STATE.gameStartTime += (Date.now() - pauseFreezeStart);
        }
        pauseFreezeStart = 0;
    }
}

function bindPause() {
    const btn = $('pause-btn');
    if (btn) btn.addEventListener('click', (e) => { e.currentTarget.blur(); togglePause(); });
    const resume = $('pause-resume');
    if (resume) resume.addEventListener('click', (e) => { e.currentTarget.blur(); togglePause(false); });
    // the panel's own leave button is wired in game.online.js

    // offline: stop the match and go back (a WK match to the tournament, not counted)
    const quit = $('pause-quit');
    if (quit) quit.addEventListener('click', (e) => {
        e.currentTarget.blur();
        if (STATE.mode === 'online' || STATE.screen !== 'playing') return;
        if (STATE.wkMatch && typeof wkContinue === 'function') { wkContinue(); return; }
        teardownGame();
        STATE.score1 = 0; STATE.score2 = 0;
        gotoScreen('launch', { replace: true });
    });

    // P or ESC anywhere during play
    document.addEventListener('keydown', (e) => {
        if (e.repeat) return;
        if (STATE.screen !== 'playing') return;
        if (e.code === 'KeyP' || e.code === 'Escape') {
            e.preventDefault();
            togglePause();
        }
    });
}

// ----------- HUD -----------
// Fills one key-legend panel: player name, then [keys] + label groups.
function fillHudKeys(el, player, groups, note) {
    if (!el) return;
    el.replaceChildren();
    el.dataset.team = player.team === 1 ? 'red' : 'blue';

    const who = document.createElement('span');
    who.className = 'hud-keys__who';
    who.textContent = player.name;
    el.appendChild(who);

    groups.forEach(([keyCaps, label]) => {
        const group = document.createElement('span');
        group.className = 'hud-keys__group';
        keyCaps.forEach(cap => {
            const kbd = document.createElement('kbd');
            kbd.textContent = cap;
            group.appendChild(kbd);
        });
        const lbl = document.createElement('span');
        lbl.className = 'hud-keys__label';
        lbl.textContent = label;
        group.appendChild(lbl);
        el.appendChild(group);
    });

    if (note) {
        const n = document.createElement('span');
        n.className = 'hud-keys__label';
        n.textContent = note;
        el.appendChild(n);
    }
}

// Three letters for the scoreboard, the way TV shortens a club:
//   Diego -> DIE, Computer -> COM, Speler 1 -> SP1, Real Madrid -> RMA,
//   Jan de Vries -> JDV. Accents go (Élodie -> ELO). Two equal codes are
//   told apart by the last letter of the second.
function teamCode(name) {
    const words = String(name || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toUpperCase().split(/[^A-Z0-9]+/).filter(Boolean);
    if (!words.length) return '???';
    const [a, b, c] = words;
    let code;
    if (words.length === 1) code = a.slice(0, 3);
    else if (/^\d+$/.test(b)) code = a.slice(0, 3 - Math.min(2, b.length)) + b.slice(0, 2);
    else if (c) code = a[0] + b[0] + c[0];
    else code = a[0] + b.slice(0, 2);
    return code.padEnd(3, a.slice(code.length - 1) || 'X').slice(0, 3);
}
function hudCodes() {
    if (STATE.wkMatch) return { red: STATE.wkMatch.me, blue: STATE.wkMatch.opp };
    const redPlayer  = STATE.p1.team === 1 ? STATE.p1 : STATE.p2;
    const bluePlayer = STATE.p1.team === 2 ? STATE.p1 : STATE.p2;
    const red = teamCode(redPlayer.name);
    let blue = teamCode(bluePlayer.name);
    if (blue === red) {
        const letters = String(bluePlayer.name).normalize('NFD').toUpperCase().replace(/[^A-Z0-9]/g, '');
        const alt = [...letters.slice(3), ...'XYZ2'].find(ch => ch !== red[2]);
        blue = blue.slice(0, 2) + alt;
    }
    return { red, blue };
}

function paintHud() {
    // a WK match gets the World Cup scoreboard, every other match the European one
    document.querySelector('.scorebug')?.classList.toggle('scorebug--wk', !!STATE.wkMatch);
    $('goal-flash')?.classList.toggle('goal-flash--wk', !!STATE.wkMatch);
    // Scoreboard halves are fixed: red on the left, blue on the right.
    const redPlayer  = STATE.p1.team === 1 ? STATE.p1 : STATE.p2;
    const bluePlayer = STATE.p1.team === 2 ? STATE.p1 : STATE.p2;
    const codes = hudCodes();
    $('hud-p1-name').textContent = codes.red;
    $('hud-p2-name').textContent = codes.blue;
    $('hud-p1-name').title = redPlayer.name;
    $('hud-p2-name').title = bluePlayer.name;

    // Key legends follow the keyboard instead: P1 (WASD) left, P2 (arrows) right.
    const cpu = STATE.mode === 'cpu' || STATE.mode === 'online';     // one person on this keyboard
    fillHudKeys($('hud-keys-p1'), STATE.p1, [
        [['W', 'A', 'S', 'D'], cpu ? 'of pijltjes' : 'bewegen'],
        [['Spatie'], 'schieten / tackle'],
        [['W', 'Spatie'], 'samen: hoog schot'],
        [['Spatie'], 'lang: powershot'],
        [['Q'], STATE.mode === 'online' ? 'passen / wisselen' : 'passen / bal vragen'],
        [['W', 'Q'], 'samen: hoge pass'],
        [['Shift'], 'sprinten'],
    ]);
    fillHudKeys($('hud-keys-p2'), STATE.p2, cpu ? [] : [
        [['↑', '←', '↓', '→'], 'bewegen'],
        [['Enter'], 'schieten / tackle'],
        [['↑', 'Enter'], 'samen: hoog schot'],
        [['Enter'], 'lang: powershot'],
        [['Shift'], 'passen / wisselen'],
        [['↑', 'Shift'], 'samen: hoge pass'],
        [['Alt'], 'sprinten'],
    ], STATE.mode === 'online' ? 'online' : cpu ? `niveau ${getLevel().label.toLowerCase()}` : '');
}

// ----------- kickoff countdown -----------
function runKickoffCountdown(done) {
    const overlay = $('kickoff-overlay');
    const num = $('kickoff-num');
    const seq = ['3','2','1','Hup!'];
    let i = 0;
    overlay.hidden = false;
    num.textContent = seq[0];
    // re-trigger animation each step
    const tick = () => {
        num.textContent = seq[i];
        num.classList.toggle('is-word', !/^\d+$/.test(seq[i]));
        num.style.animation = 'none';
        // force reflow
        void num.offsetWidth;
        num.style.animation = 'kickoff-num 1s ease-out';
        i++;
        if (i < seq.length) {
            setTimeout(tick, 850);
        } else {
            setTimeout(() => {
                overlay.hidden = true;
                done && done();
            }, 600);
        }
    };
    tick();
}


// ----------- TOUCH CONTROLS -----------
// Left half of the pitch: a stick that appears under your thumb. Right: Schiet
// (hold to charge, release to shoot, exactly like the space bar) and Pass (the
// Q key: back to your keeper, or ask him for the ball). The stick is analogue;
// movePlayer() reads touchMove for player 1.
const touchMove = { active: false, x: 0, z: 0 };
let touchShotHigh = false;      // the last Schiet was let go with a swipe up
let touchPassHigh = false;      // the last Pass was let go with a swipe up: a high pass
const SWIPE_HIGH_PX = 28;       // how far up the thumb must slide
const STICK_TRAVEL = 52;        // px the knob can move from the centre, on the full-size stick
const STICK_DEAD = 0.18;        // ignore tiny movements of the thumb

function isPortrait() {
    return window.matchMedia ? matchMedia('(orientation: portrait)').matches : window.innerHeight > window.innerWidth;
}

function resetTouch() {
    touchMove.active = false;
    touchMove.x = touchMove.z = 0;
    const stick = $('touch-stick'), knob = $('touch-knob');
    if (stick) { stick.style.left = ''; stick.style.top = ''; stick.classList.remove('is-held'); }
    if (knob) knob.style.transform = '';
    ['touch-shoot', 'touch-pass', 'touch-sprint'].forEach(id => $(id)?.classList.remove('is-down', 'is-high', 'is-power'));
    $('touch-shoot')?.style.removeProperty('--charge');
    touchShotHigh = false;
    touchPassHigh = false;
}

let touchBound = false;
function bindTouch() {
    if (!IS_TOUCH || touchBound) return;     // once only (switchToTouch can call it late)
    touchBound = true;
    const zone = $('touch-zone'), stick = $('touch-stick'), knob = $('touch-knob');
    const shoot = $('touch-shoot'), pass = $('touch-pass');
    if (!zone || !stick || !knob || !shoot || !pass) return;

    // ---- the stick ----
    let stickId = null, cx = 0, cy = 0, travel = STICK_TRAVEL;
    const moveStick = (e) => {
        let dx = e.clientX - cx, dy = e.clientY - cy;
        const d = Math.hypot(dx, dy);
        if (d > travel) { dx = dx / d * travel; dy = dy / d * travel; }
        knob.style.transform = `translate(${dx}px, ${dy}px)`;
        // screen right is +x, screen down is +z (towards the camera)
        touchMove.x = dx / travel;
        touchMove.z = dy / travel;
        touchMove.active = Math.hypot(touchMove.x, touchMove.z) > STICK_DEAD;
    };
    zone.addEventListener('pointerdown', (e) => {
        if (stickId !== null) return;
        e.preventDefault();
        stickId = e.pointerId;
        try { zone.setPointerCapture(stickId); } catch (_) {}   // keeps the thumb's moves when it leaves the zone
        const r = zone.getBoundingClientRect();
        // the stick is smaller on a small phone (styles.css): so is the knob's travel
        travel = Math.max(34, (stick.offsetWidth || 132) * STICK_TRAVEL / 132);
        cx = e.clientX; cy = e.clientY;
        stick.style.left = `${cx - r.left}px`;
        stick.style.top = `${cy - r.top}px`;
        stick.classList.add('is-held');
        moveStick(e);
    });
    zone.addEventListener('pointermove', (e) => { if (e.pointerId === stickId) moveStick(e); });
    const releaseStick = (e) => {
        if (e.pointerId !== stickId) return;
        stickId = null;
        touchMove.active = false;
        touchMove.x = touchMove.z = 0;
        knob.style.transform = '';
        stick.style.left = '';
        stick.style.top = '';
        stick.classList.remove('is-held');
    };
    zone.addEventListener('pointerup', releaseStick);
    zone.addEventListener('pointercancel', releaseStick);

    // ---- the buttons: each acts as its key while a finger is on it ----
    const hold = (btn, code, onDown, onUp) => {
        let id = null;
        btn.addEventListener('pointerdown', (e) => {
            if (id !== null) return;
            e.preventDefault();
            id = e.pointerId;
            try { btn.setPointerCapture(id); } catch (_) {}
            btn.classList.add('is-down');
            keys[code] = true;
            keysPressed[code] = true;
            onDown?.(e);
        });
        const up = (e) => {
            if (e.pointerId !== id) return;
            id = null;
            btn.classList.remove('is-down');
            onUp?.(e);                     // before the key goes up: a swipe is read first
            keys[code] = false;
        };
        btn.addEventListener('pointerup', up);
        btn.addEventListener('pointercancel', up);
        btn.addEventListener('contextmenu', (e) => e.preventDefault());
    };

    // Schiet fills a ring while it charges, so you can see how hard it will be;
    // held on, it turns red: a power shot. Swipe up over it as you let go and
    // the shot goes high (touchShotHigh, read by handleShoot); the button turns
    // "Hoog" once the swipe is far enough.
    let raf = 0, start = 0, startY = 0;
    const paint = () => {
        const ms = performance.now() - start;
        shoot.style.setProperty('--charge', Math.min(1, ms / CHARGE_MAX_MS).toFixed(3));
        shoot.classList.toggle('is-power', ms >= POWER_SHOT_MS && !shoot.classList.contains('is-tackle') && !shoot.classList.contains('is-high'));
        raf = ms < POWER_SHOT_MS ? requestAnimationFrame(paint) : 0;
    };
    const swipedUp = (e, y0) => y0 - e.clientY > SWIPE_HIGH_PX;
    hold(shoot, 'Space',
        (e) => { start = performance.now(); startY = e.clientY; cancelAnimationFrame(raf); paint(); },
        (e) => {
            touchShotHigh = swipedUp(e, startY);
            shoot.classList.remove('is-high', 'is-power');
            cancelAnimationFrame(raf); raf = 0; shoot.style.removeProperty('--charge');
        });
    shoot.addEventListener('pointermove', (e) => {
        if (shoot.classList.contains('is-down')) shoot.classList.toggle('is-high', swipedUp(e, startY));
    });
    // Pass plays when you let go, so a swipe up over it can make it a high
    // pass (touchPassHigh, read by handlePass); it says "Hoog" once far enough
    let passY = 0, passId = null;
    pass.addEventListener('pointerdown', (e) => {
        if (passId !== null) return;
        e.preventDefault();
        passId = e.pointerId;
        passY = e.clientY;
        try { pass.setPointerCapture(passId); } catch (_) {}
        pass.classList.add('is-down');
    });
    pass.addEventListener('pointermove', (e) => {
        if (e.pointerId === passId) pass.classList.toggle('is-high', pass.classList.contains('is-ball') && swipedUp(e, passY));
    });
    const passUp = (e) => {
        if (e.pointerId !== passId) return;
        passId = null;
        pass.classList.remove('is-down', 'is-high');
        if (e.type === 'pointercancel') return;
        touchPassHigh = swipedUp(e, passY);
        keysPressed.KeyQ = true;          // one press, as the Q key
    };
    pass.addEventListener('pointerup', passUp);
    pass.addEventListener('pointercancel', passUp);
    pass.addEventListener('contextmenu', (e) => e.preventDefault());
    const sprint = $('touch-sprint');
    if (sprint) hold(sprint, 'ShiftLeft');

    // turning the phone upright mid-match pauses it
    if (window.matchMedia) {
        matchMedia('(orientation: portrait)').addEventListener?.('change', (e) => {
            if (e.matches && STATE.screen === 'playing' && !STATE.inputLocked && STATE.mode !== 'online') {
                resetTouch();
                togglePause(true);
            }
        });
    }
}

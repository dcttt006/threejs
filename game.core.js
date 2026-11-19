// =====================================================
// PITCH ROYALE
// Core state/config/navigation bootstrap
// =====================================================

// Cache-bust marker: bump GAME_BUILD on every change so we can verify
// the live site is actually serving the latest game.js. If this string
// doesn't show up in DevTools console after a refresh, the browser /
// GitHub Pages CDN is still serving an older cached copy.
const GAME_BUILD = 'v90-online (2026-11-18)';
console.log(`%c[GAME] build: ${GAME_BUILD}`,
    'background:#16a34a;color:#000;font-weight:bold;padding:3px 8px;border-radius:3px');

// ----------- state -----------
const STATE = {
    screen: 'loading',         // loading | launch | setup | coin | playing | over
    mode: 'duo',               // duo (Hot-Seat) | cpu | online (game.online.js)
    onlineRole: null,          // online: 'host' (red, runs the match) or 'guest' (blue, draws it)
    onlineStadium: null,       // online: the host's stadium id
    onlineElapsed: 0,          // online guest: the host's match clock, in seconds
    p1: { name: 'Speler 1', team: 1 },   // team: 1 = red, 2 = blue
    p2: { name: 'Speler 2', team: 2 },
    callerSide: 'p1',          // who calls heads/tails
    kickoffTeam: 1,
    score1: 0,
    score2: 0,
    gameDuration: 90,          // seconds
    gameStartTime: null,
    inputLocked: true,         // unlocked after kickoff countdown
    scoring: false,            // true during the goal-celebration freeze
    paused: false,             // true while the pause overlay is up
    difficulty: 'medium',      // easy | medium | hard, against the computer
};

// ----------- difficulty against the computer -----------
// Everything the computer does better or worse, in one place. Only the
// computer's side uses it: its field player and its keeper. Your own keeper,
// and both keepers in a two-player match, always play at 'medium'.
//   run         its speed, relative to the medium bot
//   press       how close the ball must be before it goes in for a tackle
//   steal       chance per tick (60 a second) of winning the ball in a duel
//   read        how quickly it follows the ball (0.1 ≈ a 150 ms lag)
//   shootFrom   distance to goal from which it shoots
//   shootChance chance per tick of shooting once in range
//   aim / miss  how far towards a post it aims, and its spread (units)
//   power       its shot strength, as a part of the charge range [min, max]
//   pass        chance per tick of passing to a teammate who is free and further forward
//   sprint      0 = never sprints, 1 = sprints whenever chasing (35% faster, costs stamina)
//   lane        how far a defender stands in the way of a pass to his man (part of the way to the ball)
//   keeper      react: ticks before moving on a shot; lunge: dive speed;
//               dive: extra reach at full stretch; shuffle: positioning speed
// The opponents' outfield players play at the chosen level; your own computer
// teammates play smart (MATE_LEVEL, below).
const LEVEL_STORAGE_KEY = 'pitchRoyale.level';
const LEVELS = {
    easy: {
        label: 'Makkelijk',
        desc: 'Speelt rustig, wint de bal zelden terug en de keeper laat er wat door.',
        run: 0.82, press: 10, steal: 0.012, read: 0.06, pass: 0.006, sprint: 0, lane: 0.06,
        shootFrom: 24, shootChance: 0.014, aim: 0.12, miss: 12, power: [0.05, 0.4],
        keeper: { react: 10, lunge: 0.62, dive: 1.5, shuffle: 0.28 },
    },
    medium: {
        label: 'Gemiddeld',
        desc: 'Een eerlijke wedstrijd: zet druk en schiet als hij de kans krijgt.',
        run: 1, press: 16, steal: 0.025, read: 0.10, pass: 0.014, sprint: 0.6, lane: 0.12,
        shootFrom: 30, shootChance: 0.025, aim: 0.24, miss: 9, power: [0.15, 0.65],
        keeper: { react: 5, lunge: 0.75, dive: 2.1, shuffle: 0.34 },
    },
    hard: {
        label: 'Moeilijk',
        desc: 'Snel, jaagt op de bal, schiet in de hoeken en de keeper houdt veel.',
        run: 1.07, press: 24, steal: 0.045, read: 0.17, pass: 0.024, sprint: 1, lane: 0.18,
        shootFrom: 34, shootChance: 0.04, aim: 0.36, miss: 5, power: [0.4, 0.95],
        keeper: { react: 4, lunge: 0.85, dive: 2.6, shuffle: 0.38 },
    },
};
try {
    const saved = localStorage.getItem(LEVEL_STORAGE_KEY);
    if (LEVELS[saved]) STATE.difficulty = saved;
} catch (_) {}
function getLevel() { return LEVELS[STATE.difficulty] || LEVELS.medium; }
// the level the computer's outfield players play at: the chosen one against
// the computer, medium for the computer teammates in a two-player match
function aiLevel() { return STATE.mode === 'cpu' ? getLevel() : LEVELS.medium; }
// Against the computer you play one player and the computer plays the rest
// of your side: those teammates always play smart, whatever the level of the
// opponents. They read the game quickly, run, press and win the ball like the
// hard level (they hardly ever have the ball long: you take it over).
const MATE_LEVEL = Object.assign({}, LEVELS.hard, { label: 'Teamgenoot', read: 0.25, lane: 0.25 });
function levelFor(p) {
    return STATE.mode === 'cpu' && p && p.team === STATE.p1.team ? MATE_LEVEL : aiLevel();
}
function setLevel(id) {
    if (!LEVELS[id]) return;
    STATE.difficulty = id;
    try { localStorage.setItem(LEVEL_STORAGE_KEY, id); } catch (_) {}
}

// ----------- in-game color palette (Stadium Nightfall) -----------
const COLORS = {
    pitch:        0x0e6a3a,
    pitchDark:    0x094f29,
    line:         0xe7e2d2,
    ground:       0x080a14,
    team1:        0xe0203a,    // crimson
    team1Hot:     0xff5b6e,
    team2:        0x1f5dff,    // cobalt
    team2Hot:     0x6da4ff,
    skin:         0xe2c39a,
    keeperBand:   0xf0c14a,
    skyTop:       0x000000,
    skyMid:       0x040406,
    skyBottom:    0x000000,
    fogColor:     0x000000,
};

// ----------- field constants -----------
// The pitch is PITCH_SCALE times the 110 x 70 the game was first tuned on, so
// a player is small next to it, as on a real pitch: it feels big, as in FC
// Mobile, and the camera shows a part of it and goes with the play. The shape
// of the sides, runs and markings are written for 110 x 70 and scaled by it.
const PITCH_SCALE = 1.8;
const FIELD_W = 110 * PITCH_SCALE;
const FIELD_L = 70 * PITCH_SCALE;
const GOAL_W = 22;
const GOAL_H = 10;
const PLAYER_SIZE = 3.4;
const BALL_SIZE = 1.05;

// ----------- stadium catalog -----------
// `pitch` says where the lines of the model's pitch are; see fitStadiumToPitch().
const STADIUMS = [
    {
        id: 'camp-nou',
        name: 'Camp Nou',
        club: 'FC Barcelona',
        city: 'Barcelona',
        file: 'media/models/stadiums/camp_nou_stadium.glb',
        capacity: '99.354',
        pitch: { x: -6.7, z: 0.24, w: 113.75, l: 78, angle: 1.202, y: 0.11 },
    },
    {
        id: 'old-trafford',
        name: 'Old Trafford',
        club: 'Manchester United',
        city: 'Manchester',
        file: 'media/models/stadiums/old_trafford.glb',
        capacity: '74.310',
        pitch: { x: -6.9, z: 13.98, w: 74.45, l: 47.84, angle: 0, y: 8.42 },
    },
    {
        id: 'etihad',
        name: 'Etihad Stadium',
        club: 'Manchester City',
        city: 'Manchester',
        file: 'media/models/stadiums/ETIHAD STADIUM.glb',
        capacity: '53.400',
        pitch: { x: -0.66, z: 0.69, w: 85.5, l: 55.46, angle: 1.397, y: 17.03 },
    },
    {
        id: 'anfield',
        name: 'Anfield',
        club: 'Liverpool FC',
        city: 'Liverpool',
        file: 'media/models/stadiums/anfield_stadium.glb',
        capacity: '61.276',
        // scan of the whole neighbourhood; the stadium is a small part of it
        pitch: { x: 14.53, z: 21.07, w: 65.3, l: 43.9, angle: -0.78, y: 18.39 },
    },
    {
        id: 'emirates',
        name: 'Emirates Stadium',
        club: 'Arsenal',
        city: 'Londen',
        file: 'media/models/stadiums/emirates-stadium (1)/source/untitled.glb',
        capacity: '60.704',
        pitch: { x: 1.17, z: 0.74, w: 107.4, l: 69.8, angle: -1.542, y: 9.08 },
        look: { photo: true, gain: 1.3, sat: 1.0, contrast: 1.04, grassLift: 1, grassLevel: 0.07, grassSat: 1.12 },
    },
    {
        id: 'wanda-metropolitano',
        name: 'Wanda Metropolitano',
        club: 'Atlético Madrid',
        city: 'Madrid',
        file: 'media/models/stadiums/wanda_metropolitano_stadium.glb',
        capacity: '70.460',
        pitch: { x: -4.1, z: -5.5, w: 37, l: 24, angle: 0.305, y: 4.83, own: true },
    },
    {
        id: 'la-bombonera',
        name: 'La Bombonera',
        club: 'Boca Juniors',
        city: 'Buenos Aires',
        file: 'media/models/stadiums/la_bombonera_boca_juniors.glb',
        capacity: '54.000',
        pitch: { x: 29.63, z: -3.8, w: 110.9, l: 67.45, angle: 1.571, y: 9.14 },
    },
    {
        id: 'otkritie-arena',
        name: 'Otkritie Arena',
        club: 'Spartak Moskou',
        city: 'Moskou',
        file: 'media/models/stadiums/otkritie_arena.glb',
        capacity: '45.360',
        // night-time scan: its grass is near black and full of holes
        pitch: { x: 5.2, z: -3.3, w: 54.7, l: 36.4, angle: 1.571, y: 9.76, own: true },
    },
    {
        id: 'home-park',
        name: 'Home Park',
        club: 'Plymouth Argyle',
        city: 'Plymouth',
        file: 'media/models/stadiums/plymouth_argyle_-_home_park.glb',
        capacity: '17.900',
        pitch: { x: -9.33, z: -5.63, w: 82.8, l: 52.95, angle: 1.587, y: 10.99 },
    },
    {
        id: 'cheltenham',
        name: 'Cheltenham Pitch',
        club: 'Cheltenham Town',
        city: 'Cheltenham',
        file: 'media/models/stadiums/cheltenham_football_pitch.glb',
        capacity: '7.066',
        pitch: { x: -8.59, z: 4.97, w: 128.2, l: 81.6, angle: 0.912, y: 4.63 },
    },
    {
        id: 'olympiastadion',
        name: 'Olympiastadion',
        club: 'Hertha BSC',
        city: 'Berlijn',
        file: 'media/models/stadiums/berlin_olympiastadion.glb',
        capacity: '74.475',
        // the pitch lies below street level, inside the athletics track
        pitch: { x: -7.55, z: -2.92, w: 52.7, l: 34.8, angle: -3.121, y: 0.58 },
        // the roof's shadow lies across half the grass in the photos: lifted to the sunlit part
        look: { photo: true, gain: 1.05, sat: 1.0, contrast: 1.04, grassLift: 1, grassLevel: 0.21, grassSat: 1.1, shadowGreen: 1 },
    },
    {
        id: 'jeju',
        name: 'Jeju World Cup Stadium',
        club: 'Jeju SK FC',
        city: 'Seogwipo',
        file: 'media/models/stadiums/jeju_world_cup_stadium.glb',
        capacity: '29.791',
        pitch: { x: -39.64, z: 26.27, w: 54.24, l: 35.08, angle: 2.811, y: 8.09, sink: 8 },
        look: { photo: true, gain: 1.3, sat: 1.0, contrast: 1.04, grassLift: 1, grassLevel: 0.07, grassSat: 1.12 },
    },
    {
        id: 'jordan-hare',
        name: 'Jordan-Hare Stadium',
        club: 'Auburn Tigers',
        city: 'Auburn',
        file: 'media/models/stadiums/jordan_hare_stadium.glb',
        capacity: '88.043',
        // an American football field: no football lines, so our pitch covers it
        pitch: { x: -2.64, z: -2.96, w: 35, l: 21.8, angle: -0.987, y: 7.5, own: true },
        look: { photo: true, gain: 1.5, sat: 1.0, contrast: 1.04 },
    },
    {
        id: 'lotto-park',
        name: 'Lotto Park',
        club: 'RSC Anderlecht',
        city: 'Brussel',
        // ?v=: raise it with every new export, or browsers keep showing the old model
        file: 'media/models/stadiums/lotto_park.glb?v=12',
        capacity: '22.500',
        // our own Blender model; turned so the stand with the three stars is the far one
        pitch: { x: 0, z: 0, w: 98.23, l: 62.51, angle: Math.PI, y: 0.17 },
        // its floodlit night is baked into the model: drawn unlit, at twice the stored light
        look: { photo: true, baked: true, gain: 2, sat: 1, contrast: 1 },
        // the camera aims a little further out, so the big screen in the far corner stays in frame
        view: { lookZ: -8 },
    },
    {
        id: 'metlife',
        name: 'MetLife Stadium',
        club: 'New York New Jersey',
        city: 'East Rutherford',
        // built from nothing by tools/metlife_build.py; ?v=: raise it with every new export
        file: 'media/models/stadiums/metlife.glb?v=5',
        screen: 'wk',                  // World Cup screens: team colours, flags, the clock on navy
        capacity: '82.500',
        pitch: { x: 0, z: 0, w: 60.19, l: 38.30, angle: Math.PI, y: 0.03 },
        look: { photo: true, baked: true, gain: 2, sat: 1, contrast: 1 },
        // a tall bowl: the camera aims further out, so the big screens over
        // the club band on the far side stay in frame (-17: they sit just under the top, the near touchline still in view)
        view: { lookZ: -17 },
    },
    {
        id: 'de-kuip',
        name: 'De Kuip',
        club: 'Feyenoord',
        city: 'Rotterdam',
        // built from nothing by tools/dekuip_build.py; ?v=: raise it with every new export
        file: 'media/models/stadiums/de_kuip.glb?v=3',
        capacity: '47.500',
        pitch: { x: 0, z: 0, w: 77.18, l: 49.12, angle: Math.PI, y: 0.10 },
        look: { photo: true, baked: true, gain: 2, sat: 1, contrast: 1 },
        // the long red scoreboard, in the band behind both goals; the home logo
        // shows when this file exists (put the official logo there yourself)
        screen: 'kuip',
        screenLogo: 'img/feyenoord.png',
        nets: ['#d8141c', '#ffffff'],     // the nets: red on the left, white on the right, at both goals
        view: { lookZ: -12 },
    },
    {
        id: 'el-campin',
        name: 'El Campín',
        club: 'Millonarios · Santa Fe',
        city: 'Bogotá',
        // built from nothing by tools/campin_build.py; ?v=: raise it with every new export
        file: 'media/models/stadiums/el_campin.glb?v=1',
        capacity: '36.343',
        pitch: { x: 0, z: 0, w: 79.73, l: 50.73, angle: Math.PI, y: 0.07 },
        look: { photo: true, baked: true, gain: 2, sat: 1, contrast: 1 },
        // the big screen over the north end: both teams' colours, score and clock
        screen: 'campin',
        view: { lookZ: -12 },
    },
    {
        id: 'johan-cruijff-arena',
        name: 'Johan Cruijff ArenA',
        club: 'AFC Ajax',
        city: 'Amsterdam',
        // built from nothing by tools/arena_build.py; ?v=: raise it with every new export
        file: 'media/models/stadiums/johan_cruijff_arena.glb?v=4',
        capacity: '56.120',
        pitch: { x: 0, z: 0.41, w: 72.60, l: 46.20, angle: Math.PI, y: 5.81 },
        look: { photo: true, baked: true, gain: 2, sat: 1, contrast: 1 },
        // the two screens hanging under the championship banners at both ends
        // of the roof opening: the clock, the score and a badge per team, the
        // home side with the Ajax logo (img/logo3.png)
        screen: 'arena',
        screenLogo: 'img/logo3.png',
        hangOverPitch: true,          // the screens and banners hang over the pitch: not cut away (dressStadium)
        view: { lookZ: -12 },
    },
];

const STADIUM_STORAGE_KEY = 'pitchRoyale.stadium';
// Lotto Park is the stadium every time the game is opened; a stadium you pick
// counts for as long as the game stays open (sessionStorage), not for good.
try { localStorage.removeItem(STADIUM_STORAGE_KEY); } catch (_) {}     // the old, lasting choice
function getSelectedStadium() {
    let id = null;
    try { id = sessionStorage.getItem(STADIUM_STORAGE_KEY); } catch (_) {}
    return STADIUMS.find(s => s.id === id) || STADIUMS.find(s => s.id === 'lotto-park');
}
// the stadium a match is played in: a WK match goes to the World Cup stadium
// (the one with World Cup screens, MetLife), otherwise the chosen one
function matchStadium() {
    if (typeof STATE !== 'undefined' && STATE.mode === 'online' && STATE.onlineStadium) {
        const own = STADIUMS.find(s => s.id === STATE.onlineStadium);
        if (own) return own;
    }
    if (typeof STATE !== 'undefined' && STATE.wkMatch) {
        const wkStadium = STADIUMS.find(s => s.screen === 'wk' && s.file);
        if (wkStadium) return wkStadium;
    }
    return getSelectedStadium();
}
function setSelectedStadium(id) {
    if (!STADIUMS.find(s => s.id === id)) return;
    try { sessionStorage.setItem(STADIUM_STORAGE_KEY, id); } catch (_) {}
}

// ----------- camera views (Instellingen) -----------
// The match camera, as the camera options in FIFA: always on the long side
// (the game cuts the near stand away towards it), each with its own height,
// distance, lens and how far it follows the ball. A laptop and a phone each
// keep their own choice, plus a height and a zoom from 0 to 10 (5 = as set).
const CAMERA_VIEWS = [
    // shift: how much of a stadium's own aim (catalog view.lookZ) it takes; the
    // low and steep views would lose the near touchline with it
    { id: 'uitzending', name: 'Uitzending', meta: 'Zoals op tv',               height: 46, back: 118, fov: 30, follow: 0.95, maxX: 92, shift: 1, followZ: 0.55 },
    { id: 'stadion',    name: 'Stadion',    meta: 'Met de schermen in beeld',  height: 40, back: 132, fov: 36, follow: 0.9,  maxX: 86, shift: 0, lookZ: -30, followZ: 0.5 },
    { id: 'tele',       name: 'Tele',       meta: 'Van ver weg, vlak beeld',   height: 66, back: 170, fov: 21, follow: 0.95, maxX: 92, shift: 1, followZ: 0.6 },
    { id: 'dichtbij',   name: 'Dichtbij',   meta: 'Laag en dicht op het veld', height: 28, back: 82,  fov: 40, follow: 1,    maxX: 98, shift: 0, followZ: 0.7 },
    { id: 'hoog',       name: 'Hoog',       meta: 'Het hele veld van boven',   height: 110, back: 110, fov: 46, follow: 0.6,  maxX: 50, shift: 0, followZ: 0.3 },
    { id: 'dynamisch',  name: 'Dynamisch',  meta: 'Gaat mee met de bal',       height: 34, back: 84,  fov: 38, follow: 1,    maxX: 100, shift: 0, followZ: 0.75 },
];
const CAMERA_STORAGE_KEY = 'pitchRoyale.camera';
const CAMERA_DEFAULT = { view: 'uitzending', height: 5, zoom: 5 };
function getCameraSettings() {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(CAMERA_STORAGE_KEY) || 'null'); } catch (_) {}
    const one = (o) => {
        const v = Object.assign({}, CAMERA_DEFAULT, o || {});
        if (!CAMERA_VIEWS.some(c => c.id === v.view)) v.view = CAMERA_DEFAULT.view;
        v.height = Math.max(0, Math.min(10, Math.round(+v.height || 0)));
        v.zoom = Math.max(0, Math.min(10, Math.round(+v.zoom || 0)));
        return v;
    };
    return { laptop: one(saved && saved.laptop), phone: one(saved && saved.phone) };
}
function setCameraSettings(device, values) {
    const all = getCameraSettings();
    all[device] = Object.assign({}, all[device], values);
    try { localStorage.setItem(CAMERA_STORAGE_KEY, JSON.stringify(all)); } catch (_) {}
}
// the camera for a device: the view with its height and lens adjusted
function cameraFor(device) {
    const set = getCameraSettings()[device];
    const view = CAMERA_VIEWS.find(c => c.id === set.view);
    return Object.assign({ lookZ: 0, followZ: 0 }, view, {
        height: view.height * (0.7 + 0.06 * set.height),       // 0: 70%, 10: 130%
        fov: view.fov * (1.25 - 0.05 * set.zoom),              // 0: wider, 10: 25% closer
    });
}

// ----------- DOM helpers -----------
const $ = (id) => document.getElementById(id);
const screens = ['loading-screen','launch-screen','setup-screen','coin-screen','game-screen','over-screen','stadium-screen','wk-screen','wk-hub-screen','online-screen','settings-screen'];
const SCREEN_TO_DOM = {
    loading: 'loading-screen',
    launch:  'launch-screen',
    setup:   'setup-screen',
    coin:    'coin-screen',
    playing: 'game-screen',
    over:    'over-screen',
    stadium: 'stadium-screen',
    wk:      'wk-screen',
    wkhub:   'wk-hub-screen',
    online:  'online-screen',
    settings: 'settings-screen',
};
function showScreen(id) {
    screens.forEach(s => {
        const el = $(s);
        if (!el) return;
        // a screen you come back to starts at the top, not where you left it
        if (s === id && !el.classList.contains('active')) el.scrollTop = 0;
        el.classList.toggle('active', s === id);
    });
}

function gotoScreen(target, { replace = false } = {}) {
    if (STATE.screen === 'playing' && target !== 'playing') teardownGame();
    if (typeof ONLINE !== 'undefined') ONLINE.onScreen(target);
    if (STATE.screen === 'stadium' && target !== 'stadium') { STADIUM_PREVIEW?.detach(); }
    STATE.screen = target;
    showScreen(SCREEN_TO_DOM[target] || (target + '-screen'));
    const stateObj = { screen: target };
    const cleanUrl = location.pathname + location.search;
    if (replace) history.replaceState(stateObj, '', cleanUrl);
    else         history.pushState(stateObj, '', cleanUrl);
}

function navigateToFromPopState(target) {
    if (STATE.screen === 'playing' && target !== 'playing') teardownGame();
    if (typeof ONLINE !== 'undefined') ONLINE.onScreen(target);
    if (STATE.screen === 'stadium' && target !== 'stadium') { STADIUM_PREVIEW?.detach(); }
    STATE.screen = target;
    showScreen(SCREEN_TO_DOM[target] || (target + '-screen'));
}

// ----------- screen flow -----------
const QUICK_MODE = location.pathname.endsWith('play.html');

document.addEventListener('DOMContentLoaded', () => {
    if (QUICK_MODE) {
        // Quick-play page: skip launch/setup/coin entirely, jump straight into
        // an infinite-duration match with sensible defaults. Pause still works.
        bindPause();
        bindTouch();
        STATE.p1.name = 'P1';
        STATE.p2.name = 'P2';
        STATE.mode = 'duo';
        STATE.kickoffTeam = 1;
        STATE.gameDuration = Infinity;
        history.replaceState({ screen: 'playing' }, '', location.pathname + location.search);
        startGame();
        return;
    }

    bindLaunch();
    bindSetup();
    bindCoin();
    bindOver();
    bindPause();
    bindStadium();
    bindTouch();
    bindWk();
    updateLaunchStadiumLabel();
    window.addEventListener('keydown', (e) => {
        if (STATE.screen !== 'launch') return;
        if (e.code !== 'Space' && e.code !== 'Enter') return;
        // a focused menu button handles its own Enter / Space
        if (e.target instanceof Element && e.target.closest('button')) return;
        goToSetup();
    });

    // short splash while the web fonts come in
    setTimeout(() => {
        if (STATE.screen === 'loading') gotoScreen('launch', { replace: true });
        preloadSelectedStadium();
    }, 900);

    history.replaceState({ screen: 'loading' }, '', location.pathname + location.search);

    window.addEventListener('popstate', (e) => {
        const target = (e.state && e.state.screen) || 'launch';
        navigateToFromPopState(target);
    });
});

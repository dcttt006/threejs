// =====================================================
// PITCH ROYALE — WK 2026
// The World Cup in Canada, Mexico and the USA: the 48 teams in the groups of
// the final draw (5 December 2025) with the winners of the March 2026
// play-offs, and the official format: 12 groups of four; the top two of each
// group and the eight best third-placed teams go to a round of 32, then
// knockouts to the final in New York New Jersey. You play your own country's
// matches against the computer; every other match is simulated.
//
// No FIFA logos, emblem, mascots or trophy artwork: those are trademarks.
// Team strengths are our own estimates, used for the simulation and the
// computer's level; kit colours are approximations of each team's colours.
// =====================================================

const WK_STORAGE_KEY = 'pitchRoyale.wk2026';

// FIFA code -> Dutch name, flag file (media/flags), strength, kits [shirt, shorts, socks]
const WK_TEAMS = {
    MEX: { name: 'Mexico',          flag: 'mx',     r: 80, home: ['#0f6b3c', '#ffffff', '#c8102e'], away: ['#f2efe6', '#1a1a1a', '#f2efe6'] },
    RSA: { name: 'Zuid-Afrika',     flag: 'za',     r: 70, home: ['#ffcc00', '#0b7a3e', '#ffcc00'], away: ['#0b7a3e', '#0b7a3e', '#ffffff'] },
    KOR: { name: 'Zuid-Korea',      flag: 'kr',     r: 78, home: ['#d7192d', '#1a1a1a', '#d7192d'], away: ['#f4f4f4', '#1a1a1a', '#f4f4f4'] },
    CZE: { name: 'Tsjechië',        flag: 'cz',     r: 76, home: ['#d7141a', '#ffffff', '#11457e'], away: ['#f4f4f4', '#11457e', '#f4f4f4'] },
    CAN: { name: 'Canada',          flag: 'ca',     r: 77, home: ['#d52b1e', '#d52b1e', '#d52b1e'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    BIH: { name: 'Bosnië',          flag: 'ba',     r: 72, home: ['#1f3f8f', '#1f3f8f', '#1f3f8f'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    QAT: { name: 'Qatar',           flag: 'qa',     r: 68, home: ['#7a1f3d', '#7a1f3d', '#7a1f3d'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    SUI: { name: 'Zwitserland',     flag: 'ch',     r: 80, home: ['#d52b1e', '#d52b1e', '#d52b1e'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    BRA: { name: 'Brazilië',        flag: 'br',     r: 88, home: ['#f7d417', '#1f4fa8', '#f4f4f4'], away: ['#1f4fa8', '#f4f4f4', '#1f4fa8'] },
    MAR: { name: 'Marokko',         flag: 'ma',     r: 83, home: ['#c1272d', '#0b6b3a', '#c1272d'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    HAI: { name: 'Haïti',           flag: 'ht',     r: 60, home: ['#1d3f9a', '#d21034', '#1d3f9a'], away: ['#f4f4f4', '#1d3f9a', '#f4f4f4'] },
    SCO: { name: 'Schotland',       flag: 'gb-sct', r: 74, home: ['#1b2a4a', '#f4f4f4', '#1b2a4a'], away: ['#f4f4f4', '#1b2a4a', '#f4f4f4'] },
    USA: { name: 'Verenigde Staten', flag: 'us',    r: 80, home: ['#f4f4f4', '#1b2a5a', '#f4f4f4'], away: ['#1b2a5a', '#1b2a5a', '#1b2a5a'] },
    PAR: { name: 'Paraguay',        flag: 'py',     r: 75, home: ['#d52b1e', '#1d3f9a', '#1d3f9a'], away: ['#1d3f9a', '#1d3f9a', '#1d3f9a'] },
    AUS: { name: 'Australië',       flag: 'au',     r: 75, home: ['#ffcd00', '#0b6b3a', '#ffcd00'], away: ['#0b6b3a', '#0b6b3a', '#0b6b3a'] },
    TUR: { name: 'Turkije',         flag: 'tr',     r: 79, home: ['#e30a17', '#e30a17', '#e30a17'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    GER: { name: 'Duitsland',       flag: 'de',     r: 86, home: ['#f4f4f4', '#1a1a1a', '#f4f4f4'], away: ['#3a2a5a', '#3a2a5a', '#3a2a5a'] },
    CUW: { name: 'Curaçao',         flag: 'cw',     r: 62, home: ['#1d4fa8', '#1d4fa8', '#1d4fa8'], away: ['#f9d616', '#1d4fa8', '#f9d616'] },
    CIV: { name: 'Ivoorkust',       flag: 'ci',     r: 77, home: ['#f77f00', '#f4f4f4', '#009e60'], away: ['#f4f4f4', '#009e60', '#f4f4f4'] },
    ECU: { name: 'Ecuador',         flag: 'ec',     r: 79, home: ['#ffdd00', '#1d3f9a', '#d52b1e'], away: ['#1d3f9a', '#1d3f9a', '#1d3f9a'] },
    NED: { name: 'Nederland',       flag: 'nl',     r: 87, home: ['#f36c21', '#f36c21', '#f36c21'], away: ['#1b2a5a', '#1b2a5a', '#1b2a5a'] },
    JPN: { name: 'Japan',           flag: 'jp',     r: 81, home: ['#1d3f9a', '#1d3f9a', '#1d3f9a'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    SWE: { name: 'Zweden',          flag: 'se',     r: 77, home: ['#fecc02', '#1d5aa8', '#fecc02'], away: ['#1d3f7a', '#1d3f7a', '#1d3f7a'] },
    TUN: { name: 'Tunesië',         flag: 'tn',     r: 72, home: ['#e70013', '#f4f4f4', '#e70013'], away: ['#f4f4f4', '#e70013', '#f4f4f4'] },
    BEL: { name: 'België',          flag: 'be',     r: 85, home: ['#c8102e', '#c8102e', '#c8102e'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    EGY: { name: 'Egypte',          flag: 'eg',     r: 75, home: ['#c8102e', '#f4f4f4', '#1a1a1a'], away: ['#f4f4f4', '#1a1a1a', '#f4f4f4'] },
    IRN: { name: 'Iran',            flag: 'ir',     r: 77, home: ['#f4f4f4', '#f4f4f4', '#f4f4f4'], away: ['#da0000', '#da0000', '#da0000'] },
    NZL: { name: 'Nieuw-Zeeland',   flag: 'nz',     r: 64, home: ['#f4f4f4', '#1a1a1a', '#f4f4f4'], away: ['#1a1a1a', '#1a1a1a', '#1a1a1a'] },
    ESP: { name: 'Spanje',          flag: 'es',     r: 92, home: ['#c60b1e', '#1b2a5a', '#c60b1e'], away: ['#f2ecd6', '#f2ecd6', '#f2ecd6'] },
    CPV: { name: 'Kaapverdië',      flag: 'cv',     r: 67, home: ['#1d3f9a', '#1d3f9a', '#1d3f9a'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    KSA: { name: 'Saoedi-Arabië',   flag: 'sa',     r: 70, home: ['#0b6b3a', '#f4f4f4', '#0b6b3a'], away: ['#f4f4f4', '#0b6b3a', '#f4f4f4'] },
    URU: { name: 'Uruguay',         flag: 'uy',     r: 83, home: ['#5cbfeb', '#1a1a1a', '#1a1a1a'], away: ['#f4f4f4', '#5cbfeb', '#f4f4f4'] },
    FRA: { name: 'Frankrijk',       flag: 'fr',     r: 91, home: ['#1b2a5a', '#f4f4f4', '#c8102e'], away: ['#f4f4f4', '#1b2a5a', '#f4f4f4'] },
    SEN: { name: 'Senegal',         flag: 'sn',     r: 80, home: ['#f4f4f4', '#f4f4f4', '#f4f4f4'], away: ['#0b8a3e', '#0b8a3e', '#0b8a3e'] },
    IRQ: { name: 'Irak',            flag: 'iq',     r: 68, home: ['#0b6b3a', '#0b6b3a', '#0b6b3a'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    NOR: { name: 'Noorwegen',       flag: 'no',     r: 80, home: ['#ba0c2f', '#f4f4f4', '#1b2a5a'], away: ['#f4f4f4', '#1b2a5a', '#f4f4f4'] },
    ARG: { name: 'Argentinië',      flag: 'ar',     r: 92, home: ['#75aadb', '#1a1a1a', '#f4f4f4'], away: ['#1b2a5a', '#1b2a5a', '#1b2a5a'] },
    ALG: { name: 'Algerije',        flag: 'dz',     r: 75, home: ['#f4f4f4', '#f4f4f4', '#f4f4f4'], away: ['#0b6b3a', '#0b6b3a', '#0b6b3a'] },
    AUT: { name: 'Oostenrijk',      flag: 'at',     r: 79, home: ['#c8102e', '#f4f4f4', '#c8102e'], away: ['#f4f4f4', '#1a1a1a', '#f4f4f4'] },
    JOR: { name: 'Jordanië',        flag: 'jo',     r: 68, home: ['#f4f4f4', '#f4f4f4', '#f4f4f4'], away: ['#c8102e', '#c8102e', '#c8102e'] },
    POR: { name: 'Portugal',        flag: 'pt',     r: 88, home: ['#c8102e', '#0b5e2e', '#c8102e'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
    COD: { name: 'DR Congo',        flag: 'cd',     r: 72, home: ['#4aa3df', '#4aa3df', '#4aa3df'], away: ['#c8102e', '#f7d417', '#c8102e'] },
    UZB: { name: 'Oezbekistan',     flag: 'uz',     r: 70, home: ['#f4f4f4', '#f4f4f4', '#f4f4f4'], away: ['#1d5aa8', '#1d5aa8', '#1d5aa8'] },
    COL: { name: 'Colombia',        flag: 'co',     r: 83, home: ['#fcd116', '#1b2a5a', '#c8102e'], away: ['#1b2a5a', '#f4f4f4', '#1b2a5a'] },
    ENG: { name: 'Engeland',        flag: 'gb-eng', r: 90, home: ['#f4f4f4', '#1b2a5a', '#f4f4f4'], away: ['#c8102e', '#c8102e', '#c8102e'] },
    CRO: { name: 'Kroatië',         flag: 'hr',     r: 84, home: ['#d81e2c', '#f4f4f4', '#1d3f9a'], away: ['#1b2a5a', '#1b2a5a', '#1b2a5a'] },
    GHA: { name: 'Ghana',           flag: 'gh',     r: 73, home: ['#f4f4f4', '#f4f4f4', '#f4f4f4'], away: ['#fcd116', '#1a1a1a', '#fcd116'] },
    PAN: { name: 'Panama',          flag: 'pa',     r: 70, home: ['#d21034', '#d21034', '#d21034'], away: ['#f4f4f4', '#f4f4f4', '#f4f4f4'] },
};

// the groups of the draw, each in draw position order (1 to 4)
const WK_GROUPS = {
    A: ['MEX', 'RSA', 'KOR', 'CZE'],
    B: ['CAN', 'BIH', 'QAT', 'SUI'],
    C: ['BRA', 'MAR', 'HAI', 'SCO'],
    D: ['USA', 'PAR', 'AUS', 'TUR'],
    E: ['GER', 'CUW', 'CIV', 'ECU'],
    F: ['NED', 'JPN', 'SWE', 'TUN'],
    G: ['BEL', 'EGY', 'IRN', 'NZL'],
    H: ['ESP', 'CPV', 'KSA', 'URU'],
    I: ['FRA', 'SEN', 'IRQ', 'NOR'],
    J: ['ARG', 'ALG', 'AUT', 'JOR'],
    K: ['POR', 'COD', 'UZB', 'COL'],
    L: ['ENG', 'CRO', 'GHA', 'PAN'],
};
const WK_LETTERS = Object.keys(WK_GROUPS);
// who plays whom on each of the three matchdays (draw positions, home first)
const WK_MATCHDAYS = [[[0, 1], [2, 3]], [[0, 2], [3, 1]], [[3, 0], [1, 2]]];

// the knockout bracket, by match number. A third-placed team goes to the slot
// whose list of groups contains its own; which one exactly depends on which
// eight thirds go through (FIFA has a table for that; we pick a valid fit).
const WK_R32 = [
    { m: 73, a: '2A', b: '2B',     city: 'Los Angeles' },
    { m: 74, a: '1E', b: '3ABCDF', city: 'Boston' },
    { m: 75, a: '1F', b: '2C',     city: 'Monterrey' },
    { m: 76, a: '1C', b: '2F',     city: 'Houston' },
    { m: 77, a: '1I', b: '3CDFGH', city: 'New York New Jersey' },
    { m: 78, a: '2E', b: '2I',     city: 'Dallas' },
    { m: 79, a: '1A', b: '3CEFHI', city: 'Mexico-Stad' },
    { m: 80, a: '1L', b: '3EHIJK', city: 'Atlanta' },
    { m: 81, a: '1D', b: '3BEFIJ', city: 'San Francisco Bay Area' },
    { m: 82, a: '1G', b: '3AEHIJ', city: 'Seattle' },
    { m: 83, a: '2K', b: '2L',     city: 'Toronto' },
    { m: 84, a: '1H', b: '2J',     city: 'Los Angeles' },
    { m: 85, a: '1B', b: '3EFGIJ', city: 'Vancouver' },
    { m: 86, a: '1J', b: '2H',     city: 'Miami' },
    { m: 87, a: '1K', b: '3DEIJL', city: 'Kansas City' },
    { m: 88, a: '2D', b: '2G',     city: 'Dallas' },
];
// later rounds: winners of matches a and b (negative = the loser)
const WK_LATER = [
    { m: 89,  a: 74,   b: 77,   round: 'r16',    city: 'Philadelphia' },
    { m: 90,  a: 73,   b: 75,   round: 'r16',    city: 'Houston' },
    { m: 91,  a: 76,   b: 78,   round: 'r16',    city: 'New York New Jersey' },
    { m: 92,  a: 79,   b: 80,   round: 'r16',    city: 'Mexico-Stad' },
    { m: 93,  a: 83,   b: 84,   round: 'r16',    city: 'Dallas' },
    { m: 94,  a: 81,   b: 82,   round: 'r16',    city: 'Seattle' },
    { m: 95,  a: 86,   b: 88,   round: 'r16',    city: 'Atlanta' },
    { m: 96,  a: 85,   b: 87,   round: 'r16',    city: 'Vancouver' },
    { m: 97,  a: 89,   b: 90,   round: 'qf',     city: 'Boston' },
    { m: 98,  a: 93,   b: 94,   round: 'qf',     city: 'Los Angeles' },
    { m: 99,  a: 91,   b: 92,   round: 'qf',     city: 'Miami' },
    { m: 100, a: 95,   b: 96,   round: 'qf',     city: 'Kansas City' },
    { m: 101, a: 97,   b: 98,   round: 'sf',     city: 'Dallas' },
    { m: 102, a: 99,   b: 100,  round: 'sf',     city: 'Atlanta' },
    { m: 103, a: -101, b: -102, round: 'bronze', city: 'Miami' },
    { m: 104, a: 101,  b: 102,  round: 'final',  city: 'New York New Jersey' },
];
// The 16 host stadiums, photographed by Wikimedia Commons contributors under
// free licences (CC BY, CC BY-SA, CC0, public domain). Each photo is shown
// with its photographer and licence, as those licences ask.
const WK_VENUES = {
    "New York New Jersey": { stadium: "MetLife Stadium", file: 'new-york-new-jersey.jpg', by: "Thecoolone1223", license: 'CC BY 4.0', page: 'https://commons.wikimedia.org/wiki/File:MetLife_Stadium_2022.jpg' },
    "Dallas": { stadium: "AT&T Stadium", file: 'dallas.jpg', by: "Michael Barera", license: 'CC BY-SA 4.0', page: 'https://commons.wikimedia.org/wiki/File:Arlington_June_2020_4_(AT%26T_Stadium).jpg' },
    "Kansas City": { stadium: "Arrowhead Stadium", file: 'kansas-city.jpg', by: "Ichabod", license: 'CC BY-SA 3.0', page: 'https://commons.wikimedia.org/wiki/File:Aerial_view_of_Arrowhead_Stadium_08-31-2013.jpg' },
    "Houston": { stadium: "NRG Stadium", file: 'houston.jpg', by: "eschipul", license: 'CC BY-SA 2.0', page: 'https://commons.wikimedia.org/wiki/File:Reliantstadium.jpg' },
    "Atlanta": { stadium: "Mercedes-Benz Stadium", file: 'atlanta.jpg', by: "Atlanta Falcons", license: 'CC BY 3.0', page: 'https://commons.wikimedia.org/wiki/File:Mercedes_Benz_Stadium_time_lapse_capture_2017-08-13.jpg' },
    "Los Angeles": { stadium: "SoFi Stadium", file: 'los-angeles.jpg', by: "Thank You (21 Millions+) views", license: 'CC BY 2.0', page: 'https://commons.wikimedia.org/wiki/File:SoFi_Stadium_(51126606022).jpg' },
    "Philadelphia": { stadium: "Lincoln Financial Field", file: 'philadelphia.jpg', by: "Betp", license: 'CC BY-SA 3.0', page: 'https://commons.wikimedia.org/wiki/File:Lincoln_Financial_Field,_Philadelphia.jpg' },
    "Seattle": { stadium: "Lumen Field", file: 'seattle.jpg', by: "SounderBruce", license: 'CC BY-SA 4.0', page: 'https://commons.wikimedia.org/wiki/File:Lumen_Field_north_side_at_dusk.jpg' },
    "San Francisco Bay Area": { stadium: "Levi's Stadium", file: 'san-francisco-bay-area.jpg', by: "Matthew Roth", license: 'CC BY-SA 2.0', page: 'https://commons.wikimedia.org/wiki/File:Levi%27s_Stadium_interior_1.jpg' },
    "Boston": { stadium: "Gillette Stadium", file: 'boston.jpg', by: "Bernard Gagnon", license: 'CC BY-SA 3.0', page: 'https://commons.wikimedia.org/wiki/File:Gillette_Stadium02.jpg' },
    "Miami": { stadium: "Hard Rock Stadium", file: 'miami.jpg', by: "Eisenthesky Productions", license: 'CC BY-SA 4.0', page: 'https://commons.wikimedia.org/wiki/File:Hard_Rock_Stadium_Prior_to_first_NFL_game.jpg' },
    "Mexico-Stad": { stadium: "Estadio Azteca", file: 'mexico-stad.jpg', by: "Carlos Valenzuela Montuy", license: 'CC BY-SA 4.0', page: 'https://commons.wikimedia.org/wiki/File:Estadio_Azteca1706p2.jpg' },
    "Guadalajara": { stadium: "Estadio Akron", file: 'guadalajara.jpg', by: "Alejan98", license: 'CC0', page: 'https://commons.wikimedia.org/wiki/File:Estadio_Akron_02-07-2022_cabecera_sur_lado_derecho.jpg' },
    "Monterrey": { stadium: "Estadio BBVA", file: 'monterrey.jpg', by: "Presidencia de la República Mexicana", license: 'CC BY 2.0', page: 'https://commons.wikimedia.org/wiki/File:Estadio_BBVA_Bancomer_(1).jpg' },
    "Toronto": { stadium: "BMO Field", file: 'toronto.jpg', by: "Wladyslaw", license: 'CC BY-SA 3.0', page: 'https://commons.wikimedia.org/wiki/File:Toronto_-_ON_-_BMO_Field.jpg' },
    "Vancouver": { stadium: "BC Place", file: 'vancouver.jpg', by: "Yvrphoto", license: 'CC BY-SA 3.0', page: 'https://commons.wikimedia.org/wiki/File:BC_Place_Opening_Day_2011-09-30.jpg' },
};
const WK_ROUND_ORDER = ['r32', 'r16', 'qf', 'sf', 'bronze', 'final'];
const WK_ROUND_NAME = {
    group: 'Groepsfase', r32: 'Laatste 32', r16: 'Achtste finale', qf: 'Kwartfinale',
    sf: 'Halve finale', bronze: 'Troostfinale', final: 'Finale',
};

// ----------- the tournament in progress -----------
let wk = null;

function wkSave() {
    try { localStorage.setItem(WK_STORAGE_KEY, JSON.stringify(wk)); } catch (_) {}
}
function wkLoad() {
    try {
        const s = JSON.parse(localStorage.getItem(WK_STORAGE_KEY));
        if (s && s.v === 1 && WK_TEAMS[s.team]) wk = s;
    } catch (_) {}
}
function wkNew(team, level) {
    wk = { v: 1, team, level, md: 0, group: {}, ko: {}, round: 'group', out: null };
    wkSave();
}

const wkClamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const wkGroupOf = (code) => WK_LETTERS.find(L => WK_GROUPS[L].includes(code));
const wkFlagSrc = (code) => `media/flags/${WK_TEAMS[code].flag}.svg`;

// ----------- simulating the matches you don't play -----------
function wkPoisson(l) {
    const L = Math.exp(-l);
    let k = 0, p = 1;
    do { k++; p *= Math.random(); } while (p > L);
    return k - 1;
}
function wkSimScore(a, b) {
    const d = (WK_TEAMS[a].r - WK_TEAMS[b].r) / 10;
    return [wkPoisson(wkClamp(1.35 + 0.32 * d, 0.25, 3.5)), wkPoisson(wkClamp(1.35 - 0.32 * d, 0.25, 3.5))];
}
function wkSimPens() {
    let a = 0, b = 0;
    for (let i = 0; i < 5; i++) { a += Math.random() < 0.76; b += Math.random() < 0.76; }
    while (a === b) {
        const x = Math.random() < 0.76, y = Math.random() < 0.76;
        a += x; b += y;
    }
    return [a, b];
}

// ----------- group stage -----------
function wkFixtures(L) {
    const t = WK_GROUPS[L];
    return WK_MATCHDAYS.flatMap((day, md) => day.map(([h, a]) => ({ md, home: t[h], away: t[a], letter: L })));
}
function wkStandings(L) {
    const rows = WK_GROUPS[L].map(code => ({ code, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0 }));
    const row = (c) => rows.find(r => r.code === c);
    wkFixtures(L).forEach(f => {
        const res = wk.group[`${f.home}-${f.away}`];
        if (!res) return;
        const h = row(f.home), a = row(f.away);
        h.p++; a.p++;
        h.gf += res[0]; h.ga += res[1]; a.gf += res[1]; a.ga += res[0];
        if (res[0] > res[1]) { h.w++; a.l++; h.pts += 3; }
        else if (res[0] < res[1]) { a.w++; h.l++; a.pts += 3; }
        else { h.d++; a.d++; h.pts++; a.pts++; }
    });
    // points, goal difference, goals scored, then (our simplification) strength
    return rows.sort((x, y) => (y.pts - x.pts) || ((y.gf - y.ga) - (x.gf - x.ga)) || (y.gf - x.gf) || (WK_TEAMS[y.code].r - WK_TEAMS[x.code].r));
}
function wkThirds() {
    return WK_LETTERS.map(L => ({ ...wkStandings(L)[2], letter: L }))
        .sort((x, y) => (y.pts - x.pts) || ((y.gf - y.ga) - (x.gf - x.ga)) || (y.gf - x.gf) || (WK_TEAMS[y.code].r - WK_TEAMS[x.code].r));
}

// play out one matchday in every group (your own match is already in)
function wkSimMatchday(md) {
    WK_LETTERS.forEach(L => wkFixtures(L).forEach(f => {
        const key = `${f.home}-${f.away}`;
        if (f.md === md && !wk.group[key]) wk.group[key] = wkSimScore(f.home, f.away);
    }));
}

// after matchday 3: who goes where in the round of 32
function wkDrawRound32() {
    const seat = {};
    WK_LETTERS.forEach(L => {
        const s = wkStandings(L);
        seat['1' + L] = s[0].code;
        seat['2' + L] = s[1].code;
    });
    const best = wkThirds().slice(0, 8);
    wk.thirds = best.map(t => t.code);
    // fit the eight thirds into the eight slots that allow their group
    const slots = WK_R32.filter(x => x.b.startsWith('3'));
    const used = new Set();
    const fit = (i) => {
        if (i === slots.length) return true;
        for (const t of best) {
            if (used.has(t.code) || !slots[i].b.includes(t.letter)) continue;
            used.add(t.code); seat[slots[i].b] = t.code;
            if (fit(i + 1)) return true;
            used.delete(t.code);
        }
        return false;
    };
    fit(0);
    WK_R32.forEach(x => { wk.ko[x.m] = { a: seat[x.a], b: seat[x.b] }; });
}

// ----------- knockouts -----------
function wkMatchInfo(m) {
    return WK_R32.find(x => x.m === m) ? { ...WK_R32.find(x => x.m === m), round: 'r32' } : WK_LATER.find(x => x.m === m);
}
function wkRoundMatches(round) {
    return round === 'r32' ? WK_R32.map(x => x.m) : WK_LATER.filter(x => x.round === round).map(x => x.m);
}
function wkWinner(m)  { const k = wk.ko[m]; return k && k.w; }
function wkLoser(m)   { const k = wk.ko[m]; return k && k.w && (k.w === k.a ? k.b : k.a); }
function wkBuildRound(round) {
    WK_LATER.filter(x => x.round === round).forEach(x => {
        const pick = (n) => n < 0 ? wkLoser(-n) : wkWinner(n);
        wk.ko[x.m] = wk.ko[x.m] && wk.ko[x.m].w ? wk.ko[x.m] : { a: pick(x.a), b: pick(x.b) };
    });
}
function wkSetResult(m, ga, gb, pens) {
    const k = wk.ko[m];
    k.ga = ga; k.gb = gb; k.pens = pens || null;
    k.w = ga > gb ? k.a : gb > ga ? k.b : (pens[0] > pens[1] ? k.a : k.b);
}
function wkSimRound(round) {
    wkRoundMatches(round).forEach(m => {
        const k = wk.ko[m];
        if (!k || k.w || !k.a || !k.b) return;
        const [ga, gb] = wkSimScore(k.a, k.b);
        wkSetResult(m, ga, gb, ga === gb ? wkSimPens() : null);
    });
}
// play every round that is left, without you
function wkSimulateRest() {
    WK_ROUND_ORDER.forEach(round => {
        if (round !== 'r32') wkBuildRound(round);
        wkSimRound(round);
    });
}
const wkChampion = () => wkWinner(104);

// ----------- your next match -----------
function wkMyFixture() {
    if (!wk || wk.out) return null;
    if (wk.round === 'group') {
        const L = wkGroupOf(wk.team);
        const f = wkFixtures(L).find(x => x.md === wk.md && (x.home === wk.team || x.away === wk.team));
        return f ? { kind: 'group', ...f } : null;
    }
    for (const m of wkRoundMatches(wk.round)) {
        const k = wk.ko[m];
        if (k && !k.w && (k.a === wk.team || k.b === wk.team)) return { kind: 'ko', m, ...wkMatchInfo(m), a: k.a, b: k.b };
    }
    return null;
}
const wkOpponent = (f) => f.kind === 'group' ? (f.home === wk.team ? f.away : f.home) : (f.a === wk.team ? f.b : f.a);

// your result is in: play the rest of that round and move on
function wkRecord(f, mine, theirs, pens) {
    if (f.kind === 'group') {
        wk.group[`${f.home}-${f.away}`] = f.home === wk.team ? [mine, theirs] : [theirs, mine];
        wkSimMatchday(wk.md);
        wk.md++;
        if (wk.md === 3) {
            wkDrawRound32();
            const through = Object.values(wk.ko).some(k => k.a === wk.team || k.b === wk.team);
            if (through) wk.round = 'r32';
            else { wk.out = 'group'; wkSimulateRest(); }
        }
    } else {
        const k = wk.ko[f.m];
        const meA = k.a === wk.team;
        wkSetResult(f.m, meA ? mine : theirs, meA ? theirs : mine, pens ? (meA ? pens : [pens[1], pens[0]]) : null);
        const round = f.round;
        wkSimRound(round);
        const won = k.w === wk.team;
        if (round === 'final' || round === 'bronze') {
            if (round === 'bronze') { wkSimRound('final'); }
            wk.out = round === 'final' ? (won ? 'champion' : 'runnerup') : (won ? 'third' : 'fourth');
        } else if (round === 'sf') {
            wkBuildRound('bronze'); wkBuildRound('final');
            if (won) { wkSimRound('bronze'); wk.round = 'final'; }
            else wk.round = 'bronze';
        } else if (won) {
            const next = WK_ROUND_ORDER[WK_ROUND_ORDER.indexOf(round) + 1];
            wkBuildRound(next);
            wk.round = next;
        } else {
            wk.out = round;
            wkSimulateRest();
        }
    }
    wkSave();
}

// ----------- playing a match -----------
// The computer's level: your choice, one step up against the strongest teams
// and one down against the weakest.
function wkMatchLevel(opp) {
    const ids = ['easy', 'medium', 'hard'];
    let i = ids.indexOf(wk.level);
    if (i < 0) i = 1;
    if (WK_TEAMS[opp].r >= 86) i++;
    if (WK_TEAMS[opp].r < 72) i--;
    return ids[wkClamp(i, 0, 2)];
}

function wkStartMatch() {
    const f = wkMyFixture();
    if (!f) return;
    const opp = wkOpponent(f);
    STATE.wkSaved = { p1: { ...STATE.p1 }, p2: { ...STATE.p2 }, mode: STATE.mode, difficulty: STATE.difficulty };
    STATE.mode = 'cpu';
    STATE.difficulty = wkMatchLevel(opp);
    STATE.p1.name = WK_TEAMS[wk.team].name; STATE.p1.team = 1;
    STATE.p2.name = WK_TEAMS[opp].name;     STATE.p2.team = 2;
    STATE.kickoffTeam = Math.random() < 0.5 ? 1 : 2;
    STATE.score1 = 0; STATE.score2 = 0;
    STATE.gameDuration = 90;
    STATE.goldenGoal = false;
    STATE.wkMatch = { f, me: wk.team, opp, knockout: f.kind === 'ko', city: f.kind === 'ko' ? f.city : null, extra: false };
    STATE.wkStarting = true;
    startGame();
    STATE.wkStarting = false;
    wkDecorateHud();
}

// Called by startGame(): the WK look for a WK match, the normal one otherwise.
const KIT_NORMAL = {};
function wkApply() {
    if (!Object.keys(KIT_NORMAL).length) [1, 2].forEach(t => { KIT_NORMAL[t] = { ...KIT[t] }; });
    const screens = [$('game-screen'), $('over-screen')];
    if (!STATE.wkStarting || !STATE.wkMatch) {
        STATE.wkMatch = null;
        STATE.goldenGoal = false;
        [1, 2].forEach(t => Object.assign(KIT[t], KIT_NORMAL[t]));
        screens.forEach(s => s && ['--red', '--blue', '--red-ink', '--blue-ink'].forEach(v => s.style.removeProperty(v)));
        document.querySelectorAll('.scorebug__flag').forEach(el => el.remove());
        return;
    }
    const m = STATE.wkMatch;
    const me = WK_TEAMS[m.me], them = WK_TEAMS[m.opp];
    // the opponent changes kit when the shirts are too alike; you too, if that doesn't help
    let mine = me.home, theirs = them.home;
    if (wkClash(mine[0], theirs[0])) theirs = them.away;
    if (wkClash(mine[0], theirs[0])) mine = me.away;
    // keepers: a colour unlike both outfield shirts and unlike the other keeper
    const KEEPER = ['#2fb463', '#f2c230', '#8a3ffc', '#ff4fa0', '#00b5c8', '#9be000', '#1b1b1b', '#ff7a00', '#f4f4f4'];
    const keeper = (taken) => KEEPER.find(c => c !== taken && !wkClash(c, mine[0], 140) && !wkClash(c, theirs[0], 140))
        || KEEPER.find(c => c !== taken && !wkClash(c, mine[0]) && !wkClash(c, theirs[0])) || '#9be000';
    KIT[1].shirt = mine[0]; KIT[1].shorts = mine[1]; KIT[1].socks = mine[2]; KIT[1].keeper = keeper(null);
    KIT[2].shirt = theirs[0]; KIT[2].shorts = theirs[1]; KIT[2].socks = theirs[2]; KIT[2].keeper = keeper(KIT[1].keeper);
    // the scoreboard stripes and the goal band take the kit colours
    const stripe = (kit) => wkLight(kit[0]) > 0.82 ? (wkLight(kit[1]) > 0.82 ? '#8a8f96' : kit[1]) : kit[0];
    screens.forEach(s => {
        if (!s) return;
        s.style.setProperty('--red', stripe(mine));
        s.style.setProperty('--blue', stripe(theirs));
        s.style.setProperty('--red-ink', wkLight(stripe(mine)) > 0.6 ? '#121512' : '#ffffff');
        s.style.setProperty('--blue-ink', wkLight(stripe(theirs)) > 0.6 ? '#121512' : '#ffffff');
    });
}
function wkRgb(hex) {
    const n = parseInt(String(hex).replace('#', ''), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function wkClash(a, b, limit = 120) {
    const x = wkRgb(a), y = wkRgb(b);
    return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]) < limit;
}
function wkLight(hex) {
    const [r, g, b] = wkRgb(hex);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

// TV-style scoreboard: flag and FIFA code on each side
function wkDecorateHud() {
    const m = STATE.wkMatch;
    if (!m) return;
    const put = (side, code) => {
        const box = document.querySelector(`.scorebug__team--${side}`);
        const name = $(side === 'red' ? 'hud-p1-name' : 'hud-p2-name');
        if (!box || !name) return;
        box.querySelectorAll('.scorebug__flag').forEach(el => el.remove());
        const img = document.createElement('img');
        img.className = 'scorebug__flag';
        img.src = wkFlagSrc(code);
        img.alt = '';
        if (side === 'red') box.appendChild(img); else box.insertBefore(img, name);
        name.textContent = code;
    };
    put('red', m.me);
    put('blue', m.opp);
}

// a knockout match level at full time: golden-goal extra time first
function wkBeforeEnd() {
    const m = STATE.wkMatch;
    if (!m || !m.knockout || m.pens || STATE.score1 !== STATE.score2) return false;
    if (m.extra) {
        // still level after extra time: a penalty shoot-out (game.pens.js)
        if (typeof PENS === 'undefined') return false;
        STATE.inputLocked = true;
        PENS.start((score) => { m.pens = score; endGame(); });
        return true;
    }
    // level at full time: 30 seconds of extra time, played to the end (no golden goal)
    m.extra = true;
    STATE.gameDuration += 30;
    const b = $('wk-banner');
    if (b) {
        b.hidden = false;
        clearTimeout(wkBeforeEnd.t);
        wkBeforeEnd.t = setTimeout(() => { b.hidden = true; }, 2600);
    }
    return true;
}

// full time: record the result and turn the result screen into a WK one
function wkAfterMatch() {
    const m = STATE.wkMatch;
    const normal = !m;
    $('play-again').hidden = !normal;
    $('back-home').hidden = !normal;
    $('wk-continue').hidden = normal;
    $('wk-banner') && ($('wk-banner').hidden = true);
    if (normal) return;
    const mine = STATE.score1, theirs = STATE.score2;
    const pens = m.knockout && mine === theirs ? (m.pens || wkSimPens()) : null;
    wkRecord(m.f, mine, theirs, pens);
    const me = WK_TEAMS[m.me].name, them = WK_TEAMS[m.opp].name;
    let verdict;
    if (pens) verdict = pens[0] > pens[1]
        ? `${me} wint na strafschoppen (${pens[0]}-${pens[1]})`
        : `${them} wint na strafschoppen (${pens[1]}-${pens[0]})`;
    else if (mine > theirs) verdict = `${me} wint`;
    else if (theirs > mine) verdict = `${them} wint`;
    else verdict = 'Gelijkspel';
    if (m.extra && !pens && mine !== theirs) verdict += ' in de verlenging';
    $('over-winner').textContent = verdict;
}

// back from the result screen: the normal look again, and the tournament
function wkContinue() {
    if (STATE.wkSaved) {
        Object.assign(STATE.p1, STATE.wkSaved.p1);
        Object.assign(STATE.p2, STATE.wkSaved.p2);
        STATE.mode = STATE.wkSaved.mode;
        STATE.difficulty = STATE.wkSaved.difficulty;
        STATE.wkSaved = null;
    }
    STATE.gameDuration = 90;
    teardownGame();
    STATE.score1 = 0; STATE.score2 = 0;
    STATE.wkStarting = false;
    wkApply();
    gotoScreen('wkhub', { replace: true });
    wkRenderHub();
}

// ----------- the WK stadium -----------
// No 3D model: a bowl of stands around the pitch, open on the camera side,
// with a crowd in the colours of both teams and a ribbon board between the
// tiers. Light enough for any phone.
function wkBoardText() {
    const m = STATE.wkMatch;
    return ['WK 2026', m && m.city ? m.city : 'Canada Mexico USA'];
}

function wkCrowdTexture(colors) {
    const c = document.createElement('canvas');
    c.width = 512; c.height = 256;
    const g = c.getContext('2d');
    g.fillStyle = '#191d24';
    g.fillRect(0, 0, 512, 256);
    const pal = [...colors, ...colors, ...colors, '#f2f2f2', '#d8d2c4', '#2b2f36', '#c9a27e', '#8a5a3b', '#e6c39a', '#3d4450'];
    for (let y = 1; y < 256; y += 8) {
        g.fillStyle = '#242a33';
        g.fillRect(0, y + 5, 512, 2);
        for (let x = ((y / 8) % 2) * 3; x < 512; x += 6) {
            if (x % 128 < 10) continue;                       // a stairway
            if (Math.random() < 0.07) continue;               // an empty seat
            g.fillStyle = pal[(Math.random() * pal.length) | 0];
            g.fillRect(x, y, 4, 5);
        }
    }
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return tex;
}

function wkRibbonTexture() {
    const c = document.createElement('canvas');
    c.width = 1024; c.height = 64;
    const g = c.getContext('2d');
    g.fillStyle = '#0d0f12';
    g.fillRect(0, 0, 1024, 64);
    const [a, b] = wkBoardText();
    g.font = '800 40px "Barlow Condensed", "Arial Narrow", Arial, sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillStyle = '#ffd60a';
    g.fillText(a.toUpperCase(), 256, 35);
    g.fillStyle = '#ffffff';
    g.fillText(b.toUpperCase(), 768, 35, 480);
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    tex.wrapS = THREE.RepeatWrapping;
    return tex;
}

// points every ~2 units along a rounded rectangle, starting in the middle of
// the camera side and going round; each with its outward normal and distance
function wkRoundedRect(A, B, R, step) {
    const pts = [];
    let s = 0, last = null;
    const add = (x, z, nx, nz) => {
        if (last) s += Math.hypot(x - last.x, z - last.z);
        last = { x, z };
        pts.push({ x, z, nx, nz, s });
    };
    const line = (x0, z0, x1, z1, nx, nz) => {
        const n = Math.max(1, Math.round(Math.hypot(x1 - x0, z1 - z0) / step));
        for (let i = 0; i < n; i++) add(x0 + (x1 - x0) * i / n, z0 + (z1 - z0) * i / n, nx, nz);
    };
    const arc = (cx, cz, t0, t1) => {
        const n = Math.max(2, Math.round(Math.abs(t1 - t0) * R / step));
        for (let i = 0; i < n; i++) {
            const t = t0 + (t1 - t0) * i / n;
            add(cx + R * Math.cos(t), cz + R * Math.sin(t), Math.cos(t), Math.sin(t));
        }
    };
    const a = A - R, b = B - R, H = Math.PI / 2;
    line(0, B, a, B, 0, 1);
    arc(a, b, H, 0);
    line(A, b, A, -b, 1, 0);
    arc(a, -b, 0, -H);
    line(a, -B, -a, -B, 0, -1);
    arc(-a, -b, -H, -Math.PI);
    line(-A, -b, -A, b, -1, 0);
    arc(-a, b, Math.PI, H);
    line(-a, B, 0, B, 0, 1);
    return pts;
}

function buildWkStadium() {
    const colors = [KIT[1].shirt, KIT[2].shirt].map(c => typeof c === 'number' ? '#' + c.toString(16).padStart(6, '0') : c);
    const seats = new THREE.MeshLambertMaterial({ map: wkCrowdTexture(colors), side: THREE.DoubleSide });
    const ribbon = new THREE.MeshBasicMaterial({ map: wkRibbonTexture(), side: THREE.DoubleSide });
    const shell = new THREE.MeshLambertMaterial({ color: srgb(0x22262d), side: THREE.DoubleSide });

    // concrete round the pitch, under the drawn grass
    const apron = new THREE.Mesh(new THREE.PlaneGeometry(420, 320), new THREE.MeshLambertMaterial({ color: srgb(0x2c3137) }));
    apron.rotation.x = -Math.PI / 2;
    apron.position.y = -0.05;
    scene.add(apron);

    const A = FIELD_W / 2 + 12, B = FIELD_L / 2 + 11, R = 16;
    const path = wkRoundedRect(A, B, R, 2).filter(p => p.z < B * 0.3);   // open towards the camera
    // the cross-section: [distance out from the inner edge, height]
    const profile = [[0, 0.4], [21, 12.5], [21.6, 15.6], [43, 32], [44, 34.5], [51, 39.5]];
    const mats = [seats, ribbon, seats, shell, shell];
    for (let k = 0; k < mats.length; k++) {
        const [o0, y0] = profile[k], [o1, y1] = profile[k + 1];
        const slope = Math.hypot(o1 - o0, y1 - y0);
        const pos = [], uv = [], idx = [];
        path.forEach((p, i) => {
            pos.push(p.x + p.nx * o0, y0, p.z + p.nz * o0, p.x + p.nx * o1, y1, p.z + p.nz * o1);
            const u = mats[k] === ribbon ? -p.s / 40 : p.s / 14;   // seen from inside: run the ribbon backwards
            uv.push(u, 0, u, mats[k] === ribbon ? 1 : slope / 7);
            if (i > 0) {
                const q = i * 2;
                idx.push(q - 2, q - 1, q, q, q - 1, q + 1);
            }
        });
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
        geo.setIndex(idx);
        geo.computeVertexNormals();
        scene.add(new THREE.Mesh(geo, mats[k]));
    }

    // floodlight towers behind the far corners
    const pole = new THREE.MeshLambertMaterial({ color: srgb(0x30343a) });
    const lamp = new THREE.MeshBasicMaterial({ color: srgb(0xfff4d6) });
    [-1, 1].forEach(sx => {
        const x = sx * (A + 34), z = -(B + 34);
        const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 1.2, 64, 8), pole);
        mast.position.set(x, 32, z);
        scene.add(mast);
        const head = new THREE.Mesh(new THREE.BoxGeometry(10, 4, 1.2), lamp);
        head.position.set(x * 0.97, 64, z * 0.97);
        head.lookAt(0, 0, 0);
        scene.add(head);
    });
}

// the WK ball: white with red, green and blue panels for the three hosts
function wkBallTexture() {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 128;
    const g = c.getContext('2d');
    g.fillStyle = '#f7f7f4';
    g.fillRect(0, 0, 256, 128);
    const cols = ['#d52b1e', '#0b8a3e', '#1d4fa8'];
    for (let i = 0; i < 6; i++) {
        g.fillStyle = cols[i % 3];
        g.beginPath();
        const x = i * 256 / 6;
        g.moveTo(x, 18);
        g.bezierCurveTo(x + 30, 6, x + 40, 52, x + 18, 64);
        g.bezierCurveTo(x + 40, 76, x + 30, 122, x, 110);
        g.bezierCurveTo(x + 14, 86, x + 14, 42, x, 18);
        g.fill();
    }
    const tex = new THREE.CanvasTexture(c);
    tex.encoding = THREE.sRGBEncoding;
    return tex;
}

// ----------- screens -----------
let wkPick = null;          // the country chosen on the pick screen
let wkPickLevel = null;

// A team's badge: its crest when you have put one in media/wk/crests/<CODE>.png
// (NED.png, BRA.png ...), its flag otherwise. Missing crests are remembered,
// so each is only tried once.
const WK_NO_CREST = new Set();
function wkFlag(code, cls = 'flag') {
    const img = document.createElement('img');
    img.className = cls;
    img.alt = '';
    img.width = 30; img.height = 20;
    img.decoding = 'async';
    if (WK_NO_CREST.has(code)) {
        img.src = wkFlagSrc(code);
    } else {
        img.classList.add('is-crest');
        img.src = `media/wk/crests/${code}.png`;
        img.addEventListener('error', () => {
            WK_NO_CREST.add(code);
            img.classList.remove('is-crest');
            img.src = wkFlagSrc(code);
        }, { once: true });
    }
    return img;
}

// A stadium photo with what it shows and who took it.
function wkVenuePhoto(city, caption) {
    const v = WK_VENUES[city];
    if (!v) return null;
    const fig = wkEl('figure', 'wk-photo');
    const img = document.createElement('img');
    img.src = `media/wk/venues/${v.file}`;
    img.alt = `${v.stadium}, ${city}`;
    img.loading = 'lazy';
    img.decoding = 'async';
    const cap = wkEl('figcaption', 'wk-photo__cap');
    cap.appendChild(wkEl('span', 'wk-photo__what', caption || `${v.stadium}, ${city}`));
    const credit = wkEl('a', 'wk-photo__credit', `Foto: ${v.by}, ${v.license}, Wikimedia Commons`);
    credit.href = v.page;
    credit.target = '_blank';
    credit.rel = 'noopener';
    cap.appendChild(credit);
    fig.append(img, cap);
    return fig;
}

// The tournament emblem: shown when you have put media/wk/emblem.png in place.
function wkShowEmblems() {
    document.querySelectorAll('.wk-emblem').forEach(img => {
        if (img.dataset.tried) return;
        img.dataset.tried = '1';
        img.addEventListener('load', () => { img.hidden = false; }, { once: true });
        img.addEventListener('error', () => { img.hidden = true; }, { once: true });
        img.src = 'media/wk/emblem.png';
    });
}
function wkEl(tag, cls, text) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
}

function openWk() {
    wkLoad();
    wkPick = null;
    wkPickLevel = wkPickLevel || STATE.difficulty || 'medium';
    gotoScreen('wk');
    wkRenderPick();
}

function wkRenderPick() {
    const hero = $('wk-hero');
    if (hero && !hero.children.length) {
        const fig = wkVenuePhoto('Mexico-Stad', 'Estadio Azteca, Mexico-Stad: hier begint het WK, op 11 juni 2026 met Mexico tegen Zuid-Afrika.');
        if (fig) hero.appendChild(fig);
    }
    const grid = $('wk-groups');
    if (!grid.children.length) {
        WK_LETTERS.forEach(L => {
            const card = wkEl('section', 'wk-group');
            card.appendChild(wkEl('h2', 'wk-group__name', `Groep ${L}`));
            WK_GROUPS[L].forEach(code => {
                const b = wkEl('button', 'wk-team');
                b.type = 'button';
                b.dataset.code = code;
                b.append(wkFlag(code), wkEl('span', 'wk-team__name', WK_TEAMS[code].name));
                b.addEventListener('click', () => { wkPick = code; wkRenderPick(); });
                card.appendChild(b);
            });
            grid.appendChild(card);
        });
    }
    grid.querySelectorAll('.wk-team').forEach(b => {
        const on = b.dataset.code === wkPick;
        b.classList.toggle('is-picked', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    document.querySelectorAll('#wk-level .seg__btn').forEach(b => {
        const on = b.dataset.level === wkPickLevel;
        b.classList.toggle('active', on);
        b.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    const start = $('wk-start');
    start.disabled = !wkPick;
    start.textContent = wkPick ? `Start het WK met ${WK_TEAMS[wkPick].name}` : 'Kies je land';
    // a tournament that is still going can be picked up again
    const resume = $('wk-resume');
    const going = wk && !wk.out;
    resume.hidden = !going;
    if (going) {
        const t = $('wk-resume-text');
        t.replaceChildren(wkFlag(wk.team), wkEl('span', '', `Je WK met ${WK_TEAMS[wk.team].name} loopt nog: ${WK_ROUND_NAME[wk.round]}.`));
    }
}

function wkStageIndex() {
    if (!wk) return 0;
    const order = ['group', 'r32', 'r16', 'qf', 'sf', 'final'];
    const r = wk.round === 'bronze' ? 'sf' : wk.round;
    return order.indexOf(r);
}

function wkRenderHub() {
    if (!wk) return;
    const me = WK_TEAMS[wk.team];
    const L = wkGroupOf(wk.team);
    $('wk-hub-flag').src = wkFlagSrc(wk.team);
    $('wk-hub-team').textContent = me.name;
    $('wk-hub-sub').textContent = `Groep ${L}`;

    // where you are in the tournament
    const path = $('wk-path');
    path.replaceChildren();
    const stages = ['group', 'r32', 'r16', 'qf', 'sf', 'final'];
    const at = wkStageIndex();
    stages.forEach((st, i) => {
        const li = wkEl('li', 'wk-path__step', WK_ROUND_NAME[st]);
        const outHere = wk.out && wk.out !== 'champion' && (
            (wk.out === st) || (st === 'sf' && (wk.out === 'third' || wk.out === 'fourth')) || (st === 'final' && wk.out === 'runnerup'));
        if (outHere) li.classList.add('is-out');
        else if (wk.out === 'champion' || i < at || (wk.out && i < at)) li.classList.add('is-done');
        else if (i === at && !wk.out) li.classList.add('is-now');
        path.appendChild(li);
    });

    // your group
    $('wk-table-title').textContent = `Groep ${L}`;
    wkFillTable($('wk-table'), L, true);

    // your matches so far
    const list = $('wk-fixtures');
    list.replaceChildren();
    wkFixtures(L).filter(f => f.home === wk.team || f.away === wk.team).forEach(f => {
        const res = wk.group[`${f.home}-${f.away}`];
        const opp = f.home === wk.team ? f.away : f.home;
        const mine = res ? (f.home === wk.team ? res[0] : res[1]) : null;
        const theirs = res ? (f.home === wk.team ? res[1] : res[0]) : null;
        list.appendChild(wkFixtureRow(`Speelronde ${f.md + 1}`, opp, mine, theirs, null));
    });
    Object.keys(wk.ko).map(Number).sort((a, b) => a - b).forEach(m => {
        const k = wk.ko[m];
        if (k.a !== wk.team && k.b !== wk.team) return;
        const info = wkMatchInfo(m);
        const meA = k.a === wk.team;
        const opp = meA ? k.b : k.a;
        if (!opp) return;
        const pens = k.pens ? (meA ? k.pens : [k.pens[1], k.pens[0]]) : null;
        list.appendChild(wkFixtureRow(WK_ROUND_NAME[info.round], opp,
            k.w ? (meA ? k.ga : k.gb) : null, k.w ? (meA ? k.gb : k.ga) : null, pens));
    });

    // the next match, or how it ended
    const next = $('wk-next');
    next.replaceChildren();
    const f = wkMyFixture();
    if (f) {
        const opp = wkOpponent(f);
        next.append(
            wkEl('p', 'wk-next__label', f.kind === 'group' ? `Groep ${L}, speelronde ${f.md + 1}` : WK_ROUND_NAME[f.round]),
            wkEl('p', 'wk-next__vs', 'tegen'),
        );
        const opponent = wkEl('div', 'wk-next__team');
        opponent.append(wkFlag(opp, 'flag flag--big'), wkEl('span', 'wk-next__name', WK_TEAMS[opp].name));
        next.appendChild(opponent);
        if (f.kind === 'ko') {
            const v = WK_VENUES[f.city];
            const photo = wkVenuePhoto(f.city);
            if (photo) next.insertBefore(photo, next.firstChild);
            next.appendChild(wkEl('p', 'wk-next__city', `In ${v ? v.stadium + ', ' : ''}${f.city}. Gelijk na 90 seconden: verlenging, wie scoort wint, anders strafschoppen.`));
        }
        const play = wkEl('button', 'btn wk-next__play', 'Speel de wedstrijd');
        play.type = 'button';
        play.addEventListener('click', wkStartMatch);
        next.appendChild(play);
    } else if (wk.out) {
        const champ = wkChampion();
        const texts = {
            champion: 'Wereldkampioen!',
            runnerup: 'Verloren in de finale',
            third: 'Derde van de wereld',
            fourth: 'Vierde van de wereld',
            group: 'Uitgeschakeld in de groep',
            r32: 'Uitgeschakeld in de laatste 32',
            r16: 'Uitgeschakeld in de achtste finale',
            qf: 'Uitgeschakeld in de kwartfinale',
        };
        next.classList.toggle('is-champion', wk.out === 'champion');
        if (wk.out === 'champion') {
            const photo = wkVenuePhoto('New York New Jersey', 'MetLife Stadium, New York New Jersey: de finale van 19 juli 2026.');
            if (photo) next.appendChild(photo);
        }
        next.appendChild(wkEl('p', 'wk-next__result', texts[wk.out] || 'Klaar'));
        if (champ) {
            const c = wkEl('div', 'wk-next__team');
            c.append(wkFlag(champ, 'flag flag--big'), wkEl('span', 'wk-next__name', `Wereldkampioen: ${WK_TEAMS[champ].name}`));
            next.appendChild(c);
        }
        const again = wkEl('button', 'btn wk-next__play', 'Nieuw WK');
        again.type = 'button';
        again.addEventListener('click', openWk);
        next.appendChild(again);
    }

    // every group, for a look at the rest of the tournament
    const all = $('wk-all');
    all.replaceChildren();
    WK_LETTERS.forEach(G => {
        const box = wkEl('div', 'wk-all__group');
        box.appendChild(wkEl('h3', 'wk-all__name', `Groep ${G}`));
        const t = wkEl('table', 'wk-table wk-table--small');
        wkFillTable(t, G, false);
        box.appendChild(t);
        all.appendChild(box);
    });
}

function wkFixtureRow(label, opp, mine, theirs, pens) {
    const li = wkEl('li', 'wk-fixture');
    li.append(wkEl('span', 'wk-fixture__round', label), wkFlag(opp), wkEl('span', 'wk-fixture__opp', WK_TEAMS[opp].name));
    let score = 'nog te spelen', cls = 'wk-fixture__score';
    if (mine !== null) {
        score = `${mine}-${theirs}` + (pens ? ` (${pens[0]}-${pens[1]} str.)` : '');
        const won = mine > theirs || (pens && pens[0] > pens[1]);
        const lost = mine < theirs || (pens && pens[0] < pens[1]);
        cls += won ? ' is-won' : lost ? ' is-lost' : ' is-draw';
    }
    li.appendChild(wkEl('span', cls, score));
    return li;
}

function wkFillTable(table, L, full) {
    table.replaceChildren();
    const head = wkEl('tr');
    (full ? ['', 'Land', 'GS', 'W', 'G', 'V', 'DS', 'PT'] : ['', 'Land', 'DS', 'PT']).forEach((h, i) => {
        const th = wkEl('th', i < 2 ? '' : 'num', h);
        th.scope = 'col';
        head.appendChild(th);
    });
    const thead = wkEl('thead'); thead.appendChild(head);
    const tbody = wkEl('tbody');
    const thirdsThrough = wk && wk.thirds ? wk.thirds : [];
    wkStandings(L).forEach((r, i) => {
        const tr = wkEl('tr');
        if (r.code === wk.team) tr.classList.add('is-me');
        if (wk.md >= 3 && (i < 2 || (i === 2 && thirdsThrough.includes(r.code)))) tr.classList.add('is-through');
        const name = wkEl('td', 'wk-table__team');
        name.append(wkFlag(r.code), wkEl('span', '', full ? WK_TEAMS[r.code].name : r.code));
        const gd = r.gf - r.ga;
        const cells = full ? [r.p, r.w, r.d, r.l, (gd > 0 ? '+' : '') + gd, r.pts] : [(gd > 0 ? '+' : '') + gd, r.pts];
        tr.append(wkEl('td', 'wk-table__pos', String(i + 1)), name, ...cells.map(v => wkEl('td', 'num', String(v))));
        tbody.appendChild(tr);
    });
    table.append(thead, tbody);
}

function bindWk() {
    wkShowEmblems();
    $('launch-wk')?.addEventListener('click', openWk);
    $('wk-start')?.addEventListener('click', () => {
        if (!wkPick) return;
        wkNew(wkPick, wkPickLevel || 'medium');
        if (typeof PR_STATS !== 'undefined') PR_STATS.wkStart(wkPick, wkPickLevel || 'medium');
        gotoScreen('wkhub');
        wkRenderHub();
    });
    $('wk-resume-go')?.addEventListener('click', () => { gotoScreen('wkhub'); wkRenderHub(); });
    document.querySelectorAll('#wk-level .seg__btn').forEach(b => {
        b.addEventListener('click', () => { wkPickLevel = b.dataset.level; wkRenderPick(); });
    });
    $('wk-hub-back')?.addEventListener('click', () => gotoScreen('launch', { replace: true }));
    $('wk-continue')?.addEventListener('click', (e) => { e.currentTarget.blur(); wkContinue(); });
    wkLoad();
}

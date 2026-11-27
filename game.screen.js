// =====================================================
// PITCH ROYALE — live stadium screen
// The big screens in a stadium model (a node named 'StadiumScreens') show the
// match: the clock in a purple block, the score in an orange and a white box,
// the club logo on the left (img/logo2.png) and
// the CPU shield on the right. A model can also have a small score panel in
// the band between its tiers ('StadiumRibbonScore'): the score in an orange
// and a white box, the clock on purple. Both are canvases used as textures,
// redrawn only when the clock or the score changes.
// A stadium with screen: 'wk' in the catalog (MetLife) shows the World Cup
// layout instead: each team's panel in its colour with its flag and score,
// in the middle the clock on navy with gold rays and a gold band.
// screen: 'kuip' (De Kuip) is one long red board: the home logo, the score,
// the CPU shield, a white end with DE KUIP and the clock in a dark tab on top.
// The home logo is the file the catalog names (screenLogo); without it a white
// disc with the club's short name.
// screen: 'campin' (El Campín) is the big screen of Bogotá: the two teams'
// colours running into each other, a plain shield for each with its short
// name, the score '0 : 0' in the middle and the clock under it.
// screen: 'arena' (Johan Cruijff ArenA) is the ArenA's screen: an almost black
// board, the clock small at the top, the home logo in a white disc on the left
// (the file the catalog names: screenLogo), the away side's disc on the right,
// the score in square figures with round corners and a long bar between them.
// screen: 'montjuic' (Estadi Olímpic Lluís Companys) is the screen over the
// south curve, as on the photo of a Clásico there: Barça's half blue with its
// crest, the other half red with Real Madrid's, the scores big by the seam,
// the minutes of the goals under them and the clock small at the bottom.
// screen: 'bernabeu' (Santiago Bernabéu) is the 360-degree ring round the
// roof's opening, on royal blue as on the photos of a Clásico there: on each
// side the clock, Real Madrid's crest, REAL MADRID C.F. and its score, the
// match in the middle as on television (the match camera's own picture), the
// score, F.C. BARCELONA and its crest, and the clock again; the corners
// only the clock (media/hud/realmadrid.png, media/hud/fcbarcelona.png).
// screen: 'janbreydel' (Jan Breydelstadion) is the scoreboard in the open
// south-west corner, as on the photos: adverts over most of it, changing
// every 8 seconds, and under them a blue bar: Club Brugge's badge, its score,
// an arrow, the clock, an arrow, the other score and Cercle's badge
// (media/hud/clubbrugge.png, cerclebrugge.png).
// screen: 'marien' (Stade Joseph Marien) is the scoreboard over the north-east
// end, as on the photo from the seats under it: almost black, the scores
// either side of the clock along the top, Union's crest on the left and the
// other side's on the right with VS between, a teal stripe down the left edge
// and a blue one by each crest (media/hud/union.png, clubbrugge.png).
// screen: 'philips' (Philips Stadion) is each of the four screens at the ends
// of the long stands, as on the photo of a match there: orange-red, a bar
// along the top (a white box with the club's words, a black one with PSV and
// the clock in a white box), PSV's crest in a white disc on the left, the
// score big in white across the middle with a thin light line slanting
// through the board, the other side's crest in a white disc on the right
// (img/psvlogo.svg, img/logo3.png).
// screen: 'centenario' (Estadio Centenario) is the LED screen on its table over
// the Colombes, as on the photo of the Libertadores final there: a dark board
// with a warm red and orange haze and golden arcs down both edges, along the
// top MONUMENTO AL FÚTBOL MUNDIAL - ESTADIO CENTENARIO, the golden cup in the
// middle, the home crest left and the other right, the score '1 x 1' between
// them and the clock under it (media/hud/boca.png, media/hud/millonarios.png).
// =====================================================

const STADIUM_SCREEN = (() => {
    // Layouts are drawn in these sizes (16:9 and the band's 4.4:1) and squeezed
    // onto power-of-two canvases, which the GPU can shrink smoothly (mipmaps):
    // without that a far screen breaks up into a few flickering pixels.
    const W = 1024, H = 576;                       // the big screens are 16:9
    const CW = 1024, CH = 512, RCH = 256;
    const PURPLE = '#5c2db4', ORANGE = '#e88034', WHITE = '#f6f4f0', INK = '#282234', BLACK = '#08080c';
    const SERIF = '"Times New Roman", Times, serif';
    let canvas = null, ctx = null, texture = null, last = '';
    const RW = 1024, RH = 234;                     // the band panel: 4.2 x 0.96 m
    let rCanvas = null, rCtx = null, rTexture = null;
    let logo = null;                               // the club logo, once loaded

    const img = new Image();
    img.onload = () => { logo = img; last = ''; redraw(); };
    img.src = 'img/logo2.png';                     // the official club logo; missing file: the left stays black

    // ---- the World Cup layout (screens of 22 x 8 m) ----
    const WKW = 1100, WKH = 400;
    const WKF = '"Saira Condensed", "Barlow Condensed", "Arial Narrow", sans-serif';
    let wCanvas = null, wCtx = null, wTexture = null;
    const flags = {};                              // flag file -> Image, once loaded
    let fontReady = false;
    if (typeof document !== 'undefined' && document.fonts && document.fonts.load) {
        document.fonts.load(`900 120px "Saira Condensed"`).then(() => { fontReady = true; last = ''; redraw(); }).catch(() => {});
    }
    // without a World Cup match: on the test page Spain - Argentina, as on the photo
    const DEMO = [{ code: 'ESP', color: '#c60b1e', flag: 'es' }, { code: 'ARG', color: '#75aadb', flag: 'ar' }];
    const hex = (c) => typeof c === 'number' ? '#' + c.toString(16).padStart(6, '0') : c;
    function wkTeams() {
        if (typeof STATE !== 'undefined' && STATE.wkMatch && typeof WK_TEAMS !== 'undefined') {
            return [STATE.wkMatch.me, STATE.wkMatch.opp].map(code => ({ code, color: WK_TEAMS[code].home[0], flag: WK_TEAMS[code].flag }));
        }
        if (typeof STATE !== 'undefined' && STATE.screen === 'playing' && typeof KIT !== 'undefined') {
            const codes = typeof hudCodes === 'function' ? hudCodes() : { red: 'RED', blue: 'BLU' };
            return [{ code: codes.red, color: hex(KIT[1].shirt), flag: null }, { code: codes.blue, color: hex(KIT[2].shirt), flag: null }];
        }
        return DEMO;
    }
    function flagImage(name) {
        if (!name) return null;
        if (!flags[name]) {
            const im = new Image();
            im.onload = () => { im.ready = true; last = ''; redraw(); };
            im.src = `media/flags/${name}.svg`;
            flags[name] = im;
        }
        return flags[name].ready ? flags[name] : null;
    }
    const lightness = (c) => {
        const n = parseInt(String(c).replace('#', ''), 16);
        return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
    };

    function wkText(c, str, cx, cy, size, color) {
        c.font = `900 ${size}px ${WKF}`;
        c.fillStyle = color;
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText(str, cx, cy);
    }
    // the score: wide, bold figures, the zero with a slash through it as on the
    // World Cup screens
    function wkScore(c, str, cx, cy, size, color) {
        const wide = 1.35;
        c.save();
        c.translate(cx, cy);
        c.scale(wide, 1);
        wkText(c, str, 0, 0, size, color);
        const total = c.measureText(str).width;
        let x = -total / 2;
        for (const ch of str) {
            const w = c.measureText(ch).width;
            if (ch === '0') {
                c.strokeStyle = color;
                c.lineWidth = size * 0.075;
                c.lineCap = 'butt';
                c.beginPath();
                c.moveTo(x + w * 0.34, size * 0.17);
                c.lineTo(x + w * 0.66, -size * 0.17);
                c.stroke();
            }
            x += w;
        }
        c.restore();
    }
    function roundRect(c, x, y, w, h, r) {
        c.beginPath();
        c.moveTo(x + r, y); c.lineTo(x + w - r, y); c.quadraticCurveTo(x + w, y, x + w, y + r);
        c.lineTo(x + w, y + h - r); c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        c.lineTo(x + r, y + h); c.quadraticCurveTo(x, y + h, x, y + h - r);
        c.lineTo(x, y + r); c.quadraticCurveTo(x, y, x + r, y);
        c.closePath();
    }
    function wkPanel(c, x0, w, team, score) {
        c.fillStyle = team.color;
        c.fillRect(x0, 0, w, WKH);
        const shade = c.createLinearGradient(0, 0, 0, WKH);
        shade.addColorStop(0, 'rgba(255,255,255,0.10)');
        shade.addColorStop(1, 'rgba(0,0,0,0.20)');
        c.fillStyle = shade;
        c.fillRect(x0, 0, w, WKH);
        const ink = lightness(team.color) > 0.62 ? '#0d1a4f' : '#ffffff';
        // the flag in a white frame, or the team code when there is none
        const fw = 168, fh = 112, fx = x0 + w / 2 - fw / 2, fy = 30;
        const im = flagImage(team.flag);
        if (im) {
            c.save();
            roundRect(c, fx, fy, fw, fh, 10);
            c.clip();
            const k = Math.max(fw / (im.width || 3), fh / (im.height || 2));
            const iw = (im.width || 3) * k, ih = (im.height || 2) * k;
            c.drawImage(im, fx + fw / 2 - iw / 2, fy + fh / 2 - ih / 2, iw, ih);
            // a soft light from the top and the gold edge on its left, like the waving flags on the photo
            const sheen = c.createLinearGradient(fx, fy, fx + fw, fy + fh);
            sheen.addColorStop(0, 'rgba(255,255,255,0.22)');
            sheen.addColorStop(0.5, 'rgba(255,255,255,0)');
            sheen.addColorStop(1, 'rgba(0,0,0,0.18)');
            c.fillStyle = sheen;
            c.fillRect(fx, fy, fw, fh);
            c.restore();
            c.fillStyle = '#d9a640';
            c.fillRect(fx - 7, fy + 6, 7, fh - 12);
        } else {
            wkText(c, team.code, x0 + w / 2, fy + fh / 2, 84, ink);
        }
        wkScore(c, String(score), x0 + w / 2, 272, 200, ink);
    }
    // the line over the clock: THE FINAL only in the final, otherwise the round
    // the screens speak English, like the real ones
    const ROUND_EN = { r32: 'ROUND OF 32', r16: 'ROUND OF 16', qf: 'QUARTER-FINAL', sf: 'SEMI-FINAL', bronze: 'THIRD PLACE', final: 'THE FINAL' };
    function wkHeading() {
        const m = typeof STATE !== 'undefined' && STATE.wkMatch;
        if (!m || !m.f) return 'METLIFE STADIUM';
        if (m.f.kind === 'group') return 'GROUP ' + (typeof wkGroupOf === 'function' ? wkGroupOf(m.me) : '');
        return ROUND_EN[m.f.round] || 'WORLD CUP 26';
    }
    function wkCentre(c, x0, w, clock) {
        const bg = c.createLinearGradient(0, 0, 0, WKH);
        bg.addColorStop(0, '#16278a'); bg.addColorStop(1, '#0a1350');
        c.fillStyle = bg;
        c.fillRect(x0, 0, w, WKH);
        // gold rays bursting from behind the clock (the same every time)
        c.save();
        c.beginPath(); c.rect(x0, 0, w, WKH); c.clip();
        const cx = x0 + w / 2, cy = 190;
        let seed = 7;
        const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
        c.lineCap = 'round';
        for (let i = 0; i < 46; i++) {
            const a = (i / 46) * Math.PI * 2 + rnd() * 0.08;
            const r0 = 150 + rnd() * 70, r1 = r0 + 40 + rnd() * 90;
            c.strokeStyle = `rgba(${200 + rnd() * 40 | 0}, ${150 + rnd() * 40 | 0}, ${60 + rnd() * 30 | 0}, ${0.55 + rnd() * 0.35})`;
            c.lineWidth = 7 + rnd() * 7;
            c.beginPath();
            c.moveTo(cx + Math.cos(a) * r0 * 1.25, cy + Math.sin(a) * r0 * 0.85);
            c.lineTo(cx + Math.cos(a) * r1 * 1.25, cy + Math.sin(a) * r1 * 0.85);
            c.stroke();
        }
        c.restore();
        wkText(c, wkHeading(), cx, 62, 62, '#ffffff');
        wkText(c, clock, cx, 182, 188, '#ffffff');
        // the gold band
        const by = 292, bh = 66, bx0 = x0 + 70, bx1 = x0 + w - 70;
        const gold = c.createLinearGradient(bx0, 0, bx1, 0);
        gold.addColorStop(0, '#a8761f'); gold.addColorStop(0.5, '#e9bd5b'); gold.addColorStop(1, '#a8761f');
        c.fillStyle = gold;
        c.beginPath();
        c.moveTo(bx0 + 18, by); c.lineTo(bx1, by); c.lineTo(bx1 - 18, by + bh); c.lineTo(bx0, by + bh); c.closePath();
        c.fill();
        wkText(c, 'WORLD CUP 26', cx, by + bh / 2 + 2, 52, '#0d1a4f');
    }
    function drawWk(clock, s1, s2) {
        const c = wCtx, [a, b] = wkTeams();
        c.fillStyle = '#05070f'; c.fillRect(0, 0, WKW, WKH);
        wkPanel(c, 0, 300, a, s1);
        wkCentre(c, 300, 500, clock);
        wkPanel(c, 800, 300, b, s2);
        c.fillStyle = '#05070f';
        c.fillRect(298, 0, 4, WKH); c.fillRect(798, 0, 4, WKH);
        wTexture.needsUpdate = true;
    }

    function ensure() {
        if (canvas) return;
        let aniso = 8;
        try { if (typeof renderer !== 'undefined' && renderer) aniso = renderer.capabilities.getMaxAnisotropy(); } catch (_) {}
        const make = (w, h, sy) => {
            const cv = document.createElement('canvas');
            cv.width = w; cv.height = h;
            const cx = cv.getContext('2d');
            cx.setTransform(1, 0, 0, sy, 0, 0);    // draw in layout units
            const tex = new THREE.CanvasTexture(cv);
            tex.encoding = THREE.sRGBEncoding;
            tex.flipY = false;                     // glTF UVs
            tex.anisotropy = aniso;                // sharp when seen at an angle
            return [cv, cx, tex];
        };
        [canvas, ctx, texture] = make(CW, CH, CH / H);
        [rCanvas, rCtx, rTexture] = make(RW, RCH, RCH / RH);
        [wCanvas, wCtx, wTexture] = make(1024, 512, 512 / WKH);
        wCtx.setTransform(1024 / WKW, 0, 0, 512 / WKH, 0, 0);
        [kCanvas, kCtx, kTexture] = make(1024, 256, 256 / KH);
        [eCanvas, eCtx, eTexture] = make(CW2, CH2, 1);
        [aCanvas, aCtx, aTexture] = make(1024, 512, 512 / AH);
        [mCanvas, mCtx, mTexture] = make(MCW, MCH, 1);
        [bCanvas, bCtx, bTexture] = make(BW, BH, 1);
        [jCanvas, jCtx, jTexture] = make(1024, 1024, 1024 / JH);
        [xCanvas, xCtx, xTexture] = make(1024, 512, 512 / XH);
        [pCanvas, pCtx, pTexture] = make(1024, 512, 512 / PH_);
        [cCanvas, cCtx, cTexture] = make(1024, 512, 512 / CH_);
        cCtx.setTransform(1024 / CW_, 0, 0, 512 / CH_, 0, 0);
        pCtx.setTransform(1024 / PW_, 0, 0, 512 / PH_, 0, 0);
        xCtx.setTransform(1024 / XW, 0, 0, 512 / XH, 0, 0);
        jCtx.setTransform(1024 / JW, 0, 0, 1024 / JH, 0, 0);
        kCtx.setTransform(1024 / KW, 0, 0, 256 / KH, 0, 0);
    }

    // the band panel: [|0][|0][  00:00  ]
    //   left block  black, white figure, a thin stripe on its left: purple over white
    //   right block white, black figure, a thin stripe on its left: blue over yellow
    //   the clock   white on purple
    function drawRibbon(clock, s1, s2) {
        const c = rCtx, sq = RH, gap = 6, stripe = 16;
        c.fillStyle = BLACK; c.fillRect(0, 0, RW, RH);
        c.fillStyle = '#111114'; c.fillRect(0, 0, sq, RH);
        c.fillStyle = WHITE; c.fillRect(sq + gap, 0, sq, RH);
        c.fillStyle = PURPLE; c.fillRect(2 * (sq + gap), 0, RW - 2 * (sq + gap), RH);
        const bar = (x, top, bottom) => {
            c.fillStyle = top; c.fillRect(x, 0, stripe, RH / 2);
            c.fillStyle = bottom; c.fillRect(x, RH / 2, stripe, RH / 2);
        };
        bar(0, PURPLE, WHITE);
        bar(sq + gap, '#1f5dff', '#f2c230');
        const text = (str, cx, size, color) => {
            c.save();
            c.font = `bold ${size}px ${SERIF}`;
            c.fillStyle = color;
            c.textAlign = 'center';
            c.textBaseline = 'alphabetic';
            const capH = c.measureText('0').actualBoundingBoxAscent || size * 0.66;
            c.translate(cx, (RH + capH) / 2);
            c.scale(0.8, 1);
            c.fillText(str, 0, 0);
            c.restore();
        };
        text(String(s1), stripe + (sq - stripe) / 2, 190, WHITE);
        text(String(s2), sq + gap + stripe + (sq - stripe) / 2, 190, '#08080c');
        text(clock, 2 * (sq + gap) + (RW - 2 * (sq + gap)) / 2, 210, WHITE);
        rTexture.needsUpdate = true;
    }

    // the screen's lettering: Times Bold, narrowed and set tight, centred in a box
    function narrow(text, cx, top, size, color) {
        ctx.save();
        ctx.font = `bold ${size}px ${SERIF}`;
        ctx.fillStyle = color;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        const m = ctx.measureText('0');
        const capH = m.actualBoundingBoxAscent || size * 0.66;
        ctx.translate(cx, top + capH);
        ctx.scale(0.8, 1);
        if ('letterSpacing' in ctx) ctx.letterSpacing = `${-size * 0.02}px`;
        ctx.fillText(text, 0, 0);
        ctx.restore();
        return capH;
    }

    function digitsIn(text, x0, y0, x1, y1, size, color) {
        ctx.font = `bold ${size}px ${SERIF}`;
        const capH = ctx.measureText('0').actualBoundingBoxAscent || size * 0.66;
        narrow(text, (x0 + x1) / 2, (y0 + y1 - capH) / 2, size, color);
    }

    function shieldPath(cx, cy, w, h, c = ctx) {
        const r = w / 2, yTop = cy - h / 2, yMid = cy + h * 0.05;
        c.beginPath();
        c.moveTo(cx - r, yTop);
        c.lineTo(cx + r, yTop);
        c.lineTo(cx + r, yMid);
        c.ellipse(cx, yMid, r, h * 0.45, 0, 0, Math.PI);
        c.closePath();
    }

    function cpuShield(cx, cy, s, c = ctx) {
        shieldPath(cx, cy, 147 * s, 186 * s, c); c.fillStyle = '#eceef2'; c.fill();
        shieldPath(cx, cy, 128 * s, 166 * s, c); c.fillStyle = '#1c2c5c'; c.fill();
        c.fillStyle = '#eceef2';
        c.fillRect(cx - 64 * s, cy - 45 * s, 128 * s, 19 * s);
        c.font = `bold ${42 * s}px Arial, Helvetica, sans-serif`;
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('CPU', cx, cy + 16 * s);
    }

    // ---- De Kuip: the long red board (16:3.2, drawn 1200 x 240) ----
    const KW = 1200, KH = 240, KTOP = 22, KSPLIT = 905;
    const KF = '"Barlow Semi Condensed", "Arial Narrow", sans-serif';
    const KRED = '#e3302a', KINK = '#2a2326', KWHITE = '#f4f2ee';
    let kCanvas = null, kCtx = null, kTexture = null;
    let kuipFont = false, kuipLogo = null, kuipLogoSrc = null;
    if (typeof document !== 'undefined' && document.fonts && document.fonts.load) {
        document.fonts.load(`700 120px "Barlow Semi Condensed"`).then(() => { kuipFont = true; last = ''; redraw(); }).catch(() => {});
    }
    function loadKuipLogo(src) {
        if (!src || src === kuipLogoSrc) return;
        kuipLogoSrc = src;
        const im = new Image();
        im.onload = () => { kuipLogo = im; last = ''; redraw(); };
        im.src = src;                              // missing file: the white disc stays
    }
    // ---- El Campín: the big screen (2:1) ----
    const CW2 = 1024, CH2 = 512;
    const CF = '"Montserrat", "Arial", sans-serif';
    let eCanvas = null, eCtx = null, eTexture = null, campinFont = false;
    if (typeof document !== 'undefined' && document.fonts && document.fonts.load) {
        Promise.all([document.fonts.load(`500 150px "Montserrat"`), document.fonts.load(`600 80px "Montserrat"`)])
            .then(() => { campinFont = true; last = ''; redraw(); }).catch(() => {});
    }
    function campinTeams() {
        if (typeof STATE !== 'undefined' && STATE.screen === 'playing' && typeof KIT !== 'undefined') {
            const codes = typeof hudCodes === 'function' ? hudCodes() : { red: 'RED', blue: 'BLU' };
            return [{ code: codes.red, color: hex(KIT[1].shirt) }, { code: codes.blue, color: hex(KIT[2].shirt) }];
        }
        return [{ code: 'BOG', color: '#1d5cd6' }, { code: 'CPU', color: '#12a150' }];   // blue against green, as on the photo
    }
    const mix = (c1, c2, t) => {
        const a = parseInt(c1.slice(1), 16), b = parseInt(c2.slice(1), 16);
        const ch = (sh) => Math.round(((a >> sh) & 255) * (1 - t) + ((b >> sh) & 255) * t);
        return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
    };
    function drawCampin(clock, s1, s2) {
        const c = eCtx, [ta, tb] = campinTeams();
        c.fillStyle = '#08080a'; c.fillRect(0, 0, CW2, CH2);
        const x0 = 60, x1 = CW2 - 60, y0 = 50, y1 = CH2 - 50;
        const g = c.createLinearGradient(x0, 0, x1, 0);
        g.addColorStop(0, ta.color); g.addColorStop(0.3, ta.color);
        g.addColorStop(0.5, mix(mix(ta.color, tb.color, 0.5), '#000000', 0.55));     // darker where they meet
        g.addColorStop(0.7, tb.color); g.addColorStop(1, tb.color);
        c.fillStyle = g; c.fillRect(x0, y0, x1 - x0, y1 - y0);
        const shade = c.createLinearGradient(0, y0, 0, y1);
        shade.addColorStop(0, 'rgba(255,255,255,0.08)'); shade.addColorStop(1, 'rgba(0,0,0,0.25)');
        c.fillStyle = shade; c.fillRect(x0, y0, x1 - x0, y1 - y0);
        const shieldAt = (cx, cy, col, code) => {
            const path = (k) => {
                c.beginPath();
                c.moveTo(cx - 70 * k, cy - 85 * k); c.lineTo(cx + 70 * k, cy - 85 * k); c.lineTo(cx + 70 * k, cy + 10 * k);
                c.lineTo(cx, cy + 90 * k); c.lineTo(cx - 70 * k, cy + 10 * k); c.closePath();
            };
            path(1); c.fillStyle = '#ffffff'; c.fill();
            path(0.83); c.fillStyle = col; c.fill();
            c.font = `700 44px ${CF}`; c.fillStyle = '#ffffff'; c.textAlign = 'center'; c.textBaseline = 'middle';
            c.fillText(code, cx, cy - 6);
        };
        shieldAt(230, 230, ta.color, ta.code);
        shieldAt(794, 230, tb.color, tb.code);
        c.fillStyle = '#ffffff'; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.font = `500 150px ${CF}`;
        c.fillText(`${s1} : ${s2}`, 512, 236);
        c.font = `600 80px ${CF}`;
        c.fillText(clock, 512, 372);
        eTexture.needsUpdate = true;
    }

    // ---- the Johan Cruijff ArenA: the screen over each end (14.5 x 7.7 m, drawn 1024 x 541) ----
    // As on the photos of the screen in a match: an almost black board, the
    // clock small at the top, the home logo in a white disc on the left, the
    // away side's badge on the right, between them the score in the screen's
    // own figures (square with round corners, a slash through the 0) with a
    // long bar between them. The lower part of the board stays empty.
    const AW = 1024, AH = 541;
    let aCanvas = null, aCtx = null, aTexture = null;
    let arenaLogo = null, arenaLogoSrc = null;
    function loadArenaLogo(src) {
        if (!src || src === arenaLogoSrc) return;
        arenaLogoSrc = src;
        const im = new Image();
        im.onload = () => { arenaLogo = im; last = ''; redraw(); };
        im.src = src;                              // missing file: a white disc with the short name
    }
    // for now the away side shows the game's own club badge (a test), as the
    // screen shows the visitors' crest; without the file a disc in their colour
    const ARENA_AWAY = 'img/logo2.png';
    let arenaAway = null;
    function loadArenaAway() {
        if (arenaAway || typeof Image === 'undefined') return;
        const im = new Image();
        im.onload = () => { arenaAway = im; last = ''; redraw(); };
        im.src = ARENA_AWAY;
    }
    // the figures as strokes in a unit box (x right, y down); the corners rounded
    const ARENA_GLYPHS = {
        '0': [[[0, 0], [1, 0], [1, 1], [0, 1], 'z']],
        '1': [[[0.18, 0.2], [0.62, 0], [0.62, 1]]],
        '2': [[[0, 0], [1, 0], [1, 0.5], [0, 0.5], [0, 1], [1, 1]]],
        '3': [[[0, 0], [1, 0], [1, 1], [0, 1]], [[0.3, 0.5], [1, 0.5]]],
        '4': [[[0.78, 1], [0.78, 0], [0, 0.66], [1, 0.66]]],
        '5': [[[1, 0], [0, 0], [0, 0.48], [1, 0.48], [1, 1], [0, 1]]],
        '6': [[[1, 0], [0, 0], [0, 1], [1, 1], [1, 0.5], [0, 0.5]]],
        '7': [[[0, 0], [1, 0], [1, 0.28], [0.42, 1]]],
        '8': [[[0, 0], [1, 0], [1, 1], [0, 1], 'z'], [[0, 0.5], [1, 0.5]]],
        '9': [[[1, 0.5], [0, 0.5], [0, 0], [1, 0], [1, 1], [0, 1]]],
    };
    function arenaFigure(c, ch, x, y, w, h, lw) {
        const g = ARENA_GLYPHS[ch];
        if (!g) return;
        const ix = x + lw / 2, iy = y + lw / 2, iw = w - lw, ih = h - lw;
        const r = Math.min(iw, ih) * 0.42;
        c.lineWidth = lw; c.lineCap = 'round'; c.lineJoin = 'round';
        g.forEach((line) => {
            const closed = line[line.length - 1] === 'z';
            const pts = (closed ? line.slice(0, -1) : line).map(([u, v]) => [ix + u * iw, iy + v * ih]);
            c.beginPath();
            if (closed) {
                const n = pts.length, mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
                const s0 = mid(pts[n - 1], pts[0]);
                c.moveTo(s0[0], s0[1]);
                for (let k = 0; k < n; k++) c.arcTo(pts[k][0], pts[k][1], pts[(k + 1) % n][0], pts[(k + 1) % n][1], r);
                c.closePath();
            } else {
                c.moveTo(pts[0][0], pts[0][1]);
                for (let k = 1; k < pts.length - 1; k++) c.arcTo(pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1], r);
                c.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]);
            }
            c.stroke();
        });
        if (ch === '0') {                                   // the slash through the 0, thinner
            c.lineWidth = lw * 0.62;
            c.beginPath();
            c.moveTo(ix + iw * 0.3, iy + ih * 0.7);
            c.lineTo(ix + iw * 0.7, iy + ih * 0.3);
            c.stroke();
        }
    }
    // a string of figures (and ':'), centred on cx
    function arenaString(c, str, cx, y, h, lw, aspect, gap) {
        const w = h * aspect;
        const widths = [...str].map(ch => ch === ':' ? h * 0.22 : w);
        const total = widths.reduce((a, b) => a + b, 0) + gap * (str.length - 1);
        let x = cx - total / 2;
        [...str].forEach((ch, k) => {
            if (ch === ':') {
                const d = lw * 1.1;
                c.fillRect(x + widths[k] / 2 - d / 2, y + h * 0.27 - d / 2, d, d);
                c.fillRect(x + widths[k] / 2 - d / 2, y + h * 0.73 - d / 2, d, d);
            } else {
                arenaFigure(c, ch, x, y, w, h, lw);
            }
            x += widths[k] + gap;
        });
    }
    function drawArena(clock, s1, s2) {
        const c = aCtx;
        // in a match the two sides; on the test page Ajax against the CPU
        const playing = typeof STATE !== 'undefined' && STATE.screen === 'playing';
        const [ta, tb] = playing ? campinTeams() : [{ code: 'AJA', color: '#d2122e' }, { code: 'CPU', color: '#1c2c5c' }];
        c.fillStyle = '#1b1c1f'; c.fillRect(0, 0, AW, AH);
        c.fillStyle = '#f2f2f2'; c.strokeStyle = '#f2f2f2';
        // the clock, small at the top
        arenaString(c, clock, AW / 2, 66, 46, 7, 0.62, 7);
        // a badge each side: the home logo in a white disc, the away side a disc in its colour
        const R = 88, BY = 262;
        const badge = (cx, team, img) => {
            if (img && img === arenaAway) {                 // a crest as it is, no disc, as on the photos
                const k = Math.min(2.1 * R / img.width, 2.1 * R / img.height);
                c.drawImage(img, cx - img.width * k / 2, BY - img.height * k / 2, img.width * k, img.height * k);
                return;
            }
            c.save();
            c.beginPath(); c.arc(cx, BY, R, 0, Math.PI * 2); c.closePath();
            c.fillStyle = '#f4f4f4'; c.fill();
            if (img) {
                c.clip();
                const k = (2 * R) / Math.min(img.width, img.height) * 1.02;
                c.drawImage(img, cx - img.width * k / 2, BY - img.height * k / 2, img.width * k, img.height * k);
            } else {
                c.fillStyle = team.color;
                c.beginPath(); c.arc(cx, BY, R - 12, 0, Math.PI * 2); c.fill();
                c.fillStyle = lightness(team.color) > 0.62 ? '#1b1c1f' : '#f4f4f4';
                c.font = `700 50px ${CF}`; c.textAlign = 'center'; c.textBaseline = 'middle';
                c.fillText(team.code, cx, BY + 3);
            }
            c.restore();
        };
        badge(146, ta, arenaLogo);
        badge(AW - 146, tb, arenaAway);
        // the score: the figures and the long bar between them
        c.fillStyle = '#f2f2f2'; c.strokeStyle = '#f2f2f2';
        const FH = 176, FY = BY - FH / 2, LW = 25;
        arenaString(c, String(s1), AW / 2 - 168, FY, FH, LW, 0.46, 14);
        arenaString(c, String(s2), AW / 2 + 168, FY, FH, LW, 0.46, 14);
        c.lineCap = 'round'; c.lineWidth = 22;
        c.beginPath(); c.moveTo(AW / 2 - 62, BY); c.lineTo(AW / 2 + 62, BY); c.stroke();
        aTexture.needsUpdate = true;
    }

    // ---- Montjuïc: the screen over the south curve (1000 x 690 on a 1024 x 512 canvas; 11 x 7.6 m) ----
    // as on the photo of a Clásico there: Barça's half blue, the other red,
    // the crests outside, the two scores big by the seam, under each score
    // the minutes of that side's goals; the match clock small at the bottom
    const MW = 1000, MH = 690, MCW = 1024, MCH = 512;
    const M_FONT = '"Barlow Condensed", "Arial Narrow", sans-serif';
    let mCanvas = null, mCtx = null, mTexture = null;
    let mGoals = [[], []], mPrev = [0, 0];
    // the minute of each goal, from the clock when a score goes up
    function montjuicGoals(clock, s1, s2) {
        const now = [s1, s2];
        if (s1 + s2 === 0) mGoals = [[], []];
        // a match lasts STATE.gameDuration seconds (90): played out over 90 minutes
        const [mm, ss] = clock.split(':').map((v) => parseInt(v, 10) || 0);
        const dur = (typeof STATE !== 'undefined' && STATE.gameDuration) || 90;
        const min = Math.max(1, Math.min(120, Math.ceil((mm * 60 + ss) * 90 / dur)));
        for (let k = 0; k < 2; k++) {
            if (now[k] > mPrev[k]) for (let i = mPrev[k]; i < now[k]; i++) mGoals[k].push(min);
            else if (now[k] < mPrev[k]) mGoals[k].length = Math.min(mGoals[k].length, now[k]);
        }
        mPrev = now;
    }
    function drawMontjuic(clock, s1, s2) {
        const c = mCtx, SEAM = 497;
        c.setTransform(MCW / MW, 0, 0, MCH / MH, 0, 0);
        c.fillStyle = '#4a66dc'; c.fillRect(0, 0, SEAM, MH);
        c.fillStyle = '#e65f59'; c.fillRect(SEAM, 0, MW - SEAM, MH);
        // the LED rows, faint
        c.fillStyle = 'rgba(0,0,0,0.05)';
        for (let y = 0; y < MH; y += 6) c.fillRect(0, y, MW, 2);
        const crest = (im, x, y, box) => {
            if (!im) return;
            const k = Math.min(box / im.width, box / im.height);
            c.drawImage(im, x - im.width * k / 2, y - im.height * k / 2, im.width * k, im.height * k);
        };
        crest(fcbLogo, 153, 160, 175);
        crest(rmLogo, 845, 160, 160);
        c.fillStyle = '#f7f6f4'; c.textBaseline = 'middle';
        c.font = `700 340px ${M_FONT}`; c.textAlign = 'center';
        c.fillText(String(s1), 390, 160);
        c.fillText(String(s2), 618, 160);
        // the goals: one line each, the fourth and later run on the last line
        const lines = (mins) => {
            const out = mins.slice(0, 2).map((m) => `GOL ${m}'`);
            if (mins.length > 2) out.push('GOL ' + mins.slice(2).map((m) => `${m}'`).join(' '));
            return out;
        };
        c.font = `700 40px ${M_FONT}`;
        c.textAlign = 'right';
        lines(mGoals[0]).forEach((t, i) => c.fillText(t, 440, 358 + i * 84, 400));
        c.textAlign = 'left';
        lines(mGoals[1]).forEach((t, i) => c.fillText(t, 560, 358 + i * 84, 400));
        c.font = `600 46px ${M_FONT}`; c.textAlign = 'center';
        c.fillText(clock, SEAM, 640);
        c.setTransform(1, 0, 0, 1, 0, 0);
        mTexture.needsUpdate = true;
    }

    // ---- Jan Breydel: the scoreboard in the south-west corner (1000 x 680 on a 1024 x 1024 canvas; 10 x 6.8 m) ----
    const JW = 1000, JH = 680, J_BAR = 560, J_FONT = '"Barlow Condensed", "Arial Narrow", sans-serif';
    const J_SERIF = 'Georgia, "Times New Roman", serif';
    let jCanvas = null, jCtx = null, jTexture = null, cbLogo = null, ceLogo = null;
    function loadJanLogos() {
        if (typeof Image === 'undefined' || cbLogo) return;
        const load = (src, set) => { const im = new Image(); im.onload = () => { set(im); last = ''; redraw(); }; im.src = src; };
        load('media/hud/clubbrugge.png', (im) => { cbLogo = im; });
        load('media/hud/cerclebrugge.png', (im) => { ceLogo = im; });
    }
    function janAd() { return Math.floor(Date.now() / 8000) % 4; }
    // the adverts: plain panels in the style of the photos (a wine merchant's
    // red with white serif capitals), with the club's and the city's words
    function janAdvert(c, k) {
        const H = J_BAR;
        c.textAlign = 'center'; c.textBaseline = 'middle';
        if (k === 0) {
            c.fillStyle = '#d23a32'; c.fillRect(0, 0, JW, H);
            c.fillStyle = '#fbeee6';
            c.font = `400 52px ${J_SERIF}`; c.fillText('VAN', JW / 2, 120);
            c.font = `400 150px ${J_SERIF}`; c.fillText('BRUGGE', JW / 2, 245);
            c.font = `400 44px ${J_SERIF}`; c.fillText('SINDS 1891', JW / 2, 360);
            c.strokeStyle = '#fbeee6'; c.lineWidth = 6;
            c.beginPath(); c.arc(JW / 2, 455, 34, 0, Math.PI * 2); c.stroke();
            c.beginPath(); c.moveTo(JW / 2 - 90, 455); c.lineTo(JW / 2 - 40, 455); c.moveTo(JW / 2 + 40, 455); c.lineTo(JW / 2 + 90, 455); c.stroke();
        } else if (k === 1) {
            c.fillStyle = '#0d0d10'; c.fillRect(0, 0, JW, H);
            c.fillStyle = '#1d5cc0';
            for (let i = -4; i < 12; i++) { c.beginPath(); c.moveTo(i * 120, H); c.lineTo(i * 120 + 60, H); c.lineTo(i * 120 + 60 + H * 0.6, 0); c.lineTo(i * 120 + H * 0.6, 0); c.closePath(); c.fill(); }
            c.fillStyle = 'rgba(10,10,14,0.82)'; c.fillRect(0, 150, JW, 260);
            c.fillStyle = '#ffffff'; c.font = `700 170px ${J_FONT}`; c.fillText('NO SWEAT NO GLORY', JW / 2, 285, JW - 80);
        } else if (k === 2) {
            c.fillStyle = '#f1f0ec'; c.fillRect(0, 0, JW, H);
            c.fillStyle = '#0d4fa8'; c.font = `700 150px ${J_FONT}`; c.fillText('JAN BREYDEL', JW / 2, 220);
            c.fillStyle = '#16181c'; c.font = `600 74px ${J_FONT}`; c.fillText('STADION · BRUGGE', JW / 2, 345);
            c.fillStyle = '#0d4fa8'; c.fillRect(0, H - 40, JW, 40);
        } else {
            c.fillStyle = '#0a7a48'; c.fillRect(0, 0, JW, H);
            c.fillStyle = '#0b0b0d'; c.fillRect(0, 0, JW, 60); c.fillRect(0, H - 60, JW, 60);
            c.fillStyle = '#ffffff'; c.font = `700 160px ${J_FONT}`; c.fillText('CERCLE BRUGGE', JW / 2, 285, JW - 80);
        }
    }
    function drawJanBreydel(clock, s1, s2) {
        const c = jCtx;
        janAdvert(c, janAd());
        // the bar: deep blue, lighter round the clock, white figures, arrows pointing at the clock
        const y0 = J_BAR, h = JH - J_BAR, ym = y0 + h / 2;
        const g = c.createLinearGradient(0, 0, JW, 0);
        g.addColorStop(0, '#0f2a9a'); g.addColorStop(0.5, '#2a56d8'); g.addColorStop(1, '#0f2a9a');
        c.fillStyle = g; c.fillRect(0, y0, JW, h);
        c.fillStyle = '#081a70'; c.fillRect(0, y0, JW, 4);
        const badge = (img, cx, size) => {
            if (!img) return;
            const k = Math.min(size / img.width, size / img.height);
            c.drawImage(img, cx - img.width * k / 2, ym - img.height * k / 2, img.width * k, img.height * k);
        };
        badge(cbLogo, 60, 104);
        badge(ceLogo, JW - 60, 96);
        c.fillStyle = '#ffffff'; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.font = `700 104px ${J_FONT}`;
        c.fillText(String(s1), 250, ym + 4);
        c.fillText(String(s2), JW - 250, ym + 4);
        c.fillStyle = '#5fa0ff';
        c.beginPath(); c.moveTo(330, y0 + 22); c.lineTo(372, ym); c.lineTo(330, y0 + h - 22); c.closePath(); c.fill();
        c.beginPath(); c.moveTo(JW - 330, y0 + 22); c.lineTo(JW - 372, ym); c.lineTo(JW - 330, y0 + h - 22); c.closePath(); c.fill();
        c.fillStyle = '#ffffff'; c.font = `700 84px ${J_FONT}`;
        c.fillText(clock, JW / 2, ym + 3);
        jTexture.needsUpdate = true;
    }

    // ---- Joseph Marien: the scoreboard over the north-east end (1000 x 612 on a 1024 x 512 canvas; 8 x 4.9 m) ----
    const XW = 1000, XH = 612;
    let xCanvas = null, xCtx = null, xTexture = null, usgLogo = null, xAwayLogo = null;
    function loadMarienLogos() {
        if (typeof Image === 'undefined' || usgLogo) return;
        const load = (src, set) => { const im = new Image(); im.onload = () => { set(im); last = ''; redraw(); }; im.src = src; };
        load('media/hud/union.png', (im) => { usgLogo = im; });
        load('media/hud/clubbrugge.png', (im) => { xAwayLogo = im; });
    }
    function drawMarien(clock, s1, s2) {
        const c = xCtx;
        c.fillStyle = '#0b0c0f'; c.fillRect(0, 0, XW, XH);
        c.fillStyle = '#1b8f88'; c.fillRect(0, 128, 58, XH - 128);
        c.fillStyle = '#2140b0'; c.fillRect(276, 172, 76, XH - 172); c.fillRect(812, 172, 76, XH - 172);
        const crest = (img, cx, cy, h) => {
            if (!img) return;
            const k = h / img.height;
            c.drawImage(img, cx - img.width * k / 2, cy - h / 2, img.width * k, h);
        };
        crest(usgLogo, 262, 382, 250);
        crest(xAwayLogo, 730, 380, 236);
        c.textAlign = 'center'; c.textBaseline = 'middle';
        c.fillStyle = '#b9a76a'; c.font = `600 46px ${J_FONT}`;
        c.fillText('VS', 505, 364);
        c.fillStyle = '#ffffff'; c.font = `600 86px ${J_FONT}`;
        c.fillText(String(s1), 284, 86);
        c.fillText(clock, 462, 86);
        c.fillText(String(s2), 650, 86);
        xTexture.needsUpdate = true;
    }

    // ---- Philips Stadion: the four screens (1000 x 562 on a 1024 x 512 canvas; 8 x 4.5 m) ----
    const PW_ = 1000, PH_ = 562;
    let pCanvas = null, pCtx = null, pTexture = null, psvLogo = null, pAwayLogo = null;
    function loadPhilipsLogos() {
        if (typeof Image === 'undefined' || psvLogo) return;
        const load = (src, set) => { const im = new Image(); im.onload = () => { set(im); last = ''; redraw(); }; im.src = src; };
        load('img/psvlogo.svg', (im) => { psvLogo = im; });
        load('img/logo3.png', (im) => { pAwayLogo = im; });
    }
    function drawPhilips(clock, s1, s2) {
        const c = pCtx;
        // the board: orange-red, a shade lighter left of the slanting line
        c.fillStyle = '#ea573b'; c.fillRect(0, 0, PW_, PH_);
        c.fillStyle = '#ee6a50';
        c.beginPath(); c.moveTo(0, 0); c.lineTo(548, 0); c.lineTo(548, 112); c.lineTo(424, PH_); c.lineTo(0, PH_); c.closePath(); c.fill();
        c.strokeStyle = '#f6a690'; c.lineWidth = 4;
        c.beginPath(); c.moveTo(520, 112); c.lineTo(548, 112); c.lineTo(424, PH_); c.stroke();
        // the bar along the top: the club's words, PSV, the clock
        c.fillStyle = '#f7f5f2'; c.fillRect(26, 32, 450, 80);
        c.fillStyle = '#26222b'; c.fillRect(476, 32, 176, 80);
        c.fillStyle = '#f7f5f2'; c.fillRect(652, 32, 196, 80);
        c.textAlign = 'center'; c.textBaseline = 'middle';
        c.fillStyle = '#4a4450'; c.font = `600 30px ${J_FONT}`;
        c.fillText('VOOR DE SUPPORTERS,', 251, 56, 420);
        c.fillText('DE CLUB EN DE STAD', 251, 89, 420);
        c.fillStyle = '#f7f5f2'; c.font = `700 44px ${J_SERIF}`;
        c.fillText('PSV', 564, 74, 160);
        c.fillStyle = '#2b2831'; c.font = `800 64px ${J_FONT}`;
        c.fillText(clock, 750, 74, 180);
        // the crests in white discs
        const disc = (img, cx, cy, r) => {
            c.fillStyle = '#f7f5f2';
            c.beginPath(); c.ellipse(cx, cy, r * 1.08, r, 0, 0, Math.PI * 2); c.fill();
            if (!img) return;
            const k = Math.min(r * 1.6 / img.width, r * 1.6 / img.height);
            c.drawImage(img, cx - img.width * k / 2, cy - img.height * k / 2, img.width * k, img.height * k);
        };
        // PSV's own logo carries its white oval (img/psvlogo.svg)
        if (psvLogo) {
            const w = psvLogo.naturalWidth || psvLogo.width || 741, h = psvLogo.naturalHeight || psvLogo.height || 604;
            const k = Math.min(200 / w, 190 / h);
            c.drawImage(psvLogo, 146 - w * k / 2, 286 - h * k / 2, w * k, h * k);
        }
        disc(pAwayLogo, 846, 296, 74);
        // the score: heavy white figures, leaning a little, a bar between them
        c.fillStyle = '#ffffff';
        c.font = `italic 900 250px ${J_FONT}`;
        c.fillText(String(s1), 356, 308);
        c.fillText(String(s2), 640, 308);
        c.beginPath(); c.moveTo(474, 280); c.lineTo(530, 280); c.lineTo(524, 306); c.lineTo(468, 306); c.closePath(); c.fill();
        pTexture.needsUpdate = true;
    }

    // ---- Estadio Centenario: the screen over the Colombes (1000 x 538 on a 1024 x 512 canvas; 12.48 x 6.72 m) ----
    const CW_ = 1000, CH_ = 538;
    const C_FONT = '"Montserrat", "Barlow", "Arial", sans-serif';
    let cCanvas = null, cCtx = null, cTexture = null, cHome = null, cAway = null;
    function loadCentenarioLogos() {
        if (typeof Image === 'undefined' || cHome) return;
        const load = (src, set) => { const im = new Image(); im.onload = () => { set(im); last = ''; redraw(); }; im.src = src; };
        load('media/hud/boca.png', (im) => { cHome = im; });
        load('media/hud/millonarios.png', (im) => { cAway = im; });
    }
    function drawCentenario(clock, s1, s2) {
        const c = cCtx;
        c.fillStyle = '#170f0f'; c.fillRect(0, 0, CW_, CH_);
        // the haze: big soft patches of dark red and burnt orange, overlapping
        const blob = (x, y, r, col) => { c.fillStyle = col; c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill(); };
        c.globalAlpha = 0.28;
        blob(660, 170, 300, '#6a1e16'); blob(260, 460, 320, '#5a1a14'); blob(860, 470, 260, '#7a3416');
        blob(130, 150, 230, '#6e3a1a'); blob(500, 330, 220, '#4a1612'); blob(380, 120, 200, '#5a2416');
        c.globalAlpha = 0.18;
        blob(720, 480, 180, '#b0561f'); blob(200, 260, 160, '#a04a1c'); blob(560, 90, 150, '#a2441e'); blob(900, 260, 140, '#8a3418');
        c.globalAlpha = 1;
        // the golden arcs down both edges, outside the crests
        const arcs = (cx, dir) => {
            [[20, '#c98a3c'], [8, '#f2c472']].forEach(([w, col], i) => {
                c.strokeStyle = col; c.lineWidth = w;
                for (let k = 0; k < 2; k++) {
                    c.beginPath();
                    c.ellipse(cx + dir * (k * 34 + i * 5), 300, 70 + k * 22, 250, 0, dir > 0 ? Math.PI * 0.6 : -Math.PI * 0.4, dir > 0 ? Math.PI * 1.4 : Math.PI * 0.4);
                    c.stroke();
                }
            });
        };
        arcs(70, -1);
        arcs(930, 1);
        // the bar along the top
        c.fillStyle = '#2a2a2d'; c.fillRect(0, 0, CW_, 46);
        c.fillStyle = '#f2f2f0'; c.font = `700 29px ${C_FONT}`; c.textAlign = 'left'; c.textBaseline = 'middle';
        c.fillText('MONUMENTO AL FÚTBOL MUNDIAL - ESTADIO CENTENARIO', 12, 24, CW_ - 24);
        // the golden cup and its name
        c.save(); c.translate(500, 104);
        c.fillStyle = '#d9a24a';
        c.beginPath();
        c.moveTo(-22, -34); c.lineTo(22, -34); c.lineTo(16, -6); c.quadraticCurveTo(10, 8, 5, 12);
        c.lineTo(9, 30); c.lineTo(-9, 30); c.lineTo(-5, 12); c.quadraticCurveTo(-10, 8, -16, -6); c.closePath(); c.fill();
        c.fillStyle = '#8a5a20'; for (let k = -2; k <= 2; k++) c.fillRect(k * 7 - 1.5, -30, 3, 28);
        c.restore();
        c.fillStyle = '#f2f2f0'; c.textAlign = 'center';
        c.font = `600 11px ${C_FONT}`; c.fillText('CONMEBOL', 500, 146);
        c.font = `800 20px ${C_FONT}`; c.fillText('LIBERTADORES', 500, 164);
        // the faded crest of the visitors in the top corner, as on the photo
        if (cAway) {
            c.globalAlpha = 0.14;
            const k = 150 / cAway.height;
            c.drawImage(cAway, 860 - cAway.width * k / 2, 85, cAway.width * k, 150);
            c.globalAlpha = 1;
        }
        const crest = (img, cx, cy, h) => {
            if (!img) return;
            const k = h / img.height;
            c.drawImage(img, cx - img.width * k / 2, cy - h / 2, img.width * k, h);
        };
        crest(cHome, 245, 312, 196);
        crest(cAway, 745, 312, 190);
        // the score and the clock
        c.fillStyle = '#ffffff'; c.font = `700 104px ${C_FONT}`; c.textAlign = 'center';
        c.fillText(String(s1), 418, 318);
        c.fillText(String(s2), 582, 318);
        c.fillStyle = '#e2ad55'; c.font = `700 52px ${C_FONT}`; c.fillText('x', 500, 322);
        c.fillStyle = '#ffffff'; c.font = `700 74px ${C_FONT}`; c.fillText(clock, 500, 446);
        cTexture.needsUpdate = true;
    }

    // ---- Bernabéu: the 360 ring round the roof's opening (2048 x 512) ----
    // As on the photos of a Clásico there: on each side, read from the pitch,
    // the clock, Real Madrid's crest, REAL MADRID C.F. and its score, the match
    // as on television in the middle, the score, F.C. BARCELONA and its crest,
    // the clock again. The top half is a long side (80 m of screen), the
    // bottom half an end (its left 1235 px, 44 m) and a corner (the rest).
    // The television picture is the match camera's own frame, taken twice a
    // second (frame(), called by the game right after it draws); before a
    // match a still of the pitch from the camera's side.
    const BW = 2048, BH = 512, B_END = 1235;
    let bCanvas = null, bCtx = null, bTexture = null, rmLogo = null, fcbLogo = null;
    let vCanvas = null, vCtx = null, vLast = 0;
    const VW = 512, VH = 288;
    function loadBernabeuLogos() {
        if (typeof Image === 'undefined' || rmLogo) return;
        const load = (src, set) => { const im = new Image(); im.onload = () => { set(im); last = ''; redraw(); }; im.src = src; };
        load('media/hud/realmadrid.png', (im) => { rmLogo = im; });
        load('media/hud/fcbarcelona.png', (im) => { fcbLogo = im; });
    }
    // the colours and letters as measured on the photos (img/7.png, 8.png):
    // the panels almost black navy with a bright blue glow from the top, the
    // clock's panel running from navy to a light blue at its inner edge with a
    // thin white slanting line; narrow upright bold capitals
    const B_DEEP = '#020430', B_NAVY = '#03034f', B_FONT = '"Barlow Condensed", "Arial Narrow", sans-serif';
    let bFont = false;
    if (typeof document !== 'undefined' && document.fonts && document.fonts.load) {
        Promise.all([document.fonts.load(`700 80px "Barlow Condensed"`), document.fonts.load(`600 80px "Barlow Condensed"`)])
            .then(() => { bFont = true; last = ''; redraw(); }).catch(() => {});
    }
    // a crest fitted into a box of w x h, centred on (cx, cy)
    function crestAt(c, img, cx, cy, w, h) {
        if (!img) return;
        const k = Math.min(w / img.width, h / img.height);
        c.drawImage(img, cx - img.width * k / 2, cy - img.height * k / 2, img.width * k, img.height * k);
    }
    // a team's panel: near-black navy, lit from the top by a blue glow, a
    // touch of violet at the edge by the television picture (inner: +1 right, -1 left)
    function teamField(c, x, y, w, h, inner) {
        c.fillStyle = B_NAVY; c.fillRect(x, y, w, h);
        c.save();
        c.beginPath(); c.rect(x, y, w, h); c.clip();
        let g = c.createRadialGradient(x + w * 0.5, y - h * 0.15, 0, x + w * 0.5, y - h * 0.15, w * 0.62);
        g.addColorStop(0, 'rgba(46,96,245,0.95)'); g.addColorStop(0.45, 'rgba(26,58,205,0.55)'); g.addColorStop(1, 'rgba(3,3,79,0)');
        c.fillStyle = g; c.fillRect(x, y, w, h);
        const ex = inner > 0 ? x + w : x;
        g = c.createRadialGradient(ex, y + h * 0.75, 0, ex, y + h * 0.75, h * 1.1);
        g.addColorStop(0, 'rgba(110,64,150,0.55)'); g.addColorStop(1, 'rgba(110,64,150,0)');
        c.fillStyle = g; c.fillRect(x, y, w, h);
        c.restore();
    }
    // the clock's panel: navy at its outer end to light blue at its inner edge,
    // a thin white line slanting across near that edge (inner: +1 right, -1 left)
    function clockField(c, x, y, w, h, inner) {
        const g = c.createLinearGradient(inner > 0 ? x : x + w, y + h, inner > 0 ? x + w : x, y);
        g.addColorStop(0, '#010358'); g.addColorStop(0.55, '#1a3fc8'); g.addColorStop(0.85, '#4e80e6'); g.addColorStop(1, '#9db9f8');
        c.fillStyle = g; c.fillRect(x, y, w, h);
        c.strokeStyle = 'rgba(255,255,255,0.85)'; c.lineWidth = 2.5;
        const lx = inner > 0 ? x + w * 0.80 : x + w * 0.20;
        c.beginPath(); c.moveTo(lx - inner * h * 0.18, y); c.lineTo(lx + inner * h * 0.18, y + h); c.stroke();
    }
    // the still before a match: the stands and the pitch seen from the camera's side
    function stillPicture() {
        const c = vCtx;
        const sky = c.createLinearGradient(0, 0, 0, VH * 0.42);
        sky.addColorStop(0, '#0d1424'); sky.addColorStop(1, '#1e2b4a');
        c.fillStyle = sky; c.fillRect(0, 0, VW, VH * 0.42);
        let r = 7;
        const rnd = () => ((r = (r * 9301 + 49297) % 233280) / 233280);
        for (let k = 0; k < 900; k++) {                    // the crowd
            c.fillStyle = rnd() < 0.5 ? 'rgba(230,230,240,0.55)' : 'rgba(120,130,170,0.5)';
            c.fillRect(rnd() * VW, VH * 0.06 + rnd() * VH * 0.34, 2, 2);
        }
        c.fillStyle = '#e8e8f0'; c.fillRect(0, VH * 0.40, VW, 4);
        const top = VH * 0.42;
        for (let k = 0; k < 12; k++) {                     // the stripes, wider towards the camera
            c.fillStyle = k % 2 ? '#3d8f3a' : '#35823a';
            const x0 = k / 12, x1 = (k + 1) / 12;
            c.beginPath();
            c.moveTo(VW * (0.12 + 0.76 * x0), top); c.lineTo(VW * (0.12 + 0.76 * x1), top);
            c.lineTo(VW * (-0.35 + 1.7 * x1), VH); c.lineTo(VW * (-0.35 + 1.7 * x0), VH); c.closePath(); c.fill();
        }
        c.strokeStyle = 'rgba(255,255,255,0.85)'; c.lineWidth = 2;
        c.beginPath(); c.moveTo(VW * 0.12, top + 6); c.lineTo(VW * 0.88, top + 6); c.stroke();
        c.beginPath(); c.moveTo(VW / 2, top + 6); c.lineTo(VW / 2, VH); c.stroke();
        c.beginPath(); c.ellipse(VW / 2, VH * 0.70, VW * 0.13, VH * 0.11, 0, 0, Math.PI * 2); c.stroke();
    }
    function ensureVideo() {
        if (vCanvas || typeof document === 'undefined') return;
        vCanvas = document.createElement('canvas');
        vCanvas.width = VW; vCanvas.height = VH;
        vCtx = vCanvas.getContext('2d');
        stillPicture();
    }
    // the picture in its frame
    function videoAt(c, x, y, w, h) {
        c.fillStyle = '#05091f'; c.fillRect(x - 5, y - 5, w + 10, h + 10);
        if (vCanvas) c.drawImage(vCanvas, x, y, w, h);
    }
    function drawBernabeu(clock, s1, s2) {
        const c = bCtx;
        ensureVideo();
        c.fillStyle = B_DEEP; c.fillRect(0, 0, BW, BH);
        c.textAlign = 'center'; c.textBaseline = 'middle';
        const text = (str, x, y, size, maxW = 1e4, weight = 700) => {
            c.font = `${weight} ${size}px ${B_FONT}`;
            const w = c.measureText(str).width;
            if (w > maxW) c.font = `${weight} ${Math.floor(size * maxW / w)}px ${B_FONT}`;
            c.fillStyle = '#ffffff'; c.fillText(str, x, y);
        };
        const GAP = 6;                                   // the dark seams between the panels
        // one side of the ring: [clock][crest name score][television][score name crest][clock]
        const side = (y0, h, L, video, names) => {
            const mid = y0 + h / 2;
            const half = (sgn, logo, name, score) => {
                const X = (x, w) => sgn > 0 ? x : L.total - x - w;      // a box, mirrored on the right
                const P = (x) => sgn > 0 ? x : L.total - x;               // a point, mirrored
                clockField(c, X(0, L.clock), y0, L.clock, h, sgn);
                text(clock, P(L.clock * 0.42), mid + 2, L.clockSize, L.clock - 70, 600);
                const tx = L.clock + GAP;
                teamField(c, X(tx, L.team), y0, L.team, h, sgn);
                crestAt(c, logo, P(tx + L.crestX), mid, L.crestW, h * 0.86);
                if (names) text(name, P(tx + L.nameX), mid + 2, 58, L.nameW);
                text(String(score), P(tx + L.team - L.scoreR), mid + 6, L.scoreSize, 130);
            };
            half(1, rmLogo, 'REAL MADRID C.F.', s1);
            half(-1, fcbLogo, 'F.C. BARCELONA', s2);
            const vx = L.clock + L.team + 2 * GAP;
            teamField(c, vx, y0, L.total - 2 * vx, h, 1);
            videoAt(c, (L.total - video.w) / 2, y0 + (h - video.h) / 2, video.w, video.h);
        };
        // a long side: 2048 px, the top half
        side(8, 240, { total: BW, clock: 205, clockSize: 84, team: 640, crestX: 118, crestW: 200, nameX: 380, nameW: 250, scoreR: 62, scoreSize: 180 },
             { w: 330, h: 186 }, true);
        // an end: 1235 px, the bottom half, no names
        side(264, 240, { total: B_END, clock: 170, clockSize: 66, team: 312, crestX: 100, crestW: 175, nameX: 0, nameW: 0, scoreR: 58, scoreSize: 160 },
             { w: 246, h: 150 }, false);
        // a corner: the clock on its light blue, as at the ends of the screen on the photos
        clockField(c, B_END + GAP, 264, BW - B_END - GAP, 240, 1);
        text(clock, (B_END + GAP + BW) / 2 - 20, 388, 96, BW - B_END - 160, 600);
        bTexture.needsUpdate = true;
    }
    // called by the game right after it draws the match: twice a second the
    // frame goes onto the screen as its television picture
    function frame(src, now) {
        if (activeStyle !== 'bernabeu' || !bCtx || !src || !src.width) return;
        if (now - vLast < 500) return;
        vLast = now;
        ensureVideo();
        const sw = src.width, sh = src.height, want = VW / VH;
        let cw = sw, ch = sw / want;
        if (ch > sh) { ch = sh; cw = sh * want; }
        try {
            vCtx.drawImage(src, (sw - cw) / 2, (sh - ch) / 2, cw, ch, 0, 0, VW, VH);
        } catch (_) { return; }
        drawBernabeu(current.clock, current.s1, current.s2);
    }

    function drawKuip(clock, s1, s2) {
        const c = kCtx, mid = KTOP + (KH - KTOP) / 2;
        c.fillStyle = '#0b0b0d'; c.fillRect(0, 0, KW, KH);
        c.fillStyle = KRED; c.fillRect(0, KTOP, KSPLIT, KH - KTOP);
        c.fillStyle = KWHITE; c.fillRect(KSPLIT + 10, KTOP, KW - KSPLIT - 10, KH - KTOP);
        const text = (str, x, y, size, color) => {
            c.font = `700 ${size}px ${KF}`;
            c.fillStyle = color;
            c.textAlign = 'center';
            c.textBaseline = 'middle';
            c.fillText(str, x, y);
        };
        // the home logo
        if (kuipLogo) {
            const box = 168, k = Math.min(box / kuipLogo.width, box / kuipLogo.height);
            const w = kuipLogo.width * k, h = kuipLogo.height * k;
            c.drawImage(kuipLogo, 105 - w / 2, mid - h / 2, w, h);
        } else {
            c.fillStyle = KWHITE;
            c.beginPath(); c.arc(105, mid, 70, 0, Math.PI * 2); c.fill();
            text('FEY', 105, mid + 3, 60, KRED);
        }
        // the score, under the clock tab
        text(String(s1), 300, mid + 14, 196, '#ffffff');
        c.fillStyle = '#ffffff'; c.fillRect(432, mid + 6, 56, 20);
        text(String(s2), 620, mid + 14, 196, '#ffffff');
        cpuShield(805, mid + 4, 0.82, c);
        // the clock in its dark tab, hanging from the top edge
        c.fillStyle = KINK;
        c.beginPath();
        c.moveTo(345, 0); c.lineTo(575, 0); c.lineTo(575, 60);
        c.quadraticCurveTo(575, 88, 547, 88); c.lineTo(373, 88);
        c.quadraticCurveTo(345, 88, 345, 60); c.closePath();
        c.fill();
        text(clock, 460, 46, 68, '#ffffff');
        text('DE KUIP', (KSPLIT + 10 + KW) / 2, mid + 2, 66, KRED);
        kTexture.needsUpdate = true;
    }

    function draw(clock, s1, s2) {
        ctx.fillStyle = BLACK;
        ctx.fillRect(0, 0, W, H);
        // the board in the middle: purple clock block over the two score boxes
        const bx0 = 301, bx1 = 723, top = 109, mid = 301, bot = 493, split = (bx0 + bx1) / 2;
        ctx.fillStyle = PURPLE; ctx.fillRect(bx0, top, bx1 - bx0, mid - top);
        narrow(clock, split, top + 26, 138, WHITE);
        ctx.fillStyle = ORANGE; ctx.fillRect(bx0, mid, split - bx0, bot - mid);
        ctx.fillStyle = WHITE; ctx.fillRect(split, mid, bx1 - split, bot - mid);
        digitsIn(String(s1), bx0, mid, split, bot, 192, WHITE);
        digitsIn(String(s2), split, mid, bx1, bot, 192, INK);
        // club logo left, CPU shield right
        if (logo) {
            const box = 170, k = Math.min(box / logo.width, box / logo.height);
            const w = logo.width * k, h = logo.height * k;
            ctx.drawImage(logo, 154 - w / 2, H / 2 - h / 2, w, h);
        }
        cpuShield(870, H / 2, 1);
        texture.needsUpdate = true;
    }

    let current = { clock: '00:00', s1: 0, s2: 0 };
    let activeStyle = null;                        // the style of the screens on the model in use
    function redraw() {
        if (!canvas) return;
        const teams = wkTeams();
        const key = `${wkHeading()}|${new Date().getMinutes()}|${current.clock}|${current.s1}|${current.s2}|${!!logo}|${fontReady}|${kuipFont}|${!!kuipLogo}|${campinFont}|${!!arenaLogo}|${!!arenaAway}|${!!rmLogo}|${!!fcbLogo}|${bFont}|${!!cbLogo}|${!!ceLogo}|${janAd()}|${!!usgLogo}|${mGoals.join('/')}|${!!xAwayLogo}|${!!psvLogo}|${!!pAwayLogo}|${!!cHome}|${!!cAway}|${campinTeams().map(t => t.code + t.color).join()}|${teams.map(t => t.code + t.color + !!flagImage(t.flag)).join()}`;
        if (key === last) return;
        last = key;
        draw(current.clock, current.s1, current.s2);
        drawRibbon(current.clock, current.s1, current.s2);
        drawWk(current.clock, current.s1, current.s2);
        drawKuip(current.clock, current.s1, current.s2);
        drawCampin(current.clock, current.s1, current.s2);
        drawArena(current.clock, current.s1, current.s2);
        drawMontjuic(current.clock, current.s1, current.s2);
        drawBernabeu(current.clock, current.s1, current.s2);
        drawJanBreydel(current.clock, current.s1, current.s2);
        drawMarien(current.clock, current.s1, current.s2);
        drawPhilips(current.clock, current.s1, current.s2);
        drawCentenario(current.clock, current.s1, current.s2);
    }

    // put the screen on a loaded model; returns true if it has screens
    function attach(root, style, logo) {
        const node = root && root.getObjectByName('StadiumScreens');
        const band = root && root.getObjectByName('StadiumRibbonScore');
        if (!node && !band) return false;
        ensure();
        const use = (n, tex) => n && n.traverse((c) => {
            if (!c.isMesh) return;
            const mats = Array.isArray(c.material) ? c.material : [c.material];
            mats.forEach((m) => { m.map = tex; m.color && m.color.setRGB(1, 1, 1); m.needsUpdate = true; });
        });
        if (style === 'kuip') loadKuipLogo(logo);
        if (style === 'arena') { loadArenaLogo(logo); loadArenaAway(); }
        if (style === 'bernabeu') { loadBernabeuLogos(); vLast = 0; if (vCtx) stillPicture(); }
        if (style === 'janbreydel') loadJanLogos();
        if (style === 'montjuic') { loadBernabeuLogos(); mGoals = [[], []]; mPrev = [0, 0]; }
        if (style === 'marien') loadMarienLogos();
        if (style === 'philips') loadPhilipsLogos();
        if (style === 'centenario') loadCentenarioLogos();
        if (node) activeStyle = style;
        use(node, style === 'wk' ? wTexture : style === 'kuip' ? kTexture : style === 'campin' ? eTexture : style === 'arena' ? aTexture : style === 'montjuic' ? mTexture : style === 'bernabeu' ? bTexture : style === 'janbreydel' ? jTexture : style === 'marien' ? xTexture : style === 'philips' ? pTexture : style === 'centenario' ? cTexture : texture);
        use(band, rTexture);
        last = '';
        redraw();
        return true;
    }

    // called by the game every frame; cheap unless something changed
    function update(clock, s1, s2) {
        current = { clock, s1, s2 };
        if (activeStyle === 'montjuic') montjuicGoals(clock, s1, s2);
        redraw();
    }

    return { attach, update, frame };
})();

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
// screen: 'arena' (Johan Cruijff ArenA) is the ArenA's screen: dark navy with
// a red glow across the middle, the clock at the top, the big score with a
// small red and white mark between the figures, a round badge for each team.
// The home logo is the file the catalog names (screenLogo), with three gold
// stars over it as on the screen; without it a white disc with the short name.
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

    // ---- the Johan Cruijff ArenA: the big screen (14 x 7.4 m, drawn 1024 x 541) ----
    const AW = 1024, AH = 541;
    let aCanvas = null, aCtx = null, aTexture = null;
    let arenaLogo = null, arenaLogoSrc = null;
    function loadArenaLogo(src) {
        if (!src || src === arenaLogoSrc) return;
        arenaLogoSrc = src;
        const im = new Image();
        im.onload = () => { arenaLogo = im; last = ''; redraw(); };
        im.src = src;                              // missing file: the white disc stays
    }
    function star(c, cx, cy, r) {
        c.beginPath();
        for (let i = 0; i < 10; i++) {
            const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.42 : r;
            c.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
        }
        c.closePath();
        c.fill();
    }
    function drawArena(clock, s1, s2) {
        const c = aCtx;
        // in a match the two sides; on the test page Ajax red against the CPU
        const playing = typeof STATE !== 'undefined' && STATE.screen === 'playing';
        const [ta, tb] = playing ? campinTeams() : [{ code: 'AJA', color: '#d2122e' }, { code: 'CPU', color: '#1c2c5c' }];
        // dark navy, a little lighter at the top, a red glow across the middle
        const bg = c.createLinearGradient(0, 0, 0, AH);
        bg.addColorStop(0, '#2a3046'); bg.addColorStop(1, '#1b2032');
        c.fillStyle = bg; c.fillRect(0, 0, AW, AH);
        const glow = c.createLinearGradient(0, AH * 0.38, 0, AH * 0.86);
        glow.addColorStop(0, 'rgba(150,36,48,0)'); glow.addColorStop(0.5, 'rgba(150,36,48,0.42)'); glow.addColorStop(1, 'rgba(150,36,48,0)');
        c.fillStyle = glow; c.fillRect(0, AH * 0.38, AW, AH * 0.48);
        c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = '#f4f4f6';
        // the clock at the top
        c.font = `700 92px ${CF}`;
        c.fillText(clock, AW / 2, 96);
        // a round badge each side: the home logo with three gold stars, or a disc with the short name
        const badge = (cx, cy, team, logoImg) => {
            if (logoImg) {
                const box = 190, k = Math.min(box / logoImg.width, box / logoImg.height);
                c.drawImage(logoImg, cx - logoImg.width * k / 2, cy - logoImg.height * k / 2, logoImg.width * k, logoImg.height * k);
                c.fillStyle = '#e4b12f';
                [-46, 0, 46].forEach((dx) => star(c, cx + dx, cy - 128 + (dx ? 6 : 0), 15));
                return;
            }
            c.fillStyle = '#f4f4f6';
            c.beginPath(); c.arc(cx, cy, 92, 0, Math.PI * 2); c.fill();
            c.fillStyle = team.color;
            c.beginPath(); c.arc(cx, cy, 80, 0, Math.PI * 2); c.fill();
            c.fillStyle = lightness(team.color) > 0.62 ? '#1b2032' : '#f4f4f6';
            c.font = `700 52px ${CF}`;
            c.fillText(team.code, cx, cy + 3);
        };
        badge(186, 318, ta, arenaLogo);
        badge(AW - 186, 318, tb, null);
        // the score, and the small red and white mark between the figures
        c.fillStyle = '#f4f4f6';
        c.font = `700 210px ${CF}`;
        c.fillText(String(s1), AW / 2 - 165, 326);
        c.fillText(String(s2), AW / 2 + 165, 326);
        c.fillStyle = '#f4f4f6'; c.fillRect(AW / 2 - 13, 314, 26, 26);
        c.fillStyle = '#d2122e'; c.fillRect(AW / 2 - 13, 314, 26, 13);
        aTexture.needsUpdate = true;
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
    function redraw() {
        if (!canvas) return;
        const teams = wkTeams();
        const key = `${wkHeading()}|${current.clock}|${current.s1}|${current.s2}|${!!logo}|${fontReady}|${kuipFont}|${!!kuipLogo}|${campinFont}|${!!arenaLogo}|${campinTeams().map(t => t.code + t.color).join()}|${teams.map(t => t.code + t.color + !!flagImage(t.flag)).join()}`;
        if (key === last) return;
        last = key;
        draw(current.clock, current.s1, current.s2);
        drawRibbon(current.clock, current.s1, current.s2);
        drawWk(current.clock, current.s1, current.s2);
        drawKuip(current.clock, current.s1, current.s2);
        drawCampin(current.clock, current.s1, current.s2);
        drawArena(current.clock, current.s1, current.s2);
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
        if (style === 'arena') loadArenaLogo(logo);
        use(node, style === 'wk' ? wTexture : style === 'kuip' ? kTexture : style === 'campin' ? eTexture : style === 'arena' ? aTexture : texture);
        use(band, rTexture);
        last = '';
        redraw();
        return true;
    }

    // called by the game every frame; cheap unless something changed
    function update(clock, s1, s2) {
        current = { clock, s1, s2 };
        redraw();
    }

    return { attach, update };
})();

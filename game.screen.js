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

    function shieldPath(cx, cy, w, h) {
        const r = w / 2, yTop = cy - h / 2, yMid = cy + h * 0.05;
        ctx.beginPath();
        ctx.moveTo(cx - r, yTop);
        ctx.lineTo(cx + r, yTop);
        ctx.lineTo(cx + r, yMid);
        ctx.ellipse(cx, yMid, r, h * 0.45, 0, 0, Math.PI);
        ctx.closePath();
    }

    function cpuShield(cx, cy, s) {
        shieldPath(cx, cy, 147 * s, 186 * s); ctx.fillStyle = '#eceef2'; ctx.fill();
        shieldPath(cx, cy, 128 * s, 166 * s); ctx.fillStyle = '#1c2c5c'; ctx.fill();
        ctx.fillStyle = '#eceef2';
        ctx.fillRect(cx - 64 * s, cy - 45 * s, 128 * s, 19 * s);
        ctx.font = `bold ${42 * s}px Arial, Helvetica, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('CPU', cx, cy + 16 * s);
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
        const key = `${wkHeading()}|${current.clock}|${current.s1}|${current.s2}|${!!logo}|${fontReady}|${teams.map(t => t.code + t.color + !!flagImage(t.flag)).join()}`;
        if (key === last) return;
        last = key;
        draw(current.clock, current.s1, current.s2);
        drawRibbon(current.clock, current.s1, current.s2);
        drawWk(current.clock, current.s1, current.s2);
    }

    // put the screen on a loaded model; returns true if it has screens
    function attach(root, style) {
        const node = root && root.getObjectByName('StadiumScreens');
        const band = root && root.getObjectByName('StadiumRibbonScore');
        if (!node && !band) return false;
        ensure();
        const use = (n, tex) => n && n.traverse((c) => {
            if (!c.isMesh) return;
            const mats = Array.isArray(c.material) ? c.material : [c.material];
            mats.forEach((m) => { m.map = tex; m.color && m.color.setRGB(1, 1, 1); m.needsUpdate = true; });
        });
        use(node, style === 'wk' ? wTexture : texture);
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

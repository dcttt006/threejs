// =====================================================
// PITCH ROYALE — live stadium screen
// The big screens in a stadium model (a node named 'StadiumScreens') show the
// match: the clock in a purple block, the score in an orange and a white box,
// the club logo on the left (img/logo2.png) and
// the CPU shield on the right. A model can also have a small score panel in
// the band between its tiers ('StadiumRibbonScore'): the score in an orange
// and a white box, the clock on purple. Both are canvases used as textures,
// redrawn only when the clock or the score changes.
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
        const key = `${current.clock}|${current.s1}|${current.s2}|${!!logo}`;
        if (key === last) return;
        last = key;
        draw(current.clock, current.s1, current.s2);
        drawRibbon(current.clock, current.s1, current.s2);
    }

    // put the screen on a loaded model; returns true if it has screens
    function attach(root) {
        const node = root && root.getObjectByName('StadiumScreens');
        const band = root && root.getObjectByName('StadiumRibbonScore');
        if (!node && !band) return false;
        ensure();
        const use = (n, tex) => n && n.traverse((c) => {
            if (!c.isMesh) return;
            const mats = Array.isArray(c.material) ? c.material : [c.material];
            mats.forEach((m) => { m.map = tex; m.color && m.color.setRGB(1, 1, 1); m.needsUpdate = true; });
        });
        use(node, texture);
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

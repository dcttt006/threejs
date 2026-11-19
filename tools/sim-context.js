// =====================================================
// PITCH ROYALE — the stand-in browser for the tests
// The game's own code runs in it without a browser: a THREE whose objects keep
// real positions (everything else does nothing), a page whose elements accept
// whatever the game does to them, a virtual clock and a seeded random.
// Used by tools/gameplay-test.js and tools/vargame-test.js.
// =====================================================
'use strict';
const vm = require('vm');

function makeContext(seed) {
    let clock = 1_000_000;                       // virtual ms
    const timers = [];
    let s = seed >>> 0 || 1;
    const rand = () => {                         // mulberry32
        s = (s + 0x6D2B79F5) >>> 0;
        let t = s;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const noop = () => {};
    const classList = () => ({ add: noop, remove: noop, toggle: noop, contains: () => false });
    const ctx2d = new Proxy({}, {
        get: (t, k) => k === 'getImageData' ? (x, y, w, h) => ({ data: new Uint8ClampedArray(Math.max(4, w * h * 4)) })
            : k === 'measureText' ? () => ({ width: 10, actualBoundingBoxAscent: 10 })
            : k in t ? t[k] : noop,
        set: (t, k, v) => { t[k] = v; return true; },
    });
    const el = () => ({
        textContent: '', hidden: true, value: '', disabled: false,
        style: { setProperty: noop, removeProperty: noop }, dataset: {}, classList: classList(),
        addEventListener: noop, removeEventListener: noop, appendChild: noop, append: noop, replaceChildren: noop,
        querySelector: () => el(), querySelectorAll: () => [], setAttribute: noop, focus: noop, blur: noop,
        getContext: () => ctx2d, getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
        scrollIntoView: noop, setPointerCapture: noop, offsetWidth: 0, width: 0, height: 0,
    });
    const elements = new Map();
    const document = {
        addEventListener: noop, removeEventListener: noop,
        documentElement: { classList: classList() },
        getElementById: (id) => { if (!elements.has(id)) elements.set(id, el()); return elements.get(id); },
        createElement: () => el(), querySelector: () => el(), querySelectorAll: () => [], body: el(),
    };

    // THREE: real positions, everything else inert
    class V3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
        set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; } setScalar(v) { this.x = this.y = this.z = v; return this; }
        copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; } clone() { return new V3(this.x, this.y, this.z); } }
    class Obj3D { constructor() { this.position = new V3(); this.rotation = new V3(); this.rotation.order = 'XYZ'; this.scale = new V3(1, 1, 1);
        this.userData = {}; this.children = []; this.visible = true; this.renderOrder = 0; }
        add(...c) { this.children.push(...c); return this; } remove(c) { this.children = this.children.filter(x => x !== c); return this; }
        traverse(f) { f(this); this.children.forEach(c => c.traverse && c.traverse(f)); } lookAt() {} getObjectByName() { return null; } }
    class Mesh extends Obj3D { constructor(geometry, material) { super(); this.geometry = geometry; this.material = material; } }
    class Color { constructor() { this.r = this.g = this.b = 1; } convertSRGBToLinear() { return this; } setRGB() { return this; }
        clone() { return new Color(); } multiplyScalar() { return this; } set() { return this; } copy() { return this; } }
    class Material { constructor(o = {}) { Object.assign(this, o); this.color = new Color(); } clone() { return new Material(this); } dispose() {} }
    // anything else: an object whose every method does nothing and returns itself
    const inert = () => { const o = {}; const px = new Proxy(o, { get: (t, k) => (k in t ? t[k] : (k === Symbol.toPrimitive || k === 'then' ? undefined : () => px)), set: (t, k, v) => { t[k] = v; return true; } }); return px; };
    function Inert() { return inert(); }
    const special = { Object3D: Obj3D, Group: Obj3D, Scene: Obj3D, Mesh, Sprite: Mesh, Vector3: V3, Color };
    const THREE = new Proxy({}, {
        get: (t, k) => special[k] || (/Material$/.test(k) ? Material : (typeof k === 'string' && /^[A-Z][a-z]/.test(k) ? Inert : 0)),
    });

    const M = Object.create(Math);
    M.random = rand;
    const DateShim = class extends Date { static now() { return clock; } };
    const sandbox = {
        THREE, document, Math: M, Date: DateShim, console: { log: noop, warn: noop, error: (...a) => console.error(...a), info: noop },
        navigator: { userAgent: 'node', maxTouchPoints: 0 }, location: { search: '', pathname: '/index.html' },
        history: { pushState: noop, replaceState: noop }, localStorage: { getItem: () => null, setItem: noop },
        matchMedia: () => ({ matches: false, addEventListener: noop }), URLSearchParams,
        performance: { now: () => clock }, requestAnimationFrame: () => 0, cancelAnimationFrame: noop,
        setTimeout: (f, ms) => { timers.push({ at: clock + (ms || 0), f }); return timers.length; }, clearTimeout: noop,
        ResizeObserver: class { observe() {} disconnect() {} }, Image: class { set src(v) {} },
        addEventListener: noop, removeEventListener: noop, innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1,
    };
    sandbox.window = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    sandbox.__advance = (ms) => {
        clock += ms;
        for (let i = 0; i < timers.length; i++) if (timers[i] && timers[i].at <= clock) { const t = timers[i]; timers[i] = null; t.f(); }
    };
    return sandbox;
}

module.exports = { makeContext };

// node tests/test_v30_depth.cjs — prévia JS contra a fixture gerada pelo Python (splat 0).
const assert = require('assert');
const fs = require('fs');
const path = require('path');
(async () => {
  const mod = await import(path.join(__dirname, '..', 'web', 'depth-warp.js'));
  const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'depth_warp_js.json'), 'utf8'));
  const { w, h } = fx;
  const cloud = mod.buildCloud(fx.z, fx.src, w, h, fx.fx_norm, fx.thr, 3);
  let checked = 0;
  for (const c of fx.cases) {
    const cam = mod.orbitCamera(c.pose, c.pivot, c.aim, 1);
    // colunas de C: right, down, forward, eye
    for (let r = 0; r < 3; r++) {
      assert(Math.abs(cam.right[r] - c.C[r][0]) < 1e-9, 'right');
      assert(Math.abs(cam.down[r] - c.C[r][1]) < 1e-9, 'down');
      assert(Math.abs(cam.forward[r] - c.C[r][2]) < 1e-9, 'forward');
      assert(Math.abs(cam.eye[r] - c.C[r][3]) < 1e-9, 'eye');
    }
    const out = new Uint8ClampedArray(w*h*4), zbuf = new Float64Array(w*h);
    const holes = mod.renderCloud(cloud, cam, 0, out, zbuf);
    let diff = 0;
    for (let i = 0; i < w*h; i++) {
      const hole = zbuf[i] === Infinity ? 1 : 0;
      if (hole !== c.holes[i] || out[i*4] !== c.rgb[i*3] || out[i*4+1] !== c.rgb[i*3+1] || out[i*4+2] !== c.rgb[i*3+2]) diff++;
    }
    assert(diff <= Math.ceil(w*h*0.005), `pose ${JSON.stringify(c.pose)}: ${diff} pixels differ`);
    assert(Math.abs(holes - c.holes.reduce((a, b) => a + b, 0)/(w*h)) < 0.01);
    checked++;
  }
  {
    const out = new Uint8ClampedArray(w*h*4), zbuf = new Float64Array(w*h);
    const far = mod.orbitCamera({ azimuth: 170, elevation: 0, distance: 1 }, fx.cases[0].pivot, 'source');
    mod.renderCloud(cloud, far, 1, out, zbuf, [128, 128, 128]);
    let grey = 0; for (let i = 0; i < w*h; i++) if (zbuf[i] === Infinity) { assert(out[i*4] === 128 && out[i*4+1] === 128 && out[i*4+2] === 128); grey++; }
    assert(grey > 0, 'meridian hole colour');
  }
  assert.strictEqual(mod.roundHalfEven(2.5), 2); assert.strictEqual(mod.roundHalfEven(3.5), 4);
  assert.strictEqual(mod.roundHalfEven(-2.5), -2); assert.strictEqual(mod.roundHalfEven(-1.5), -2);
  const z = mod.decodeDepth(new Uint8ClampedArray([255, 255, 0, 255, 0, 0, 255, 255]), 2, 1, 1, 5);
  assert(Math.abs(z[0] - 5) < 1e-12 && Number.isNaN(z[1]));
  // identidade: pose inicial com mira da fonte não move nada
  const id = mod.orbitCamera({ azimuth: 0, elevation: 0, distance: 1 }, [0.3, -0.1, 2.5], 'source');
  assert(Math.abs(id.forward[2] - 1) < 1e-9 && Math.abs(id.right[0] - 1) < 1e-9 && Math.hypot(...id.eye) < 1e-9);
  console.log(`depth warp JS: ${checked} poses match Python fixture`);
})().catch(e => { console.error(e); process.exit(1); });

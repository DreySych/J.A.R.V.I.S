'use strict';
const PARTICLE_VS = `
attribute vec2 inPosition;
varying vec2 fragUV;
void main() {
  gl_Position = vec4(inPosition, 0.0, 1.0);
  fragUV = (inPosition + 1.0) / 2.0;
}`;

const PARTICLE_FS = `
precision mediump float;
uniform float uNoiseOffset;
uniform float uAmplitude;
uniform float uSeed;
uniform float uDotSpacing;
uniform float uDotOffset;
uniform float uSphereRadius;
uniform float uFeather;
uniform float uNoiseFrequency;
uniform float uNoiseAmplitude;
uniform float uCenterPush;
varying vec2 fragUV;

float hash(vec3 p) {
  p = fract(p * 0.3183099 + 0.1);
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(hash(i + vec3(0.0, 0.0, 0.0)), hash(i + vec3(1.0, 0.0, 0.0)), f.x),
        mix(hash(i + vec3(0.0, 1.0, 0.0)), hash(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
    mix(mix(hash(i + vec3(0.0, 0.0, 1.0)), hash(i + vec3(1.0, 0.0, 1.0)), f.x),
        mix(hash(i + vec3(0.0, 1.0, 1.0)), hash(i + vec3(1.0, 1.0, 1.0)), f.x), f.y), f.z
  );
}

float fractalNoise(vec3 coord) {
  return noise(coord + uSeed) * 0.5 
       + noise(coord * 2.0 + uSeed) * 0.25 
       + noise(coord * 4.0 + uSeed) * 0.125;
}

void main() {
  float n = fractalNoise(vec3(fragUV * uNoiseFrequency, uNoiseOffset)) * uNoiseAmplitude;
  vec3 dotCenter = vec3(fragUV * uDotSpacing + uDotOffset + n, (n + 0.5 * uNoiseAmplitude) * uAmplitude * 0.4);
  
  float radialDist = length(dotCenter.xy);
  float push = 1.0 + uCenterPush * max(0.0, 1.0 - radialDist / 0.8);
  dotCenter.xy *= push;
  
  float distanceFromCenter = length(dotCenter);
  dotCenter /= distanceFromCenter;
  distanceFromCenter = min(uSphereRadius, distanceFromCenter);
  dotCenter *= distanceFromCenter;
  
  float featherRadius = uSphereRadius - uFeather;
  float featherStrength = 1.0 - clamp((distanceFromCenter - featherRadius) / uFeather, 0.0, 1.0);
  dotCenter *= featherStrength * (uSphereRadius / distanceFromCenter - 1.0) + 1.0;
  
  dotCenter.y *= -1.0;
  gl_FragColor = vec4(dotCenter.xy * 0.5 + 0.5, 0.0, 1.0);
}`;

const DOT_VS = `
uniform int uDotCount;
uniform float uDotRadius;
uniform float uDotRadiusPX;
uniform float uAspectRatio;
uniform float uCenterFade;
uniform sampler2D uParticleTexture;
attribute vec2 inPosition;
attribute float aInstanceID;
varying vec2 fragUV;
varying float fragDotRadiusPX;
varying float fragAlpha;
void main() {
  float u = (mod(aInstanceID, float(uDotCount)) + 0.5) / float(uDotCount);
  float v = (floor(aInstanceID / float(uDotCount)) + 0.5) / float(uDotCount);
  vec2 dotCenter = texture2D(uParticleTexture, vec2(u, v)).xy * 2.0 - 1.0;
  float centerDist = length(dotCenter);
  float atten = mix(uCenterFade, 1.0, smoothstep(0.0, 0.5, centerDist));
  fragAlpha = atten;
  float sizeScale = mix(0.75, 1.0, smoothstep(0.0, 0.35, centerDist));
  
  vec2 pos = dotCenter + inPosition * uDotRadius * sizeScale;
  pos.x /= uAspectRatio;
  gl_Position = vec4(pos, 0.0, 1.0);
  
  fragUV = inPosition;
  fragDotRadiusPX = uDotRadiusPX + 1.0;
}`;

const DOT_FS = `
precision mediump float;
varying vec2 fragUV;
varying float fragDotRadiusPX;
varying float fragAlpha;
void main() {
  float dist = length(fragUV);
  if (dist > 1.0) discard;
  float t = smoothstep(1.0, 0.0, dist);
  gl_FragColor = vec4(vec3(t * fragAlpha), 1.0);
}`;

const FINAL_VS = `
attribute vec2 inPosition;
varying vec2 fragUV;
void main() {
  gl_Position = vec4(inPosition, 0.0, 1.0);
  fragUV = (inPosition + 1.0) / 2.0;
}`;

const FINAL_FS = `
precision mediump float;
uniform sampler2D uOriginalTexture;
uniform vec3 uOutputColor1;
uniform vec3 uOutputColor2;
uniform float uSeparateGlow;
uniform float uBass;
uniform float uTime;
varying vec2 fragUV;
void main() {
  float orig = texture2D(uOriginalTexture, fragUV).r;
  float isBlack = 1.0 - smoothstep(0.01, 0.2, length(uOutputColor1));
  float value = orig;
  if (value < 0.01) { gl_FragColor = vec4(0.0); return; }
  vec2 toCenter = fragUV - vec2(0.5);
  float angle = atan(toCenter.y, toCenter.x);
  float sweep = sin(angle + uTime * 1.0) * 0.5 + 0.5;
  float density = smoothstep(0.2, 0.9, value);
  float mixFactor = clamp(sweep * 0.6 + density * 0.4, 0.2, 0.8);
  vec3 standardColor = mix(uOutputColor1, uOutputColor2, mixFactor);
  float coreMask = smoothstep(0.4, 0.8, orig);
  vec3 glowColor = uOutputColor2 * 1.3;
  vec3 splitColor = mix(glowColor, uOutputColor1, coreMask);
  vec3 color = mix(standardColor, splitColor, uSeparateGlow);
  color *= (1.0 + uBass * 0.15);
  float specular = smoothstep(0.95, 1.0, value) * 0.1 * (1.0 - uSeparateGlow);
  color = mix(color, vec3(1.0), specular * (1.0 - isBlack));
  color = mix(color, vec3(0.0), isBlack);
  float dimmer = 1.5;
  float alpha = mix(value * dimmer, value, isBlack);
  gl_FragColor = vec4(color * value * dimmer, alpha);
}`;

export function hashString(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i);
    h |= 0;
  }
  return h;
}

export class NCSVisualizer {
  static NCS_GENRE_COLORS = {
    drumstep:       [1.0,   0.0,   0.0,     0.6,   0.0,   0.0  ],
    indieDance:     [1.0,   0.647, 0.0,     0.85,  0.35,  0.0  ],
    house:          [1.0,   1.0,   0.0,     0.85,  0.75,  0.0  ],
    trap:           [0.478, 0.992, 0.251,   0.25,  0.80,  0.35 ],
    glitchHop:      [0.2,   0.9,   0.5,     0.6,   1.0,   0.8  ],
    melodicDubstep: [0.227, 1.0,   0.945,   0.1,   0.75,  0.9  ],
    dubstep:        [0.118, 0.463, 1.0,     0.15,  0.30,  0.80 ],
    futureHouse:    [0.15,  0.0,   0.5,     0.6,   0.2,   1.0  ],
    futureBass:     [0.584, 0.439, 1.0,     0.65,  0.2,   1.0  ],
    drumAndBass:    [1.0,   0.196, 0.969,   0.75,  0.05,  0.65 ],
    angelcore:      [1.0,   1.0,   1.0,     1.0,   0.6,   0.85 ],
    electronic:     [1.0,   1.0,   1.0,     0.85,  0.85,  0.85 ],
    miscellaneous:  [0.0,   0.0,   0.0,     0.0,   0.0,   0.0  ]
  };

  static i = -1;

  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.options = { dotCount: 32, color: [1.0, 1.0, 1.0, 0.85, 0.85, 0.85], ...options };
    const c = this.options.color;
    if (c.length === 3) this.options.color = [...c, c[0]*0.5, c[1]*0.5, c[2]*0.5];

    this._smoothAmp = 0;
    this._smoothBass = 0;
    this.pulsationStrength = 1.0;
    this.isListening = false;
    this._listeningScale = 1.0;
    this._targetListeningScale = 1.0;
    this.audioCtx = null;
    this.sourceNode = null;
    this.analyserNode = null;
    this.audioElement = null;
    this.isPlaying = false;
    this._demoTime = 0;
    this._amplitudeIntegral = 0;
    this._smoothAmp = 0;
    this._smoothBass = 0;
    this._ampVelocity = 0;
    this._seed = Math.random() * 10.0;
    this._lastFrameTime = 0;
    this._running = false;
    this._animId = null;
    this._vpSize = 0;
    this._freqData = null;
    this._currentColor = [...this.options.color];
    this._targetColor = [...this.options.color];
    this.rainbowMode = false;
    this._rainbowHue = 0;
    this._separateGlow = 0.0;
    this._targetSeparateGlow = 0.0;
    this._currentSeparateGlow = 0.0;
    this._initGL();
    this._initFBOs();
    this._onResize = () => this._resize();
    window.addEventListener('resize', this._onResize);
    this._resize();
  }

  static get COLORS() { return this.NCS_GENRE_COLORS; }

  static newColor() {
    const colors = Object.values(NCSVisualizer.COLORS);
    this.i = (this.i + 1) % colors.length;
    return colors[this.i];
  }

  setColor(...args) {
    let newColor;
    if (args.length === 1 && Array.isArray(args[0])) {
      const c = args[0];
      newColor = c.length === 3 ? [...c, c[0]*0.5, c[1]*0.5, c[2]*0.5] : c;
    } else if (args.length === 3) {
      newColor = [...args, args[0]*0.5, args[1]*0.5, args[2]*0.5];
    } else if (args.length === 6) {
      newColor = args;
    }
    if (newColor) {
      this._targetColor = [...newColor];
      const keys = Object.keys(NCSVisualizer.NCS_GENRE_COLORS);
      const angelcoreIndex = keys.indexOf('angelcore');
      let isAngelcore = (NCSVisualizer.i === angelcoreIndex);
      if (!isAngelcore) {
        const ac = NCSVisualizer.NCS_GENRE_COLORS.angelcore;
        isAngelcore = newColor.every((val, idx) => Math.abs(val - ac[idx]) < 0.01);
      }
      this._targetSeparateGlow = isAngelcore ? 1.0 : 0.0;
    }
  }

  setRainbowMode(enabled) { this.rainbowMode = enabled; }
  setListening(enabled) {
    this.isListening = enabled;
    this._targetListeningScale = enabled ? 1.3 : 1.0;
  }
  setPulsationStrength(value) { this.pulsationStrength = Math.max(0.0, value); }

  setAudioNodes(audioCtx, analyserNode, audioElement, seed) {
    if (this.sourceNode) { try { this.sourceNode.disconnect(); } catch (e) {} this.sourceNode = null; }
    if (this.analyserNode && this.analyserNode !== analyserNode) { try { this.analyserNode.disconnect(); } catch (e) {} }
    this.audioCtx = audioCtx;
    this.analyserNode = analyserNode;
    this.audioElement = audioElement;
    this._seed = (seed || Math.random() * 10.0) % 100.0;
    this._demoTime = 0;
    if (analyserNode) this._freqData = new Uint8Array(analyserNode.frequencyBinCount);
    else this._freqData = null;
  }

  _initGL() {
    const gl = this.canvas.getContext('webgl', { alpha: true, antialias: false });
    if (!gl) throw new Error('WebGL not supported');
    this.gl = gl;

    this.ext = gl.getExtension('ANGLE_instanced_arrays');

    const cs = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const cp = (vs, fs) => {
      const p = gl.createProgram();
      gl.attachShader(p, vs);
      gl.attachShader(p, fs);
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
      return p;
    };

    this._prog = {
      p: cp(cs(gl.VERTEX_SHADER, PARTICLE_VS), cs(gl.FRAGMENT_SHADER, PARTICLE_FS)),
      d: cp(cs(gl.VERTEX_SHADER, DOT_VS), cs(gl.FRAGMENT_SHADER, DOT_FS)),
      f: cp(cs(gl.VERTEX_SHADER, FINAL_VS), cs(gl.FRAGMENT_SHADER, FINAL_FS)),
    };

    this.quadBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,-1,1,1,1,1,-1]), gl.STATIC_DRAW);

    const U = (prog, name) => gl.getUniformLocation(prog, name);
    const A = (prog, name) => gl.getAttribLocation(prog, name);

    const p = this._prog.p;
    this._u = {
      pInPos: A(p, 'inPosition'), uNoiseOffset: U(p, 'uNoiseOffset'), uAmplitude: U(p, 'uAmplitude'),
      uSeed: U(p, 'uSeed'), uDotSpacing: U(p, 'uDotSpacing'), uDotOffset: U(p, 'uDotOffset'),
      uSphereRadius: U(p, 'uSphereRadius'), uFeather: U(p, 'uFeather'), uNoiseFreq: U(p, 'uNoiseFrequency'),
      uNoiseAmp: U(p, 'uNoiseAmplitude'), uCenterPush: U(p, 'uCenterPush'),
    };

    const d = this._prog.d;
    this._u.dInPos = A(d, 'inPosition');
    this._u.aInstanceID = A(d, 'aInstanceID');
    this._u.uDotCount = U(d, 'uDotCount');
    this._u.uDotRadius = U(d, 'uDotRadius');
    this._u.uDotRadiusPX = U(d, 'uDotRadiusPX');
    this._u.uParticleTex = U(d, 'uParticleTexture');
    this._u.uAspectRatio = U(d, 'uAspectRatio');
    this._u.uCenterFade = U(d, 'uCenterFade');

    const f = this._prog.f;
    this._u.fInPos = A(f, 'inPosition');
    this._u.uOutputColor1 = U(f, 'uOutputColor1');
    this._u.uOutputColor2 = U(f, 'uOutputColor2');
    this._u.uBass = U(f, 'uBass');
    this._u.uTime = U(f, 'uTime');
    this._u.uSeparateGlow = U(f, 'uSeparateGlow');
    this._u.uOriginalTex = U(f, 'uOriginalTexture');

    gl.enable(gl.BLEND);
    gl.blendEquation(gl.FUNC_ADD);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
    gl.clearColor(0, 0, 0, 0);
  }

  _createFB(filter) {
    const gl = this.gl;
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    return { fb, tex };
  }

  _initFBOs() {
    const gl = this.gl;
    const dc = this.options.dotCount;
    this._pf = this._createFB(gl.NEAREST);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, dc, dc, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    this._prevDotCount = dc;
    this._df = this._createFB(gl.NEAREST);
    this._dotCount = dc;
    this._pf_tex = this._pf.tex; this._pf_fb = this._pf.fb;
    this._df_tex = this._df.tex; this._df_fb = this._df.fb;

    if (this.ext) {
      this.instanceBuf = gl.createBuffer();
      const instIDs = new Float32Array(dc * dc);
      for (let i = 0; i < instIDs.length; i++) instIDs[i] = i;
      gl.bindBuffer(gl.ARRAY_BUFFER, this.instanceBuf);
      gl.bufferData(gl.ARRAY_BUFFER, instIDs, gl.STATIC_DRAW);
    } else {
      const quads = new Float32Array([ -1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1 ]);
      const totalQuads = dc * dc;
      const posData = new Float32Array(totalQuads * 12);
      const idData = new Float32Array(totalQuads * 6);
      for (let i = 0; i < totalQuads; i++) {
        posData.set(quads, i * 12);
        idData.fill(i, i * 6, i * 6 + 6);
      }
      this.fallbackQuadBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.fallbackQuadBuf);
      gl.bufferData(gl.ARRAY_BUFFER, posData, gl.STATIC_DRAW);

      this.fallbackIdBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.fallbackIdBuf);
      gl.bufferData(gl.ARRAY_BUFFER, idData, gl.STATIC_DRAW);
    }
  }

  _resize() {
    const gl = this.gl;
    const dpr = Math.min(window.devicePixelRatio || 1, 500 / Math.max(window.innerWidth, window.innerHeight));
    const cw = this.canvas.clientWidth;
    const ch = this.canvas.clientHeight;
    if (cw < 1 || ch < 1) return;
    const pw = Math.round(cw * dpr);
    const ph = Math.round(ch * dpr);
    if (this.canvas.width === pw && this.canvas.height === ph) return;
    this.canvas.width = pw; this.canvas.height = ph;
    this._w = pw; this._h = ph;
    const size = Math.min(pw, ph);
    this._vpSize = size;
    this._vpX = Math.round((pw - size) / 2);
    this._vpY = Math.round((ph - size) / 2);
    this._aspect = 1;
    this._invSize = 1 / size;
    gl.bindTexture(gl.TEXTURE_2D, this._df_tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, size, size, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  }

  loadAudio(file) {
    if (this.audioElement) { this.audioElement.pause(); this.audioElement = null; }
    if (!this.audioCtx) this.audioCtx = new AudioContext();
    const url = URL.createObjectURL(file);
    this.audioElement = new Audio(url);
    this.sourceNode = this.audioCtx.createMediaElementSource(this.audioElement);
    this.analyserNode = this.audioCtx.createAnalyser();
    this.analyserNode.fftSize = 2048;
    this.analyserNode.smoothingTimeConstant = 0.85;
    this.sourceNode.connect(this.analyserNode);
    // this.analyserNode.connect(this.audioCtx.destination);
    this.audioElement.addEventListener('ended', () => { this.isPlaying = false; });
    this.isPlaying = false;
    this._seed = Math.random() * 10.0;
    this._freqData = new Uint8Array(this.analyserNode.frequencyBinCount);
  }

  playFromUrl(url) {
    if (this.audioElement) { this.audioElement.pause(); this.audioElement = null; }
    if (!this.audioCtx) this.audioCtx = new AudioContext();
    this.audioElement = new Audio(url);
    this.sourceNode = this.audioCtx.createMediaElementSource(this.audioElement);
    this.analyserNode = this.audioCtx.createAnalyser();
    this.analyserNode.fftSize = 2048;
    this.analyserNode.smoothingTimeConstant = 0.85;
    this.sourceNode.connect(this.analyserNode);
    this.analyserNode.connect(this.audioCtx.destination);
    this.audioElement.addEventListener('ended', () => { this.isPlaying = false; });
    this.isPlaying = true;
    this._freqData = new Uint8Array(this.analyserNode.frequencyBinCount);
    if (this.audioCtx.state === 'suspended') this.audioCtx.resume();
    this.audioElement.play();
  }

  play() { if (this.audioElement) { this.audioElement.play(); this.isPlaying = true; } }
  pause() { if (this.audioElement) { this.audioElement.pause(); this.isPlaying = false; } }
  togglePlay() { this.isPlaying ? this.pause() : this.play(); }
  get isActive() { return this.isPlaying; }
  get hasAudio() { return !!this.audioElement; }
  start() { this._running = true; this._render(0); }

  destroy() {
    this._running = false;
    if (this._animId) cancelAnimationFrame(this._animId);
    window.removeEventListener('resize', this._onResize);
  }

  _getBassAmplitude() {
    if (!this.analyserNode || !this.isPlaying) {
      this._demoTime += 0.016;
      const demo = 0.15 + Math.sin(this._demoTime * 1.5) * 0.09 + Math.sin(this._demoTime * 0.8) * 0.06 + Math.sin(this._demoTime * 0.3) * 0.035;
      return Math.max(0.05, demo);
    }
    this.analyserNode.getByteFrequencyData(this._freqData);
    let sumSq = 0, weightSum = 0;
    const binHz = this.audioCtx.sampleRate / this.analyserNode.fftSize;
    const lo = Math.floor(20 / binHz);
    const hi = Math.min(this._freqData.length - 1, Math.ceil(150 / binHz));
    for (let i = lo; i <= hi; i++) {
      const v = this._freqData[i] / 255;
      const w = Math.exp(-Math.pow(i * binHz - 70, 2) / 3200);
      sumSq += v * v * w;
      weightSum += w;
    }
    const bass = weightSum > 0 ? Math.sqrt(sumSq / weightSum) : 0;
    this._smoothBass += (bass - this._smoothBass) * 0.06;
    return Math.min(1, (bass * 0.75 + 0.1) + Math.max(0, bass - this._smoothBass) * 5.0);
  }

  _drawQuad(loc) {
    const gl = this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_FAN, 0, 4);
  }

  _render(time) {
    if (!this._running) return;
    this._animId = requestAnimationFrame(t => this._render(t));
    const gl = this.gl;
    this._resize();
    if (!this._vpSize) return;

    const dotCount = this._dotCount, size = this._vpSize, u = this._u, pp = this._prog;
    const dt = this._lastFrameTime ? (time - this._lastFrameTime) / 1000 : 1 / 60;
    this._lastFrameTime = time;

    const rawAmp = this._getBassAmplitude();
    const clampedDt = Math.min(dt, 0.04);
    const force = 220.0 * (rawAmp - this._smoothAmp) - 14.0 * this._ampVelocity;
    this._ampVelocity += force * clampedDt;
    this._smoothAmp += this._ampVelocity * clampedDt;
    this._smoothAmp = Math.max(0.0, this._smoothAmp);

    const uAmplitude = this._smoothAmp * this.pulsationStrength;
    this._amplitudeIntegral += uAmplitude * dt * 3;

    let offset = (0.5 * (this.audioElement?.currentTime ?? this._demoTime) + this._amplitudeIntegral) * 0.75;
    offset = offset % 100.0;
    const uNoiseOffset = offset;

    this._listeningScale += (this._targetListeningScale - this._listeningScale) * 0.05;
    let currentRadius = (0.6 + uAmplitude * (this.isListening ? 0.05 : 0.2)) * this._listeningScale;
    if (this.isListening) currentRadius += Math.sin(time * 0.002) * 0.01;

    const uSphereRadius = currentRadius;
    const uDotRadius = (1.8 / dotCount) * this._listeningScale;
    const uDotRadiusPX = uDotRadius * 0.5 * size;
    const uFeather = Math.pow(uAmplitude + 3, 2) * (45 / 1568);

    gl.disable(gl.BLEND);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this._pf_fb);
    gl.viewport(0, 0, dotCount, dotCount);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(pp.p);
    gl.uniform1f(u.uNoiseOffset, uNoiseOffset); gl.uniform1f(u.uAmplitude, uAmplitude);
    gl.uniform1f(u.uSeed, this._seed); gl.uniform1f(u.uDotSpacing, 0.9);
    gl.uniform1f(u.uDotOffset, -0.45); gl.uniform1f(u.uSphereRadius, uSphereRadius);
    gl.uniform1f(u.uFeather, uFeather); gl.uniform1f(u.uNoiseFreq, 4);
    gl.uniform1f(u.uNoiseAmp, 0.288); gl.uniform1f(u.uCenterPush, 0.1);
    this._drawQuad(u.pInPos);

    gl.enable(gl.BLEND);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this._df_fb);
    gl.viewport(0, 0, size, size);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(pp.d);
    gl.uniform1i(u.uDotCount, dotCount); gl.uniform1f(u.uDotRadius, uDotRadius);
    gl.uniform1f(u.uDotRadiusPX, uDotRadiusPX); gl.uniform1f(u.uAspectRatio, 1.0);
    gl.uniform1f(u.uCenterFade, 0.2); gl.uniform1i(u.uParticleTex, 0);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this._pf_tex);

    if (this.ext) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
      gl.enableVertexAttribArray(u.dInPos);
      gl.vertexAttribPointer(u.dInPos, 2, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ARRAY_BUFFER, this.instanceBuf);
      gl.enableVertexAttribArray(u.aInstanceID);
      gl.vertexAttribPointer(u.aInstanceID, 1, gl.FLOAT, false, 0, 0);
      this.ext.vertexAttribDivisorANGLE(u.aInstanceID, 1);
      this.ext.drawArraysInstancedANGLE(gl.TRIANGLE_FAN, 0, 4, dotCount * dotCount);
      this.ext.vertexAttribDivisorANGLE(u.aInstanceID, 0);
    } else {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.fallbackQuadBuf);
      gl.enableVertexAttribArray(u.dInPos);
      gl.vertexAttribPointer(u.dInPos, 2, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ARRAY_BUFFER, this.fallbackIdBuf);
      gl.enableVertexAttribArray(u.aInstanceID);
      gl.vertexAttribPointer(u.aInstanceID, 1, gl.FLOAT, false, 0, 0);

      gl.drawArrays(gl.TRIANGLES, 0, dotCount * dotCount * 6);
    }

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this._w, this._h);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.viewport(this._vpX, this._vpY, size, size);
    gl.useProgram(pp.f);

    if (this.rainbowMode) {
      this._rainbowHue = (this._rainbowHue + (0.05 + uAmplitude * 0.2) * dt) % 1.0;
      const h = this._rainbowHue, i = Math.floor(h * 6), f = h * 6 - i, p = 1.0, q = 1.0 - f, t = f;
      let r,g,b;
      switch (i % 6) {
        case 0: r=1; g=t; b=0; break; case 1: r=q; g=1; b=0; break; case 2: r=0; g=1; b=t; break;
        case 3: r=0; g=q; b=1; break; case 4: r=t; g=0; b=1; break; case 5: r=1; g=0; b=q; break;
      }
      this._targetColor = [r,g,b, r*0.8,g*0.8,b*0.8];
    }

    const lerp = Math.min(1.0, dt * 3.0);
    for (let i = 0; i < 6; i++) this._currentColor[i] += (this._targetColor[i] - this._currentColor[i]) * lerp;
    this._currentSeparateGlow += (this._targetSeparateGlow - this._currentSeparateGlow) * lerp;

    gl.uniform3f(u.uOutputColor1, this._currentColor[0], this._currentColor[1], this._currentColor[2]);
    gl.uniform3f(u.uOutputColor2, this._currentColor[3], this._currentColor[4], this._currentColor[5]);
    gl.uniform1f(u.uSeparateGlow, this._currentSeparateGlow);
    gl.uniform1f(u.uBass, uAmplitude);
    gl.uniform1f(u.uTime, time * 0.001);
    gl.uniform1i(u.uOriginalTex, 0);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this._df_tex);
    this._drawQuad(u.fInPos);
  }
}

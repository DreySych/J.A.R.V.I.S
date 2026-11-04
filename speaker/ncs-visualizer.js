'use strict';
const PARTICLE_VS = `#version 300 es
in vec2 inPosition;
out vec2 fragUV;
void main() {
  gl_Position = vec4(inPosition, 0.0, 1.0);
  fragUV = (inPosition + 1.0) / 2.0;
}`;

const PARTICLE_FS = `#version 300 es
precision highp float;
uniform float uNoiseOffset;
uniform float uAmplitude;
uniform int uSeed;
uniform float uDotSpacing;
uniform float uDotOffset;
uniform float uSphereRadius;
uniform float uFeather;
uniform float uNoiseFrequency;
uniform float uNoiseAmplitude;
uniform float uCenterPush;
in vec2 fragUV;
out vec2 outColor;
const float FREQUENCY = 0.01;
const float GAIN = 0.5;
const float LACUNARITY = 1.5;
const float FRACTAL_BOUNDING = 1.0 / 1.75;
const ivec3 PRIMES = ivec3(501125321, 1136930381, 1720413743);
const float GRADIENTS_3D[] = float[](
  0., 1., 1., 0.,  0.,-1., 1., 0.,  0., 1.,-1., 0.,  0.,-1.,-1., 0.,
  1., 0., 1., 0., -1., 0., 1., 0.,  1., 0.,-1., 0., -1., 0.,-1., 0.,
  1., 1., 0., 0., -1., 1., 0., 0.,  1.,-1., 0., 0., -1.,-1., 0., 0.,
  0., 1., 1., 0.,  0.,-1., 1., 0.,  0., 1.,-1., 0.,  0.,-1.,-1., 0.,
  1., 0., 1., 0., -1., 0., 1., 0.,  1., 0.,-1., 0., -1., 0.,-1., 0.,
  1., 1., 0., 0., -1., 1., 0., 0.,  1.,-1., 0., 0., -1.,-1., 0., 0.,
  0., 1., 1., 0.,  0.,-1., 1., 0.,  0., 1.,-1., 0.,  0.,-1.,-1., 0.,
  1., 0., 1., 0., -1., 0., 1., 0.,  1., 0.,-1., 0., -1., 0.,-1., 0.,
  1., 1., 0., 0., -1., 1., 0., 0.,  1.,-1., 0., 0., -1.,-1., 0., 0.,
  0., 1., 1., 0.,  0.,-1., 1., 0.,  0., 1.,-1., 0.,  0.,-1.,-1., 0.,
  1., 0., 1., 0., -1., 0., 1., 0.,  1., 0.,-1., 0., -1., 0.,-1., 0.,
  1., 1., 0., 0., -1., 1., 0., 0.,  1.,-1., 0., 0., -1.,-1., 0., 0.,
  0., 1., 1., 0.,  0.,-1., 1., 0.,  0., 1.,-1., 0.,  0.,-1.,-1., 0.,
  1., 0., 1., 0., -1., 0., 1., 0.,  1., 0.,-1., 0., -1., 0.,-1., 0.,
  1., 1., 0., 0., -1., 1., 0., 0.,  1.,-1., 0., 0., -1.,-1., 0., 0.,
  1., 1., 0., 0.,  0.,-1., 1., 0., -1., 1., 0., 0.,  0.,-1.,-1., 0.
);
float smootherStep(float t) { return t * t * t * (t * (t * 6.0 - 15.0) + 10.0); }
vec3 smootherStep(vec3 coord) { return vec3(smootherStep(coord.x), smootherStep(coord.y), smootherStep(coord.z)); }
int hash(int seed, ivec3 primed) { return (seed ^ primed.x ^ primed.y ^ primed.z) * 0x27d4eb2d; }
float gradCoord(int seed, ivec3 primed, vec3 d) {
  int h = hash(seed, primed);
  h ^= h >> 15;
  h &= 63 << 2;
  return d.x * GRADIENTS_3D[h] + d.y * GRADIENTS_3D[h | 1] + d.z * GRADIENTS_3D[h | 2];
}
float perlinSingle(int seed, vec3 coord) {
  ivec3 coord0 = ivec3(floor(coord));
  vec3 d0 = coord - vec3(coord0);
  vec3 d1 = d0 - 1.0;
  vec3 s = smootherStep(d0);
  coord0 *= PRIMES;
  ivec3 coord1 = coord0 + PRIMES;
  float xf00 = mix(gradCoord(seed, coord0, d0), gradCoord(seed, ivec3(coord1.x, coord0.yz), vec3(d1.x, d0.yz)), s.x);
  float xf10 = mix(gradCoord(seed, ivec3(coord0.x, coord1.y, coord0.z), vec3(d0.x, d1.y, d0.z)), gradCoord(seed, ivec3(coord1.xy, coord0.z), vec3(d1.xy, d0.z)), s.x);
  float xf01 = mix(gradCoord(seed, ivec3(coord0.xy, coord1.z), vec3(d0.xy, d1.z)), gradCoord(seed, ivec3(coord1.x, coord0.y, coord1.z), vec3(d1.x, d0.y, d1.z)), s.x);
  float xf11 = mix(gradCoord(seed, ivec3(coord0.x, coord1.yz), vec3(d0.x, d1.yz)), gradCoord(seed, coord1, d1), s.x);
  float yf0 = mix(xf00, xf10, s.y);
  float yf1 = mix(xf01, xf11, s.y);
  return mix(yf0, yf1, s.z) * 0.964921414852142333984375;
}
float fractalNoise(vec3 coord) {
  return perlinSingle(uSeed, coord) * FRACTAL_BOUNDING
    + perlinSingle(uSeed + 1, coord * LACUNARITY) * FRACTAL_BOUNDING * GAIN
    + perlinSingle(uSeed + 2, coord * LACUNARITY * LACUNARITY) * FRACTAL_BOUNDING * GAIN * GAIN;
}
void main() {
  float noise = fractalNoise(vec3(fragUV * uNoiseFrequency, uNoiseOffset)) * uNoiseAmplitude;
  vec3 dotCenter = vec3(fragUV * uDotSpacing + uDotOffset + noise, (noise + 0.5 * uNoiseAmplitude) * uAmplitude * 0.4);
  
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
  outColor = dotCenter.xy;
}`;

const DOT_VS = `#version 300 es
uniform int uDotCount;
uniform float uDotRadius;
uniform float uDotRadiusPX;
uniform float uAspectRatio;
uniform float uCenterFade;
uniform sampler2D uParticleTexture;
in vec2 inPosition;
out vec2 fragUV;
out float fragDotRadiusPX;
out float fragAlpha;
void main() {
  ivec2 dotIndex = ivec2(gl_InstanceID % uDotCount, gl_InstanceID / uDotCount);
  vec2 dotCenter = texelFetch(uParticleTexture, dotIndex, 0).xy;
  float centerDist = length(dotCenter);
  float atten = mix(uCenterFade, 1.0, smoothstep(0.0, 0.5, centerDist));
  fragAlpha = atten;
  float sizeScale = mix(0.75, 1.0, smoothstep(0.0, 0.35, centerDist));
  vec2 pos = dotCenter + inPosition * uDotRadius * sizeScale * (1.0 + 1.0 / uDotRadiusPX);
  pos.x /= uAspectRatio;
  gl_Position = vec4(pos, 0.0, 1.0);
  fragUV = inPosition;
  fragDotRadiusPX = uDotRadiusPX + 1.0;
}`;

const DOT_FS = `#version 300 es
precision highp float;
in vec2 fragUV;
in float fragDotRadiusPX;
in float fragAlpha;
out float outColor;
void main() {
  float t = clamp((1.0 - length(fragUV)) * fragDotRadiusPX, 0.0, 1.0);
  outColor = t * fragAlpha;
}`;

const BLUR_VS = `#version 300 es
uniform float uBlurRadius;
uniform vec2 uBlurDirection;
in vec2 inPosition;
out vec2 fragUV;
flat out vec2 fragBlurDirection;
flat out int fragSupport;
flat out vec3 fragGaussCoefficients;
float calculateGaussianTotal(int support, vec3 gaussCoefficients) {
  float total = gaussCoefficients.x;
  for (int i = 1; i < support; i++) {
    gaussCoefficients.xy *= gaussCoefficients.yz;
    total += 2.0 * gaussCoefficients.x;
  }
  return total;
}
void main() {
  fragSupport = int(ceil(1.5 * uBlurRadius)) * 2;
  fragGaussCoefficients = vec3(1.0 / (sqrt(2.0 * 3.14159265) * uBlurRadius), exp(-0.5 / (uBlurRadius * uBlurRadius)), 0.0);
  fragGaussCoefficients.z = fragGaussCoefficients.y * fragGaussCoefficients.y;
  fragGaussCoefficients.x /= calculateGaussianTotal(fragSupport, fragGaussCoefficients);
  gl_Position = vec4(inPosition, 0.0, 1.0);
  fragUV = (inPosition + 1.0) / 2.0;
  fragBlurDirection = uBlurDirection;
}`;

const BLUR_FS = `#version 300 es
precision highp float;
uniform sampler2D uInputTexture;
in vec2 fragUV;
flat in vec2 fragBlurDirection;
flat in int fragSupport;
flat in vec3 fragGaussCoefficients;
out float outColor;
void main() {
  vec3 gc = fragGaussCoefficients;
  outColor = gc.x * texture(uInputTexture, fragUV).r;
  for (int i = 1; i < fragSupport; i += 2) {
    gc.xy *= gc.yz;
    float coefficientSum = gc.x;
    gc.xy *= gc.yz;
    coefficientSum += gc.x;
    float pixelRatio = gc.x / coefficientSum;
    vec2 offset = (float(i) + pixelRatio) * fragBlurDirection;
    outColor += coefficientSum * (texture(uInputTexture, fragUV + offset).r + texture(uInputTexture, fragUV - offset).r);
  }
}`;

const FINAL_VS = `#version 300 es
uniform vec3 uOutputColor1;
uniform vec3 uOutputColor2;
uniform float uBass;
uniform float uTime;
in vec2 inPosition;
out vec2 fragUV;
out vec3 fragColor1;
out vec3 fragColor2;
out float fragBass;
out float fragTime;
void main() {
  gl_Position = vec4(inPosition, 0.0, 1.0);
  fragUV = (inPosition + 1.0) / 2.0;
  fragColor1 = uOutputColor1;
  fragColor2 = uOutputColor2;
  fragBass = uBass;
  fragTime = uTime;
}`;

const FINAL_FS = `#version 300 es
precision highp float;
uniform sampler2D uBlurredTexture;
uniform sampler2D uOriginalTexture;
in vec2 fragUV;
in vec3 fragColor1;
in vec3 fragColor2;
in float fragBass;
in float fragTime;
out vec4 outColor;

void main() {
  float value = max(texture(uBlurredTexture, fragUV).r, texture(uOriginalTexture, fragUV).r);
  if (value < 0.01) { outColor = vec4(0.0); return; }

  vec2 toCenter = fragUV - vec2(0.5);
  float angle = atan(toCenter.y, toCenter.x);

  // 1. Вращающийся градиент
  float sweep = sin(angle + fragTime * 1.0) * 0.5 + 0.5;
  
  // 2. Плотность
  float density = smoothstep(0.2, 0.9, value);
  
  // Смешиваем. Ограничиваем (0.2 - 0.8), чтобы цвета не перекрывали друг друга на 100%
  float mixFactor = clamp(sweep * 0.6 + density * 0.4, 0.2, 0.8);

  // 3. Смешиваем цвета
  vec3 color = mix(fragColor1, fragColor2, mixFactor);

  // 4. Бас дает пульсацию (всего 0.3, чтобы не выжигать в белый)
  color *= (1.0 + fragBass * 0.3);

  // 5. Убираем сильный белый засвет (теперь только на самых-самых пиках)
  float specular = smoothstep(0.95, 1.0, value) * 0.15;
  color = mix(color, vec3(1.0), specular);

  outColor = vec4(color * value, value);
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
      // Основной (каноничный NCS) + Акцент (близкий оттенок)
      drumstep:       [1.0,   0.0,   0.0,     0.6,   0.0,   0.0  ], // Чистый красный Roy Knox + Тёмно-красный
      indieDance:     [1.0,   0.647, 0.0,     0.85,  0.35,  0.0  ], // Оранжевый + Жжёный оранжевый
      house:          [1.0,   1.0,   0.0,     0.85,  0.75,  0.0  ], // Жёлтый + Золотой
      trap:           [0.478, 0.992, 0.251,   0.25,  0.80,  0.35 ], // #7afd40 + Тёмно-зелёный
      glitchHop:      [0.2,   0.9,   0.5,     0.6,   1.0,   0.8  ], // Насыщенная мята + Светлая мята
      melodicDubstep: [0.227, 1.0,   0.945,   0.1,   0.75,  0.9  ], // #3afff1 + Глубокий аквамарин
      dubstep:        [0.118, 0.463, 1.0,     0.15,  0.30,  0.80 ], // #1e76ff + Индиго
      futureHouse:    [0.15,  0.0,   0.5,     0.6,   0.2,   1.0  ], // Глубокий индиго (тень) + Неоновый фиолетовый (свет)
      futureBass:     [0.584, 0.439, 1.0,     0.65,  0.2,   1.0  ], // #9570ff (база) + Глубокий неоновый фиолетовый
      // futureHouse:    [0.443, 0.165, 0.961,   0.6,   0.25,  0.95 ], // #712af5 (глубокий) + Умеренный фиолетовый
      // futureBass:     [0.584, 0.439, 1.0,     0.75,  0.65,  1.0  ], // #9570ff (лаванда) + Светящаяся лаванда
      drumAndBass:    [1.0,   0.196, 0.969,   0.75,  0.05,  0.65 ], // #ff32f7 + Тёмная фуксия
      witchHouse:     [1.0,  1.0,   1.0,      0.9,   0.5,   0.7  ], // Белый + Светло-розовый
      electronic:     [1.0,   1.0,   1.0,     0.75,  0.85,  1.0  ], // Белый + Бледно-голубой
      miscellaneous:  [0.0,   0.0,   0.0,     0.15,  0.15,  0.15 ], // Чёрный + Тёмно-серый
    };

  static i = -1;

  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.options = { dotCount: 322, color: [1.0,   1.0,   1.0,     0.75,  0.85,  1.0  ], ...options };
    const c = this.options.color;
    if (c.length === 3) {
      this.options.color = [...c, c[0]*0.5, c[1]*0.5, c[2]*0.5];
    }
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
    this._seed = 0;
    this._lastFrameTime = 0;
    this._running = false;
    this._animId = null;
    this._vpSize = 0;
    this._ampBuffer = new Float32Array(8);
    this._freqData = null;
    this._currentColor = [...this.options.color];
    this._targetColor = [...this.options.color];
    this.rainbowMode = false;
    this._rainbowHue = 0;
    this._initGL();
    this._initFBOs();
    this._onResize = () => this._resize();
    window.addEventListener('resize', this._onResize);
    this._resize();
  }

  static get COLORS() {
    return this.NCS_GENRE_COLORS;
  }

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
    }
  }

  setRainbowMode(enabled) {
    this.rainbowMode = enabled;
  }

  setListening(enabled) {
    this.isListening = enabled;
    this._targetListeningScale = enabled ? 1.3 : 1.0;
  }

  setPulsationStrength(value) {
    this.pulsationStrength = Math.max(0.0, value);
  }

  setAudioNodes(audioCtx, analyserNode, audioElement, seed) {
    if (this.sourceNode) { try { this.sourceNode.disconnect(); } catch (e) {} this.sourceNode = null; }
    if (this.analyserNode && this.analyserNode !== analyserNode) { try { this.analyserNode.disconnect(); } catch (e) {} }
    this.audioCtx = audioCtx;
    this.analyserNode = analyserNode;
    this.audioElement = audioElement;
    this._seed = seed || 0;
    this._amplitudeIntegral = 0;
    this._smoothAmp = 0;
    this._smoothBass = 0;
    this._ampVelocity = 0;
    this._demoTime = 0;
    this._ampBuffer.fill(0);
    if (analyserNode) {
      this._freqData = new Uint8Array(analyserNode.frequencyBinCount);
    } else {
      this._freqData = null;
    }
  }

  _initGL() {
    const gl = this.canvas.getContext('webgl2', { alpha: true, antialias: false });
    if (!gl) throw new Error('WebGL2 not supported');
    this.gl = gl;
    if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('EXT_color_buffer_float is required');

    const cs = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        const err = gl.getShaderInfoLog(s);
        gl.deleteShader(s);
        throw new Error(err);
      }
      return s;
    };
    const cp = (vs, fs) => {
      const p = gl.createProgram();
      gl.attachShader(p, vs);
      gl.attachShader(p, fs);
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
        const err = gl.getProgramInfoLog(p);
        gl.deleteProgram(p);
        throw new Error(err);
      }
      return p;
    };

    this._prog = {
      p: cp(cs(gl.VERTEX_SHADER, PARTICLE_VS), cs(gl.FRAGMENT_SHADER, PARTICLE_FS)),
      d: cp(cs(gl.VERTEX_SHADER, DOT_VS), cs(gl.FRAGMENT_SHADER, DOT_FS)),
      b: cp(cs(gl.VERTEX_SHADER, BLUR_VS), cs(gl.FRAGMENT_SHADER, BLUR_FS)),
      f: cp(cs(gl.VERTEX_SHADER, FINAL_VS), cs(gl.FRAGMENT_SHADER, FINAL_FS)),
    };

    this.quadBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,-1,1,1,1,1,-1]), gl.STATIC_DRAW);

    const U = (prog, name) => gl.getUniformLocation(prog, name);
    const A = (prog, name) => gl.getAttribLocation(prog, name);

    const p = this._prog.p;
    this._u = {
      pInPos: A(p, 'inPosition'),
      uNoiseOffset: U(p, 'uNoiseOffset'),
      uAmplitude: U(p, 'uAmplitude'),
      uSeed: U(p, 'uSeed'),
      uDotSpacing: U(p, 'uDotSpacing'),
      uDotOffset: U(p, 'uDotOffset'),
      uSphereRadius: U(p, 'uSphereRadius'),
      uFeather: U(p, 'uFeather'),
      uNoiseFreq: U(p, 'uNoiseFrequency'),
      uNoiseAmp: U(p, 'uNoiseAmplitude'),
      uCenterPush: U(p, 'uCenterPush'),
    };

    const d = this._prog.d;
    this._u.dInPos = A(d, 'inPosition');
    this._u.uDotCount = U(d, 'uDotCount');
    this._u.uDotRadius = U(d, 'uDotRadius');
    this._u.uDotRadiusPX = U(d, 'uDotRadiusPX');
    this._u.uParticleTex = U(d, 'uParticleTexture');
    this._u.uAspectRatio = U(d, 'uAspectRatio');
    this._u.uCenterFade = U(d, 'uCenterFade');

    const b = this._prog.b;
    this._u.bInPos = A(b, 'inPosition');
    this._u.uBlurRadius = U(b, 'uBlurRadius');
    this._u.uBlurDir = U(b, 'uBlurDirection');
    this._u.uBlurInput = U(b, 'uInputTexture');

    const f = this._prog.f;
    this._u.fInPos = A(f, 'inPosition');
    this._u.uOutputColor1 = U(f, 'uOutputColor1');
    this._u.uOutputColor2 = U(f, 'uOutputColor2');
    this._u.uBass = U(f, 'uBass');
    this._u.uTime = U(f, 'uTime');
    this._u.uBlurredTex = U(f, 'uBlurredTexture');
    this._u.uOriginalTex = U(f, 'uOriginalTexture');

    gl.enable(gl.BLEND);
    gl.blendEquation(gl.MAX);
    gl.clearColor(0, 0, 0, 0);
  }

  _createFB(internalFormat, format, type, filter) {
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
    return { fb, tex, internalFormat, format, type };
  }

  _initFBOs() {
    const gl = this.gl;
    const dc = this.options.dotCount;
    this._pf = this._createFB(gl.RG32F, gl.RG, gl.FLOAT, gl.NEAREST);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG32F, dc, dc, 0, gl.RG, gl.FLOAT, null);
    this._prevDotCount = dc;
    this._df = this._createFB(gl.R8, gl.RED, gl.UNSIGNED_BYTE, gl.NEAREST);
    this._bxf = this._createFB(gl.R8, gl.RED, gl.UNSIGNED_BYTE, gl.LINEAR);
    this._byf = this._createFB(gl.R8, gl.RED, gl.UNSIGNED_BYTE, gl.NEAREST);
    this._dotCount = dc;
    this._pf_tex = this._pf.tex;
    this._pf_fb = this._pf.fb;
    this._df_tex = this._df.tex;
    this._df_fb = this._df.fb;
    this._bxf_tex = this._bxf.tex;
    this._bxf_fb = this._bxf.fb;
    this._byf_tex = this._byf.tex;
    this._byf_fb = this._byf.fb;
  }

  _resize() {
    const gl = this.gl;
    const dpr = window.devicePixelRatio || 1;
    const cw = this.canvas.clientWidth;
    const ch = this.canvas.clientHeight;
    if (cw < 1 || ch < 1) return;
    const pw = Math.round(cw * dpr);
    const ph = Math.round(ch * dpr);
    if (this.canvas.width === pw && this.canvas.height === ph) return;
    this.canvas.width = pw;
    this.canvas.height = ph;
    this._w = pw;
    this._h = ph;
    const size = Math.min(pw, ph);
    this._vpSize = size;
    this._vpX = Math.round((pw - size) / 2);
    this._vpY = Math.round((ph - size) / 2);
    this._aspect = 1;
    this._blurRadius = 0.01 * size;
    this._invSize = 1 / size;
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.bindTexture(gl.TEXTURE_2D, this._df_tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, this._df.internalFormat, size, size, 0, this._df.format, this._df.type, null);
    gl.bindTexture(gl.TEXTURE_2D, this._bxf_tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, this._bxf.internalFormat, size, size, 0, this._bxf.format, this._bxf.type, null);
    gl.bindTexture(gl.TEXTURE_2D, this._byf_tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, this._byf.internalFormat, size, size, 0, this._byf.format, this._byf.type, null);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
  }

  loadAudio(file) {
    if (this.audioElement) { this.audioElement.pause(); this.audioElement = null; }
    if (!this.audioCtx) this.audioCtx = new AudioContext();
    const url = URL.createObjectURL(file);
    this.audioElement = new Audio(url);
    this.audioElement.crossOrigin = 'anonymous';
    this.sourceNode = this.audioCtx.createMediaElementSource(this.audioElement);
    this.analyserNode = this.audioCtx.createAnalyser();
    this.analyserNode.fftSize = 2048;
    this.analyserNode.smoothingTimeConstant = 0.85;
    this.sourceNode.connect(this.analyserNode);
    this.analyserNode.connect(this.audioCtx.destination);
    this.audioElement.addEventListener('ended', () => { this.isPlaying = false; });
    this.isPlaying = false;
    this._amplitudeIntegral = 0;
    this._smoothAmp = 0;
    this._smoothBass = 0;
    this._seed = Date.now() | 0;
    this._demoTime = 0;
    this._ampBuffer.fill(0);
    this._freqData = new Uint8Array(this.analyserNode.frequencyBinCount);
  }

  playFromUrl(url) {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement = null;
    }
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

  play() {
    if (!this.audioElement) return;
    if (this.audioCtx?.state === 'suspended') this.audioCtx.resume();
    this.audioElement.play();
    this.isPlaying = true;
  }

  pause() {
    if (!this.audioElement) return;
    this.audioElement.pause();
    this.isPlaying = false;
  }

  togglePlay() { if (this.isPlaying) this.pause(); else this.play(); }
  get isActive() { return this.isPlaying; }
  get hasAudio() { return !!this.audioElement; }
  start() { this._running = true; this._render(0); }

  destroy() {
    this._running = false;
    if (this._animId) cancelAnimationFrame(this._animId);
    if (this.audioElement) { this.audioElement.pause(); this.audioElement = null; }
    if (this.sourceNode) { this.sourceNode.disconnect(); this.sourceNode = null; }
    if (this.analyserNode) { this.analyserNode.disconnect(); this.analyserNode = null; }
    window.removeEventListener('resize', this._onResize);
  }

    _getBassAmplitude() {
      if (!this.analyserNode || !this.isPlaying) {
        this._demoTime += 0.016;
        const wave1 = Math.sin(this._demoTime * 1.5) * 0.09;
        const wave2 = Math.sin(this._demoTime * 0.8) * 0.06;
        const wave3 = Math.sin(this._demoTime * 0.3) * 0.035;
        const demo = 0.15 + wave1 + wave2 + wave3;
        return Math.max(0.05, demo);
      }
      const binCount = this.analyserNode.frequencyBinCount;
      if (!this._freqData || this._freqData.length !== binCount) {
        this._freqData = new Uint8Array(binCount);
      }
      this.analyserNode.getByteFrequencyData(this._freqData);
      const bins = binCount;
      const binHz = this.audioCtx.sampleRate / this.analyserNode.fftSize;
      const lo = Math.floor(20 / binHz);
      const hi = Math.min(bins - 1, Math.ceil(150 / binHz));
      let sumSq = 0, weightSum = 0;
      for (let i = lo; i <= hi; i++) {
        const hz = i * binHz;
        const v = this._freqData[i] / 255;
        const dist = hz - 70;
        const weight = Math.exp(-(dist * dist) / (2 * 40 * 40));
        sumSq += v * v * weight;
        weightSum += weight;
      }
      const bassRMS = weightSum > 0 ? Math.sqrt(sumSq / weightSum) : 0;
      this._smoothBass += (bassRMS - this._smoothBass) * 0.06;
      const delta = Math.max(0, bassRMS - this._smoothBass);
      const base = bassRMS * 0.75 + 0.1;
      const boost = delta * 5.0;
      return Math.min(1, base + boost);
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

    const dotCount = this._dotCount;
    const size = this._vpSize;
    const u = this._u;
    const pp = this._prog;
    const progress = this.audioElement?.currentTime ?? this._demoTime;
    const dt = this._lastFrameTime ? (time - this._lastFrameTime) / 1000 : 1 / 60;
    this._lastFrameTime = time;

    const rawAmp = this._getBassAmplitude();
    const stiffness = 220.0;
    const damping = 14.0;
    const clampedDt = Math.min(dt, 0.1);
    const force = stiffness * (rawAmp - this._smoothAmp) - damping * this._ampVelocity;
    this._ampVelocity += force * clampedDt;
    this._smoothAmp += this._ampVelocity * clampedDt;
    this._smoothAmp = Math.max(0.0, this._smoothAmp);

    const uAmplitude = this._smoothAmp * this.pulsationStrength;
    this._amplitudeIntegral += uAmplitude * dt * 3;
    const uNoiseOffset = (0.5 * progress + this._amplitudeIntegral) * 0.75;
    this._listeningScale += (this._targetListeningScale - this._listeningScale) * 0.05;
    let ampReaction = this.isListening ? 0.05 : 0.2;
    let currentRadius = 0.6 + uAmplitude * ampReaction;
    currentRadius *= this._listeningScale;
    if (this.isListening) {
      currentRadius += Math.sin(time * 0.002) * 0.01;
    }
    const uSphereRadius = currentRadius;
    const uDotRadius = (0.9 / dotCount) * this._listeningScale;
    const uDotRadiusPX = uDotRadius * 0.5 * size;
    const amp3 = uAmplitude + 3;
    const uFeather = amp3 * amp3 * (45 / 1568);

    // === Pass 1: particles → _pf_fb ===
    gl.disable(gl.BLEND);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this._pf_fb);
    gl.viewport(0, 0, dotCount, dotCount);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(pp.p);
    gl.uniform1f(u.uNoiseOffset, uNoiseOffset);
    gl.uniform1f(u.uAmplitude, uAmplitude);
    gl.uniform1i(u.uSeed, this._seed);
    gl.uniform1f(u.uDotSpacing, 0.9);
    gl.uniform1f(u.uDotOffset, -0.45);
    gl.uniform1f(u.uSphereRadius, uSphereRadius);
    gl.uniform1f(u.uFeather, uFeather);
    gl.uniform1f(u.uNoiseFreq, 4);
    gl.uniform1f(u.uNoiseAmp, 0.288);
    gl.uniform1f(u.uCenterPush, 0.45);
    this._drawQuad(u.pInPos);

    if (this._prevDotCount !== dotCount) {
      gl.bindTexture(gl.TEXTURE_2D, this._pf_tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG32F, dotCount, dotCount, 0, gl.RG, gl.FLOAT, null);
      this._prevDotCount = dotCount;
    }

    // === Pass 2: dots → _df_fb ===
    gl.enable(gl.BLEND);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this._df_fb);
    gl.viewport(0, 0, size, size);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(pp.d);
    gl.uniform1i(u.uDotCount, dotCount);
    gl.uniform1f(u.uDotRadius, uDotRadius);
    gl.uniform1f(u.uDotRadiusPX, uDotRadiusPX);
    gl.uniform1f(u.uAspectRatio, 1.0);
    gl.uniform1f(u.uCenterFade, 0.2);
    gl.uniform1i(u.uParticleTex, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this._pf_tex);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    gl.enableVertexAttribArray(u.dInPos);
    gl.vertexAttribPointer(u.dInPos, 2, gl.FLOAT, false, 0, 0);
    gl.drawArraysInstanced(gl.TRIANGLE_FAN, 0, 4, dotCount * dotCount);

    // === Pass 3: horizontal blur ===
    gl.bindFramebuffer(gl.FRAMEBUFFER, this._bxf_fb);
    gl.viewport(0, 0, size, size);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(pp.b);
    gl.uniform1f(u.uBlurRadius, this._blurRadius);
    gl.uniform2f(u.uBlurDir, this._invSize, 0);
    gl.uniform1i(u.uBlurInput, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this._df_tex);
    this._drawQuad(u.bInPos);

    // === Pass 4: vertical blur ===
    gl.bindFramebuffer(gl.FRAMEBUFFER, this._byf_fb);
    gl.viewport(0, 0, size, size);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform2f(u.uBlurDir, 0, this._invSize);
    gl.bindTexture(gl.TEXTURE_2D, this._bxf_tex);
    this._drawQuad(u.bInPos);

    // === Pass 5: composite → canvas ===
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this._w, this._h);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.viewport(this._vpX, this._vpY, size, size);
    gl.useProgram(pp.f);
    if (this.rainbowMode) {
      const speed = 0.05 + uAmplitude * 0.2;
      this._rainbowHue = (this._rainbowHue + speed * dt) % 1.0;
      const hsvToRgb = (h, s, v) => {
        let r, g, b;
        const i = Math.floor(h * 6);
        const f = h * 6 - i;
        const p = v * (1 - s);
        const q = v * (1 - f * s);
        const t = v * (1 - (1 - f) * s);
        switch (i % 6) {
          case 0: r = v; g = t; b = p; break;
          case 1: r = q; g = v; b = p; break;
          case 2: r = p; g = v; b = t; break;
          case 3: r = p; g = q; b = v; break;
          case 4: r = t; g = p; b = v; break;
          case 5: r = v; g = p; b = q; break;
        }
        return [r, g, b];
      };
      const baseColor = hsvToRgb(this._rainbowHue, 1.0, 1.0);
      const accentColor = hsvToRgb((this._rainbowHue + 0.1) % 1.0, 1.0, 0.8);
      this._targetColor = [...baseColor, ...accentColor];
    }
    const colorLerpFactor = Math.min(1.0, dt * 3.0);
    for (let i = 0; i < 6; i++) {
      this._currentColor[i] += (this._targetColor[i] - this._currentColor[i]) * colorLerpFactor;
    }
    gl.uniform3f(u.uOutputColor1, this._currentColor[0], this._currentColor[1], this._currentColor[2]);
    gl.uniform3f(u.uOutputColor2, this._currentColor[3], this._currentColor[4], this._currentColor[5]);
    gl.uniform1f(u.uTime, time * 0.001);
    gl.uniform1i(u.uBlurredTex, 0);
    gl.uniform1i(u.uOriginalTex, 1);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this._byf_tex);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this._df_tex);
    this._drawQuad(u.fInPos);
  }
}
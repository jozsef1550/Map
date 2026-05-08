/**
 * Parchment shader — sepia-toned ancient map look.
 * Applied as a Three.js ShaderMaterial post-process pass.
 */

export const parchmentVertexShader = /* glsl */`
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

export const parchmentFragmentShader = /* glsl */`
uniform sampler2D tMap;
uniform float uTime;
varying vec2 vUv;

// Pseudo-random noise for parchment texture
float rand(vec2 co) {
  return fract(sin(dot(co.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = rand(i);
  float b = rand(i + vec2(1.0, 0.0));
  float c = rand(i + vec2(0.0, 1.0));
  float d = rand(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void main() {
  vec4 texColor = texture2D(tMap, vUv);

  // Convert to greyscale
  float grey = dot(texColor.rgb, vec3(0.299, 0.587, 0.114));

  // Sepia toning
  vec3 sepia = vec3(
    clamp(grey * 1.10 + 0.12, 0.0, 1.0),
    clamp(grey * 0.94 + 0.06, 0.0, 1.0),
    clamp(grey * 0.74,        0.0, 1.0)
  );

  // Paper grain
  float grain = noise(vUv * 300.0) * 0.06 - 0.03;
  sepia += grain;

  // Edge darkening (vignette)
  vec2 uv2 = vUv * (1.0 - vUv.yx);
  float vignette = pow(uv2.x * uv2.y * 12.0, 0.3);
  sepia *= vignette;

  // Ink burn at corners
  float burn = 1.0 - smoothstep(0.3, 0.5, distance(vUv, vec2(0.5)));
  sepia = mix(sepia * 0.6, sepia, burn);

  gl_FragColor = vec4(sepia, texColor.a);
}
`

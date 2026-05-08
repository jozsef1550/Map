/**
 * 8-bit JRPG shader — posterised palette with scanlines.
 */

export const jrpgVertexShader = /* glsl */`
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

export const jrpgFragmentShader = /* glsl */`
uniform sampler2D tMap;
uniform vec2 uResolution;
varying vec2 vUv;

void main() {
  // Pixelate: snap UV to 4×4 pixel blocks
  float blockSize = 4.0;
  vec2 snapped = floor(vUv * uResolution / blockSize) * blockSize / uResolution;
  vec4 texColor = texture2D(tMap, snapped);

  // Posterise to 4 levels per channel
  float levels = 4.0;
  vec3 posterised = floor(texColor.rgb * levels) / (levels - 1.0);

  // Scanlines
  float scanline = mod(floor(vUv.y * uResolution.y / blockSize), 2.0);
  posterised *= 0.88 + scanline * 0.12;

  // Slight colour boost
  posterised = pow(posterised, vec3(0.9));

  gl_FragColor = vec4(posterised, texColor.a);
}
`

/**
 * Topographic / Satellite shader.
 * Adds contour lines, hillshade, and optional satellite-style colour grading.
 */

export const topoVertexShader = /* glsl */`
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

export const topoFragmentShader = /* glsl */`
uniform sampler2D tMap;
uniform sampler2D tHeight;
uniform float uContourInterval;  // e.g. 0.05
uniform float uHillshade;        // 0-1
uniform bool uSatellite;
varying vec2 vUv;

void main() {
  vec4 biomeColor = texture2D(tMap, vUv);
  float h  = texture2D(tHeight, vUv).r;

  // Contour lines: highlight at fixed intervals
  float contour = fract(h / uContourInterval);
  float line = 1.0 - smoothstep(0.0, 0.06, min(contour, 1.0 - contour));
  vec3 col = biomeColor.rgb * (1.0 - line * 0.4);

  // Simple hillshade from height gradient (approx)
  float hR  = texture2D(tHeight, vUv + vec2(0.003, 0.0)).r;
  float hU  = texture2D(tHeight, vUv + vec2(0.0, 0.003)).r;
  float gx  = (hR - h) * 30.0;
  float gy  = (hU - h) * 30.0;
  vec3  lightDir = normalize(vec3(-1.0, -1.0, 2.0));
  vec3  normal   = normalize(vec3(-gx, -gy, 1.0));
  float shade    = clamp(dot(normal, lightDir), 0.2, 1.0);
  col *= mix(1.0, shade, uHillshade);

  // Satellite-style: boost saturation
  if (uSatellite) {
    float grey = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(grey), col, 1.5);
  }

  gl_FragColor = vec4(col, biomeColor.a);
}
`

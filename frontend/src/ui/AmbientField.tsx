import { useEffect, useRef } from "react";
import type * as Three from "three";

import { isTestMode, pointerState, prefersReduced, scrollState } from "./motion";

const VERTEX_SHADER = /* glsl */ `
  uniform float uTime;
  uniform float uPixelRatio;
  uniform vec2 uPointer;
  uniform float uPointerStrength;
  varying float vAlpha;
  varying float vLift;

  void main() {
    vec3 p = position;
    float wave =
      sin(p.x * 0.42 + uTime * 0.55) * 0.34 +
      sin(p.z * 0.61 - uTime * 0.42) * 0.3 +
      sin((p.x + p.z) * 0.24 + uTime * 0.3) * 0.36;
    float reach = distance(p.xz, uPointer);
    float lift = exp(-reach * reach * 0.22) * uPointerStrength;
    p.y += wave + lift * 1.5;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;

    float depth = -mv.z;
    gl_PointSize = (2.1 + wave * 1.1 + lift * 3.2) * uPixelRatio * (16.0 / depth);
    // fade toward the horizon and at the near edge
    float fade = smoothstep(46.0, 16.0, depth) * smoothstep(3.0, 8.0, depth);
    vAlpha = fade * (0.34 + wave * 0.22 + lift * 0.5);
    vLift = lift;
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  precision mediump float;
  uniform vec3 uInk;
  uniform vec3 uAccent;
  varying float vAlpha;
  varying float vLift;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float disc = smoothstep(0.5, 0.32, d);
    vec3 color = mix(uInk, uAccent, clamp(vLift * 1.4, 0.0, 1.0));
    gl_FragColor = vec4(color, disc * vAlpha);
  }
`;

const COLUMNS = 132;
const ROWS = 54;
const SPACING = 0.62;

/**
 * Ambient backdrop for the workspace: a field of ledger dots rolling like a
 * slow swell, lifting where the pointer passes. One Three.js draw call with a
 * small shader. Decorative, aria-hidden, paused off-screen, static under
 * reduced motion and absent in tests or without WebGL.
 */
export default function AmbientField({ className }: { className?: string }) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || isTestMode()) return;
    if (!("WebGLRenderingContext" in window) && !("WebGL2RenderingContext" in window)) return;

    const canvas = document.createElement("canvas");
    host.appendChild(canvas);
    let cancelled = false;
    let dispose: (() => void) | null = null;

    const start = async () => {
      let THREE: typeof Three;
      try {
        THREE = await import("three");
      } catch {
        return;
      }
      if (cancelled) return;

      let renderer: Three.WebGLRenderer;
      try {
        renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
      } catch {
        return;
      }
      const reduced = prefersReduced();
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.75);
      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(pixelRatio);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 120);
      camera.position.set(0, 6.4, 19);
      camera.lookAt(0, 0.4, -6);

      const positions = new Float32Array(COLUMNS * ROWS * 3);
      let offset = 0;
      for (let row = 0; row < ROWS; row += 1) {
        for (let column = 0; column < COLUMNS; column += 1) {
          positions[offset] = (column - (COLUMNS - 1) / 2) * SPACING;
          positions[offset + 1] = 0;
          positions[offset + 2] = (row - (ROWS - 1) / 2) * SPACING - 8;
          offset += 3;
        }
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

      const uniforms = {
        uTime: { value: 0 },
        uPixelRatio: { value: pixelRatio },
        uPointer: { value: new THREE.Vector2(999, 999) },
        uPointerStrength: { value: 0 },
        uInk: { value: new THREE.Color(0x0a1326) },
        uAccent: { value: new THREE.Color(0x1f4fe0) },
      };
      const material = new THREE.ShaderMaterial({
        uniforms,
        vertexShader: VERTEX_SHADER,
        fragmentShader: FRAGMENT_SHADER,
        transparent: true,
        depthTest: false,
        depthWrite: false,
      });
      const points = new THREE.Points(geometry, material);
      points.frustumCulled = false;
      scene.add(points);

      const raycaster = new THREE.Raycaster();
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
      const ndc = new THREE.Vector2();
      const hit = new THREE.Vector3();
      const pointerTarget = new THREE.Vector2(999, 999);
      let strengthTarget = 0;

      const resize = () => {
        const bounds = host.getBoundingClientRect();
        const width = Math.max(1, bounds.width);
        const height = Math.max(1, bounds.height);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
        renderer.render(scene, camera);
      };

      let previous = 0;
      let running = false;
      const tick = (now: number) => {
        const delta = previous ? Math.min((now - previous) / 1000, 0.05) : 0.016;
        previous = now;
        // scrolling stirs the swell a little faster
        uniforms.uTime.value += delta * (1 + Math.min(2.5, Math.abs(scrollState.velocity) / 900));

        const bounds = host.getBoundingClientRect();
        const inside =
          pointerState.active &&
          pointerState.y >= bounds.top &&
          pointerState.y <= bounds.bottom &&
          pointerState.x >= bounds.left &&
          pointerState.x <= bounds.right;
        if (inside) {
          ndc.set(
            ((pointerState.x - bounds.left) / bounds.width) * 2 - 1,
            -(((pointerState.y - bounds.top) / bounds.height) * 2 - 1),
          );
          raycaster.setFromCamera(ndc, camera);
          if (raycaster.ray.intersectPlane(plane, hit)) {
            pointerTarget.set(hit.x, hit.z);
            strengthTarget = 1;
          }
        } else {
          strengthTarget = 0;
        }
        uniforms.uPointer.value.lerp(pointerTarget, 0.12);
        uniforms.uPointerStrength.value += (strengthTarget - uniforms.uPointerStrength.value) * 0.08;
        renderer.render(scene, camera);
      };

      const setRunning = (next: boolean) => {
        if (reduced || next === running) return;
        running = next;
        previous = 0;
        renderer.setAnimationLoop(next ? tick : null);
      };

      let onScreen = true;
      const visibility =
        typeof IntersectionObserver === "undefined"
          ? null
          : new IntersectionObserver((entries) => {
              onScreen = entries.some((entry) => entry.isIntersecting);
              setRunning(onScreen && !document.hidden);
            });
      visibility?.observe(host);
      const onVisibilityChange = () => setRunning(onScreen && !document.hidden);
      document.addEventListener("visibilitychange", onVisibilityChange);
      const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
      resizeObserver?.observe(host);

      resize();
      host.dataset.ready = "true";
      if (!visibility) setRunning(true);

      dispose = () => {
        renderer.setAnimationLoop(null);
        visibility?.disconnect();
        resizeObserver?.disconnect();
        document.removeEventListener("visibilitychange", onVisibilityChange);
        geometry.dispose();
        material.dispose();
        renderer.dispose();
        renderer.forceContextLoss();
        delete host.dataset.ready;
      };
      if (cancelled) dispose();
    };

    void start();
    return () => {
      cancelled = true;
      dispose?.();
      canvas.remove();
    };
  }, []);

  return <div ref={hostRef} className={`ambient-field${className ? ` ${className}` : ""}`} aria-hidden="true" />;
}

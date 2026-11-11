import { useEffect, useRef } from "react";
import type * as Three from "three";
import type * as Cannon from "cannon-es";

import { isTestMode, pointerState, prefersReduced, scrollState } from "./motion";

interface ConvergenceSceneProps {
  className?: string;
  /** Where the bodies gather, as fractions of the stage from its top-left corner. */
  anchorX?: number;
  anchorY?: number;
  /**
   * Optional selector (resolved inside the stage's parent) for an element whose
   * centre is the gathering point. Lets CSS decide where the cluster lives at
   * each breakpoint; overrides anchorX / anchorY while the element exists.
   */
  anchorSelector?: string;
  /**
   * Optional selector (resolved inside the stage's parent) for text the bodies
   * must not fly across on their way in. They then arrive from the open sides.
   */
  avoidSelector?: string;
  /** Upper bound on bodies; small stages use fewer. */
  maxBodies?: number;
}

/** Porcelain, midnight, cobalt, mist and a little brass: the product palette as materials. */
const PALETTE = [
  { color: 0xffffff, roughness: 0.42, metalness: 0, clearcoat: 0, share: 0.34 },
  { color: 0x0b1632, roughness: 0.18, metalness: 0.12, clearcoat: 1, share: 0.22 },
  { color: 0x1f4fe0, roughness: 0.3, metalness: 0.04, clearcoat: 0.6, share: 0.19 },
  { color: 0xc6d2ea, roughness: 0.52, metalness: 0, clearcoat: 0, share: 0.17 },
  { color: 0xc49a45, roughness: 0.3, metalness: 0.85, clearcoat: 0, share: 0.08 },
] as const;

const FOV = 30;
const FIXED_STEP = 1 / 60;

/** How the bodies travel to the gathering point (world units, seconds). */
const APPROACH = {
  /** cruising speed far from the point */
  speed: 10,
  /** speed asked for per unit of remaining distance, so arrival eases out */
  ease: 3.2,
  /** how firmly the radial speed is corrected */
  gain: 7,
  /** cap on that correction: keeps a burst dramatic and the return gentle */
  limit: 60,
  /** sideways drift that keeps the settled cluster slowly turning */
  swirl: 2.6,
} as const;

/** Radius of the settled cluster, in body units, used to fit it to its well. */
const CLUSTER_SPAN = 7.1;

/** Small seeded generator so the arrangement is the same on every visit. */
function seeded(seed: number) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * "Bring your trade agreements together", literally: rigid bodies simulated
 * with cannon-es drift toward one point, pack into a cluster and react to the
 * pointer (push), a press on empty space (burst) and scroll (inertia).
 * Rendered with Three.js. Purely decorative: aria-hidden, no pointer capture,
 * static frame under reduced motion, nothing at all in tests or without WebGL.
 */
export default function ConvergenceScene({
  className,
  anchorX = 0.5,
  anchorY = 0.5,
  anchorSelector,
  avoidSelector,
  maxBodies = 34,
}: ConvergenceSceneProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const settings = useRef({ x: anchorX, y: anchorY, anchorSelector, avoidSelector, maxBodies });

  useEffect(() => {
    settings.current = { x: anchorX, y: anchorY, anchorSelector, avoidSelector, maxBodies };
  }, [anchorX, anchorY, anchorSelector, avoidSelector, maxBodies]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || isTestMode()) return;
    if (!("WebGLRenderingContext" in window) && !("WebGL2RenderingContext" in window)) return;

    // The canvas is created here rather than rendered by React so that every
    // mount owns a fresh WebGL context, which is released again on unmount.
    const canvas = document.createElement("canvas");
    host.appendChild(canvas);
    const bodyLimit = settings.current.maxBodies;

    let cancelled = false;
    let dispose: (() => void) | null = null;

    const start = async () => {
      let THREE: typeof Three;
      let CANNON: typeof Cannon;
      let RoomEnvironment: typeof import("three/addons/environments/RoomEnvironment.js").RoomEnvironment;
      try {
        [THREE, CANNON, { RoomEnvironment }] = await Promise.all([
          import("three"),
          import("cannon-es"),
          import("three/addons/environments/RoomEnvironment.js"),
        ]);
      } catch {
        return;
      }
      if (cancelled) return;

      let renderer: Three.WebGLRenderer;
      try {
        renderer = new THREE.WebGLRenderer({
          canvas,
          alpha: true,
          antialias: true,
          powerPreference: "high-performance",
        });
      } catch {
        return;
      }

      const reduced = prefersReduced();
      const random = seeded(20261111);

      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.NeutralToneMapping;
      renderer.toneMappingExposure = 1.08;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 200);
      const pmrem = new THREE.PMREMGenerator(renderer);
      const environment = pmrem.fromScene(new RoomEnvironment(), 0.03);
      scene.environment = environment.texture;
      scene.environmentIntensity = 0.85;

      const key = new THREE.DirectionalLight(0xffffff, 2.4);
      key.position.set(-7, 11, 14);
      key.castShadow = true;
      key.shadow.mapSize.set(1024, 1024);
      key.shadow.camera.near = 1;
      key.shadow.camera.far = 60;
      key.shadow.camera.left = -11;
      key.shadow.camera.right = 11;
      key.shadow.camera.top = 11;
      key.shadow.camera.bottom = -11;
      key.shadow.bias = -0.0006;
      key.shadow.normalBias = 0.03;
      key.shadow.radius = 5;
      scene.add(key, key.target);
      scene.add(new THREE.AmbientLight(0xe8eefc, 0.5));
      const rim = new THREE.PointLight(0x5b8cff, 160, 60, 1.6);
      rim.position.set(9, -7, 9);
      scene.add(rim);

      // ---- stage size drives how many bodies there are and how big they look
      const measure = () => {
        const bounds = host.getBoundingClientRect();
        return { width: Math.max(1, bounds.width), height: Math.max(1, bounds.height) };
      };
      let stage = measure();
      const count = Math.max(12, Math.min(bodyLimit, Math.round((stage.width * stage.height) / 34000)));
      let visibleWidth = 1;
      let visibleHeight = 1;
      const tanHalfFov = Math.tan((FOV * Math.PI) / 360);

      const attractor = new THREE.Vector3();
      const anchor = { x: settings.current.x, y: settings.current.y };
      /**
       * Resolve the gathering point: the anchor element's centre, else the props.
       * Returns the shorter side of the anchor element (0 when there is none).
       */
      const readAnchor = (bounds: DOMRect) => {
        const selector = settings.current.anchorSelector;
        const well = selector ? host.parentElement?.querySelector<HTMLElement>(selector) : null;
        const rect = well?.getBoundingClientRect();
        if (rect && rect.width > 0 && rect.height > 0 && bounds.width > 0 && bounds.height > 0) {
          anchor.x = (rect.left + rect.width / 2 - bounds.left) / bounds.width;
          anchor.y = (rect.top + rect.height / 2 - bounds.top) / bounds.height;
          return Math.min(rect.width, rect.height);
        }
        anchor.x = settings.current.x;
        anchor.y = settings.current.y;
        return 0;
      };
      const layout = () => {
        stage = measure();
        const wellSide = readAnchor(host.getBoundingClientRect());
        // keep bodies a comfortable size in CSS pixels whatever the stage is,
        // and small enough that the settled cluster stays inside its well
        let pixelsPerUnit = Math.min(58, Math.min(stage.width, stage.height * 1.25) / 11);
        if (wellSide > 0) pixelsPerUnit = Math.min(pixelsPerUnit, wellSide / CLUSTER_SPAN);
        pixelsPerUnit = Math.max(26, pixelsPerUnit);
        visibleHeight = stage.height / pixelsPerUnit;
        visibleWidth = stage.width / pixelsPerUnit;
        camera.aspect = stage.width / stage.height;
        camera.position.set(0, 0, visibleHeight / 2 / tanHalfFov);
        camera.updateProjectionMatrix();
        renderer.setSize(stage.width, stage.height, false);
      };
      const placeAttractor = (time: number) => {
        const drift = reduced ? 0 : 1;
        attractor.set(
          (anchor.x - 0.5) * visibleWidth + Math.sin(time * 0.31) * 0.35 * drift,
          (0.5 - anchor.y) * visibleHeight + Math.cos(time * 0.23) * 0.28 * drift,
          0,
        );
        key.target.position.copy(attractor);
        key.position.set(attractor.x - 7, attractor.y + 11, 14);
      };
      layout();
      placeAttractor(0);

      // ---- physics world: no gravity, bodies are pulled to the attractor
      const world = new CANNON.World({ gravity: new CANNON.Vec3(0, 0, 0) });
      world.broadphase = new CANNON.SAPBroadphase(world);
      world.allowSleep = false;
      (world.solver as Cannon.GSSolver).iterations = 8;
      world.defaultContactMaterial.friction = 0.12;
      world.defaultContactMaterial.restitution = 0.22;

      const geometry = new THREE.SphereGeometry(1, 48, 32);
      const materials = PALETTE.map(
        (entry) =>
          new THREE.MeshPhysicalMaterial({
            color: entry.color,
            roughness: entry.roughness,
            metalness: entry.metalness,
            clearcoat: entry.clearcoat,
            clearcoatRoughness: 0.18,
          }),
      );
      const pickMaterial = (roll: number) => {
        let total = 0;
        for (let index = 0; index < PALETTE.length; index += 1) {
          total += PALETTE[index].share;
          if (roll <= total) return materials[index];
        }
        return materials[0];
      };

      // Text the inbound paths keep clear of, as boxes in world units.
      const keepClear: Array<{ left: number; right: number; top: number; bottom: number }> = [];
      {
        const selector = settings.current.avoidSelector;
        const bounds = host.getBoundingClientRect();
        const blocks = selector ? host.parentElement?.querySelectorAll<HTMLElement>(selector) : null;
        blocks?.forEach((block) => {
          const rect = block.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0 || bounds.width <= 0 || bounds.height <= 0) return;
          keepClear.push({
            left: ((rect.left - bounds.left) / bounds.width - 0.5) * visibleWidth,
            right: ((rect.right - bounds.left) / bounds.width - 0.5) * visibleWidth,
            top: (0.5 - (rect.top - bounds.top) / bounds.height) * visibleHeight,
            bottom: (0.5 - (rect.bottom - bounds.top) / bounds.height) * visibleHeight,
          });
        });
      }
      /** Does the straight run from a start point to the gathering point cross the text? */
      const crossesText = (startX: number, startY: number, margin: number) => {
        for (const box of keepClear) {
          for (let sample = 0; sample <= 32; sample += 1) {
            const along = sample / 32;
            const x = startX + (attractor.x - startX) * along;
            const y = startY + (attractor.y - startY) * along;
            if (x > box.left - margin && x < box.right + margin && y > box.bottom - margin && y < box.top + margin) {
              return true;
            }
          }
        }
        return false;
      };

      const bodies: Array<{ body: Cannon.Body; mesh: Three.Mesh; radius: number }> = [];
      for (let index = 0; index < count; index += 1) {
        // a few large anchors, many small companions
        const size = random();
        const radius = index < 3 ? 1.02 + size * 0.22 : 0.4 + size * size * 0.62;
        let angle = random() * Math.PI * 2;
        const distance = 9 + random() * 8;
        // walk round the ring (by the golden angle) until the way in is clear
        for (let attempt = 0; attempt < 24; attempt += 1) {
          const startX = attractor.x + Math.cos(angle) * distance;
          const startY = attractor.y + Math.sin(angle) * distance * 0.8;
          if (!crossesText(startX, startY, radius + 0.25)) break;
          angle += 2.399963;
        }
        const body = new CANNON.Body({
          mass: radius * radius * radius * 3,
          shape: new CANNON.Sphere(radius),
          position: new CANNON.Vec3(
            attractor.x + Math.cos(angle) * distance,
            attractor.y + Math.sin(angle) * distance * 0.8,
            (random() - 0.5) * 6,
          ),
          linearDamping: 0.68,
          angularDamping: 0.45,
        });
        body.angularVelocity.set(random() - 0.5, random() - 0.5, random() - 0.5);
        world.addBody(body);

        const mesh = new THREE.Mesh(geometry, pickMaterial(random()));
        mesh.scale.setScalar(radius);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        scene.add(mesh);
        bodies.push({ body, mesh, radius });
      }

      // the pointer is a kinematic body: it shoves, it is never shoved
      const pointerBody = new CANNON.Body({
        type: CANNON.Body.KINEMATIC,
        shape: new CANNON.Sphere(1.55),
        position: new CANNON.Vec3(0, 0, 60),
      });
      world.addBody(pointerBody);

      const force = new CANNON.Vec3();
      const pointerTarget = new THREE.Vector3(0, 0, 60);
      let lastPress = pointerState.pressedAt;
      let elapsed = 0;

      const toWorld = (clientX: number, clientY: number, bounds: DOMRect, out: Three.Vector3) => {
        const nx = (clientX - bounds.left) / bounds.width - 0.5;
        const ny = 0.5 - (clientY - bounds.top) / bounds.height;
        return out.set(nx * visibleWidth, ny * visibleHeight, 0);
      };

      const applyForces = () => {
        // content scrolling past pushes the cluster the other way (inertia)
        const scrollPush = Math.max(-26, Math.min(26, -scrollState.velocity * 0.011));
        for (const { body } of bodies) {
          const dx = attractor.x - body.position.x;
          const dy = attractor.y - body.position.y;
          const dz = attractor.z - body.position.z;
          const distance = Math.hypot(dx, dy, dz) || 1;
          const towardX = dx / distance;
          const towardY = dy / distance;
          const towardZ = dz / distance;
          // Steer the speed *toward* the point to what the remaining distance
          // calls for: bodies cruise in, ease out and stop without swinging
          // past. Sideways motion is left alone, so the cluster keeps turning.
          const closing = body.velocity.x * towardX + body.velocity.y * towardY + body.velocity.z * towardZ;
          const wanted = Math.min(APPROACH.speed, distance * APPROACH.ease);
          const push = Math.max(-APPROACH.limit, Math.min(APPROACH.limit, (wanted - closing) * APPROACH.gain));
          force.set(
            towardX * push - towardY * APPROACH.swirl,
            towardY * push + towardX * APPROACH.swirl + scrollPush,
            towardZ * push * 1.25,
          );
          force.scale(body.mass, force);
          body.applyForce(force);
        }
      };

      const burst = (origin: Three.Vector3) => {
        for (const { body } of bodies) {
          const dx = body.position.x - origin.x;
          const dy = body.position.y - origin.y;
          const dz = body.position.z - origin.z + 0.4;
          const distance = Math.hypot(dx, dy, dz) || 1;
          const strength = (34 / (1 + distance * 0.35)) * body.mass;
          body.applyImpulse(new CANNON.Vec3((dx / distance) * strength, (dy / distance) * strength, (dz / distance) * strength));
        }
      };

      const sync = () => {
        for (const { body, mesh } of bodies) {
          mesh.position.set(body.position.x, body.position.y, body.position.z);
          mesh.quaternion.set(body.quaternion.x, body.quaternion.y, body.quaternion.z, body.quaternion.w);
        }
      };

      // Forces are cleared after every internal step, so they are applied from
      // the solver's pre-step hook: the pull is then the same at any frame rate.
      world.addEventListener("preStep", applyForces);

      const settle = (steps: number) => {
        for (let step = 0; step < steps; step += 1) world.step(FIXED_STEP);
      };

      // arrive mid-flight; under reduced motion arrive already gathered
      settle(reduced ? 520 : 26);
      sync();
      renderer.render(scene, camera);
      host.dataset.ready = "true";

      let previous = 0;
      let running = false;
      const tick = (now: number) => {
        const delta = previous ? Math.min((now - previous) / 1000, 0.05) : FIXED_STEP;
        previous = now;
        elapsed += delta;

        const bounds = host.getBoundingClientRect();
        readAnchor(bounds);
        placeAttractor(elapsed);
        const inside =
          pointerState.active &&
          pointerState.x >= bounds.left &&
          pointerState.x <= bounds.right &&
          pointerState.y >= bounds.top &&
          pointerState.y <= bounds.bottom;
        if (inside) {
          toWorld(pointerState.x, pointerState.y, bounds, pointerTarget);
          if (pointerBody.position.z > 30) {
            pointerBody.position.set(pointerTarget.x, pointerTarget.y, 0);
          }
          // chase the pointer with velocity so contact carries momentum
          pointerBody.velocity.set(
            (pointerTarget.x - pointerBody.position.x) * 24,
            (pointerTarget.y - pointerBody.position.y) * 24,
            -pointerBody.position.z * 24,
          );
        } else {
          pointerBody.velocity.set(0, 0, 0);
          pointerBody.position.set(0, 0, 60);
        }

        if (pointerState.pressedAt !== lastPress) {
          lastPress = pointerState.pressedAt;
          if (inside) burst(toWorld(pointerState.x, pointerState.y, bounds, new THREE.Vector3()));
        }

        world.step(FIXED_STEP, delta, 3);
        sync();
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
          : new IntersectionObserver(
              (entries) => {
                onScreen = entries.some((entry) => entry.isIntersecting);
                setRunning(onScreen && !document.hidden);
              },
              { rootMargin: "80px" },
            );
      visibility?.observe(host);
      const onVisibilityChange = () => setRunning(onScreen && !document.hidden);
      document.addEventListener("visibilitychange", onVisibilityChange);

      const onResize = () => {
        layout();
        placeAttractor(elapsed);
        if (reduced) {
          settle(120);
          sync();
        }
        renderer.render(scene, camera);
      };
      const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(onResize);
      resizeObserver?.observe(host);

      if (!visibility) setRunning(true);

      dispose = () => {
        renderer.setAnimationLoop(null);
        visibility?.disconnect();
        resizeObserver?.disconnect();
        document.removeEventListener("visibilitychange", onVisibilityChange);
        geometry.dispose();
        materials.forEach((material) => material.dispose());
        environment.dispose();
        pmrem.dispose();
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

  return <div ref={hostRef} className={`convergence${className ? ` ${className}` : ""}`} aria-hidden="true" />;
}

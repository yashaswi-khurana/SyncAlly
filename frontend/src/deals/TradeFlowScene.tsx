import { useEffect, useRef } from "react";
import type * as Three from "three";
import { sceneState } from "../ui/motion";

export default function TradeFlowScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const host = canvas?.parentElement;
    if (!canvas || !host) {
      return;
    }
    if (!("WebGLRenderingContext" in window) && !("WebGL2RenderingContext" in window)) {
      return;
    }

    let cancelled = false;
    let started = false;
    let disposeScene: (() => void) | null = null;
    const startScene = async () => {
      if (started) {
        return;
      }
      started = true;

      let three: typeof import("three");
      let RoundedBoxGeometry: typeof import("three/addons/geometries/RoundedBoxGeometry.js").RoundedBoxGeometry;
      try {
        [three, { RoundedBoxGeometry }] = await Promise.all([
          import("three"),
          import("three/addons/geometries/RoundedBoxGeometry.js"),
        ]);
      } catch {
        return;
      }
      if (cancelled) {
        return;
      }

      let renderer: Three.WebGLRenderer;
      try {
        renderer = new three.WebGLRenderer({
          canvas,
          alpha: true,
          antialias: true,
          powerPreference: "low-power",
        });
      } catch {
        return;
      }

      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.outputColorSpace = three.SRGBColorSpace;

      const scene = new three.Scene();
      const camera = new three.OrthographicCamera(-3, 3, 1.7, -1.7, 0.1, 40);
      camera.position.set(0, 0, 10);

      const network = new three.Group();
      scene.add(network);
      scene.add(new three.HemisphereLight(0xfff4df, 0x20332c, 2.1));

      const buyerColor = 0xe36c48;
      const sellerColor = 0xa8d6b3;
      const paperColor = 0xf5edda;
      const buyer = new three.Vector3(-2.75, 0.02, 0);
      const seller = new three.Vector3(2.75, 0.02, 0);

      const addNode = (position: Three.Vector3, color: number) => {
        const group = new three.Group();
        group.position.copy(position);
        const sphere = new three.Mesh(
          new three.SphereGeometry(0.31, 32, 24),
          new three.MeshStandardMaterial({
            color,
            emissive: color,
            emissiveIntensity: 0.22,
            metalness: 0.32,
            roughness: 0.24,
          }),
        );
        group.add(sphere);

        const halo = new three.Mesh(
          new three.TorusGeometry(0.49, 0.012, 8, 72),
          new three.MeshBasicMaterial({ color, transparent: true, opacity: 0.7 }),
        );
        halo.rotation.x = -0.24;
        halo.rotation.y = 0.35;
        group.add(halo);
        network.add(group);
        return group;
      };

      const buyerNode = addNode(buyer, buyerColor);
      const sellerNode = addNode(seller, sellerColor);

      const upperRoute = new three.CubicBezierCurve3(
        buyer.clone(),
        new three.Vector3(-1.5, 1.34, -0.12),
        new three.Vector3(1.5, 1.34, -0.12),
        seller.clone(),
      );
      const lowerRoute = new three.CubicBezierCurve3(
        seller.clone(),
        new three.Vector3(1.5, -1.34, -0.12),
        new three.Vector3(-1.5, -1.34, -0.12),
        buyer.clone(),
      );

      for (const [route, color] of [
        [upperRoute, buyerColor],
        [lowerRoute, sellerColor],
      ] as const) {
        network.add(
          new three.Mesh(
            new three.TubeGeometry(route, 96, 0.012, 6, false),
            new three.MeshBasicMaterial({ color, transparent: true, opacity: 0.55 }),
          ),
        );
      }

      const record = new three.Group();
      record.position.set(0, 0, 0.35);
      record.rotation.set(-0.16, -0.2, -0.08);
      const card = new three.Mesh(
        new RoundedBoxGeometry(1.05, 1.38, 0.2, 5, 0.08),
        new three.MeshStandardMaterial({
          color: paperColor,
          roughness: 0.34,
          metalness: 0.04,
        }),
      );
      record.add(card);

      const ink = new three.MeshStandardMaterial({
        color: 0x263c31,
        roughness: 0.8,
      });
      const coral = new three.MeshStandardMaterial({
        color: buyerColor,
        emissive: buyerColor,
        emissiveIntensity: 0.15,
      });
      const addMark = (width: number, y: number, material: Three.Material, x = 0) => {
        const mark = new three.Mesh(new three.BoxGeometry(width, 0.035, 0.018), material);
        mark.position.set(x, y, 0.115);
        record.add(mark);
      };

      addMark(0.32, 0.4, coral, -0.22);
      addMark(0.62, 0.12, ink);
      addMark(0.62, -0.05, ink);
      addMark(0.45, -0.22, ink, -0.08);

      const seal = new three.Mesh(
        new three.CircleGeometry(0.12, 32),
        new three.MeshBasicMaterial({ color: 0x64876a }),
      );
      seal.position.set(0.29, -0.48, 0.12);
      record.add(seal);
      network.add(record);

      // direction §2: seal settles into gold as consensus rises
      const sealSettled = new three.Color(0x64876a);
      const sealGold = new three.Color(0xc28b38);

      const pulses = [
        { route: upperRoute, phase: 0, color: buyerColor },
        { route: upperRoute, phase: 0.5, color: paperColor },
        { route: lowerRoute, phase: 0.28, color: sellerColor },
        { route: lowerRoute, phase: 0.78, color: paperColor },
      ].map(({ route, phase, color }) => {
        const pulse = new three.Mesh(
          new three.SphereGeometry(0.052, 16, 12),
          new three.MeshBasicMaterial({ color }),
        );
        network.add(pulse);
        return { route, phase, pulse };
      });

      let width = 0;
      let height = 0;
      let frame = 0;
      let previousFrame = 0;
      let elapsed = 0;
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      const coarsePointer = window.matchMedia?.("(pointer: coarse)").matches ?? false;
      const parallaxEnabled = !reducedMotion && !coarsePointer;
      const parallax = { x: 0, y: 0, targetX: 0, targetY: 0 };
      let scrollYaw = 0;
      let scrollYawTarget = 0;
      const maxTilt = (8 * Math.PI) / 180; // ≤8° pointer parallax (direction §2)

      const handlePointerMove = (event: PointerEvent) => {
        if (!parallaxEnabled) return;
        const bounds = host.getBoundingClientRect();
        if (bounds.width === 0 || bounds.height === 0) return;
        const nx = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
        const ny = ((event.clientY - bounds.top) / bounds.height) * 2 - 1;
        parallax.targetX = Math.max(-1, Math.min(1, nx)) * maxTilt;
        parallax.targetY = Math.max(-1, Math.min(1, ny)) * maxTilt;
      };
      const handleScroll = () => {
        if (reducedMotion) return;
        scrollYawTarget = Math.max(-0.3, Math.min(0.3, window.scrollY * 0.0004));
      };
      if (parallaxEnabled) {
        host.addEventListener("pointermove", handlePointerMove);
      }
      if (!reducedMotion) {
        window.addEventListener("scroll", handleScroll, { passive: true });
      }
      for (const { route, phase, pulse } of pulses) {
        pulse.position.copy(route.getPointAt(phase));
      }

      const resize = () => {
        const bounds = host.getBoundingClientRect();
        width = Math.max(1, bounds.width);
        height = Math.max(1, bounds.height);
        const aspect = width / height;
        const halfHeight = Math.max(1.5, 2.55 / aspect);
        const halfWidth = halfHeight * aspect;
        camera.left = -halfWidth;
        camera.right = halfWidth;
        camera.top = halfHeight;
        camera.bottom = -halfHeight;
        camera.updateProjectionMatrix();
        network.scale.x = Math.min(1.4, (halfWidth * 0.9) / 3.3);
        renderer.setSize(width, height, false);
        renderer.render(scene, camera);
      };

      let consensusSmoothed = 0;
      const render = (now: number) => {
        if (now - previousFrame < 32) {
          frame = window.requestAnimationFrame(render);
          return;
        }
        const delta = Math.min((now - previousFrame) / 1000, 0.05);
        previousFrame = now;
        // reduced motion: time stays frozen (static frame) but state still applies
        if (!reducedMotion) {
          elapsed += delta;
          network.rotation.y = Math.sin(elapsed * 0.38) * 0.035;
          network.rotation.x = Math.sin(elapsed * 0.27) * 0.018;
          buyerNode.position.y = 0.02 + Math.sin(elapsed * 0.8) * 0.045;
          sellerNode.position.y = 0.02 + Math.sin(elapsed * 0.8 + Math.PI) * 0.045;
          for (const { route, phase, pulse } of pulses) {
            pulse.position.copy(route.getPointAt((elapsed * 0.12 + phase) % 1));
          }
          // damped pointer parallax (≤8°) + scroll-linked yaw (direction §2)
          parallax.x += (parallax.targetX - parallax.x) * 0.07;
          parallax.y += (parallax.targetY - parallax.y) * 0.07;
          scrollYaw += (scrollYawTarget - scrollYaw) * 0.05;
          network.rotation.y += parallax.x + scrollYaw;
          network.rotation.x += parallax.y;
        }

        // shared sceneState: orbit tightens, seal turns gold, record locks upright
        const consensusTarget = Math.max(0, Math.min(1, sceneState.consensus));
        consensusSmoothed += (consensusTarget - consensusSmoothed) * (reducedMotion ? 1 : 0.06);
        if (consensusSmoothed > 0.001) {
          const pull = consensusSmoothed * 0.28;
          buyerNode.position.x = -2.75 + pull;
          sellerNode.position.x = 2.75 - pull;
          seal.material.color.copy(sealSettled).lerp(sealGold, consensusSmoothed);
          record.rotation.y = -0.2 + consensusSmoothed * 0.2;
        }

        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(render);
      };

      resize();
      // always run: reduced-motion keeps time frozen (static frame) but must
      // still reflect sceneState changes such as a commitment landing
      frame = window.requestAnimationFrame(render);
      const handleVisibilityChange = () => {
        if (document.hidden) {
          window.cancelAnimationFrame(frame);
          frame = 0;
        } else if (frame === 0) {
          frame = window.requestAnimationFrame(render);
        }
      };
      const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
      resizeObserver?.observe(host);
      window.addEventListener("resize", resize);
      document.addEventListener("visibilitychange", handleVisibilityChange);

      disposeScene = () => {
        window.cancelAnimationFrame(frame);
        resizeObserver?.disconnect();
        window.removeEventListener("resize", resize);
        document.removeEventListener("visibilitychange", handleVisibilityChange);
        host.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("scroll", handleScroll);
        scene.traverse((object) => {
          if (object instanceof three.Mesh) {
            object.geometry.dispose();
            const materials = Array.isArray(object.material) ? object.material : [object.material];
            materials.forEach((material) => material.dispose());
          }
        });
        renderer.dispose();
      };
    };

    const observer = typeof IntersectionObserver === "undefined"
      ? null
      : new IntersectionObserver((entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            observer?.disconnect();
            void startScene();
          }
        }, { rootMargin: "120px" });
    if (observer) {
      observer.observe(host);
    } else {
      void startScene();
    }

    return () => {
      cancelled = true;
      observer?.disconnect();
      disposeScene?.();
    };
  }, []);

  return (
    <div className="trade-flow-scene">
      <svg className="trade-flow-scene__fallback" viewBox="0 0 720 180" aria-hidden="true">
        <path d="M50 92C170 4 250 4 360 92S550 180 670 92" />
        <path d="M50 92C170 180 250 180 360 92S550 4 670 92" />
        <circle cx="50" cy="92" r="8" />
        <circle cx="360" cy="92" r="14" />
        <circle cx="670" cy="92" r="8" />
      </svg>
      <canvas ref={canvasRef} aria-hidden="true" />
    </div>
  );
}

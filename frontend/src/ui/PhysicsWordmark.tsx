import { useEffect, useRef } from "react";
import type * as Cannon from "cannon-es";

import { isTestMode, pointerState, prefersReduced } from "./motion";

interface PhysicsWordmarkProps {
  text: string;
  className?: string;
}

/** Pixels per physics unit: keeps body sizes in the range the solver likes. */
const SCALE = 100;
const STEP = 1 / 60;
/** Spring that returns each letter to its place: stiffness and damping ratio. */
const SPRING = 64;
const SPRING_DAMPING = 2 * 0.5 * Math.sqrt(SPRING);
const TWIST = 34;
const TWIST_DAMPING = 2 * 0.42 * Math.sqrt(TWIST);
/** Seconds between one letter being let go and the next. */
const RELEASE_GAP = 0.055;

/**
 * The oversized wordmark that closes every page. Each letter is a rigid body
 * (cannon-es) tethered to its place by a spring: the letters drop in when the
 * footer scrolls into view, the pointer can knock them about, they collide
 * with one another and always settle back into the word. The simulation only
 * runs while something is moving. Decorative: aria-hidden, static under
 * reduced motion, not rendered in tests.
 */
export default function PhysicsWordmark({ text, className }: PhysicsWordmarkProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const plain = isTestMode();

  useEffect(() => {
    const host = hostRef.current;
    if (!host || plain || prefersReduced()) return;

    let cancelled = false;
    let dispose: (() => void) | null = null;

    const start = async () => {
      let CANNON: typeof Cannon;
      try {
        CANNON = await import("cannon-es");
        await document.fonts?.ready;
      } catch {
        host.dataset.ready = "true";
        return;
      }
      if (cancelled) return;

      const letters = Array.from(host.querySelectorAll<HTMLElement>(".wordmark__letter"));
      if (letters.length === 0) return;

      const world = new CANNON.World({ gravity: new CANNON.Vec3(0, 0, 0) });
      world.allowSleep = false;
      world.defaultContactMaterial.friction = 0.05;
      world.defaultContactMaterial.restitution = 0.45;

      type Item = { element: HTMLElement; body: Cannon.Body; homeX: number; homeY: number; releaseAt: number };
      let items: Item[] = [];
      let hostRect = host.getBoundingClientRect();
      let clock = 0;

      const pointerBody = new CANNON.Body({
        type: CANNON.Body.KINEMATIC,
        shape: new CANNON.Sphere(0.5),
        position: new CANNON.Vec3(0, 0, 50),
      });
      world.addBody(pointerBody);

      const build = (dropIn: boolean) => {
        for (const item of items) world.removeBody(item.body);
        hostRect = host.getBoundingClientRect();
        items = letters.map((element, index) => {
          element.style.transform = "";
          const rect = element.getBoundingClientRect();
          const homeX = (rect.left - hostRect.left + rect.width / 2) / SCALE;
          const homeY = -(rect.top - hostRect.top + rect.height / 2) / SCALE;
          const halfWidth = Math.max(0.08, (rect.width / 2 / SCALE) * 0.84);
          const halfHeight = Math.max(0.08, (rect.height / 2 / SCALE) * 0.56);
          const body = new CANNON.Body({
            mass: Math.max(0.4, halfWidth * halfHeight * 4),
            shape: new CANNON.Box(new CANNON.Vec3(halfWidth, halfHeight, 0.6)),
            position: new CANNON.Vec3(homeX, homeY, 0),
            linearDamping: 0.08,
            angularDamping: 0.12,
          });
          // keep the letters in the plane of the page
          body.linearFactor.set(1, 1, 0);
          body.angularFactor.set(0, 0, 1);
          if (dropIn) {
            body.position.y = homeY + 2.6 + (index % 3) * 0.3;
            body.quaternion.setFromEuler(0, 0, (index % 2 === 0 ? 1 : -1) * (0.3 + (index % 3) * 0.08));
          }
          world.addBody(body);
          // letters are let go one after another, left to right
          return { element, body, homeX, homeY, releaseAt: dropIn ? clock + index * RELEASE_GAP : 0 };
        });
      };

      const angleOf = (body: Cannon.Body) => 2 * Math.atan2(body.quaternion.z, body.quaternion.w);

      // Forces are cleared after every internal step, so the springs are applied
      // from the solver's own pre-step hook: the motion then looks the same at
      // any frame rate.
      world.addEventListener("preStep", () => {
        clock += STEP;
        for (const { body, homeX, homeY, releaseAt } of items) {
          if (clock < releaseAt) {
            body.velocity.set(0, 0, 0);
            body.angularVelocity.set(0, 0, 0);
            continue;
          }
          body.force.x += ((homeX - body.position.x) * SPRING - body.velocity.x * SPRING_DAMPING) * body.mass;
          body.force.y += ((homeY - body.position.y) * SPRING - body.velocity.y * SPRING_DAMPING) * body.mass;
          body.torque.z += (-angleOf(body) * TWIST - body.angularVelocity.z * TWIST_DAMPING) * body.inertia.z;
        }
      });

      const paint = () => {
        for (const { element, body, homeX, homeY } of items) {
          const dx = (body.position.x - homeX) * SCALE;
          const dy = -(body.position.y - homeY) * SCALE;
          element.style.transform = `translate3d(${dx.toFixed(2)}px, ${dy.toFixed(2)}px, 0) rotate(${(-angleOf(body)).toFixed(4)}rad)`;
        }
      };

      let frame = 0;
      let previous = 0;
      let visible = false;

      const tick = (now: number) => {
        frame = 0;
        const delta = previous ? Math.min((now - previous) / 1000, 0.05) : STEP;
        previous = now;

        hostRect = host.getBoundingClientRect();
        const reach = 90;
        const near =
          pointerState.active &&
          pointerState.x > hostRect.left - reach &&
          pointerState.x < hostRect.right + reach &&
          pointerState.y > hostRect.top - reach &&
          pointerState.y < hostRect.bottom + reach;
        if (near) {
          const targetX = (pointerState.x - hostRect.left) / SCALE;
          const targetY = -(pointerState.y - hostRect.top) / SCALE;
          if (pointerBody.position.z > 10) pointerBody.position.set(targetX, targetY, 0);
          pointerBody.velocity.set(
            (targetX - pointerBody.position.x) * 30,
            (targetY - pointerBody.position.y) * 30,
            0,
          );
        } else {
          pointerBody.velocity.set(0, 0, 0);
          pointerBody.position.set(0, 0, 50);
        }

        world.step(STEP, delta, 3);
        paint();

        let energy = 0;
        for (const { body, homeX, homeY } of items) {
          energy +=
            body.velocity.lengthSquared() +
            body.angularVelocity.z * body.angularVelocity.z +
            (homeX - body.position.x) ** 2 +
            (homeY - body.position.y) ** 2 +
            angleOf(body) ** 2;
        }

        const resting = energy < 0.00004 && !near;
        if (resting) {
          for (const { element, body, homeX, homeY } of items) {
            body.position.set(homeX, homeY, 0);
            body.velocity.set(0, 0, 0);
            body.angularVelocity.set(0, 0, 0);
            body.quaternion.set(0, 0, 0, 1);
            element.style.transform = "";
          }
          previous = 0;
          return;
        }
        if (visible) frame = window.requestAnimationFrame(tick);
      };

      const wake = () => {
        if (!frame && visible) frame = window.requestAnimationFrame(tick);
      };

      let entered = false;
      const observer =
        typeof IntersectionObserver === "undefined"
          ? null
          : new IntersectionObserver(
              (entries) => {
                visible = entries.some((entry) => entry.isIntersecting);
                if (!visible) return;
                if (!entered) {
                  entered = true;
                  build(true);
                  paint();
                  host.dataset.ready = "true";
                }
                wake();
              },
              { threshold: 0.2 },
            );

      if (observer) {
        observer.observe(host);
      } else {
        visible = true;
        entered = true;
        build(true);
        host.dataset.ready = "true";
        wake();
      }

      let resizeTimer = 0;
      const onResize = () => {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(() => {
          if (!entered) return;
          build(false);
          paint();
        }, 160);
      };
      window.addEventListener("resize", onResize);
      window.addEventListener("pointermove", wake, { passive: true });

      dispose = () => {
        if (frame) window.cancelAnimationFrame(frame);
        window.clearTimeout(resizeTimer);
        observer?.disconnect();
        window.removeEventListener("resize", onResize);
        window.removeEventListener("pointermove", wake);
        letters.forEach((element) => {
          element.style.transform = "";
        });
        delete host.dataset.ready;
      };
      if (cancelled) dispose();
    };

    void start();
    return () => {
      cancelled = true;
      dispose?.();
    };
  }, [plain, text]);

  if (plain) return null;
  return (
    <div ref={hostRef} className={`wordmark${className ? ` ${className}` : ""}`} aria-hidden="true">
      {Array.from(text).map((letter, index) => (
        <span key={`${index}:${letter}`} className="wordmark__letter">
          {letter}
        </span>
      ))}
    </div>
  );
}

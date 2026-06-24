"use client";

import { useEffect, useRef, useState } from "react";

type TrailPoint = { x: number; y: number; id: number };

function shortestAngleDelta(from: number, to: number): number {
  let delta = (to - from) % 360;
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;
  return delta;
}

export default function CuriosityRocket() {
  const [pos, setPos] = useState({ x: 0, y: 0, angle: 0 });
  const [trail, setTrail] = useState<TrailPoint[]>([]);

  const target = useRef({ x: 0, y: 0 });
  const current = useRef({ x: 0, y: 0 });
  const currentAngle = useRef(0);
  const trailIdRef = useRef(0);
  const rafRef = useRef<number>(0);
  const landedRef = useRef(false);
  const landingStartTime = useRef<number | null>(null);

  useEffect(() => {
    let t = 0;

    const handleScroll = () => {
      const scrollFraction = window.scrollY / Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const ctaEl = document.getElementById("final-cta-anchor");

      const wasLanded = landedRef.current;

      if (scrollFraction > 0.92 && ctaEl) {
        const rect = ctaEl.getBoundingClientRect();
        target.current = { x: rect.left - 44, y: rect.top + rect.height / 2 };
        landedRef.current = true;
        if (!wasLanded) {
          // Just started the landing approach — mark the moment so we can
          // ease the rate in smoothly over the next ~1.5s rather than snapping.
          landingStartTime.current = Date.now();
        }
      } else {
        landedRef.current = false;
        landingStartTime.current = null;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    const animate = () => {
      t += 0.006;

      if (!landedRef.current) {
        // Idle wander is now the rocket's ONLY behavior pre-landing — no
        // mouse tracking at all, always active.
        const baseX = window.innerWidth * 0.5 + Math.sin(t) * (window.innerWidth * 0.28);
        const baseY = window.innerHeight * 0.3 + Math.sin(t * 1.7) * 100;
        target.current = { x: baseX, y: baseY };
      }

      const dx = target.current.x - current.current.x;
      const dy = target.current.y - current.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      let ease = 0.025;
      if (landedRef.current && landingStartTime.current) {
        // Ramp the ease rate smoothly over the landing approach: starts gentle
        // (slow glide-in), eases further as it gets close (no final snap/overshoot).
        const elapsed = (Date.now() - landingStartTime.current) / 1000;
        const approachProgress = Math.min(1, elapsed / 1.4); // ~1.4s full approach
        const proximityFactor = dist < 40 ? Math.max(0.3, dist / 40) : 1;
        ease = (0.02 + approachProgress * 0.06) * proximityFactor;
      }

      current.current.x += dx * ease;
      current.current.y += dy * ease;

      if (dist > 1.5) {
        const targetAngle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
        const delta = shortestAngleDelta(currentAngle.current, targetAngle);
        currentAngle.current += delta * 0.1;
      }

      setPos({ x: current.current.x, y: current.current.y, angle: currentAngle.current });

      if (!landedRef.current && Math.random() > 0.6) {
        trailIdRef.current += 1;
        setTrail((prev) => [
          ...prev.slice(-18),
          { x: current.current.x, y: current.current.y, id: trailIdRef.current },
        ]);
      }

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-30 overflow-hidden">
      {trail.map((p, i) => (
        <div
          key={p.id}
          className="absolute rounded-full"
          style={{
            left: p.x, top: p.y,
            width: 3 + (i / trail.length) * 2,
            height: 3 + (i / trail.length) * 2,
            background: i % 2 === 0 ? "#8B7355" : "#5B7A8C",
            opacity: (i / trail.length) * 0.5,
            transform: "translate(-50%, -50%)",
            transition: "opacity 0.3s linear",
          }}
        />
      ))}

      <div
        className="absolute"
        style={{
          left: pos.x, top: pos.y,
          transform: `translate(-50%, -50%) rotate(${pos.angle}deg)`,
          filter: "drop-shadow(0 0 10px rgba(139, 115, 85, 0.5))",
        }}
      >
        <svg width="52" height="52" viewBox="0 0 28 28" fill="none">
          <path d="M14 2C17 6 18 11 18 15c0 2-1.5 3.5-4 3.5S10 17 10 15c0-4 1-9 4-13z"
            fill="#F5F0E8" fillOpacity="0.92" stroke="#8B7355" strokeWidth="1" />
          <circle cx="14" cy="11" r="2" fill="#5B7A8C" fillOpacity="0.8" />
          <path d="M10 15.5L6 20l4-1.5z" fill="#8B7355" />
          <path d="M18 15.5l4 4.5-4-1.5z" fill="#8B7355" />
          <path d="M12 18.5c0 2 1 4 2 5.5 1-1.5 2-3.5 2-5.5-.8.6-1.4.8-2 .8s-1.2-.2-2-.8z"
            fill="#8B7355" fillOpacity="0.7">
            <animate attributeName="opacity" values="0.7;0.3;0.7" dur="0.6s" repeatCount="indefinite" />
          </path>
        </svg>
      </div>
    </div>
  );
}
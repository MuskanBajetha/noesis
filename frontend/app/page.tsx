"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState} from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import CuriosityRocket from "@/components/CuriosityRocket";

const QUESTION_TEXT = "Why do seasons change?";
const ANSWER_TEXT = "Because Earth gets farther from the Sun in winter.";
const CONTRADICTION_TEXT = "Interesting. Then why is it summer in Australia when it's winter in Canada?";

type Phase = "typing-question" | "answer-fade" | "examining" | "contradiction" | "done";

// ── Animated method-section icons ─────────────────────

function UploadIcon() {
  return (
    <div className="relative w-6 h-6">
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
        <path d="M12 16V4M12 4L7 9M12 4l5 5" stroke="#8B7355" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          className="transition-transform duration-500 group-hover:-translate-y-0.5" />
        <path d="M4 16v3a2 2 0 002 2h12a2 2 0 002-2v-3" stroke="#8B7355" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      {/* floating document particles, appear on hover */}
      <span className="absolute -top-1 -right-1 w-1 h-1 rounded-full bg-[#5B7A8C] opacity-0 group-hover:opacity-70 group-hover:-translate-y-2 transition-all duration-700" />
      <span className="absolute -top-1 left-1 w-1 h-1 rounded-full bg-[#8B7355] opacity-0 group-hover:opacity-70 group-hover:-translate-y-3 transition-all duration-1000 delay-100" />
    </div>
  );
}

function QuestionToLightbulbIcon() {
  return (
    <div className="relative w-6 h-6">
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6 transition-opacity duration-300 group-hover:opacity-0 absolute inset-0">
        <circle cx="12" cy="12" r="9" stroke="#8B7355" strokeWidth="1.5" />
        <path d="M9.5 9a2.5 2.5 0 113.5 2.3c-.8.4-1 1-1 1.7" stroke="#8B7355" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="12" cy="16.5" r="0.6" fill="#8B7355" />
      </svg>
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6 transition-opacity duration-300 opacity-0 group-hover:opacity-100 absolute inset-0">
        <path d="M9 18h6M10 21h4" stroke="#8B7355" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M12 3a6 6 0 00-3.5 10.9c.3.2.5.6.5 1V16h6v-1.1c0-.4.2-.8.5-1A6 6 0 0012 3z" stroke="#8B7355" strokeWidth="1.5" fill="#8B7355" fillOpacity="0.15" />
      </svg>
    </div>
  );
}

function KnowledgeGraphIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
      <circle cx="12" cy="6" r="2" stroke="#8B7355" strokeWidth="1.4" className="transition-all duration-500 group-hover:fill-[#8B7355] group-hover:fill-opacity-30" />
      <circle cx="6" cy="16" r="2" stroke="#5B7A8C" strokeWidth="1.4" className="transition-all duration-500 delay-100 group-hover:fill-[#5B7A8C] group-hover:fill-opacity-30" />
      <circle cx="18" cy="16" r="2" stroke="#5B7A8C" strokeWidth="1.4" className="transition-all duration-500 delay-200 group-hover:fill-[#5B7A8C] group-hover:fill-opacity-30" />
      <path d="M11 7.5L7 14M13 7.5l4 6.5M8 16h8" stroke="#3D2817" strokeWidth="1" className="transition-all duration-500 group-hover:stroke-[#8B7355]" strokeDasharray="3 2" />
    </svg>
  );
}

function NetworkGraphIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
      <circle cx="6" cy="6" r="1.6" fill="#8B7355" className="transition-all duration-300 group-hover:r-2" />
      <circle cx="18" cy="6" r="1.6" fill="#8B7355" />
      <circle cx="12" cy="18" r="1.6" fill="#8B7355" />
      <circle cx="12" cy="11" r="1.6" fill="#5B7A8C" />
      <path d="M6 6L12 11M18 6L12 11M12 11L12 18" stroke="#3D2817" strokeWidth="1" className="transition-all duration-500 group-hover:stroke-[#5B7A8C]" />
    </svg>
  );
}

function NeuralPathwayIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
      <path d="M4 18C6 18 6 14 9 14s3 -4 5 -4 3 4 5 4" stroke="#8B7355" strokeWidth="1.5" strokeLinecap="round"
        className="transition-all duration-700" style={{ strokeDasharray: 30, strokeDashoffset: 0 }} />
      <circle cx="4" cy="18" r="1.2" fill="#5B7A8C" />
      <circle cx="19" cy="14" r="1.2" fill="#5B7A8C" className="transition-opacity duration-500 opacity-0 group-hover:opacity-100" />
    </svg>
  );
}

function StaircaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
      <path d="M4 19h3v-3h3v-3h3v-3h3v-3h3" stroke="#8B7355" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
        className="transition-transform duration-500 origin-bottom-left group-hover:-translate-y-0.5" />
    </svg>
  );
}

function BrokenConnectionIcon() {
  return (
    <div className="relative w-6 h-6">
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6 transition-opacity duration-300 group-hover:opacity-0">
        <circle cx="6" cy="12" r="2" stroke="#8B7355" strokeWidth="1.5" />
        <circle cx="18" cy="12" r="2" stroke="#8B7355" strokeWidth="1.5" />
        <path d="M9 11l2 1-2 1M15 11l-2 1 2 1" stroke="#8B7355" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6 absolute inset-0 transition-opacity duration-300 opacity-0 group-hover:opacity-100">
        <circle cx="6" cy="12" r="2" stroke="#5B7A8C" strokeWidth="1.5" fill="#5B7A8C" fillOpacity="0.2" />
        <circle cx="18" cy="12" r="2" stroke="#5B7A8C" strokeWidth="1.5" fill="#5B7A8C" fillOpacity="0.2" />
        <path d="M8 12h8" stroke="#5B7A8C" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    </div>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("typing-question");
  const [typedQuestion, setTypedQuestion] = useState("");

  // Particles are generated client-side only, after mount — avoids SSR/hydration
  // mismatches that Math.random() always causes when used during render.
  const [particles, setParticles] = useState<{
    left: number; size: number; duration: number; delay: number; opacity: number;
  }[]>([]);

  useEffect(() => {
    setParticles(
      Array.from({ length: 24 }, () => ({
        left: Math.random() * 100,
        size: Math.random() * 2 + 1,
        duration: Math.random() * 20 + 15,
        delay: Math.random() * -20,
        opacity: Math.random() * 0.25 + 0.05,
      }))
    );
  }, []);

  // Typewriter effect for the question
  useEffect(() => {
    if (phase !== "typing-question") return;
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setTypedQuestion(QUESTION_TEXT.slice(0, i));
      if (i >= QUESTION_TEXT.length) {
        clearInterval(interval);
        setTimeout(() => setPhase("answer-fade"), 400);
      }
    }, 40);
    return () => clearInterval(interval);
  }, [phase]);

  // Sequence the rest of the exchange
  useEffect(() => {
    if (phase === "answer-fade") {
      const t = setTimeout(() => setPhase("examining"), 1400);
      return () => clearTimeout(t);
    }
    if (phase === "examining") {
      const t = setTimeout(() => setPhase("contradiction"), 1500);
      return () => clearTimeout(t);
    }
    if (phase === "contradiction") {
      const t = setTimeout(() => setPhase("done"), 800);
      return () => clearTimeout(t);
    }
  }, [phase]);

  const goToStart = () => {
    const existingId = localStorage.getItem("student_id");
    router.push(existingId ? "/dashboard" : "/auth");
  };

  return (
    <div className="min-h-screen bg-[#0A0E12] text-[#F5F0E8] overflow-x-hidden relative">
      <CuriosityRocket />

      {/* Ambient drifting particles */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {particles.map((p, i) => (
          <div
            key={i}
            className="bg-particle"
            style={{
              left: `${p.left}%`,
              bottom: "-10px",
              width: `${p.size}px`,
              height: `${p.size}px`,
              opacity: p.opacity,
              animationDuration: `${p.duration}s`,
              animationDelay: `${p.delay}s`,
            }}
          />
        ))}
      </div>

      {/* ── Nav ───────────────────────────────────── */}
      <nav className="relative z-10 flex items-center justify-between px-8 md:px-16 py-7 border-b border-[#3D2817]/40">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full border border-[#8B7355] flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-[#8B7355]" />
          </div>
          <span className="font-display text-xl tracking-wide">Noesis</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#how" className="text-sm text-[#F5F0E8]/60 hover:text-[#F5F0E8] transition-colors hidden md:inline">How it works</a>
          <a href="#features" className="text-sm text-[#F5F0E8]/60 hover:text-[#F5F0E8] transition-colors hidden md:inline">Features</a>
          <Button
            variant="outline" size="sm" onClick={goToStart}
            className="border-[#8B7355]/40 text-[#F5F0E8] hover:bg-[#8B7355]/10 hover:text-[#F5F0E8]"
          >
            Sign in
          </Button>
        </div>
      </nav>

      {/* ── Hero: the animated reasoning exchange ──── */}
      <section id="hero" className="relative z-10 px-8 md:px-16 pt-24 pb-32 max-w-5xl mx-auto">
        <p className="font-mono-token text-xs tracking-[0.2em] text-[#5B7A8C] mb-8 uppercase">
          An exchange, not an answer
        </p>

        <div className="space-y-6 mb-16 min-h-[220px]">
          {/* The question, typed live */}
          <p className="font-display text-2xl md:text-3xl text-[#F5F0E8]/85 italic">
            "{typedQuestion}"
            {phase === "typing-question" && <span className="typewriter-cursor" />}
          </p>

          {/* The student's answer, fades in, then gets "examined" */}
          {phase !== "typing-question" && (
            <p
              className={`font-display text-xl md:text-2xl text-[#F5F0E8]/55 fade-up ${phase === "examining" ? "examine-pulse" : ""}`}
            >
              {ANSWER_TEXT}
            </p>
          )}

          {/* The contradiction question rises beneath it */}
          {(phase === "contradiction" || phase === "done") && (
            <p className="font-display text-2xl md:text-3xl contradiction-rise">
              {CONTRADICTION_TEXT}
            </p>
          )}

          {/* Final beat: a blinking cursor, leaving the visitor mid-thought */}
          {phase === "done" && (
            <span className="typewriter-cursor fade-up" />
          )}
        </div>

        <h1 className="font-display text-5xl md:text-7xl leading-[1.05] mb-8 max-w-3xl">
          Learn by <span className="italic text-[#8B7355]">discovering</span>,<br />
          not by being told.
        </h1>

        <p className="text-lg text-[#F5F0E8]/60 max-w-xl mb-3 leading-relaxed">
          A good teacher doesn't rush to answer. A good teacher asks the next question. 
        </p>
        <p className="text-lg text-[#F5F0E8]/60 max-w-xl mb-10 leading-relaxed">
          Noesis learns what you understand, finds where your reasoning bends, and guides you forward one question at a time.
        </p>

        <div className="flex items-center gap-4">
          <Button
            size="lg" onClick={goToStart}
            className="bg-[#8B7355] hover:bg-[#9d8265] text-[#0A0E12] text-base px-8 h-12 rounded-sm"
          >
            Start Learning <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </section>

      {/* ── How it works ──────────────────────────── */}
      <section id="how" className="relative z-10 px-8 md:px-16 py-24 border-t border-[#3D2817]/40 max-w-6xl mx-auto">
        <p className="font-mono-token text-xs tracking-[0.2em] text-[#5B7A8C] mb-4 uppercase">
          The method
        </p>
        <h2 className="font-display text-4xl md:text-5xl mb-16 max-w-2xl">
          Socrates didn't lecture. Neither do we.
        </h2>

        <div className="grid md:grid-cols-3 gap-12">
        <div className="space-y-3 group cursor-default p-5 -m-5 rounded-lg transition-all duration-300 hover:bg-[#8B7355]/[0.03] hover:-translate-y-1">
          <UploadIcon />
          <h3 className="font-display text-xl">Bring your own material</h3>
          <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">
            Studying Constitutional Law? Quantum Mechanics? Machine Learning? Ancient History? Upload what you're already using — every question Noesis asks is grounded in your material, not a generic question bank.
          </p>
        </div>
        <div className="space-y-3 group cursor-default p-5 -m-5 rounded-lg transition-all duration-300 hover:bg-[#8B7355]/[0.03] hover:-translate-y-1">
          <QuestionToLightbulbIcon />
          <h3 className="font-display text-xl">Questions first. Answers later.</h3>
          <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">
            Noesis doesn't immediately tell you what's wrong. Instead, it asks the question that makes the gap visible. Sometimes the most powerful explanation is the one you arrive at yourself.
          </p>
        </div>
        <div className="space-y-3 group cursor-default p-5 -m-5 rounded-lg transition-all duration-300 hover:bg-[#8B7355]/[0.03] hover:-translate-y-1">
          <KnowledgeGraphIcon />
          <h3 className="font-display text-xl">Your knowledge, mapped</h3>
          <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">
            Every subject becomes a living graph of connected topics. Watch mastery spread outward from what you've learned to what it connects to.
          </p>
        </div>
      </div>
      </section>

      {/* ── Features ──────────────────────────────── */}
      <section id="features" className="relative z-10 px-8 md:px-16 py-24 border-t border-[#3D2817]/40 max-w-6xl mx-auto">
        <p className="font-mono-token text-xs tracking-[0.2em] text-[#5B7A8C] mb-4 uppercase">
          Under the hood
        </p>
        <h2 className="font-display text-4xl md:text-5xl mb-16 max-w-2xl">
          Built to actually track what you know.
        </h2>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="group flex gap-4 p-6 border border-[#3D2817]/40 rounded-sm hover:border-[#8B7355]/40 hover:-translate-y-0.5 transition-all duration-300">
            <div className="shrink-0 mt-0.5"><NetworkGraphIcon /></div>
            <div>
              <h3 className="font-display text-lg mb-1.5">Concept graphs per subject</h3>
              <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">Each domain you study gets its own connected map of topics — no mixing Polity with Thermodynamics.</p>
            </div>
          </div>
          <div className="group flex gap-4 p-6 border border-[#3D2817]/40 rounded-sm hover:border-[#8B7355]/40 hover:-translate-y-0.5 transition-all duration-300">
            <div className="shrink-0 mt-0.5"><NeuralPathwayIcon /></div>
            <div>
              <h3 className="font-display text-lg mb-1.5">Mastery that grows with you</h3>
              <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">A knowledge-tracing model estimates what you've actually internalized, not just what you've answered correctly once.</p>
            </div>
          </div>
          <div className="group flex gap-4 p-6 border border-[#3D2817]/40 rounded-sm hover:border-[#8B7355]/40 hover:-translate-y-0.5 transition-all duration-300">
            <div className="shrink-0 mt-0.5"><StaircaseIcon /></div>
            <div>
              <h3 className="font-display text-lg mb-1.5">Adaptive difficulty</h3>
              <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">Struggling tightens the focus to fundamentals. Mastering something opens up harder, more synthetic questions.</p>
            </div>
          </div>
          <div className="group flex gap-4 p-6 border border-[#3D2817]/40 rounded-sm hover:border-[#8B7355]/40 hover:-translate-y-0.5 transition-all duration-300">
            <div className="shrink-0 mt-0.5"><BrokenConnectionIcon /></div>
            <div>
              <h3 className="font-display text-lg mb-1.5">Misconceptions, named</h3>
              <p className="text-[#F5F0E8]/55 text-sm leading-relaxed">When your reasoning has a specific, common flaw, Noesis recognizes it and asks the question that reveals it.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────── */}
      <section className="relative z-10 px-8 md:px-16 py-32 border-t border-[#3D2817]/40 text-center max-w-3xl mx-auto">
        <h2 className="font-display text-4xl md:text-5xl mb-3">
          Pick a subject.
        </h2>
        <h2 className="font-display text-4xl md:text-5xl mb-3 italic text-[#8B7355]">
          Start asking.
        </h2>
        <h2 className="font-display text-4xl md:text-5xl mb-6">
          See how far curiosity can take you.
        </h2>
        <p className="text-[#F5F0E8]/55 mb-2">
          Most learning platforms optimize for answers. Noesis optimizes for understanding.
        </p>
        <p className="text-[#F5F0E8]/55 mb-10">
          Your second brain shouldn't give answers. It should ask better questions.
        </p>
        <div id="final-cta-anchor" className="inline-block">
          <Button
            size="lg" onClick={goToStart}
            className="bg-[#8B7355] hover:bg-[#9d8265] text-[#0A0E12] text-base px-8 h-12 rounded-sm"
          >
            Start Learning <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </section>

      <footer className="relative z-10 px-8 md:px-16 py-8 border-t border-[#3D2817]/40 flex items-center justify-between text-xs text-[#F5F0E8]/35">
        <span>Noesis</span>
        <span className="font-mono-token">νόησις — intuitive understanding</span>
      </footer>
    </div>
  );
}
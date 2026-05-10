"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

const LOGIN_URL = "/api/v1/auth/spotify/login";

const ARCHETYPES = [
  { name: "The Midnight Romantic", icon: "🌙", gradient: "from-indigo-500 to-purple-600" },
  { name: "The Energy Alchemist", icon: "⚡", gradient: "from-orange-500 to-red-600" },
  { name: "The Introspective Poet", icon: "📖", gradient: "from-teal-500 to-slate-600" },
  { name: "The Nostalgic Dreamer", icon: "✨", gradient: "from-amber-500 to-yellow-600" },
  { name: "The Underground Explorer", icon: "🔍", gradient: "from-emerald-500 to-teal-700" },
  { name: "The Groove Architect", icon: "🎧", gradient: "from-purple-500 to-pink-600" },
];

const FEATURES = [
  {
    icon: "🧬",
    title: "Music DNA",
    body: "Your listening fingerprint decoded across 13 audio dimensions — from energy to acousticness.",
    gradient: "from-purple-500/10 to-indigo-500/10",
    border: "border-purple-500/20",
  },
  {
    icon: "💜",
    title: "Emotional Landscape",
    body: "Map the joy, nostalgia, longing, and fire inside your library with neuroscience-backed models.",
    gradient: "from-pink-500/10 to-purple-500/10",
    border: "border-pink-500/20",
  },
  {
    icon: "📝",
    title: "Lyrical DNA",
    body: "NLP dissects the words you live by — recurring themes, vocabulary richness, narrative arcs.",
    gradient: "from-teal-500/10 to-cyan-500/10",
    border: "border-teal-500/20",
  },
  {
    icon: "🤖",
    title: "AI Portrait",
    body: "GPT-4o synthesizes everything into poetic, specific insights that feel like a mirror, not a report.",
    gradient: "from-amber-500/10 to-orange-500/10",
    border: "border-amber-500/20",
  },
  {
    icon: "✨",
    title: "Your Archetype",
    body: "One of 12 music personalities. Not a genre — a soul signature built from your listening behavior.",
    gradient: "from-indigo-500/10 to-purple-500/10",
    border: "border-indigo-500/20",
  },
  {
    icon: "📤",
    title: "Share & Compare",
    body: "Export cinematic cards for stories, compare archetypes with friends, export your archetype playlist.",
    gradient: "from-cyan-500/10 to-teal-500/10",
    border: "border-cyan-500/20",
  },
];

export default function LandingPage() {
  const [archetypeIdx, setArchetypeIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(
      () => setArchetypeIdx((i) => (i + 1) % ARCHETYPES.length),
      3200,
    );
    return () => clearInterval(id);
  }, []);

  const current = ARCHETYPES[archetypeIdx];

  return (
    <main className="min-h-screen bg-brand-bg text-white overflow-x-hidden">
      {/* ── Ambient background orbs ──────────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-60 -left-60 w-[500px] h-[500px] rounded-full bg-purple-700/15 blur-[120px] animate-float" />
        <div className="absolute top-1/2 -right-60 w-[400px] h-[400px] rounded-full bg-indigo-700/15 blur-[100px] animate-float-delayed" />
        <div className="absolute -bottom-60 left-1/3 w-[600px] h-[600px] rounded-full bg-blue-700/10 blur-[140px] animate-float-slow" />
      </div>

      {/* ── Navigation ───────────────────────────────────────────────────────── */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-spotify-green flex items-center justify-center shadow-lg shadow-spotify-green/30">
            <SpotifyIcon className="w-5 h-5 text-black" />
          </div>
          <span className="text-xl font-bold tracking-tight">SoundSelf</span>
        </div>
        <a
          href={LOGIN_URL}
          className="hidden md:flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/10 text-sm text-white/70 hover:text-white hover:border-white/20 transition-all"
        >
          Sign in
        </a>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-5xl mx-auto px-8 pt-20 pb-28 text-center">
        {/* Rotating archetype badge */}
        <AnimatePresence mode="wait">
          <motion.div
            key={archetypeIdx}
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.35 }}
            className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full glass mb-10"
          >
            <span className="text-base">{current.icon}</span>
            <span className="text-sm text-white/60">
              Are you{" "}
              <span className={`font-semibold bg-gradient-to-r ${current.gradient} bg-clip-text text-transparent`}>
                {current.name}
              </span>
              ?
            </span>
          </motion.div>
        </AnimatePresence>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="text-5xl md:text-7xl lg:text-8xl font-bold leading-[1.05] tracking-tight mb-7"
        >
          Know Your{" "}
          <span className="bg-gradient-to-r from-[#1DB954] via-[#6C63FF] to-[#EC4899] bg-clip-text text-transparent">
            Music.
          </span>
          <br />
          Know Yourself.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.25 }}
          className="text-lg md:text-xl text-white/50 max-w-2xl mx-auto mb-12 leading-relaxed"
        >
          Connect your Spotify and receive a cinematic AI portrait of your music
          personality — emotional patterns, lyrical themes, behavioral rituals,
          and your unique archetype.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <motion.a
            href={LOGIN_URL}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className="inline-flex items-center gap-3 px-8 py-4 bg-spotify-green text-black font-bold text-base rounded-full shadow-xl shadow-spotify-green/20 hover:bg-spotify-green-light transition-colors"
          >
            <SpotifyIcon className="w-5 h-5" />
            Connect with Spotify
          </motion.a>
          <span className="text-sm text-white/30">Free · Takes 60 seconds</span>
        </motion.div>

        {/* Social proof */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="mt-8 text-xs text-white/20 tracking-widest uppercase"
        >
          Powered by Spotify · Genius · OpenAI GPT-4o
        </motion.p>
      </section>

      {/* ── Feature grid ─────────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-6xl mx-auto px-8 pb-32">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl md:text-4xl font-bold text-center mb-4"
        >
          Everything in one portrait
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="text-center text-white/40 mb-16"
        >
          Not a dashboard. A mirror.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              whileHover={{ y: -4, scale: 1.01 }}
              className={`p-6 rounded-2xl glass glass-hover border ${f.border} bg-gradient-to-br ${f.gradient} cursor-default`}
            >
              <span className="text-3xl mb-4 block">{f.icon}</span>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-white/50 leading-relaxed">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── CTA footer ───────────────────────────────────────────────────────── */}
      <section className="relative z-10 text-center pb-24 px-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="max-w-2xl mx-auto p-12 rounded-3xl glass border border-white/[0.06]"
          style={{ boxShadow: "0 0 80px rgba(108,99,255,0.1)" }}
        >
          <p className="text-4xl font-bold mb-4">
            Ready to meet{" "}
            <span className="gradient-accent">yourself</span>?
          </p>
          <p className="text-white/50 mb-8">
            Your music has been telling your story all along.
          </p>
          <motion.a
            href={LOGIN_URL}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className="inline-flex items-center gap-3 px-8 py-4 bg-spotify-green text-black font-bold rounded-full shadow-lg shadow-spotify-green/20 hover:bg-spotify-green-light transition-colors"
          >
            <SpotifyIcon className="w-5 h-5" />
            Connect with Spotify
          </motion.a>
        </motion.div>
      </section>
    </main>
  );
}

function SpotifyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
    </svg>
  );
}

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { saveToken, getToken } from "@/lib/api";

const STEPS = [
  { id: "auth",      icon: "🔐", label: "Authenticating your Spotify account" },
  { id: "tracks",    icon: "🎵", label: "Fetching your top tracks" },
  { id: "features",  icon: "🔬", label: "Analyzing audio fingerprints" },
  { id: "storing",   icon: "💾", label: "Mapping your music universe" },
  { id: "artists",   icon: "🎤", label: "Discovering your artist profile" },
  { id: "recent",    icon: "🕐", label: "Reading your listening sessions" },
  { id: "dna",       icon: "🧬", label: "Computing your listening DNA" },
  { id: "emotions",  icon: "💜", label: "Mapping emotional patterns" },
  { id: "archetype", icon: "✨", label: "Uncovering your music archetype" },
  { id: "insights",  icon: "🤖", label: "Generating AI insights" },
  { id: "complete",  icon: "🎉", label: "Your portrait is ready" },
];

function ConnectingInner() {
  const router = useRouter();
  const wsRef = useRef<WebSocket | null>(null);
  const [stepMap, setStepMap] = useState<Record<string, "pending" | "active" | "done">>({});
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [debugUrl, setDebugUrl] = useState("");

  useEffect(() => {
    let cancelled = false;

    setDebugUrl(window.location.href);

    const start = async () => {
      try {
        // Step 1: Get the JWT — read from URL param set by the OAuth callback,
        // or fall back to a previously saved token in localStorage.
        const params = new URLSearchParams(window.location.search);
        const urlToken = params.get("token");

        if (urlToken) {
          saveToken(urlToken);
          window.history.replaceState({}, "", "/connecting");
        }

        const token = urlToken ?? getToken();

        if (!token) {
          throw new Error("No token found — please connect with Spotify again.");
        }

        // Step 2: Start the analysis pipeline
        const pipelineRes = await fetch("/api/v1/user/me/report/generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!pipelineRes.ok) {
          const err = await pipelineRes.json().catch(() => ({}));
          throw new Error(err.detail ?? "Failed to start analysis");
        }

        const { report_id } = await pipelineRes.json();
        setStepMap({ auth: "done" });

        // Step 3: Open WebSocket directly to backend (no auth needed — report_id is the secret)
        const ws = new WebSocket(
          `ws://127.0.0.1:8000/api/v1/user/me/report/${report_id}/progress`
        );
        wsRef.current = ws;

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            const data: { step: string; message: string; progress: number } = JSON.parse(event.data);

            setProgress(data.progress ?? 0);
            setStepMap((prev) => {
              const next = { ...prev };
              let found = false;
              for (const s of STEPS) {
                if (s.id === data.step) {
                  found = true;
                  next[s.id] = data.step === "complete" ? "done" : "active";
                } else if (!found) {
                  next[s.id] = "done";
                }
              }
              return next;
            });

            if (data.step === "complete") {
              setDone(true);
              setTimeout(() => {
                router.push("/dashboard");
              }, 1800);
            }
          } catch { /* ignore parse errors */ }
        };

        ws.onerror = () => {
          if (!cancelled) setError("Connection lost. Please refresh and try again.");
        };
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Something went wrong.");
      }
    };

    start();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [router]);

  return (
    <main className="min-h-screen bg-brand-bg text-white flex flex-col items-center justify-center p-8">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-purple-600/8 blur-[160px]" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Pulsing orb */}
        <div className="flex justify-center mb-14">
          <div className="relative w-28 h-28">
            {[0, 1, 2, 3].map((i) => (
              <motion.div
                key={i}
                className="absolute inset-0 rounded-full border border-purple-500/30"
                animate={{ scale: [1, 2.2, 2.2], opacity: [0.6, 0, 0] }}
                transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.55, ease: "easeOut" }}
              />
            ))}
            <motion.div
              className="absolute inset-0 rounded-full bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center text-4xl shadow-2xl"
              animate={{ boxShadow: ["0 0 30px rgba(108,99,255,0.4)", "0 0 60px rgba(108,99,255,0.7)", "0 0 30px rgba(108,99,255,0.4)"] }}
              transition={{ duration: 2.5, repeat: Infinity }}
            >
              🎵
            </motion.div>
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center mb-2">Analyzing your universe</h1>
        <p className="text-white/40 text-center text-sm mb-3">This takes about 30 seconds</p>

        {/* Progress bar */}
        <div className="w-full h-0.5 bg-white/5 rounded-full mb-10 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Steps */}
        <div className="space-y-2">
          {STEPS.map((step, idx) => {
            const status = stepMap[step.id] ?? "pending";
            const isActive = status === "active";
            const isDone = status === "done";

            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: isDone || isActive ? 1 : 0.25, x: 0 }}
                transition={{ delay: idx * 0.04 }}
                className="flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300"
                style={{
                  background: isActive ? "rgba(108,99,255,0.1)" : "transparent",
                  border: isActive ? "1px solid rgba(108,99,255,0.25)" : "1px solid transparent",
                }}
              >
                <span className="text-xl w-8 text-center flex-shrink-0">
                  {isDone ? "✅" : step.icon}
                </span>
                <span className={`text-sm flex-1 ${isDone ? "text-white/40 line-through" : isActive ? "text-white font-medium" : "text-white/25"}`}>
                  {step.label}
                </span>
                {isActive && (
                  <motion.div
                    className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full flex-shrink-0"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
                  />
                )}
              </motion.div>
            );
          })}
        </div>

        <AnimatePresence>
          {done && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 text-center"
            >
              <a
                href="/dashboard"
                className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-full text-sm font-medium transition-colors"
              >
                View your portrait →
              </a>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-8 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-300 text-sm text-center"
            >
              {error}
              <a href="/" className="block mt-2 text-white/60 underline underline-offset-2 hover:text-white">
                Go back home
              </a>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}

export default function ConnectingPage() {
  return <ConnectingInner />;
}

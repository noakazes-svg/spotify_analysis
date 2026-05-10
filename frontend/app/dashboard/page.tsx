"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from "recharts";
import { api, type Term, type TrackEntry, type ListeningDNA } from "@/lib/api";

// ── Neon palette ─────────────────────────────────────────────────────────────
const NEON = {
  pink:   "#ec4899",
  violet: "#a855f7",
  indigo: "#6366f1",
  blue:   "#3b82f6",
  cyan:   "#06b6d4",
  teal:   "#14b8a6",
};
const CHART_COLORS = [NEON.pink, NEON.violet, NEON.indigo, NEON.blue, NEON.cyan, NEON.teal];
const TIME_COLORS: Record<string, string> = {
  morning: NEON.cyan, afternoon: NEON.blue, evening: NEON.violet, night: NEON.pink,
};

// ── Custom tooltip ────────────────────────────────────────────────────────────
function DarkTooltip({ active, payload, label }: {
  active?: boolean; payload?: {value: number; name?: string}[]; label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0d0518] border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
      {label && <p className="text-white/40 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="text-white font-semibold">{p.value}</p>
      ))}
    </div>
  );
}

// ── EQ bar animation ──────────────────────────────────────────────────────────
const EQ_HEIGHTS = [12,20,32,18,40,26,35,15,28,38,20,45,30,22,42,18,36,24,40,16,30,44,20,34,28,38,14,42,26,32];

function EQBackground() {
  return (
    <div className="fixed inset-x-0 bottom-0 h-24 flex items-end gap-[3px] px-4 pointer-events-none z-0 opacity-[0.07]">
      {EQ_HEIGHTS.map((h, i) => (
        <motion.div
          key={i}
          className="flex-1 rounded-t-sm"
          style={{ background: `linear-gradient(to top, ${NEON.pink}, ${NEON.violet})` }}
          animate={{ scaleY: [1, 0.4 + Math.random() * 0.6, 0.6 + Math.random() * 0.4, 1] }}
          transition={{ duration: 1.2 + (i % 5) * 0.3, repeat: Infinity, ease: "easeInOut", delay: i * 0.04 }}
          initial={{ height: h }}
          style={{ height: h, transformOrigin: "bottom" }}
        />
      ))}
    </div>
  );
}

// ── Glow orbs ─────────────────────────────────────────────────────────────────
function GlowOrbs() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      <div className="absolute -top-40 -left-40 w-[500px] h-[500px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(236,72,153,0.18) 0%, transparent 70%)" }} />
      <div className="absolute top-1/3 -right-60 w-[600px] h-[600px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(99,102,241,0.14) 0%, transparent 70%)" }} />
      <div className="absolute -bottom-40 left-1/3 w-[400px] h-[400px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(168,85,247,0.12) 0%, transparent 70%)" }} />
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ children, delay = 0, className = "" }: {
  children: React.ReactNode; delay?: number; className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ── Glass card ────────────────────────────────────────────────────────────────
function Card({ children, className = "", glow }: {
  children: React.ReactNode; className?: string; glow?: "pink" | "violet" | "indigo";
}) {
  const glowMap = {
    pink:   "shadow-[0_0_40px_rgba(236,72,153,0.07)]",
    violet: "shadow-[0_0_40px_rgba(168,85,247,0.07)]",
    indigo: "shadow-[0_0_40px_rgba(99,102,241,0.07)]",
  };
  return (
    <div className={`bg-[#0d0518]/80 backdrop-blur-sm border border-white/[0.06] rounded-2xl ${glow ? glowMap[glow] : ""} ${className}`}>
      {children}
    </div>
  );
}

// ── Stat badge ────────────────────────────────────────────────────────────────
function StatBadge({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-3xl font-black tracking-tight" style={{ color }}>{value}</span>
      <span className="text-[10px] uppercase tracking-[2px] text-white/25 mt-0.5">{label}</span>
    </div>
  );
}

// ── Section title ─────────────────────────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <h2 className="text-[11px] uppercase tracking-[3px] font-semibold text-white/30">{children}</h2>
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  );
}

// ── Term tabs ─────────────────────────────────────────────────────────────────
function TermTabs({ value, onChange }: { value: Term; onChange: (t: Term) => void }) {
  const tabs: { key: Term; label: string }[] = [
    { key: "short_term", label: "4 Weeks" },
    { key: "medium_term", label: "6 Months" },
    { key: "long_term", label: "All Time" },
  ];
  return (
    <div className="flex gap-1 p-1 bg-white/[0.04] rounded-xl border border-white/[0.06]">
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            value === t.key
              ? "bg-gradient-to-r from-pink-500/30 to-violet-500/30 border border-pink-500/30 text-pink-300"
              : "text-white/25 hover:text-white/50"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ── Word cloud ────────────────────────────────────────────────────────────────
function WordCloud({ words }: { words: { word: string; count: number }[] }) {
  if (!words.length) return null;
  const max = words[0].count;
  return (
    <div className="flex flex-wrap gap-2 justify-center py-4">
      {words.slice(0, 50).map(({ word, count }, i) => {
        const size = 11 + ((count / max) * 18);
        const opacity = 0.35 + (count / max) * 0.65;
        const color = CHART_COLORS[i % CHART_COLORS.length];
        return (
          <span
            key={word}
            className="transition-all duration-200 cursor-default hover:opacity-100"
            style={{ fontSize: size, color, opacity, fontWeight: count > max * 0.5 ? 700 : 400 }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
}

// ── Insight card ──────────────────────────────────────────────────────────────
function InsightCard({ title, body, accent }: { title: string; body: string; accent: string }) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-4 flex gap-3">
      <div className="w-1 rounded-full flex-shrink-0" style={{ background: accent }} />
      <div>
        <p className="text-xs font-semibold text-white/70 mb-1">{title}</p>
        <p className="text-xs text-white/35 leading-relaxed">{body}</p>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<Awaited<ReturnType<typeof api.user.me>> | null>(null);
  const [report, setReport] = useState<Awaited<ReturnType<typeof api.user.report>> | null>(null);
  const [tracks, setTracks] = useState<TrackEntry[]>([]);
  const [term, setTerm] = useState<Term>("medium_term");
  const [loading, setLoading] = useState(true);

  // Load on mount
  useEffect(() => {
    const load = async () => {
      try {
        const [userData, reportData] = await Promise.all([api.user.me(), api.user.report()]);
        setUser(userData);
        setReport(reportData);
        if (reportData?.id) {
          const td = await api.tracks.top("medium_term", 20);
          setTracks(td);
        }
      } catch {
        router.push("/");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [router]);

  // Reload tracks when term changes
  useEffect(() => {
    if (!report?.id) return;
    api.tracks.top(term, 20).then(setTracks).catch(() => {});
  }, [term, report?.id]);

  // Poll until done
  useEffect(() => {
    if (!report || report.status === "done" || report.status === "failed") return;
    const iv = setInterval(async () => {
      try {
        const r = await api.user.report();
        if (r) { setReport(r); if (r.status === "done") clearInterval(iv); }
      } catch {}
    }, 3000);
    return () => clearInterval(iv);
  }, [report]);

  const dna = report?.listening_dna as (ListeningDNA & {
    genre_counts?: { name: string; count: number }[];
    top_artists?: { name: string; count: number }[];
    decade_distribution?: { decade: string; count: number }[];
    popularity_buckets?: { range: string; count: number }[];
    lyrics_words?: { word: string; count: number }[];
    lyrics_tracks_analyzed?: number;
  }) | null;

  // Derived insights
  const insights = useMemo(() => {
    if (!dna) return [];
    const list: { title: string; body: string; accent: string }[] = [];
    const pop = dna.avg_popularity ?? 0;
    if (pop > 70) list.push({ title: "Mainstream Listener", body: `Your average track popularity is ${Math.round(pop)}/100 — you gravitate toward chart-topping artists.`, accent: NEON.pink });
    else if (pop < 40) list.push({ title: "Underground Explorer", body: `Your average track popularity is only ${Math.round(pop)}/100 — you discover music way before it's mainstream.`, accent: NEON.cyan });
    else list.push({ title: "Balanced Taste", body: `With ${Math.round(pop)}/100 average popularity, you mix chart hits with hidden gems.`, accent: NEON.violet });

    if (dna.dominant_decade) list.push({ title: `${dna.dominant_decade} Is Your Era`, body: `Most of your music comes from the ${dna.dominant_decade}. Your musical identity was shaped by that decade's sound.`, accent: NEON.indigo });

    const disc = Math.round((dna.discovery_rate ?? 0) * 100);
    if (disc > 20) list.push({ title: "Niche Curator", body: `${disc}% of your tracks have under 40 popularity — you're an active music discoverer.`, accent: NEON.teal });

    const time = dna.time_distribution ?? {};
    const peak = Object.entries(time).sort((a, b) => b[1] - a[1])[0];
    if (peak) list.push({ title: `${peak[0].charAt(0).toUpperCase() + peak[0].slice(1)} Listener`, body: `You listen most in the ${peak[0]}. Music is part of your ${peak[0] === "night" ? "late-night rituals" : peak[0] === "morning" ? "morning routine" : "daily rhythm"}.`, accent: TIME_COLORS[peak[0]] ?? NEON.pink });

    const topGenre = (dna.genre_counts ?? [])[0];
    if (topGenre) list.push({ title: `${topGenre.name.charAt(0).toUpperCase() + topGenre.name.slice(1)} at Heart`, body: `${topGenre.name} dominates your listening with ${topGenre.count} genre tags — it defines your musical identity.`, accent: NEON.blue });

    return list;
  }, [dna]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#05000f] flex items-center justify-center">
        <motion.div
          className="w-10 h-10 rounded-full border-2 border-t-transparent"
          style={{ borderColor: `${NEON.pink} transparent transparent transparent` }}
          animate={{ rotate: 360 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05000f] text-white relative overflow-x-hidden">
      <GlowOrbs />
      <EQBackground />

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 border-b border-white/[0.04] bg-[#05000f]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-gradient-to-r from-pink-500 to-violet-500" />
            <span className="text-xs font-bold tracking-[3px] uppercase text-white/60">SoundSelf</span>
          </div>
          {user && (
            <div className="flex items-center gap-3">
              {user.avatar_url && (
                <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full ring-1 ring-white/10" />
              )}
              <span className="text-xs text-white/30">{user.display_name}</span>
              <button
                onClick={() => { api.auth.logout().finally(() => router.push("/")); }}
                className="text-[10px] text-white/15 hover:text-white/40 transition-colors uppercase tracking-widest"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-12 space-y-12 pb-32">

        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <Section delay={0}>
          <p className="text-[10px] uppercase tracking-[4px] text-white/20 mb-3">Music Intelligence Report</p>
          <h1 className="text-5xl font-black tracking-tight mb-6" style={{ background: `linear-gradient(135deg, #fff 0%, ${NEON.pink} 50%, ${NEON.violet} 100%)`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            {user?.display_name?.split(" ")[0] ?? "Your"}<br />Universe
          </h1>
          <div className="flex flex-wrap gap-10">
            <StatBadge value={String(dna?.total_unique_tracks ?? "—")} label="Tracks Analyzed" color={NEON.pink} />
            <StatBadge value={String(dna?.genre_count ?? "—")} label="Genres" color={NEON.violet} />
            <StatBadge value={`${Math.round((dna?.discovery_rate ?? 0) * 100)}%`} label="Niche Score" color={NEON.indigo} />
            <StatBadge value={dna?.dominant_decade ?? "—"} label="Dominant Era" color={NEON.blue} />
            <StatBadge value={String(Math.round(dna?.avg_popularity ?? 0))} label="Avg Popularity" color={NEON.cyan} />
          </div>
        </Section>

        {/* ── Status banner ────────────────────────────────────────────────── */}
        {report?.status !== "done" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="flex items-center gap-3 p-4 rounded-xl border border-pink-500/20 bg-pink-500/5">
            <motion.div className="w-4 h-4 rounded-full border-2 border-t-transparent border-pink-400"
              animate={{ rotate: 360 }} transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }} />
            <p className="text-xs text-pink-300/70">Analysis in progress — data will appear when ready</p>
          </motion.div>
        )}

        {dna && (
          <>
            {/* ── Genre Universe + When You Listen ─────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* Genre chart */}
              {(dna.genre_counts?.length ?? 0) > 0 && (
                <Section delay={0.1}>
                  <Card className="p-6">
                    <SectionTitle>Genre Universe</SectionTitle>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart
                        data={dna.genre_counts?.slice(0, 10)}
                        layout="vertical"
                        margin={{ left: 0, right: 16, top: 0, bottom: 0 }}
                      >
                        <XAxis type="number" hide />
                        <YAxis
                          type="category" dataKey="name" width={110}
                          tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 11 }}
                          axisLine={false} tickLine={false}
                        />
                        <Tooltip content={<DarkTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={16}>
                          {dna.genre_counts?.slice(0, 10).map((_, i) => (
                            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} opacity={1 - i * 0.06} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                </Section>
              )}

              {/* Time of day */}
              {Object.keys(dna.time_distribution ?? {}).length > 0 && (
                <Section delay={0.15}>
                  <Card className="p-6">
                    <SectionTitle>When You Listen</SectionTitle>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={Object.entries(dna.time_distribution ?? {}).map(([period, count]) => ({ period, count }))}>
                        <XAxis dataKey="period" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip content={<DarkTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                        <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={60}>
                          {Object.keys(dna.time_distribution ?? {}).map((period) => (
                            <Cell key={period} fill={TIME_COLORS[period] ?? NEON.violet} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                </Section>
              )}
            </div>

            {/* ── Top Artists ──────────────────────────────────────────────── */}
            {(dna.top_artists?.length ?? 0) > 0 && (
              <Section delay={0.2}>
                <Card className="p-6" glow="violet">
                  <SectionTitle>Artist Landscape</SectionTitle>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart
                      data={dna.top_artists}
                      layout="vertical"
                      margin={{ left: 0, right: 16, top: 0, bottom: 0 }}
                    >
                      <XAxis type="number" hide />
                      <YAxis
                        type="category" dataKey="name" width={130}
                        tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 11 }}
                        axisLine={false} tickLine={false}
                      />
                      <Tooltip content={<DarkTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={14}>
                        {dna.top_artists?.map((_, i) => (
                          <Cell key={i}
                            fill={`url(#gradArtist${i})`}
                            style={{ fill: i === 0 ? NEON.pink : NEON.violet }}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </Section>
            )}

            {/* ── Era + Popularity ─────────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {(dna.decade_distribution?.length ?? 0) > 0 && (
                <Section delay={0.25}>
                  <Card className="p-6">
                    <SectionTitle>Musical Era</SectionTitle>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={dna.decade_distribution}>
                        <XAxis dataKey="decade" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip content={<DarkTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                        <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={48}>
                          {dna.decade_distribution?.map((d, i) => (
                            <Cell key={i} fill={d.decade === dna.dominant_decade ? NEON.pink : NEON.violet} opacity={d.decade === dna.dominant_decade ? 1 : 0.45} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                </Section>
              )}

              {(dna.popularity_buckets?.length ?? 0) > 0 && (
                <Section delay={0.3}>
                  <Card className="p-6">
                    <SectionTitle>Mainstream vs Niche</SectionTitle>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={dna.popularity_buckets}>
                        <XAxis dataKey="range" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip content={<DarkTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                        <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={48}>
                          {dna.popularity_buckets?.map((b, i) => (
                            <Cell key={i} fill={CHART_COLORS[i]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <div className="flex justify-between mt-2">
                      <span className="text-[10px] text-white/20 uppercase tracking-widest">Underground</span>
                      <span className="text-[10px] text-white/20 uppercase tracking-widest">Mainstream</span>
                    </div>
                  </Card>
                </Section>
              )}
            </div>

            {/* ── Top Tracks ───────────────────────────────────────────────── */}
            <Section delay={0.35}>
              <Card className="p-6" glow="indigo">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-[11px] uppercase tracking-[3px] text-white/30">Top Tracks</h2>
                  <TermTabs value={term} onChange={setTerm} />
                </div>
                <div className="space-y-1">
                  {tracks.slice(0, 15).map((item, i) => (
                    <motion.div
                      key={`${item.track.spotify_id}-${term}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center gap-4 px-3 py-2.5 rounded-xl hover:bg-white/[0.03] transition-colors group"
                    >
                      <span className="text-[10px] tabular-nums w-5 text-right text-white/15 group-hover:text-white/30 transition-colors">
                        {i + 1}
                      </span>
                      {item.track.image_url ? (
                        <img src={item.track.image_url} alt="" className="w-9 h-9 rounded-lg object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                      ) : (
                        <div className="w-9 h-9 rounded-lg bg-white/[0.04] border border-white/[0.06]" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate text-white/80 group-hover:text-white transition-colors">{item.track.name}</p>
                        <p className="text-xs text-white/25 truncate">{item.track.artist}</p>
                      </div>
                      <div className="hidden sm:flex items-center gap-2">
                        {item.track.release_year && (
                          <span className="text-[10px] text-white/15">{item.track.release_year}</span>
                        )}
                        <div className="w-14 h-[3px] rounded-full bg-white/[0.06] overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${item.track.popularity ?? 0}%`,
                              background: `linear-gradient(90deg, ${NEON.pink}, ${NEON.violet})`,
                            }}
                          />
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </Card>
            </Section>

            {/* ── Listening Insights ───────────────────────────────────────── */}
            {insights.length > 0 && (
              <Section delay={0.4}>
                <SectionTitle>Listening Insights</SectionTitle>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {insights.map((ins, i) => (
                    <InsightCard key={i} {...ins} />
                  ))}
                </div>
              </Section>
            )}

            {/* ── Lyrics Word Cloud ─────────────────────────────────────────── */}
            {(dna.lyrics_words?.length ?? 0) > 0 ? (
              <Section delay={0.45}>
                <Card className="p-6" glow="pink">
                  <SectionTitle>Lyrics Universe</SectionTitle>
                  <p className="text-xs text-white/20 text-center mb-4">
                    Most common words across your top {dna.lyrics_tracks_analyzed} tracks
                  </p>
                  <WordCloud words={dna.lyrics_words!} />
                </Card>
              </Section>
            ) : (
              <Section delay={0.45}>
                <Card className="p-8 text-center border border-pink-500/10 bg-pink-500/[0.02]">
                  <p className="text-xs uppercase tracking-[3px] text-white/15 mb-2">Lyrics Universe</p>
                  <p className="text-sm text-white/25">
                    Add your Genius API token to <code className="text-pink-400/60">.env</code> to unlock lyrics word analysis
                  </p>
                </Card>
              </Section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

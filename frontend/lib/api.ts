const TOKEN_KEY = "soundself_token";

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/";
    throw new Error("Not authenticated");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  auth: {
    loginUrl: () => "/api/v1/auth/spotify/login",
    logout: () => {
      clearToken();
      return req<{ ok: boolean }>("/api/v1/auth/logout", { method: "DELETE" });
    },
  },

  user: {
    me: () => req<User>("/api/v1/user/me"),
    report: () => req<Report | null>("/api/v1/user/me/report"),
    generateReport: () =>
      req<{ report_id: string; status: string }>("/api/v1/user/me/report/generate", {
        method: "POST",
      }),
  },

  tracks: {
    top: (term: Term = "medium_term", limit = 20) =>
      req<TrackEntry[]>(`/api/v1/tracks/top?term=${term}&limit=${limit}`),
    deepDive: (trackId: string) =>
      req<TrackDetail>(`/api/v1/tracks/${trackId}/deep-dive`),
  },

  ws: {
    progressUrl: (reportId: string) =>
      `ws://127.0.0.1:8000/api/v1/user/me/report/${reportId}/progress`,
  },
};

// ── Types ────────────────────────────────────────────────────────────────────

export type Term = "short_term" | "medium_term" | "long_term";

export type User = {
  id: string;
  spotify_id: string;
  display_name: string;
  email: string | null;
  avatar_url: string | null;
  country: string | null;
};

export type Report = {
  id: string;
  status: "queued" | "processing" | "analyzed" | "done" | "failed";
  generated_at: string;
  listening_dna: ListeningDNA | null;
  archetype_id: number | null;
  personality_scores: Record<string, number> | null;
};

export type ListeningDNA = {
  avg_features: Record<string, number>;
  top_genres: string[];
  genre_count: number;
  genre_diversity: number;
  discovery_rate: number;
  avg_popularity: number;
  total_unique_tracks: number;
  time_distribution: Record<string, number>;
  dominant_decade: string | null;
};

export type TrackEntry = {
  rank: number;
  term: Term;
  track: {
    id: string;
    spotify_id: string;
    name: string;
    artist: string;
    album: string | null;
    release_year: number | null;
    popularity: number | null;
    image_url: string | null;
    preview_url: string | null;
    audio_features: Record<string, number> | null;
  };
};

export type TrackDetail = {
  id: string;
  name: string;
  artist: string;
  album: string | null;
  release_year: number | null;
  popularity: number | null;
  image_url: string | null;
  audio_features: Record<string, number> | null;
  lyrics_cleaned: string | null;
  emotions: EmotionProfile | null;
};

export type EmotionProfile = {
  joy: number;
  sadness: number;
  anger: number;
  fear: number;
  nostalgia: number;
  longing: number;
  valence: number;
  arousal: number;
  dominant: string | null;
  theme_tags: string[] | null;
};

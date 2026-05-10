import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SoundSelf — Know Your Music. Know Yourself.",
  description:
    "Connect your Spotify and receive an AI-powered portrait of your music personality — emotional patterns, lyrical DNA, behavioral rituals, and your unique archetype.",
  openGraph: {
    title: "SoundSelf",
    description: "AI-powered Spotify intelligence platform.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`} suppressHydrationWarning>{children}</body>
    </html>
  );
}

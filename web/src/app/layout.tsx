import type { Metadata } from "next";
import { Instrument_Serif, Space_Grotesk } from "next/font/google";
import Script from "next/script";

import { AuthProvider } from "@/components/auth/auth-provider";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/"),
  title: "VeriLens | AI Image & Deepfake Video Detector",
  description:
    "World-class browser UX for detecting AI-generated images and short deepfake-style videos through the VeriLens public inference API.",
  keywords: [
    "deepfake detector",
    "ai image detector",
    "synthetic media detection",
    "deepfake video checker",
    "verilens",
  ],
  openGraph: {
    title: "VeriLens | AI Image & Deepfake Video Detector",
    description:
      "Upload images and short clips, inspect verdicts, and explore a polished authenticity workflow built on a public inference API.",
    url: "https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/",
    siteName: "VeriLens",
    images: [
      {
        url: "https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/og-preview.png",
        width: 1200,
        height: 630,
        alt: "VeriLens website preview",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "VeriLens | AI Image & Deepfake Video Detector",
    description:
      "A polished public web experience for checking AI-generated images and deepfake-style video.",
    images: ["https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/og-preview.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${instrumentSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

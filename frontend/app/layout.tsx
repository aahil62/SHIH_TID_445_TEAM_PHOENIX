import type { Metadata } from "next";
import { Instrument_Sans, Space_Mono } from "next/font/google";
import "./globals.css";

// Instrument Sans for UI text and Space Mono reserved for
// identifiers/scores/amounts/timestamps — driving globals.css's
// --font-sans/--font-mono tokens, not hardcoded per component. Deliberately
// not Inter/JetBrains Mono: both are the default-by-reflex Google Fonts
// pairing (Inter especially — the single most common "nobody chose this"
// font on the web); this pairing carries real character instead while
// staying free and self-hostable through next/font.
const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  subsets: ["latin"],
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "FraudLens — Financial Crime Operations",
  description: "FraudLens fraud investigation and case review console",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${instrumentSans.variable} ${spaceMono.variable} h-full antialiased`}>
      <body className="h-full min-h-screen" style={{ backgroundColor: "var(--canvas)" }}>
        {children}
      </body>
    </html>
  );
}

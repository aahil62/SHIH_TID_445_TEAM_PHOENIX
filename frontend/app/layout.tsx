import type { Metadata } from "next";
import { Share_Tech_Mono } from "next/font/google";
import CopilotWidget from "@/components/CopilotWidget";
import NavRail from "@/components/NavRail";
import SampleBanner from "@/components/SampleBanner";
import TopBar from "@/components/TopBar";
import "./globals.css";

// The whole app runs on this one font — no exceptions — driving
// globals.css's --font-sans/--font-mono tokens, not hardcoded per
// component. Only one weight (400) exists for this typeface.
const shareTechMono = Share_Tech_Mono({
  variable: "--font-share-tech-mono",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "FraudLens — Financial Crime Operations",
  description: "FraudLens fraud investigation and case review console",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${shareTechMono.variable} h-full antialiased`}>
      <body className="flex h-full min-h-screen flex-col" style={{ backgroundColor: "var(--canvas)" }}>
        <TopBar />
        <div className="flex min-h-0 flex-1">
          <NavRail />
          <div className="flex min-w-0 flex-1 flex-col">
            <SampleBanner />
            <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
          </div>
        </div>
        <CopilotWidget />
      </body>
    </html>
  );
}

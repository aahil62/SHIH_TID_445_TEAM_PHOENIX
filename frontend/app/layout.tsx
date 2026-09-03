import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import NavRail from "@/components/NavRail";
import SampleBanner from "@/components/SampleBanner";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FraudLens — Analyst Console",
  description: "FraudLens fraud investigation and case review console",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex h-full min-h-screen" style={{ backgroundColor: "var(--canvas)" }}>
        <NavRail />
        <div className="flex min-w-0 flex-1 flex-col">
          <SampleBanner />
          <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}

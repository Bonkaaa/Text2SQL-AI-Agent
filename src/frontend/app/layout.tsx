import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import React from "react";
import { ToastContainer } from "@/components/common/ToastContainer";
import { AppProvider } from "@/context/AppContext";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin", "vietnamese"],
  variable: "--font-jakarta",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Text2SQL Enterprise Analytics — TPC-DS Self-Service Platform",
  description:
    "Hệ thống AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp (Chuẩn TPC-DS Benchmark 24 bảng). Tích hợp DeepAgents Supervisor, LangGraph Control Pipeline và Recharts Visualization.",
  keywords: [
    "Text2SQL",
    "AI Agent",
    "TPC-DS",
    "DuckDB",
    "DeepAgents",
    "LangGraph",
    "Self-Service Analytics",
  ],
};

export const viewport: Viewport = {
  themeColor: "#0B0F17",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="vi"
      className={`dark ${plusJakartaSans.variable} ${jetbrainsMono.variable}`}
    >
      <body className="min-h-screen bg-background text-slate-100 font-sans antialiased selection:bg-brand-500/30 selection:text-brand-200">
        <AppProvider>
          {children}
          <ToastContainer />
        </AppProvider>
      </body>
    </html>
  );
}

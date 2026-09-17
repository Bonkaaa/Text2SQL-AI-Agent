import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import React from "react";
import { ToastContainer } from "@/components/common/ToastContainer";
import { AppProvider } from "@/context/AppContext";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Text2SQL AI Agent — Self-Service Analytics",
  description:
    "Hệ thống AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp (Chuẩn TPC-H Benchmark). Tích hợp DeepAgents Supervisor, LangGraph Control Pipeline và Recharts Visualization.",
  keywords: [
    "Text2SQL",
    "AI Agent",
    "TPC-H",
    "DuckDB",
    "DeepAgents",
    "LangGraph",
    "Self-Service Analytics",
  ],
};

export const viewport: Viewport = {
  themeColor: "#090d16",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={`dark ${inter.variable}`}>
      <body className="min-h-screen bg-background text-slate-100 font-sans antialiased selection:bg-brand-500/30 selection:text-brand-200">
        <AppProvider>
          {children}
          <ToastContainer />
        </AppProvider>
      </body>
    </html>
  );
}

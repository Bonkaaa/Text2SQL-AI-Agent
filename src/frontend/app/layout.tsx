import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { LanguageProvider } from "@/context/LanguageContext";

export const metadata: Metadata = {
  title: "QueryPilot — AI Text2SQL Data Workspace",
  description: "Natural language self-service analytics for enterprise omnichannel data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-canvas text-foreground">
        <LanguageProvider>
          <AuthProvider>{children}</AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}

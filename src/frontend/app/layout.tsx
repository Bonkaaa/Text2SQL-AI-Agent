import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";

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
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

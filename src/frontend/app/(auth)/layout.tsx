import React from "react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-canvas text-foreground flex flex-col justify-center">
      {children}
    </div>
  );
}

import type { ReactNode } from "react";
import "./globals.css";
import AppShell from "@/components/AppShell";

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="h-screen w-screen overflow-hidden">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

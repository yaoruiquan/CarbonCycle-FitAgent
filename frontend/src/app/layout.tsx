"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { UserProvider } from "@/lib/context/UserContext";
import { userStorage } from "@/lib/storage";
import "./globals.css";

const NAV_ITEMS = [
  { path: "/", label: "仪表盘", icon: "🍱" },
  { path: "/strategy", label: "策略", icon: "⚡" },
  { path: "/planner", label: "历史", icon: "📚" },
  { path: "/chat", label: "AI 私教", icon: "🤖" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const router = useRouter();

  // Navigation and Auth Guards
  const isAuthPage = pathname === "/login" || pathname === "/register";
  const isOnboarding = pathname === "/onboarding";
  const showNav = !isAuthPage && !isOnboarding;

  const handleLogout = () => {
    if (typeof window !== "undefined" && confirm("确定要退出账户吗？")) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_id");
      localStorage.removeItem("user_name");
      userStorage.clearUserId();
      window.location.href = "/login";
    }
  };

  // Basic Auth Guard
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token && !isAuthPage) {
      router.push("/login");
    }
  }, [pathname, isAuthPage, router]);

  return (
    <html lang="zh-CN">
      <body className="h-screen w-screen overflow-hidden">
        <UserProvider>
          <div className="relative h-full w-full flex flex-col">
            {/* Main Content Area */}
            <main className="flex-1 w-full h-full relative z-0">
              {children}
            </main>

            {/* Floating Capsule Navigation */}
            {showNav && (
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-50">
                <nav className="glass-card !rounded-full px-2 py-2 flex items-center gap-1 shadow-2xl ring-1 ring-white/50">
                  {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.path;
                    return (
                      <button
                        key={item.path}
                        onClick={() => router.push(item.path)}
                        className={`flex items-center gap-2 px-5 py-3 rounded-full transition-all duration-300 ${isActive
                          ? "bg-primary text-white shadow-lg scale-105"
                          : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                          }`}
                      >
                        <span className="text-xl">{item.icon}</span>
                        {isActive && (
                          <span className="text-sm font-bold tracking-wide animate-in fade-in slide-in-from-bottom-2 duration-300 whitespace-nowrap">
                            {item.label}
                          </span>
                        )}
                      </button>
                    );
                  })}

                  {/* Divider */}
                  <div className="w-px h-6 bg-border mx-1" />

                  {/* Logout Button */}
                  <button
                    onClick={handleLogout}
                    className="flex items-center justify-center w-10 h-10 rounded-full text-muted-foreground hover:bg-red-50 hover:text-red-500 transition-colors"
                    title="退出/重新开始"
                  >
                    <span className="text-lg">🚪</span>
                  </button>
                </nav>
              </div>
            )}
          </div>
        </UserProvider>
      </body>
    </html>
  );
}

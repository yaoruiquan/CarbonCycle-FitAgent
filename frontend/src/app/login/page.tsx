"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            const response = await authApi.login({ email, password });

            // Store token and user info
            localStorage.setItem("auth_token", response.access_token);
            localStorage.setItem("user_id", response.user_id);
            localStorage.setItem("user_name", response.user_name);

            // Broadcast login event if needed or just redirect
            window.location.href = "/";
        } catch (err: any) {
            setError(err.message || "登录失败，请检查邮箱和密码");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center p-4 relative overflow-hidden bg-[#0a0a0a]">
            {/* Dynamic Background Elements */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] animate-pulse"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '2s' }}></div>

            <div className="w-full max-w-[420px] relative z-10">
                {/* Logo Section */}
                <div className="text-center mb-10 space-y-2">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-primary-dark shadow-xl shadow-primary/20 mb-4 animate-in zoom-in duration-700">
                        <span className="text-3xl">🥦</span>
                    </div>
                    <h1 className="text-4xl font-bold tracking-tight text-white">
                        CarbonCycle <span className="text-primary">Fit</span>
                    </h1>
                    <p className="text-muted-foreground">开启您的科学控碳之旅</p>
                </div>

                {/* Login Card */}
                <div className="glass-card p-8 space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
                    <div className="space-y-2">
                        <h2 className="text-2xl font-semibold text-white">欢迎回来</h2>
                        <p className="text-sm text-muted-foreground">请输入您的凭据以继续</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider ml-1">邮箱地址</label>
                            <input
                                type="email"
                                required
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                                placeholder="name@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider ml-1">密码</label>
                            <input
                                type="password"
                                required
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-sm px-4 py-3 rounded-lg animate-in shake-in duration-300">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-primary hover:bg-primary-dark text-white font-bold py-4 rounded-xl shadow-lg shadow-primary/25 transform active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            ) : (
                                "立即登录"
                            )}
                        </button>
                    </form>

                    <div className="pt-4 text-center">
                        <p className="text-sm text-muted-foreground">
                            还没有账户？{" "}
                            <Link href="/register" className="text-primary hover:underline font-medium">
                                立即注册
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Footer info */}
                <div className="mt-12 text-center text-xs text-muted-foreground/50">
                    <p>© 2026 CarbonCycle-FitAgent. 基于科学，为健康而生。</p>
                </div>
            </div>
        </div>
    );
}

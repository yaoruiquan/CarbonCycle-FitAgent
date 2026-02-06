"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";

export default function RegisterPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [name, setName] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            setError("两次填写的密码不一致");
            return;
        }

        setLoading(true);
        setError("");

        try {
            // Create user with default profile data (will be completed in onboarding)
            const registerData = {
                email,
                password,
                name,
                // Fill defaults required by schema
                gender: "male",
                birth_date: "1990-01-01",
                height_cm: 170,
                weight_kg: 70,
                goal: "maintenance"
            };

            const user = await authApi.register(registerData);

            // Log them in immediately
            const loginResponse = await authApi.login({ email, password });

            localStorage.setItem("auth_token", loginResponse.access_token);
            localStorage.setItem("user_id", loginResponse.user_id);
            localStorage.setItem("user_name", loginResponse.user_name);

            // Redirect to onboarding to complete profile
            window.location.href = "/onboarding";
        } catch (err: any) {
            setError(err.message || "注册失败，该邮箱可能已被注册");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center p-4 relative overflow-hidden bg-[#0a0a0a]">
            {/* Background blobs */}
            <div className="absolute top-[-20%] right-[-10%] w-[60%] h-[60%] bg-primary/10 rounded-full blur-[150px]"></div>
            <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/5 rounded-full blur-[150px]"></div>

            <div className="w-full max-w-[420px] relative z-10">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2">加入 CarbonCycle</h1>
                    <p className="text-muted-foreground text-sm">仅需几分钟，开启您的健康新篇章</p>
                </div>

                <div className="glass-card p-8 space-y-6">
                    <form onSubmit={handleRegister} className="space-y-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider ml-1">如何称呼您</label>
                            <input
                                type="text"
                                required
                                minLength={2}
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                                placeholder="您的昵称"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                            <p className="text-[10px] text-muted-foreground/60 ml-1">至少 2 个字符</p>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider ml-1">电子邮箱</label>
                            <input
                                type="email"
                                required
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                                placeholder="name@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                            <p className="text-[10px] text-muted-foreground/60 ml-1">请输入有效的邮箱地址</p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider ml-1">设置密码</label>
                                <input
                                    type="password"
                                    required
                                    minLength={6}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <p className="text-[10px] text-muted-foreground/60 ml-1">至少 6 个字符</p>
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider ml-1">确认密码</label>
                                <input
                                    type="password"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                                    placeholder="••••••••"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                />
                                <p className="text-[10px] text-muted-foreground/60 ml-1">请再次输入密码</p>
                            </div>
                        </div>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs px-4 py-3 rounded-lg flex items-start gap-2 animate-in fade-in slide-in-from-top-1 duration-300">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
                                <span>{error}</span>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-primary hover:bg-primary-dark text-white font-bold py-4 rounded-xl shadow-lg shadow-primary/25 transform active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? "正在注册..." : "创建账户"}
                        </button>
                    </form>

                    <div className="text-center">
                        <p className="text-sm text-muted-foreground">
                            已经有账户了？{" "}
                            <Link href="/login" className="text-primary hover:underline font-medium">
                                立即登录
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

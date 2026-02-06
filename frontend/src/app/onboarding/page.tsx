"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { userApi, planApi } from "@/lib/api";
import { userStorage } from "@/lib/storage";

const GlassCard = ({ children, className }: any) => (
    <div className={`glass-card p-8 animate-in zoom-in-95 duration-500 ${className}`}>
        {children}
    </div>
);

export default function OnboardingPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [loadingText, setLoadingText] = useState("");
    const [error, setError] = useState("");

    // Split form data logic if needed, but keeping single state object for simplicity is fine
    // Step 1: Identity (Name)
    // Step 2: Profile (Gender, Age, Height, Weight)
    // Step 3: Goal & Plan (Goal, TargetWeight, Frequency)

    const [form, setForm] = useState({
        name: "",
        gender: "male" as "male" | "female",
        birthYear: 1995,
        height: 175,
        weight: 75,
        targetWeight: 70,
        goal: "fat_loss" as "fat_loss" | "muscle_gain" | "maintenance",
        trainingDays: 4,
    });

    const handleNext = () => {
        if (step < 3) setStep(step + 1);
        else handleSubmit();
    };

    const handleSubmit = async () => {
        setLoading(true);
        setLoadingText("正在创建你的数字档案...");
        try {
            const birthDate = `${form.birthYear}-01-01`;
            const userId = localStorage.getItem("user_id");

            let user;
            if (userId) {
                // Update existing user created during registration
                user = await userApi.update(userId, {
                    name: form.name,
                    gender: form.gender,
                    birth_date: birthDate,
                    height_cm: form.height,
                    weight_kg: form.weight,
                    target_weight_kg: form.targetWeight,
                    goal: form.goal,
                    activity_level: "moderate",
                    training_days_per_week: form.trainingDays,
                });
            } else {
                // Fallback for anonymous users (though login is now prioritized)
                user = await userApi.create({
                    name: form.name,
                    gender: form.gender,
                    birth_date: birthDate,
                    height_cm: form.height,
                    weight_kg: form.weight,
                    target_weight_kg: form.targetWeight,
                    goal: form.goal,
                    activity_level: "moderate",
                    training_days_per_week: form.trainingDays,
                });
                userStorage.setUserId(user.id);
            }

            setLoadingText("AI 正在计算基础代谢...");
            await new Promise(r => setTimeout(r, 800));

            setLoadingText("正在生成碳循环策略...");
            const today = new Date().toISOString().split("T")[0];

            // 2. Generate Plan
            await planApi.create({
                user_id: user.id,
                name: "智能生成计划",
                start_date: today,
                cycle_length_days: 7,
                num_cycles: 4,
                goal_deficit: form.goal === "fat_loss" ? -500 : form.goal === "muscle_gain" ? 300 : 0,
                high_carb_days: Math.min(form.trainingDays, 3),
                medium_carb_days: Math.max(0, form.trainingDays - 3),
                low_carb_days: 7 - form.trainingDays,
            });

            setLoadingText("系统准备就绪!");
            await new Promise(r => setTimeout(r, 500));
            router.push("/");
        } catch (err: any) {
            console.error(err);
            setError(err.message || "生成计划失败，请稍后重试");
            setLoading(false);
        }
    };

    return (
        <div className="h-screen w-screen flex items-center justify-center relative overflow-hidden">
            {/* Background Blobs */}
            <div className="absolute top-[-10%] right-[-10%] w-[50vh] h-[50vh] bg-primary/20 blur-[100px] rounded-full animate-float" />
            <div className="absolute bottom-[-10%] left-[-10%] w-[60vh] h-[60vh] bg-accent/20 blur-[120px] rounded-full animate-float" style={{ animationDelay: '-3s' }} />

            {!loading ? (
                <div className="w-full max-w-lg relative z-10 px-4">
                    {/* Progress Steps */}
                    <div className="flex justify-center gap-3 mb-8">
                        {[1, 2, 3].map(s => (
                            <div key={s} className={`h-1.5 rounded-full transition-all duration-500 ${s <= step ? 'w-8 bg-primary shadow-glow' : 'w-2 bg-primary/20'}`} />
                        ))}
                    </div>

                    <GlassCard>
                        {/* Step 1: Identity */}
                        {step === 1 && (
                            <div className="space-y-8 py-4">
                                <div className="text-center">
                                    <div className="text-5xl mb-4">👋</div>
                                    <h1 className="text-3xl font-black text-primary mb-2">欢迎来到 CarbonFit</h1>
                                    <p className="text-muted-foreground">首先，我们该怎么称呼你？</p>
                                </div>

                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold uppercase text-muted-foreground pl-1">昵称 / 姓名</label>
                                        <input
                                            value={form.name}
                                            onChange={e => setForm({ ...form, name: e.target.value })}
                                            className="w-full bg-white/50 border border-primary/10 rounded-2xl px-6 py-4 outline-none focus:ring-2 ring-primary/20 transition-all font-bold text-lg text-center shadow-inner"
                                            placeholder="你的名字"
                                            autoFocus
                                        />
                                    </div>
                                    <p className="text-xs text-center text-muted-foreground/60">这将用于你的个人 Dashboard</p>
                                </div>
                            </div>
                        )}

                        {/* Step 2: Profile Details */}
                        {step === 2 && (
                            <div className="space-y-6">
                                <div className="text-center">
                                    <h1 className="text-3xl font-black text-primary mb-2">完善个人档案</h1>
                                    <p className="text-muted-foreground">准确的数据能让 AI 规划更精准</p>
                                </div>

                                {/* Gender */}
                                <div className="flex gap-4 justify-center mb-6">
                                    {['male', 'female'].map(g => (
                                        <button
                                            key={g}
                                            onClick={() => setForm({ ...form, gender: g as any })}
                                            className={`w-32 py-4 rounded-2xl text-sm font-bold transition-all border-2 ${form.gender === g
                                                ? 'bg-primary/5 border-primary text-primary shadow-lg scale-105'
                                                : 'bg-white/40 border-transparent text-muted-foreground hover:bg-white/60'
                                                }`}
                                        >
                                            <span className="text-2xl block mb-1">{g === 'male' ? '👨' : '👩'}</span>
                                            {g === 'male' ? '男士' : '女士'}
                                        </button>
                                    ))}
                                </div>

                                {/* Metrics */}
                                <div className="grid grid-cols-2 gap-4">
                                    {[
                                        { l: '出生年份', k: 'birthYear', p: '1995' },
                                        { l: '身高 (cm)', k: 'height', p: '175' },
                                        { l: '体重 (kg)', k: 'weight', p: '70' },
                                        { l: '目标体重 (kg)', k: 'targetWeight', p: '65' }
                                    ].map((field: any) => (
                                        <div key={field.k} className="space-y-2">
                                            <label className="text-xs font-bold uppercase text-muted-foreground">{field.l}</label>
                                            <input
                                                type="number"
                                                value={form[field.k as keyof typeof form]}
                                                onChange={e => setForm({ ...form, [field.k]: +e.target.value })}
                                                className="w-full bg-white/50 border border-primary/10 rounded-xl px-2 py-3 outline-none focus:ring-2 ring-primary/20 transition-all font-medium text-center"
                                                placeholder={field.p}
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Step 3: Strategy & Goal */}
                        {step === 3 && (
                            <div className="space-y-6">
                                <div className="text-center">
                                    <h1 className="text-3xl font-black text-primary mb-2">设定训练目标</h1>
                                    <p className="text-muted-foreground">AI 将根据此生成碳循环策略</p>
                                </div>

                                {/* Goals */}
                                <div className="grid gap-3">
                                    {[
                                        { id: 'fat_loss', icon: '🔥', title: '减脂刷脂', desc: '热量缺口，激进循环' },
                                        { id: 'muscle_gain', icon: '💪', title: '增肌塑形', desc: '热量盈余，高碳日为主' },
                                        { id: 'maintenance', icon: '⚖️', title: '保持健康', desc: '灵活饮食，代谢健康' }
                                    ].map(opt => (
                                        <button
                                            key={opt.id}
                                            onClick={() => setForm({ ...form, goal: opt.id as any })}
                                            className={`flex items-center gap-4 p-4 rounded-2xl border-2 transition-all text-left group ${form.goal === opt.id
                                                ? 'border-primary bg-primary/5 shadow-inner'
                                                : 'border-transparent bg-white/40 hover:bg-white/60'
                                                }`}
                                        >
                                            <span className="text-3xl transition-transform group-hover:scale-125 duration-300">{opt.icon}</span>
                                            <div>
                                                <div className={`font-bold ${form.goal === opt.id ? 'text-primary' : 'text-foreground'}`}>{opt.title}</div>
                                                <div className="text-xs text-muted-foreground">{opt.desc}</div>
                                            </div>
                                        </button>
                                    ))}
                                </div>

                                {/* Training Frequency */}
                                <div className="bg-white/50 rounded-2xl p-4 border border-dashed border-primary/20 mt-4">
                                    <label className="text-xs font-bold uppercase text-muted-foreground block text-center mb-2">每周力量训练频率</label>
                                    <div className="flex items-center gap-4">
                                        <span className="text-xs font-bold text-muted-foreground">休闲</span>
                                        <input
                                            type="range" min={2} max={6} step={1}
                                            value={form.trainingDays}
                                            onChange={e => setForm({ ...form, trainingDays: +e.target.value })}
                                            className="flex-1 h-2 bg-gradient-to-r from-primary/20 to-primary rounded-lg appearance-none cursor-pointer accent-primary"
                                        />
                                        <span className="text-xs font-bold text-muted-foreground">硬核</span>
                                    </div>
                                    <div className="text-center mt-2 font-black text-2xl text-primary">
                                        {form.trainingDays} <span className="text-xs font-normal">练 / 周</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="mt-4 bg-red-500/10 border border-red-500/20 text-red-500 text-xs px-4 py-3 rounded-lg flex items-start gap-2 animate-in fade-in slide-in-from-top-1 duration-300">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
                                <span>{error}</span>
                            </div>
                        )}

                        {/* Navigation Buttons */}
                        <button
                            onClick={handleNext}
                            disabled={step === 1 && !form.name.trim()}
                            className="w-full mt-8 bg-primary text-white h-14 rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {step === 3 ? "生成我的专属计划 🚀" : "下一步 →"}
                        </button>
                    </GlassCard>
                </div>
            ) : (
                // Loading State
                <div className="flex flex-col items-center gap-6 z-10 transition-all animate-in fade-in duration-500">
                    <div className="relative w-24 h-24">
                        <div className="absolute inset-0 border-4 border-primary/20 rounded-full" />
                        <div className="absolute inset-0 border-4 border-primary rounded-full border-t-transparent animate-spin" />
                        <div className="absolute inset-0 flex items-center justify-center text-4xl animate-pulse">🥗</div>
                    </div>
                    <div className="text-2xl font-bold text-primary tracking-tight">{loadingText}</div>
                </div>
            )}
        </div>
    );
}

"use client";

import { useCallback, useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { userStorage } from "@/lib/storage";
import { planApi, logApi, reportApi } from "@/lib/api";
import { CarbonCyclePlan, LogStats } from "@/lib/types";

interface WeeklyStats {
    calorieTarget: number;
    calorieActual: number;
    calorieRate: number;
    trainingCompleted: number;
    trainingTotal: number;
    trainingRate: number;
    avgProtein: number;
    avgCarbs: number;
    avgFat: number;
    weightStart: number | null;
    weightEnd: number | null;
    weightChange: number | null;
}

interface HistoricalReport {
    id: string;
    user_id: string;
    week_start: string;
    week_end: string;
    calorie_rate: number;
    training_rate: number;
    weight_change: number | null;
    avg_protein: number;
    avg_carbs: number;
    avg_fat: number;
    summary: string | null;
    recommendations: string[];
    created_at: string;
}

const GlassCard = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
    <div className={`glass-card p-6 ${className}`}>{children}</div>
);

function ReportContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const weekId = searchParams.get("week");

    const [loading, setLoading] = useState(true);
    const [plan, setPlan] = useState<CarbonCyclePlan | null>(null);
    const [stats, setStats] = useState<WeeklyStats | null>(null);
    const [aiReport, setAiReport] = useState<string>("");
    const [generatingReport, setGeneratingReport] = useState(false);

    // Historical report mode
    const [historicalReport, setHistoricalReport] = useState<HistoricalReport | null>(null);
    const [isHistorical, setIsHistorical] = useState(false);
    const [notFound, setNotFound] = useState(false);

    // Weight input
    const [showWeightModal, setShowWeightModal] = useState(false);
    const [weightInput, setWeightInput] = useState("");
    const [weights, setWeights] = useState<{ date: string; value: number }[]>([]);

    const calculateStats = useCallback((planData: CarbonCyclePlan, logStats: LogStats | null) => {
        const weekDays = planData.days.slice(0, 7);

        const totalTarget = weekDays.reduce((sum: number, d) => {
            const cal = (d.macros?.protein_g * 4 || 0) + (d.macros?.carbs_g * 4 || 0) + (d.macros?.fat_g * 9 || 0);
            return sum + cal;
        }, 0);
        const avgTarget = totalTarget / 7;

        const actualCalories = logStats?.avg_calories || 0;
        const completedTraining = logStats?.training_completion_rate ?
            Math.round(logStats.training_completion_rate / 100 * weekDays.filter(d => d.training_scheduled).length) : 0;

        const trainingDays = weekDays.filter(d => d.training_scheduled);

        setStats({
            calorieTarget: avgTarget,
            calorieActual: actualCalories,
            calorieRate: avgTarget > 0 ? (actualCalories / avgTarget) * 100 : 0,
            trainingCompleted: completedTraining,
            trainingTotal: trainingDays.length,
            trainingRate: trainingDays.length > 0 ? (completedTraining / trainingDays.length) * 100 : 0,
            avgProtein: logStats?.avg_protein || 0,
            avgCarbs: logStats?.avg_carbs || 0,
            avgFat: logStats?.avg_fat || 0,
            weightStart: weights.length > 0 ? weights[0].value : null,
            weightEnd: weights.length > 1 ? weights[weights.length - 1].value : null,
            weightChange: weights.length > 1 ? weights[weights.length - 1].value - weights[0].value : null,
        });
    }, [weights]);

    const loadCurrentWeekData = useCallback(async (userId: string) => {
        try {
            const [activePlan, logStats] = await Promise.all([
                planApi.getActive(userId).catch(() => null),
                logApi.getStats(userId, 7).catch(() => null),
            ]);
            setPlan(activePlan);

            if (activePlan) {
                calculateStats(activePlan, logStats);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [calculateStats]);

    const loadHistoricalReport = useCallback(async (reportId: string) => {
        try {
            const report = await reportApi.getById(reportId);
            setHistoricalReport(report);
            setIsHistorical(true);

            // Convert historical data to stats format
            setStats({
                calorieTarget: 2000, // Not stored in historical
                calorieActual: 0,
                calorieRate: report.calorie_rate,
                trainingCompleted: Math.round(report.training_rate / 100 * 5),
                trainingTotal: 5,
                trainingRate: report.training_rate,
                avgProtein: report.avg_protein,
                avgCarbs: report.avg_carbs,
                avgFat: report.avg_fat,
                weightStart: null,
                weightEnd: null,
                weightChange: report.weight_change,
            });

            if (report.summary) {
                setAiReport(report.summary);
            }
        } catch (err) {
            console.error(err);
            setNotFound(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        const userId = userStorage.getUserId();
        if (!userId) {
            router.push("/onboarding");
            return;
        }

        if (weekId) {
            // Load historical report
            loadHistoricalReport(weekId);
        } else {
            // Load current week
            loadCurrentWeekData(userId);
        }
    }, [router, weekId, loadCurrentWeekData, loadHistoricalReport]);

    const generateAIReport = async () => {
        if (!stats || !plan) return;

        setGeneratingReport(true);

        try {
            const res = await fetch("http://localhost:8000/api/reports/weekly", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: userStorage.getUserId(),
                    stats: stats,
                    plan_id: plan.id,
                }),
            });

            if (res.ok) {
                const data = await res.json();
                setAiReport(data.report || "报告生成成功！");
            } else {
                setAiReport("报告生成失败，后端返回错误。");
            }
        } catch (err) {
            console.error(err);
            setAiReport("报告生成失败，请稍后重试。");
        } finally {
            setGeneratingReport(false);
        }
    };

    const handleAddWeight = () => {
        const value = parseFloat(weightInput);
        if (!isNaN(value) && value > 0) {
            const today = new Date().toISOString().split("T")[0];
            setWeights(prev => [...prev, { date: today, value }]);
            setWeightInput("");
            setShowWeightModal(false);
            if (plan) calculateStats(plan, null);
        }
    };

    const getWeekRange = () => {
        if (isHistorical && historicalReport) {
            const start = new Date(historicalReport.week_start);
            const end = new Date(historicalReport.week_end);
            return `${start.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })} - ${end.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })}`;
        }

        const now = new Date();
        const start = new Date(now);
        start.setDate(now.getDate() - now.getDay() + 1);
        const end = new Date(start);
        end.setDate(start.getDate() + 6);
        return `${start.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })} - ${end.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })}`;
    };

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center text-primary animate-pulse text-xl font-bold">
                正在加载数据...
            </div>
        );
    }

    if (notFound) {
        return (
            <div className="max-w-[1200px] mx-auto p-6 text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h1 className="text-2xl font-bold text-muted-foreground mb-4">未找到该周报</h1>
                <p className="text-muted-foreground mb-6">请检查链接是否正确，或返回历史记录重新选择。</p>
                <button
                    onClick={() => router.push("/planner")}
                    className="px-6 py-3 rounded-xl bg-primary text-white font-bold"
                >
                    返回历史记录
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-[1200px] mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black text-primary">
                        {isHistorical ? "📜 历史周报" : "📊 周复盘报告"}
                    </h1>
                    <p className="text-muted-foreground mt-1">{getWeekRange()}</p>
                </div>
                <div className="flex gap-3">
                    {!isHistorical && (
                        <button
                            onClick={() => setShowWeightModal(true)}
                            className="px-4 py-2 rounded-xl bg-secondary hover:bg-secondary/80 font-bold text-sm transition-colors"
                        >
                            ⚖️ 记录体重
                        </button>
                    )}
                    <button
                        onClick={() => router.push(isHistorical ? "/planner" : "/")}
                        className="px-4 py-2 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary font-bold text-sm transition-colors"
                    >
                        ← {isHistorical ? "返回历史" : "返回仪表盘"}
                    </button>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-4 gap-4">
                <GlassCard className="text-center">
                    <div className="text-4xl font-black text-primary">{stats?.calorieRate?.toFixed(0) || 0}%</div>
                    <div className="text-xs font-bold text-muted-foreground mt-2 uppercase">热量达标率</div>
                </GlassCard>

                <GlassCard className="text-center">
                    <div className="text-4xl font-black text-accent">{stats?.trainingRate?.toFixed(0) || 0}%</div>
                    <div className="text-xs font-bold text-muted-foreground mt-2 uppercase">训练完成率</div>
                    <div className="text-[10px] text-muted-foreground/60 mt-1">
                        {stats?.trainingCompleted || 0}/{stats?.trainingTotal || 0} 次
                    </div>
                </GlassCard>

                <GlassCard className="text-center">
                    <div className={`text-4xl font-black ${stats?.weightChange === null || stats?.weightChange === undefined ? "text-muted-foreground" :
                        stats.weightChange < 0 ? "text-emerald-500" :
                            stats.weightChange > 0 ? "text-rose-500" : "text-foreground"
                        }`}>
                        {stats?.weightChange !== null && stats?.weightChange !== undefined
                            ? `${stats.weightChange > 0 ? "+" : ""}${stats.weightChange.toFixed(1)}`
                            : "—"
                        }
                    </div>
                    <div className="text-xs font-bold text-muted-foreground mt-2 uppercase">体重变化 (kg)</div>
                </GlassCard>

                <GlassCard className="text-center">
                    <div className="flex justify-center gap-4 text-sm font-bold">
                        <span className="text-amber-600">碳{stats?.avgCarbs?.toFixed(0) || 0}g</span>
                        <span className="text-emerald-600">蛋{stats?.avgProtein?.toFixed(0) || 0}g</span>
                        <span className="text-rose-600">脂{stats?.avgFat?.toFixed(0) || 0}g</span>
                    </div>
                    <div className="text-xs font-bold text-muted-foreground mt-3 uppercase">日均宏量</div>
                </GlassCard>
            </div>

            {/* AI Report / Historical Summary Section */}
            <GlassCard>
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-extrabold text-primary flex items-center gap-2">
                        {isHistorical ? "📋 周报总结" : "🤖 AI 分析与建议"}
                    </h2>
                    {!isHistorical && (
                        <button
                            onClick={generateAIReport}
                            disabled={generatingReport}
                            className="px-4 py-2 rounded-xl bg-accent text-white font-bold text-sm hover:bg-accent/90 transition-colors disabled:opacity-50"
                        >
                            {generatingReport ? "生成中..." : "生成报告"}
                        </button>
                    )}
                </div>

                {aiReport ? (
                    <div className="prose prose-sm max-w-none text-foreground/90 whitespace-pre-wrap">
                        {aiReport}
                    </div>
                ) : (
                    <div className="text-center py-12 text-muted-foreground">
                        <span className="text-4xl mb-3 block opacity-50">📝</span>
                        <p>{isHistorical ? "该周报无详细分析" : "点击\"生成报告\"获取 AI 分析"}</p>
                    </div>
                )}

                {/* Historical recommendations */}
                {isHistorical && historicalReport?.recommendations && historicalReport.recommendations.length > 0 && (
                    <div className="mt-6 pt-6 border-t border-border/50">
                        <h3 className="font-bold text-sm text-muted-foreground mb-3">📌 当时的建议</h3>
                        <ul className="space-y-2">
                            {historicalReport.recommendations.map((rec, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm">
                                    <span className="text-primary">•</span>
                                    <span>{rec}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </GlassCard>

            {/* Weight Modal */}
            {showWeightModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl p-6 w-80 shadow-2xl">
                        <h3 className="text-lg font-bold mb-4">⚖️ 记录今日体重</h3>
                        <input
                            type="number"
                            step="0.1"
                            value={weightInput}
                            onChange={(e) => setWeightInput(e.target.value)}
                            placeholder="例如: 72.5"
                            className="w-full px-4 py-3 rounded-xl border bg-secondary/30 text-lg font-bold text-center focus:outline-none focus:ring-2 focus:ring-primary"
                            autoFocus
                        />
                        <div className="flex gap-3 mt-4">
                            <button
                                onClick={() => setShowWeightModal(false)}
                                className="flex-1 py-2 rounded-xl bg-secondary font-bold"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleAddWeight}
                                className="flex-1 py-2 rounded-xl bg-primary text-white font-bold"
                            >
                                确认
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function ReportPage() {
    return (
        <Suspense fallback={
            <div className="h-full flex items-center justify-center text-primary animate-pulse text-xl font-bold">
                正在加载数据...
            </div>
        }>
            <ReportContent />
        </Suspense>
    );
}

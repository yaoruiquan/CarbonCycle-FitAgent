"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { userStorage } from "@/lib/storage";

// Mock historical data (would come from backend)
interface WeeklyRecord {
    id: string;
    weekRange: string;
    calorieRate: number;
    trainingRate: number;
    weightChange: number | null;
    avgCalories: number;
}

interface WeightRecord {
    date: string;
    value: number;
}

const GlassCard = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
    <div className={`glass-card p-6 ${className}`}>{children}</div>
);

// Simple SVG line chart for weight trend
const WeightTrendChart = ({ data }: { data: WeightRecord[] }) => {
    if (data.length < 2) {
        return (
            <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                    <span className="text-4xl block mb-2 opacity-50">📊</span>
                    <p className="text-sm">记录更多体重数据后显示趋势图</p>
                </div>
            </div>
        );
    }

    const minWeight = Math.min(...data.map(d => d.value)) - 1;
    const maxWeight = Math.max(...data.map(d => d.value)) + 1;
    const range = maxWeight - minWeight;

    const width = 100;
    const height = 60;
    const padding = 10;

    const points = data.map((d, i) => {
        const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
        const y = height - padding - ((d.value - minWeight) / range) * (height - 2 * padding);
        return { x, y, ...d };
    });

    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

    return (
        <div className="h-full flex flex-col">
            <svg viewBox={`0 0 ${width} ${height}`} className="flex-1 w-full">
                {/* Grid lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
                    <line
                        key={i}
                        x1={padding}
                        y1={padding + ratio * (height - 2 * padding)}
                        x2={width - padding}
                        y2={padding + ratio * (height - 2 * padding)}
                        stroke="currentColor"
                        strokeOpacity={0.1}
                        strokeWidth={0.3}
                    />
                ))}

                {/* Line */}
                <path
                    d={pathD}
                    fill="none"
                    stroke="url(#gradient)"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />

                {/* Points */}
                {points.map((p, i) => (
                    <circle
                        key={i}
                        cx={p.x}
                        cy={p.y}
                        r={2}
                        fill="white"
                        stroke="hsl(var(--primary))"
                        strokeWidth={1.5}
                    />
                ))}

                {/* Gradient */}
                <defs>
                    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="hsl(var(--primary))" />
                        <stop offset="100%" stopColor="hsl(var(--accent))" />
                    </linearGradient>
                </defs>
            </svg>

            {/* X-axis labels */}
            <div className="flex justify-between text-[10px] text-muted-foreground px-2 mt-1">
                {points.map((p, i) => (
                    <span key={i}>{p.date.slice(5)}</span>
                ))}
            </div>

            {/* Current weight */}
            <div className="text-center mt-3">
                <span className="text-3xl font-black text-primary">{data[data.length - 1]?.value}</span>
                <span className="text-sm text-muted-foreground ml-1">kg</span>
            </div>
        </div>
    );
};

export default function HistoryPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);

    // Mock data - would come from backend
    const [weeklyRecords] = useState<WeeklyRecord[]>([
        { id: "1", weekRange: "02/03 - 02/09", calorieRate: 85, trainingRate: 80, weightChange: -0.4, avgCalories: 2050 },
        { id: "2", weekRange: "01/27 - 02/02", calorieRate: 92, trainingRate: 100, weightChange: -0.2, avgCalories: 2100 },
        { id: "3", weekRange: "01/20 - 01/26", calorieRate: 78, trainingRate: 60, weightChange: 0.1, avgCalories: 2200 },
        { id: "4", weekRange: "01/13 - 01/19", calorieRate: 88, trainingRate: 80, weightChange: -0.3, avgCalories: 2080 },
    ]);

    const [weightHistory] = useState<WeightRecord[]>([
        { date: "2026-01-13", value: 75.8 },
        { date: "2026-01-20", value: 75.5 },
        { date: "2026-01-27", value: 75.6 },
        { date: "2026-02-03", value: 75.4 },
        { date: "2026-02-09", value: 75.0 },
    ]);

    useEffect(() => {
        const userId = userStorage.getUserId();
        if (!userId) {
            router.push("/onboarding");
            return;
        }
        // Simulate loading
        setTimeout(() => setLoading(false), 300);
    }, [router]);

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center text-primary animate-pulse text-xl font-bold">
                加载历史记录...
            </div>
        );
    }

    return (
        <div className="max-w-[1200px] mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black text-primary">📚 历史记录</h1>
                    <p className="text-muted-foreground mt-1">查看过往周报告和体重趋势</p>
                </div>
                <button
                    onClick={() => router.push("/report")}
                    className="px-4 py-2 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary font-bold text-sm transition-colors"
                >
                    查看本周报告 →
                </button>
            </div>

            {/* Weight Trend Chart */}
            <GlassCard className="h-64">
                <h2 className="text-lg font-extrabold text-primary mb-4 flex items-center gap-2">
                    📈 体重趋势
                </h2>
                <div className="h-[calc(100%-2rem)]">
                    <WeightTrendChart data={weightHistory} />
                </div>
            </GlassCard>

            {/* Weekly Reports List */}
            <GlassCard>
                <h2 className="text-lg font-extrabold text-primary mb-4 flex items-center gap-2">
                    📋 周报告历史
                </h2>

                <div className="space-y-3">
                    {weeklyRecords.map((record) => (
                        <div
                            key={record.id}
                            onClick={() => router.push(`/report?week=${record.id}`)}
                            className="flex items-center gap-4 p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 cursor-pointer transition-colors group"
                        >
                            {/* Date Range */}
                            <div className="min-w-[120px]">
                                <div className="font-bold text-sm">{record.weekRange}</div>
                            </div>

                            {/* Stats */}
                            <div className="flex-1 flex items-center gap-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground">热量</span>
                                    <span className={`font-bold ${record.calorieRate >= 80 ? "text-emerald-600" : "text-amber-600"}`}>
                                        {record.calorieRate}%
                                    </span>
                                </div>

                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground">训练</span>
                                    <span className={`font-bold ${record.trainingRate >= 80 ? "text-emerald-600" : "text-amber-600"}`}>
                                        {record.trainingRate}%
                                    </span>
                                </div>

                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground">体重</span>
                                    <span className={`font-bold ${record.weightChange === null ? "text-muted-foreground" :
                                            record.weightChange < 0 ? "text-emerald-600" :
                                                record.weightChange > 0 ? "text-rose-600" : "text-foreground"
                                        }`}>
                                        {record.weightChange !== null
                                            ? `${record.weightChange > 0 ? "+" : ""}${record.weightChange.toFixed(1)}kg`
                                            : "—"
                                        }
                                    </span>
                                </div>
                            </div>

                            {/* Arrow */}
                            <span className="text-muted-foreground group-hover:text-primary transition-colors">
                                →
                            </span>
                        </div>
                    ))}
                </div>

                {weeklyRecords.length === 0 && (
                    <div className="text-center py-12 text-muted-foreground">
                        <span className="text-4xl block mb-2 opacity-50">📭</span>
                        <p>暂无历史记录</p>
                    </div>
                )}
            </GlassCard>
        </div>
    );
}

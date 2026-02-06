"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { planApi, userApi } from "@/lib/api";
import { userStorage } from "@/lib/storage";
import { CarbonCyclePlan, DayPlan, DayType } from "@/lib/types";
import DayDetailModal from "@/components/DayDetailModal";
import FoodUploadModal from "@/components/FoodUploadModal";
import TrainingChecklist from "@/components/TrainingChecklist";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

const GlassCard = ({ children, className = "", onClick }: GlassCardProps) => (
  <div onClick={onClick} className={`glass-card p-8 ${className}`}>
    {children}
  </div>
);

interface MacroRingProps {
  value: number;
  total: number;
  color: string;
  label: string;
  icon: string;
}

const MacroRing = ({ value, total, color, label, icon }: MacroRingProps) => {
  const radius = 36; // Increased from 30
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(value / total, 1) * circumference;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-24 h-24 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90">
          <circle cx="48" cy="48" r={radius} stroke="currentColor" strokeWidth="8" fill="transparent" className="text-muted/50" />
          <circle cx="48" cy="48" r={radius} stroke="currentColor" strokeWidth="8" fill="transparent"
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            className={color}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-3xl">
          {icon}
        </div>
      </div>
      <div className="text-center">
        <div className="text-xl font-black tracking-tight">{Math.round(value)}g</div>
        <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
};

const dayTypeConfig: Record<DayType, { label: string; bg: string; text: string; emoji: string }> = {
  high_carb: { label: "高碳日", bg: "bg-red-100/50", text: "text-red-700", emoji: "🔴" },
  medium_carb: { label: "中碳日", bg: "bg-yellow-100/50", text: "text-yellow-700", emoji: "🟡" },
  low_carb: { label: "低碳日", bg: "bg-green-100/50", text: "text-green-700", emoji: "🟢" },
  refeed: { label: "欺骗餐", bg: "bg-pink-100/50", text: "text-pink-700", emoji: "💗" },
};

// Food log entry interface
interface FoodLogEntry {
  id: string;
  food_name: string;
  portion: string;
  carbs_g: number;
  protein_g: number;
  fat_g: number;
  calories: number;
  time: string;
  image_path?: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [plan, setPlan] = useState<CarbonCyclePlan | null>(null);
  const [todayPlan, setTodayPlan] = useState<DayPlan | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedDay, setSelectedDay] = useState<DayPlan | null>(null);
  const [showFoodModal, setShowFoodModal] = useState(false);
  const [consumedCalories, setConsumedCalories] = useState(0);

  // Food logs for today's meals
  const [foodLogs, setFoodLogs] = useState<FoodLogEntry[]>([]);

  // Calculate consumed macros from food logs
  const consumedMacros = {
    protein_g: foodLogs.reduce((sum, log) => sum + log.protein_g, 0),
    carbs_g: foodLogs.reduce((sum, log) => sum + log.carbs_g, 0),
    fat_g: foodLogs.reduce((sum, log) => sum + log.fat_g, 0),
  };

  useEffect(() => {
    const userId = userStorage.getUserId();
    if (!userId) {
      router.push("/onboarding");
      return;
    }
    loadData(userId);
  }, [router]);

  const loadData = async (userId: string) => {
    try {
      const [userData, activePlan] = await Promise.all([
        userApi.get(userId),
        planApi.getActive(userId).catch(() => null),
      ]);
      setUser(userData);
      setPlan(activePlan);

      const todayStr = new Date().toISOString().split("T")[0];
      if (activePlan) {
        const tp = activePlan.days.find((d: DayPlan) => d.date === todayStr);
        setTodayPlan(tp || activePlan.days[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDay = async (updatedDay: DayPlan) => {
    if (!plan) return;
    const newDays = plan.days.map(d => d.date === updatedDay.date ? updatedDay : d);
    setPlan({ ...plan, days: newDays });
    if (todayPlan?.date === updatedDay.date) setTodayPlan(updatedDay);
    setSelectedDay(null);
    try {
      await planApi.update(plan.id, { days: newDays });
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="h-full flex items-center justify-center text-primary animate-pulse text-xl font-bold">正在加载数据...</div>;

  const dayConfig = todayPlan ? dayTypeConfig[todayPlan.day_type] : null;
  const macros = todayPlan ? todayPlan.macros : { protein_g: 150, carbs_g: 200, fat_g: 60 };
  const calories = macros.protein_g * 4 + macros.carbs_g * 4 + macros.fat_g * 9;

  return (
    <>
      <div className="bento-grid grid-cols-12 grid-rows-12 gap-6 p-6 max-w-[1600px] mx-auto">

        {/* 1. Today's Plan (Top Left) */}
        <GlassCard
          className="col-span-3 row-span-4 flex flex-col justify-between overflow-hidden relative group cursor-pointer hover:border-primary/50 transition-all"
          onClick={() => todayPlan && setSelectedDay(todayPlan)}
        >
          <div className="absolute top-4 right-4 p-2 opacity-30 group-hover:opacity-100 transition-opacity">
            <span className="text-3xl">📝</span>
          </div>
          <div>
            <h3 className="text-2xl font-black text-primary mb-2">今日计划</h3>
            <div className="flex items-center gap-3 mb-4">
              <span className={`px-3 py-1 rounded-full text-xs font-bold shadow-sm ${dayConfig?.bg} ${dayConfig?.text}`}>
                {dayConfig?.label}
              </span>
              <span className="text-xs text-muted-foreground font-bold group-hover:text-primary transition-colors">点击编辑详情 →</span>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase font-bold text-muted-foreground flex items-center gap-2 mb-1">
                  🏋️ 训练安排
                </div>
                <p className="text-sm font-medium text-foreground/90 line-clamp-2 leading-relaxed">
                  {todayPlan?.training_type || "暂无具体计划 (点击添加)"}
                </p>
              </div>
              <div>
                <div className="text-xs uppercase font-bold text-muted-foreground flex items-center gap-2 mb-1">
                  🥗 饮食建议
                </div>
                <p className="text-sm font-medium text-foreground/90 line-clamp-2 leading-relaxed">
                  {todayPlan?.notes || "参考宏量营养素摄入，保持血糖平稳..."}
                </p>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* 2. Primary Stats + Hello (Top Center/Right) */}
        <div className="col-span-9 row-span-4 grid grid-cols-3 gap-6">
          <GlassCard className="flex flex-col justify-center gap-2">
            <h1 className="text-4xl font-black text-primary tracking-tight">你好, {user?.name}</h1>
            <p className="text-lg text-muted-foreground font-medium">今天也要保持 {dayConfig?.label} 的节奏!</p>

            <div className="mt-6 flex items-end gap-8">
              <div>
                <div className="text-5xl font-black text-foreground">{Math.round(calories)}</div>
                <div className="text-xs uppercase font-bold text-muted-foreground mt-1 tracking-wider">目标热量 (kcal)</div>
              </div>
              <div className="h-12 w-px bg-border" />
              <div className="pb-1 opacity-60">
                <div className="text-xl font-bold line-through">{Math.round(consumedCalories)}</div>
                <div className="text-[10px] uppercase font-bold">已摄入</div>
              </div>
            </div>
          </GlassCard>

          <GlassCard
            onClick={() => setShowFoodModal(true)}
            className="bg-gradient-to-br from-accent to-orange-500 !text-white border-none cursor-pointer flex flex-col items-center justify-center gap-3 relative overflow-hidden group shadow-orange-500/20 shadow-2xl"
          >
            <div className="absolute inset-0 bg-[url('/images/bg-texture.png')] opacity-20 mix-blend-overlay" />
            <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-xl group-hover:scale-110 group-hover:rotate-12 transition-all duration-500 shadow-inner">
              <span className="text-3xl">🥗</span>
            </div>
            <div className="text-center relative z-10">
              <h3 className="text-lg font-black tracking-tight">饮食记录</h3>
              <p className="text-white/80 font-medium text-xs">拍照或手动输入</p>
            </div>
          </GlassCard>

          {/* Report Button */}
          <GlassCard
            onClick={() => router.push("/report")}
            className="bg-gradient-to-br from-violet-500 to-purple-600 !text-white border-none cursor-pointer flex flex-col items-center justify-center gap-3 relative overflow-hidden group shadow-purple-500/20 shadow-2xl"
          >
            <div className="absolute inset-0 bg-[url('/images/bg-texture.png')] opacity-20 mix-blend-overlay" />
            <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-xl group-hover:scale-110 group-hover:rotate-12 transition-all duration-500 shadow-inner">
              <span className="text-3xl">📊</span>
            </div>
            <div className="text-center relative z-10">
              <h3 className="text-lg font-black tracking-tight">周复盘报告</h3>
              <p className="text-white/80 font-medium text-xs">AI 分析建议</p>
            </div>
          </GlassCard>
        </div>

        {/* 3. Middle Row: Macros + Training + Diet Log */}
        {/* Macros */}
        <GlassCard className="col-span-5 row-span-4 flex items-center justify-around px-8">
          <MacroRing value={consumedMacros.protein_g} total={macros.protein_g} color="text-emerald-500" label="蛋白质" icon="🥩" />
          <MacroRing value={consumedMacros.carbs_g} total={macros.carbs_g} color="text-amber-500" label="碳水" icon="🍚" />
          <MacroRing value={consumedMacros.fat_g} total={macros.fat_g} color="text-rose-500" label="脂肪" icon="🥑" />
        </GlassCard>

        {/* Training Checklist (Middle) */}
        <GlassCard className="col-span-3 row-span-4 overflow-hidden">
          <TrainingChecklist
            todayPlan={todayPlan}
            onToggle={(exercise, completed) => {
              console.log(`Exercise ${exercise}: ${completed}`);
            }}
          />
        </GlassCard>

        {/* Today's Diet Log */}
        <GlassCard className="col-span-4 row-span-4 flex flex-col overflow-hidden">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-extrabold text-primary flex items-center gap-2">
              📝 今日饮食记录
            </h3>
            <span className="text-xs text-muted-foreground">共 {foodLogs.length} 餐</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {foodLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                <span className="text-4xl mb-2 opacity-50">🍽️</span>
                <p className="text-sm">还没有记录</p>
                <p className="text-xs">点击“饮食记录”开始</p>
              </div>
            ) : (
              foodLogs.map((log) => (
                <div
                  key={log.id}
                  className="bg-secondary/30 rounded-xl p-3 flex items-center gap-3 hover:bg-secondary/50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center text-lg">
                    🍲
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm truncate">{log.food_name}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {log.portion} · {log.time}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-black text-primary">{Math.round(log.calories)}</div>
                    <div className="text-[9px] text-muted-foreground uppercase">kcal</div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Summary Bar */}
          {foodLogs.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50 flex justify-between text-xs">
              <span className="text-muted-foreground">合计</span>
              <span className="font-bold">
                <span className="text-amber-600">磳{Math.round(consumedMacros.carbs_g)}g</span>
                <span className="mx-1.5 text-muted-foreground">|</span>
                <span className="text-emerald-600">蛋{Math.round(consumedMacros.protein_g)}g</span>
                <span className="mx-1.5 text-muted-foreground">|</span>
                <span className="text-rose-600">脂{Math.round(consumedMacros.fat_g)}g</span>
              </span>
            </div>
          )}
        </GlassCard>

        {/* 4. Weekly Strip (Bottom) */}
        <GlassCard className="col-span-12 row-span-4 flex flex-col overflow-hidden">
          <div className="flex justify-between items-center mb-4 px-2">
            <h3 className="text-xl font-extrabold text-primary flex items-center gap-2">
              📅 本周节奏 <span className="text-xs font-normal text-muted-foreground bg-secondary/50 px-2 py-1 rounded-full">点击查看详情</span>
            </h3>
            <button onClick={() => router.push("/strategy")} className="text-sm font-bold text-accent hover:text-accent/80 hover:underline transition-colors">
              策略全览 →
            </button>
          </div>
          <div className="flex-1 flex gap-4 overflow-x-auto no-scrollbar items-center pb-2 px-1">
            {plan?.days.slice(0, 7).map((day, i) => {
              const cfg = dayTypeConfig[day.day_type];
              const isToday = day.date === todayPlan?.date;
              return (
                <div
                  key={i}
                  onClick={() => setSelectedDay(day)}
                  className={`flex-1 min-w-[100px] h-full rounded-2xl flex flex-col items-center justify-center transition-all cursor-pointer border-2 relative group overflow-hidden ${isToday
                    ? "bg-primary text-white border-primary shadow-xl scale-105 z-10"
                    : "bg-white/50 border-transparent hover:bg-white/80 hover:border-primary/20 hover:scale-[1.02]"
                    }`}
                >
                  <span className="text-xs font-bold opacity-70 mb-2">{day.date.slice(5)}</span>
                  <span className={`text-3xl mb-3 transition-transform duration-300 ${!isToday && "group-hover:scale-125"}`}>{cfg.emoji}</span>
                  <span className="text-xs uppercase font-black tracking-wide bg-black/5 px-2 py-1 rounded-md">{cfg.label}</span>
                </div>
              );
            })}
          </div>
        </GlassCard>

      </div>

      {selectedDay && (
        <DayDetailModal
          day={selectedDay}
          isOpen={true}
          onClose={() => setSelectedDay(null)}
          onSave={handleSaveDay}
        />
      )}

      {/* Food Upload Modal */}
      <FoodUploadModal
        isOpen={showFoodModal}
        onClose={() => setShowFoodModal(false)}
        userId={userStorage.getUserId() || ""}
        onSuccess={(result) => {
          // Add to food logs
          const newLog = {
            id: Date.now().toString(),
            food_name: result.food_name,
            portion: result.portion,
            carbs_g: result.carbs_g,
            protein_g: result.protein_g,
            fat_g: result.fat_g,
            calories: result.calories,
            time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
            image_path: result.image_path,
          };
          setFoodLogs(prev => [...prev, newLog]);
          setConsumedCalories(prev => prev + result.calories);
          setShowFoodModal(false);
        }}
      />
    </>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { planApi } from "@/lib/api";
import { userStorage } from "@/lib/storage";
import { CarbonCyclePlan, DayPlan, DayType } from "@/lib/types";

import {
    DndContext,
    closestCenter,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
} from "@dnd-kit/core";
import {
    arrayMove,
    SortableContext,
    useSortable,
    horizontalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

// Day type configuration
const dayTypeConfig: Record<DayType, { label: string; bg: string; text: string; emoji: string; border: string }> = {
    high_carb: {
        label: "高碳日", bg: "bg-red-50", text: "text-red-700", emoji: "🔴", border: "border-red-200"
    },
    medium_carb: {
        label: "中碳日", bg: "bg-yellow-50", text: "text-yellow-700", emoji: "🟡", border: "border-yellow-200"
    },
    low_carb: {
        label: "低碳日", bg: "bg-green-50", text: "text-green-700", emoji: "🟢", border: "border-green-200"
    },
    refeed: {
        label: "欺骗餐", bg: "bg-pink-50", text: "text-pink-700", emoji: "💗", border: "border-pink-200"
    },
};

// Sortable Day Card Component
function SortableDayCard({
    day,
    displayIndex,
    isEditMode,
    onEdit,
}: {
    day: DayPlan;
    displayIndex: number;
    isEditMode: boolean;
    onEdit: () => void;
}) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: day.date });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 50 : 1,
    };

    const cfg = dayTypeConfig[day.day_type];
    const calories = Math.round(day.macros.protein_g * 4 + day.macros.carbs_g * 4 + day.macros.fat_g * 9);

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...(isEditMode ? listeners : {})}
            className={`
        relative rounded-2xl flex flex-col p-4 transition-all duration-200 overflow-hidden border-2
        ${isEditMode ? "cursor-grab active:cursor-grabbing" : "cursor-pointer"}
        ${isDragging ? "opacity-90 shadow-2xl scale-105 ring-4 ring-primary/30" : ""}
        ${cfg.bg} ${cfg.border}
        hover:shadow-lg hover:scale-[1.02]
      `}
            onClick={() => !isEditMode && onEdit()}
        >
            {/* Drag Handle Indicator (Edit Mode) */}
            {isEditMode && (
                <div className="absolute top-2 right-2 flex flex-col gap-0.5 opacity-40">
                    <div className="w-4 h-0.5 bg-current rounded" />
                    <div className="w-4 h-0.5 bg-current rounded" />
                    <div className="w-4 h-0.5 bg-current rounded" />
                </div>
            )}

            {/* Day Number & Date */}
            <div className="text-center mb-3">
                <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                    Day {displayIndex + 1}
                </div>
                <div className="text-sm font-bold font-mono text-foreground/70">{day.date.slice(5)}</div>
            </div>

            {/* Emoji & Label */}
            <div className="flex flex-col items-center gap-2 my-auto">
                <div className={`text-5xl transition-transform ${isDragging ? "scale-110" : ""}`}>
                    {cfg.emoji}
                </div>
                <div className={`font-bold text-sm px-3 py-1 rounded-lg bg-white/70 backdrop-blur-sm ${cfg.text}`}>
                    {cfg.label}
                </div>
            </div>

            {/* Calories */}
            <div className="text-center mt-4">
                <div className="text-2xl font-black text-foreground/80">{calories}</div>
                <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">kcal</div>
            </div>

            {/* Training & Diet Preview */}
            <div className="mt-4 space-y-2">
                <div className="bg-white/50 p-2 rounded-lg">
                    <div className="text-[10px] font-bold text-primary flex items-center gap-1 mb-1">
                        🏋️ 训练
                    </div>
                    <p className="text-[10px] text-foreground/70 line-clamp-2">
                        {day.training_type || "暂无计划"}
                    </p>
                </div>
                <div className="bg-white/50 p-2 rounded-lg">
                    <div className="text-[10px] font-bold text-accent flex items-center gap-1 mb-1">
                        🥗 饮食
                    </div>
                    <p className="text-[10px] text-foreground/70 line-clamp-2">
                        {day.notes || "暂无建议"}
                    </p>
                </div>
            </div>

            {/* Edit Hint (View Mode) */}
            {!isEditMode && (
                <div className="absolute bottom-2 inset-x-0 text-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[9px] text-muted-foreground">点击编辑</span>
                </div>
            )}
        </div>
    );
}

// Edit Modal Component
function EditDayModal({
    day,
    isOpen,
    onClose,
    onRegenerate,
    isRegenerating,
    onChangeDayType,
}: {
    day: DayPlan | null;
    isOpen: boolean;
    onClose: () => void;
    onRegenerate: () => void;
    isRegenerating: boolean;
    onChangeDayType: (newType: DayType) => void;
}) {
    if (!isOpen || !day) return null;

    const cfg = dayTypeConfig[day.day_type];
    const calories = Math.round(day.macros.protein_g * 4 + day.macros.carbs_g * 4 + day.macros.fat_g * 9);

    const dayTypes: DayType[] = ["high_carb", "medium_carb", "low_carb"];

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-3xl max-w-lg w-full max-h-[80vh] overflow-auto shadow-2xl">
                {/* Header */}
                <div className={`p-6 ${cfg.bg} border-b ${cfg.border}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-4xl">{cfg.emoji}</span>
                            <div>
                                <h2 className={`text-2xl font-black ${cfg.text}`}>{cfg.label}</h2>
                                <p className="text-sm text-muted-foreground">{day.date}</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="text-2xl text-muted-foreground hover:text-foreground">
                            ×
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Day Type Switcher */}
                    <div>
                        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">
                            🔄 切换碳类型
                        </h3>
                        <div className="flex gap-2">
                            {dayTypes.map((type) => {
                                const typeCfg = dayTypeConfig[type];
                                const isActive = day.day_type === type;
                                return (
                                    <button
                                        key={type}
                                        onClick={() => !isActive && !isRegenerating && onChangeDayType(type)}
                                        disabled={isRegenerating}
                                        className={`
                                            flex-1 py-3 px-2 rounded-xl font-bold text-sm transition-all
                                            flex flex-col items-center gap-1
                                            ${isActive
                                                ? `${typeCfg.bg} ${typeCfg.text} ring-2 ring-offset-2 ring-current scale-105`
                                                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                                            }
                                            disabled:opacity-50 disabled:cursor-not-allowed
                                        `}
                                    >
                                        <span className="text-xl">{typeCfg.emoji}</span>
                                        <span>{typeCfg.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                        <p className="text-xs text-muted-foreground mt-2 text-center">
                            切换后将自动重新生成饮食和训练计划
                        </p>
                    </div>

                    {/* Macros */}
                    <div>
                        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">
                            宏量目标
                        </h3>
                        <div className="grid grid-cols-4 gap-3 text-center">
                            <div className="bg-secondary/30 rounded-xl p-3">
                                <div className="text-2xl font-black text-primary">{calories}</div>
                                <div className="text-[10px] font-bold text-muted-foreground">热量</div>
                            </div>
                            <div className="bg-emerald-50 rounded-xl p-3">
                                <div className="text-xl font-black text-emerald-600">{day.macros.protein_g}g</div>
                                <div className="text-[10px] font-bold text-muted-foreground">蛋白质</div>
                            </div>
                            <div className="bg-amber-50 rounded-xl p-3">
                                <div className="text-xl font-black text-amber-600">{day.macros.carbs_g}g</div>
                                <div className="text-[10px] font-bold text-muted-foreground">碳水</div>
                            </div>
                            <div className="bg-rose-50 rounded-xl p-3">
                                <div className="text-xl font-black text-rose-600">{day.macros.fat_g}g</div>
                                <div className="text-[10px] font-bold text-muted-foreground">脂肪</div>
                            </div>
                        </div>
                    </div>

                    {/* Training */}
                    <div>
                        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                            🏋️ 训练计划
                        </h3>
                        <div className="bg-secondary/20 rounded-xl p-4">
                            <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                                {day.training_type || "暂无训练计划，点击重新生成"}
                            </p>
                        </div>
                    </div>

                    {/* Diet */}
                    <div>
                        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                            🥗 饮食建议
                        </h3>
                        <div className="bg-secondary/20 rounded-xl p-4">
                            <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                                {day.notes || "暂无饮食建议，点击重新生成"}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t bg-secondary/10 flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-3 rounded-xl bg-white border border-border text-foreground font-bold hover:bg-secondary/30 transition-colors"
                    >
                        关闭
                    </button>
                    <button
                        onClick={onRegenerate}
                        disabled={isRegenerating}
                        className="flex-1 px-4 py-3 rounded-xl bg-accent text-white font-bold hover:bg-accent/90 transition-colors disabled:opacity-50"
                    >
                        {isRegenerating ? "生成中..." : "🔄 重新生成计划"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// Main Strategy Page
export default function StrategyPage() {
    const router = useRouter();
    const [plan, setPlan] = useState<CarbonCyclePlan | null>(null);
    const [days, setDays] = useState<DayPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [editMode, setEditMode] = useState(false);
    const [saving, setSaving] = useState(false);

    const [selectedDay, setSelectedDay] = useState<DayPlan | null>(null);
    const [isRegenerating, setIsRegenerating] = useState(false);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8, // Require 8px movement before drag starts
            },
        })
    );

    useEffect(() => {
        loadData();
    }, []);

    const loadData = () => {
        const userId = userStorage.getUserId();
        if (!userId) return router.push("/onboarding");

        planApi.getActive(userId)
            .then(p => {
                setPlan(p);
                setDays(p.days);
            })
            .catch(() => null)
            .finally(() => setLoading(false));
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over || active.id === over.id) return;

        setDays((items) => {
            const oldIndex = items.findIndex((d) => d.date === active.id);
            const newIndex = items.findIndex((d) => d.date === over.id);
            const reordered = arrayMove(items, oldIndex, newIndex);

            // Reassign dates based on new order
            if (plan) {
                const startDate = new Date(plan.start_date);
                return reordered.map((d, i) => {
                    const newDate = new Date(startDate);
                    newDate.setDate(startDate.getDate() + i);
                    return {
                        ...d,
                        date: newDate.toISOString().split("T")[0],
                    };
                });
            }
            return reordered;
        });
    };

    const handleSave = async () => {
        if (!plan) return;
        setSaving(true);
        try {
            await planApi.update(plan.id, { days });
            setPlan({ ...plan, days });
            setEditMode(false);
        } catch (err) {
            console.error(err);
            alert("保存失败，请重试");
        } finally {
            setSaving(false);
        }
    };

    const handleRegenerate = async () => {
        if (!selectedDay || !plan) return;
        setIsRegenerating(true);
        try {
            const regenerated = await planApi.regenerateDay(plan.id, selectedDay.date);
            // Update local state
            setDays(prev => prev.map(d => d.date === selectedDay.date ? regenerated : d));
            setSelectedDay(regenerated);
        } catch (err) {
            console.error(err);
            alert("生成失败，请重试");
        } finally {
            setIsRegenerating(false);
        }
    };

    const handleChangeDayType = async (newType: DayType) => {
        if (!selectedDay || !plan) return;
        setIsRegenerating(true);
        try {
            // First update the day type locally
            const updatedDay = { ...selectedDay, day_type: newType };
            setSelectedDay(updatedDay);
            setDays(prev => prev.map(d => d.date === selectedDay.date ? updatedDay : d));

            // Save the day type change to server
            const newDays = days.map(d => d.date === selectedDay.date ? updatedDay : d);
            await planApi.update(plan.id, { days: newDays });

            // Regenerate the day's training/diet plan with new type
            const regenerated = await planApi.regenerateDay(plan.id, selectedDay.date);
            setDays(prev => prev.map(d => d.date === selectedDay.date ? regenerated : d));
            setSelectedDay(regenerated);
        } catch (err) {
            console.error(err);
            alert("切换失败，请重试");
        } finally {
            setIsRegenerating(false);
        }
    };

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center text-primary animate-pulse text-xl font-bold">
                加载策略中...
            </div>
        );
    }

    return (
        <div className="h-[calc(100vh-6rem)] p-4 flex flex-col gap-4">
            {/* Header */}
            <div className="flex justify-between items-end px-2">
                <div>
                    <h1 className="text-3xl font-extrabold text-primary">碳循环策略</h1>
                    <p className="text-muted-foreground text-sm">
                        {editMode ? "拖动卡片调整顺序，点击保存生效" : "点击卡片查看详情，点击调整计划开启拖拽模式"}
                    </p>
                </div>
                <div className="flex gap-3">
                    {editMode && (
                        <button
                            onClick={() => {
                                setDays(plan?.days || []);
                                setEditMode(false);
                            }}
                            className="px-6 py-2 rounded-full font-bold bg-white text-muted-foreground hover:bg-secondary/50 transition-all shadow-md"
                        >
                            取消
                        </button>
                    )}
                    <button
                        onClick={editMode ? handleSave : () => setEditMode(true)}
                        disabled={saving}
                        className={`px-6 py-2 rounded-full font-bold transition-all shadow-lg min-w-[120px] ${editMode
                            ? "bg-accent text-white hover:bg-accent/90"
                            : "bg-primary text-white hover:bg-primary/90"
                            }`}
                    >
                        {saving ? "保存中..." : editMode ? "保存生效" : "调整计划"}
                    </button>
                </div>
            </div>

            {/* Drag Hint */}
            {editMode && (
                <div className="px-2">
                    <div className="bg-accent/10 border border-accent/30 rounded-xl p-3 flex items-center gap-3">
                        <span className="text-2xl">🖐️</span>
                        <div>
                            <p className="text-sm font-bold text-accent">拖拽模式已开启</p>
                            <p className="text-xs text-muted-foreground">拖动卡片调整每日顺序，训练和饮食计划会跟随移动</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Grid with DnD */}
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={days.map(d => d.date)} strategy={horizontalListSortingStrategy}>
                    <div className="flex-1 grid grid-cols-7 gap-3 pb-4">
                        {days.slice(0, 7).map((day, i) => (
                            <SortableDayCard
                                key={day.date}
                                day={day}
                                displayIndex={i}
                                isEditMode={editMode}
                                onEdit={() => setSelectedDay(day)}
                            />
                        ))}
                    </div>
                </SortableContext>
            </DndContext>

            {/* Edit Modal */}
            <EditDayModal
                day={selectedDay}
                isOpen={!!selectedDay}
                onClose={() => setSelectedDay(null)}
                onRegenerate={handleRegenerate}
                isRegenerating={isRegenerating}
                onChangeDayType={handleChangeDayType}
            />
        </div>
    );
}

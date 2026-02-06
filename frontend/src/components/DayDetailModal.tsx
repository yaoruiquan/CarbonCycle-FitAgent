"use client";

import { useState, useEffect } from "react";
import { DayPlan, DayType } from "@/lib/types";

interface DayDetailModalProps {
    day: DayPlan;
    isOpen: boolean;
    onClose: () => void;
    onSave: (updatedDay: DayPlan) => void;
}

const dayConfig: Record<DayType, { label: string; bg: string; text: string; emoji: string }> = {
    high_carb: { label: "高碳日", bg: "bg-red-100", text: "text-red-700", emoji: "🔴" },
    medium_carb: { label: "中碳日", bg: "bg-yellow-100", text: "text-yellow-700", emoji: "🟡" },
    low_carb: { label: "低碳日", bg: "bg-green-100", text: "text-green-700", emoji: "🟢" },
    refeed: { label: "欺骗餐", bg: "bg-pink-100", text: "text-pink-700", emoji: "💗" },
};

export default function DayDetailModal({ day, isOpen, onClose, onSave }: DayDetailModalProps) {
    const [editedDay, setEditedDay] = useState<DayPlan>(day);

    useEffect(() => {
        setEditedDay(day);
    }, [day]);

    if (!isOpen) return null;

    const cfg = dayConfig[editedDay.day_type];
    const calories = editedDay.macros.protein_g * 4 + editedDay.macros.carbs_g * 4 + editedDay.macros.fat_g * 9;

    const handleMacroChange = (key: 'protein_g' | 'carbs_g' | 'fat_g', value: string) => {
        setEditedDay({
            ...editedDay,
            macros: { ...editedDay.macros, [key]: Number(value) }
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white/95 backdrop-blur-xl w-full max-w-lg rounded-[2rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className={`p-6 ${cfg.bg} flex justify-between items-start`}>
                    <div>
                        <h2 className="text-2xl font-black text-foreground">{editedDay.date}</h2>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="text-3xl">{cfg.emoji}</span>
                            <span className={`px-3 py-1 bg-white/50 backdrop-blur rounded-full font-bold text-sm ${cfg.text}`}>
                                {cfg.label}
                            </span>
                        </div>
                    </div>
                    <button onClick={onClose} className="w-8 h-8 rounded-full bg-white/50 flex items-center justify-center hover:bg-white text-lg">
                        ✕
                    </button>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">

                    {/* 1. Macros Input */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold uppercase text-muted-foreground">宏量营养素 (Target Macros)</label>
                        <div className="flex gap-4">
                            {[
                                { l: '蛋白质 (P)', k: 'protein_g', c: 'text-emerald-600', bg: 'bg-emerald-50' },
                                { l: '碳水 (C)', k: 'carbs_g', c: 'text-amber-600', bg: 'bg-amber-50' },
                                { l: '脂肪 (F)', k: 'fat_g', c: 'text-rose-600', bg: 'bg-rose-50' }
                            ].map((m: any) => (
                                <div key={m.k} className={`flex-1 p-3 rounded-xl ${m.bg}`}>
                                    <div className={`text-xs font-bold mb-1 ${m.c}`}>{m.l}</div>
                                    <input
                                        type="number"
                                        value={editedDay.macros[m.k as keyof typeof editedDay.macros]}
                                        onChange={e => handleMacroChange(m.k, e.target.value)}
                                        className="w-full bg-transparent font-black text-xl outline-none"
                                    />
                                    <div className="text-[10px] opacity-60 font-bold">g</div>
                                </div>
                            ))}
                        </div>
                        <div className="text-right text-xs font-bold text-muted-foreground">
                            总热量: <span className="text-primary text-base">{Math.round(calories)}</span> kcal
                        </div>
                    </div>

                    {/* 2. Training Plan */}
                    <div className="space-y-2">
                        <div className="flex justify-between items-center">
                            <label className="text-xs font-bold uppercase text-muted-foreground">🏋️ 今日训练计划 (Training Plan)</label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={editedDay.training_scheduled}
                                    onChange={e => setEditedDay({ ...editedDay, training_scheduled: e.target.checked })}
                                    className="w-4 h-4 accent-primary"
                                />
                                <span className="text-xs font-bold text-primary">有训练</span>
                            </label>
                        </div>
                        <textarea
                            value={editedDay.training_type || ""}
                            onChange={e => setEditedDay({ ...editedDay, training_type: e.target.value })}
                            placeholder="例如: 胸肌卧推 5组 + 三头下压 4组..."
                            className="w-full h-24 bg-secondary/30 rounded-xl p-4 text-sm font-medium outline-none focus:ring-2 ring-primary/20 resize-none border-secondary"
                        />
                    </div>

                    {/* 3. Diet Instructions */}
                    <div className="space-y-2">
                        <label className="text-xs font-bold uppercase text-muted-foreground">🥗 饮食指导 (Diet Instructions)</label>
                        <textarea
                            value={editedDay.notes || ""}
                            onChange={e => setEditedDay({ ...editedDay, notes: e.target.value })}
                            placeholder="例如: 早餐燕麦牛奶，午餐鸡胸肉沙拉..."
                            className="w-full h-32 bg-secondary/30 rounded-xl p-4 text-sm font-medium outline-none focus:ring-2 ring-primary/20 resize-none border-secondary"
                        />
                    </div>

                </div>

                {/* Footer Actions */}
                <div className="p-6 border-t border-border/50 bg-white/50 backdrop-blur flex gap-4">
                    <button onClick={onClose} className="flex-1 py-3 rounded-xl font-bold hover:bg-secondary/50 text-muted-foreground transition-colors">
                        取消
                    </button>
                    <button onClick={() => onSave(editedDay)} className="flex-1 py-3 rounded-xl font-bold bg-primary text-white shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all">
                        保存修改
                    </button>
                </div>

            </div>
        </div>
    );
}

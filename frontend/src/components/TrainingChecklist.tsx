"use client";

import { useState } from "react";
import { DayPlan } from "@/lib/types";

interface TrainingChecklistProps {
    todayPlan: DayPlan | null;
    onToggle?: (exercise: string, completed: boolean) => void;
}

// Parse training_type string into individual exercises
const parseExercises = (trainingType: string | undefined): string[] => {
    if (!trainingType) return [];

    // Common patterns: "胸+三头", "背部训练、二头", "腿部：深蹲、腿举"
    const exercises = trainingType
        .replace(/[+、，,：:]/g, "|")
        .split("|")
        .map(e => e.trim())
        .filter(e => e.length > 0);

    // If no parsing worked, return the whole string as one item
    if (exercises.length === 0 && trainingType.trim()) {
        return [trainingType.trim()];
    }

    return exercises;
};

export default function TrainingChecklist({ todayPlan, onToggle }: TrainingChecklistProps) {
    const exercises = parseExercises(todayPlan?.training_type ?? undefined);
    const [completed, setCompleted] = useState<Record<string, boolean>>({});

    const handleToggle = (exercise: string) => {
        const newValue = !completed[exercise];
        setCompleted(prev => ({ ...prev, [exercise]: newValue }));
        onToggle?.(exercise, newValue);
    };

    const completedCount = Object.values(completed).filter(Boolean).length;
    const totalExercises = exercises.length;
    const progressPercent = totalExercises > 0 ? (completedCount / totalExercises) * 100 : 0;

    const isRestDay = !todayPlan?.training_scheduled;

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-extrabold text-primary flex items-center gap-2">
                    🏋️ 今日训练
                </h3>
                {!isRestDay && (
                    <span className="text-xs font-bold text-muted-foreground">
                        {completedCount}/{totalExercises}
                    </span>
                )}
            </div>

            {/* Exercise List */}
            <div className="flex-1 overflow-y-auto space-y-2">
                {isRestDay ? (
                    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                        <span className="text-4xl mb-2 opacity-50">😴</span>
                        <p className="text-sm font-medium">今天是休息日</p>
                        <p className="text-xs">好好恢复，明天继续！</p>
                    </div>
                ) : exercises.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                        <span className="text-4xl mb-2 opacity-50">📝</span>
                        <p className="text-sm">暂无训练计划</p>
                        <p className="text-xs">点击今日计划添加</p>
                    </div>
                ) : (
                    exercises.map((exercise, idx) => {
                        const isCompleted = completed[exercise];
                        return (
                            <div
                                key={idx}
                                onClick={() => handleToggle(exercise)}
                                className={`
                  flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all
                  ${isCompleted ? "bg-primary/10" : "hover:bg-secondary/50"}
                `}
                            >
                                {/* Checkbox */}
                                <div
                                    className={`
                    w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 transition-all
                    ${isCompleted
                                            ? "border-primary bg-primary text-white"
                                            : "border-muted-foreground/40 hover:border-primary"
                                        }
                  `}
                                >
                                    {isCompleted && <span className="text-xs font-bold">✓</span>}
                                </div>

                                {/* Exercise name */}
                                <span className={`
                  font-medium text-sm flex-1
                  ${isCompleted ? "line-through text-muted-foreground" : ""}
                `}>
                                    {exercise}
                                </span>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Progress Bar */}
            {!isRestDay && exercises.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/50">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-bold text-muted-foreground">完成度</span>
                        <span className="text-xs font-black text-primary">{Math.round(progressPercent)}%</span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

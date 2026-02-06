"use client";

import { useState, useRef, useCallback } from "react";

interface FoodAnalysisResult {
    food_name: string;
    portion: string;
    carbs_g: number;
    protein_g: number;
    fat_g: number;
    calories: number;
    confidence: number;
    image_path?: string;
    log_id?: string;
}

interface FoodUploadModalProps {
    isOpen: boolean;
    onClose: () => void;
    userId: string;
    onSuccess?: (result: FoodAnalysisResult) => void;
}

type InputMode = "photo" | "manual";

export default function FoodUploadModal({
    isOpen,
    onClose,
    userId,
    onSuccess,
}: FoodUploadModalProps) {
    const [inputMode, setInputMode] = useState<InputMode>("photo");

    // Photo mode state
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    // Manual mode state
    const [manualFoodName, setManualFoodName] = useState("");
    const [manualWeight, setManualWeight] = useState<number>(100);
    const [useAIEstimate, setUseAIEstimate] = useState(true);

    // Shared state
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<FoodAnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Editable fields for correction
    const [editMode, setEditMode] = useState(false);
    const [editCarbs, setEditCarbs] = useState(0);
    const [editProtein, setEditProtein] = useState(0);
    const [editFat, setEditFat] = useState(0);

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setSelectedFile(file);
        setPreviewUrl(URL.createObjectURL(file));
        setResult(null);
        setError(null);
        setEditMode(false);
    }, []);

    const handleAnalyzePhoto = async () => {
        if (!selectedFile) return;

        setIsAnalyzing(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append("file", selectedFile);
            formData.append("user_id", userId);
            formData.append("meal_type", getMealType());
            formData.append("auto_log", "true");

            const res = await fetch("http://localhost:8000/api/food/analyze", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "分析失败");
            }

            const data: FoodAnalysisResult = await res.json();
            setResult(data);
            setEditCarbs(data.carbs_g);
            setEditProtein(data.protein_g);
            setEditFat(data.fat_g);

        } catch (err: unknown) {
            console.error(err);
            setError(err instanceof Error ? err.message : "分析失败，请重试");
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleManualSubmit = async () => {
        if (!manualFoodName.trim() || manualWeight <= 0) {
            setError("请输入食物名称和重量");
            return;
        }

        setIsAnalyzing(true);
        setError(null);

        try {
            if (useAIEstimate) {
                // Call AI estimation API
                const res = await fetch("http://localhost:8000/api/food/estimate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        food_name: manualFoodName,
                        weight_g: manualWeight,
                        user_id: userId,
                        meal_type: getMealType(),
                        auto_log: true,
                    }),
                });

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "估算失败");
                }

                const data: FoodAnalysisResult = await res.json();
                setResult(data);
                setEditCarbs(data.carbs_g);
                setEditProtein(data.protein_g);
                setEditFat(data.fat_g);
            } else {
                // Manual input without AI - show empty result for user to fill
                setResult({
                    food_name: manualFoodName,
                    portion: `${manualWeight}g`,
                    carbs_g: 0,
                    protein_g: 0,
                    fat_g: 0,
                    calories: 0,
                    confidence: 1.0,
                    log_id: `manual-${Date.now()}`,
                });
                setEditCarbs(0);
                setEditProtein(0);
                setEditFat(0);
                setEditMode(true); // Immediately enter edit mode
            }
        } catch (err: unknown) {
            console.error(err);
            setError(err instanceof Error ? err.message : "操作失败，请重试");
        } finally {
            setIsAnalyzing(false);
        }
    };

    const getMealType = () => {
        const hour = new Date().getHours();
        if (hour < 10) return "breakfast";
        if (hour < 14) return "lunch";
        if (hour < 18) return "snack";
        return "dinner";
    };

    const handleCorrect = async () => {
        if (!result?.log_id) return;

        try {
            const formData = new FormData();
            formData.append("carbs_g", String(editCarbs));
            formData.append("protein_g", String(editProtein));
            formData.append("fat_g", String(editFat));

            const res = await fetch(`http://localhost:8000/api/food/correct/${result.log_id}`, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) throw new Error("修正失败");

            // Update local result
            const newCalories = editCarbs * 4 + editProtein * 4 + editFat * 9;
            setResult({
                ...result,
                carbs_g: editCarbs,
                protein_g: editProtein,
                fat_g: editFat,
                calories: newCalories,
            });
            setEditMode(false);

        } catch (err) {
            console.error(err);
            alert("修正失败，请重试");
        }
    };

    const handleConfirm = () => {
        if (result && onSuccess) {
            onSuccess(result);
        }
        handleClose();
    };

    const handleClose = () => {
        setSelectedFile(null);
        setPreviewUrl(null);
        setResult(null);
        setError(null);
        setEditMode(false);
        setManualFoodName("");
        setManualWeight(100);
        setUseAIEstimate(true);
        onClose();
    };

    if (!isOpen) return null;

    const calculatedCalories = editCarbs * 4 + editProtein * 4 + editFat * 9;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-3xl max-w-md w-full max-h-[90vh] overflow-auto shadow-2xl">
                {/* Header */}
                <div className="p-6 border-b bg-gradient-to-r from-primary/10 to-accent/10">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-3xl">{inputMode === "photo" ? "📷" : "✏️"}</span>
                            <div>
                                <h2 className="text-xl font-black text-foreground">记录饮食</h2>
                                <p className="text-xs text-muted-foreground">
                                    {inputMode === "photo" ? "AI 智能识别营养成分" : "手动输入食物信息"}
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={handleClose}
                            className="text-2xl text-muted-foreground hover:text-foreground transition-colors"
                        >
                            ×
                        </button>
                    </div>
                </div>

                {/* Mode Switcher */}
                {!result && (
                    <div className="p-4 bg-secondary/30">
                        <div className="flex gap-2">
                            <button
                                onClick={() => setInputMode("photo")}
                                className={`flex-1 py-2 px-4 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${inputMode === "photo"
                                        ? "bg-primary text-white shadow-lg"
                                        : "bg-white text-muted-foreground hover:bg-white/80"
                                    }`}
                            >
                                📷 拍照识别
                            </button>
                            <button
                                onClick={() => setInputMode("manual")}
                                className={`flex-1 py-2 px-4 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${inputMode === "manual"
                                        ? "bg-primary text-white shadow-lg"
                                        : "bg-white text-muted-foreground hover:bg-white/80"
                                    }`}
                            >
                                ✏️ 手动输入
                            </button>
                        </div>
                    </div>
                )}

                {/* Content */}
                <div className="p-6 space-y-4">
                    {/* Photo Mode */}
                    {inputMode === "photo" && !result && (
                        <>
                            {/* Upload Area */}
                            <div
                                onClick={() => fileInputRef.current?.click()}
                                className={`
                                    relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all
                                    ${previewUrl ? "border-primary bg-primary/5" : "border-border hover:border-primary hover:bg-secondary/30"}
                                `}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    capture="environment"
                                    onChange={handleFileSelect}
                                    className="hidden"
                                />

                                {previewUrl ? (
                                    <img
                                        src={previewUrl}
                                        alt="食物照片"
                                        className="w-full h-48 object-cover rounded-xl"
                                    />
                                ) : (
                                    <div className="space-y-2">
                                        <div className="text-5xl">🍽️</div>
                                        <p className="text-sm font-medium text-muted-foreground">
                                            点击拍照或选择图片
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Analyze Button */}
                            {selectedFile && (
                                <button
                                    onClick={handleAnalyzePhoto}
                                    disabled={isAnalyzing}
                                    className="w-full py-3 rounded-xl bg-accent text-white font-bold hover:bg-accent/90 transition-colors disabled:opacity-50"
                                >
                                    {isAnalyzing ? (
                                        <span className="flex items-center justify-center gap-2">
                                            <span className="animate-spin">🔄</span>
                                            AI 识别中...
                                        </span>
                                    ) : (
                                        "🔍 开始识别"
                                    )}
                                </button>
                            )}
                        </>
                    )}

                    {/* Manual Mode */}
                    {inputMode === "manual" && !result && (
                        <div className="space-y-4">
                            {/* Food Name */}
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                    食物名称
                                </label>
                                <input
                                    type="text"
                                    value={manualFoodName}
                                    onChange={(e) => setManualFoodName(e.target.value)}
                                    placeholder="例如：米饭、鸡胸肉、苹果..."
                                    className="w-full px-4 py-3 rounded-xl border border-border bg-white focus:ring-2 ring-primary/20 focus:outline-none transition-all text-sm"
                                />
                            </div>

                            {/* Weight */}
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                    重量 (克)
                                </label>
                                <input
                                    type="number"
                                    value={manualWeight}
                                    onChange={(e) => setManualWeight(Number(e.target.value))}
                                    placeholder="100"
                                    min={1}
                                    className="w-full px-4 py-3 rounded-xl border border-border bg-white focus:ring-2 ring-primary/20 focus:outline-none transition-all text-sm"
                                />
                            </div>

                            {/* AI Estimate Toggle */}
                            <div className="bg-secondary/30 rounded-xl p-4">
                                <label className="flex items-center justify-between cursor-pointer">
                                    <div>
                                        <div className="font-bold text-sm text-foreground">🤖 AI 自动估算营养</div>
                                        <div className="text-xs text-muted-foreground">根据食物名称和重量自动计算</div>
                                    </div>
                                    <input
                                        type="checkbox"
                                        checked={useAIEstimate}
                                        onChange={(e) => setUseAIEstimate(e.target.checked)}
                                        className="w-5 h-5 accent-primary"
                                    />
                                </label>
                            </div>

                            {/* Submit Button */}
                            <button
                                onClick={handleManualSubmit}
                                disabled={isAnalyzing || !manualFoodName.trim()}
                                className="w-full py-3 rounded-xl bg-accent text-white font-bold hover:bg-accent/90 transition-colors disabled:opacity-50"
                            >
                                {isAnalyzing ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <span className="animate-spin">🔄</span>
                                        {useAIEstimate ? "AI 估算中..." : "处理中..."}
                                    </span>
                                ) : useAIEstimate ? (
                                    "🤖 AI 估算营养"
                                ) : (
                                    "✏️ 手动输入营养"
                                )}
                            </button>
                        </div>
                    )}

                    {/* Error Display */}
                    {error && (
                        <div className="p-3 bg-red-50 text-red-600 rounded-xl text-sm">
                            ⚠️ {error}
                        </div>
                    )}

                    {/* Analysis Result */}
                    {result && (
                        <div className="space-y-4">
                            {/* Food Name */}
                            <div className="text-center">
                                <div className="text-lg font-bold text-foreground">{result.food_name}</div>
                                <div className="text-sm text-muted-foreground">{result.portion}</div>
                                {result.confidence < 1.0 && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                        置信度: {(result.confidence * 100).toFixed(0)}%
                                    </div>
                                )}
                            </div>

                            {/* Macros */}
                            <div className="grid grid-cols-3 gap-3">
                                <div className="bg-amber-50 p-3 rounded-xl text-center">
                                    <div className="text-[10px] font-bold text-muted-foreground mb-1">🍚 碳水</div>
                                    {editMode ? (
                                        <input
                                            type="number"
                                            value={editCarbs}
                                            onChange={(e) => setEditCarbs(Number(e.target.value))}
                                            className="w-full text-center text-lg font-black text-amber-600 bg-transparent border-b border-amber-300 focus:outline-none"
                                        />
                                    ) : (
                                        <div className="text-lg font-black text-amber-600">{result.carbs_g}g</div>
                                    )}
                                </div>
                                <div className="bg-emerald-50 p-3 rounded-xl text-center">
                                    <div className="text-[10px] font-bold text-muted-foreground mb-1">🥩 蛋白</div>
                                    {editMode ? (
                                        <input
                                            type="number"
                                            value={editProtein}
                                            onChange={(e) => setEditProtein(Number(e.target.value))}
                                            className="w-full text-center text-lg font-black text-emerald-600 bg-transparent border-b border-emerald-300 focus:outline-none"
                                        />
                                    ) : (
                                        <div className="text-lg font-black text-emerald-600">{result.protein_g}g</div>
                                    )}
                                </div>
                                <div className="bg-rose-50 p-3 rounded-xl text-center">
                                    <div className="text-[10px] font-bold text-muted-foreground mb-1">🥑 脂肪</div>
                                    {editMode ? (
                                        <input
                                            type="number"
                                            value={editFat}
                                            onChange={(e) => setEditFat(Number(e.target.value))}
                                            className="w-full text-center text-lg font-black text-rose-600 bg-transparent border-b border-rose-300 focus:outline-none"
                                        />
                                    ) : (
                                        <div className="text-lg font-black text-rose-600">{result.fat_g}g</div>
                                    )}
                                </div>
                            </div>

                            {/* Total Calories */}
                            <div className="bg-primary/10 p-4 rounded-xl text-center">
                                <div className="text-sm font-bold text-primary/70 mb-1">📊 总热量</div>
                                <div className="text-3xl font-black text-primary">
                                    {editMode ? calculatedCalories.toFixed(0) : result.calories.toFixed(0)}
                                </div>
                                <div className="text-xs font-bold text-primary/60">kcal</div>
                            </div>

                            {/* Edit/Correct Button */}
                            {editMode ? (
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setEditMode(false)}
                                        className="flex-1 py-2 rounded-xl bg-secondary text-foreground font-bold"
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleCorrect}
                                        className="flex-1 py-2 rounded-xl bg-primary text-white font-bold"
                                    >
                                        确认修正
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setEditMode(true)}
                                    className="w-full py-2 rounded-xl bg-secondary/50 text-muted-foreground font-medium text-sm hover:bg-secondary transition-colors"
                                >
                                    ✏️ 手动修正数值
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                {result && !editMode && (
                    <div className="p-6 border-t bg-secondary/10">
                        <button
                            onClick={handleConfirm}
                            className="w-full py-3 rounded-xl bg-accent text-white font-bold hover:bg-accent/90 transition-colors"
                        >
                            ✅ 确认记录
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { chatApi } from "@/lib/api";
import { userStorage } from "@/lib/storage";

interface Message {
    id?: string;
    role: "user" | "assistant" | "system";
    content: string;
    actions?: ActionCard[];
    isStreaming?: boolean;
}

interface ActionCard {
    type: string;
    title: string;
    description: string;
    data?: Record<string, unknown>;
}

const QUICK_ACTIONS = [
    { icon: "📋", label: "今日计划", message: "今天的饮食和训练计划是什么？" },
    { icon: "📊", label: "进度查看", message: "我这周的执行情况怎么样？" },
    { icon: "🥗", label: "营养咨询", message: "我今天应该多吃什么来补充营养？" },
    { icon: "💪", label: "训练建议", message: "今天的训练是什么强度？" },
];

export default function ChatPage() {
    const router = useRouter();
    const [messages, setMessages] = useState<Message[]>([
        {
            role: "assistant",
            content: "你好！👋 我是你的 AI 私教 **Carbon Coach**。\n\n我可以帮你：\n- 📋 查看今日计划\n- 📊 分析执行进度\n- 🥗 营养饮食咨询\n- 💡 个性化建议\n\n有什么想问的吗？"
        }
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!userStorage.getUserId()) {
            router.push("/onboarding");
        }
    }, [router]);

    useEffect(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, [messages]);

    const handleSend = useCallback(async (content?: string) => {
        const messageContent = content || input;
        if (!messageContent.trim() || isLoading) return;

        const userId = userStorage.getUserId();
        if (!userId) return;

        // Add user message
        const userMessage: Message = { role: "user", content: messageContent };
        setMessages(prev => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        // Add placeholder for streaming response
        const streamingMessage: Message = {
            role: "assistant",
            content: "",
            isStreaming: true
        };
        setMessages(prev => [...prev, streamingMessage]);

        try {
            // Use streaming API
            let fullContent = "";
            let newSessionId = sessionId;

            for await (const chunk of chatApi.streamMessage(userId, messageContent, sessionId || undefined)) {
                if (chunk.type === "session") {
                    newSessionId = chunk.session_id;
                    setSessionId(chunk.session_id);
                } else if (chunk.type === "content") {
                    fullContent += chunk.content;
                    setMessages(prev => {
                        const updated = [...prev];
                        const lastIndex = updated.length - 1;
                        updated[lastIndex] = {
                            ...updated[lastIndex],
                            content: fullContent
                        };
                        return updated;
                    });
                } else if (chunk.type === "done") {
                    // Mark as complete
                    setMessages(prev => {
                        const updated = [...prev];
                        const lastIndex = updated.length - 1;
                        updated[lastIndex] = {
                            ...updated[lastIndex],
                            id: chunk.message_id,
                            isStreaming: false
                        };
                        return updated;
                    });
                }
            }
        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => {
                const updated = [...prev];
                const lastIndex = updated.length - 1;
                updated[lastIndex] = {
                    role: "assistant",
                    content: "抱歉，连接出现问题。请稍后重试。",
                    isStreaming: false
                };
                return updated;
            });
        } finally {
            setIsLoading(false);
        }
    }, [input, isLoading, sessionId]);

    const handleQuickAction = (message: string) => {
        handleSend(message);
    };

    const handleActionCard = (action: ActionCard) => {
        if (action.data?.route) {
            router.push(action.data.route as string);
        } else if (action.data?.action === "open_food_modal") {
            // TODO: Open food modal
        }
    };

    const handleNewChat = () => {
        setMessages([
            {
                role: "assistant",
                content: "新对话已开始！有什么我可以帮助你的吗？"
            }
        ]);
        setSessionId(null);
    };

    // Render markdown-like formatting
    const renderContent = (content: string) => {
        // Simple markdown: bold, bullet points, emoji
        const lines = content.split("\n");
        return lines.map((line, i) => {
            let processed = line;
            // Bold
            processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Bullet points
            if (processed.startsWith("- ")) {
                processed = `<span class="inline-block mr-2">•</span>${processed.slice(2)}`;
            }
            return (
                <span
                    key={i}
                    className={i > 0 ? "block mt-1" : ""}
                    dangerouslySetInnerHTML={{ __html: processed }}
                />
            );
        });
    };

    return (
        <div className="h-[calc(100vh-6rem)] p-4 max-w-4xl mx-auto flex flex-col gap-4">
            {/* Header */}
            <div className="flex items-center justify-between py-2">
                <div>
                    <h1 className="text-2xl font-black text-primary flex items-center gap-2">
                        <span className="text-3xl">🏋️</span>
                        AI 私教
                    </h1>
                    <p className="text-xs font-bold uppercase text-muted-foreground tracking-widest">
                        Carbon Coach • Powered by AI
                    </p>
                </div>
                <button
                    onClick={handleNewChat}
                    className="px-4 py-2 text-sm font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors flex items-center gap-1"
                >
                    <span>✨</span> 新对话
                </button>
            </div>

            {/* Chat Area */}
            <div className="flex-1 glass-card p-6 flex flex-col relative overflow-hidden backdrop-blur-2xl bg-white/70">
                <div className="absolute inset-0 opacity-5 bg-[url('/images/bg-texture.png')] bg-cover mix-blend-overlay" />

                <div ref={scrollRef} className="flex-1 overflow-y-auto no-scrollbar space-y-4 px-2 pb-4 relative z-10">
                    {messages.map((m, i) => {
                        const isUser = m.role === "user";
                        return (
                            <div key={i} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                                <div className={`max-w-[85%] rounded-2xl px-5 py-3 shadow-sm text-sm leading-relaxed ${isUser
                                        ? "bg-primary text-white rounded-br-sm"
                                        : "bg-white text-foreground rounded-bl-sm border border-gray-100"
                                    }`}>
                                    {/* Content */}
                                    <div className="whitespace-pre-wrap">
                                        {renderContent(m.content)}
                                    </div>

                                    {/* Streaming cursor */}
                                    {m.isStreaming && (
                                        <span className="inline-block w-2 h-4 bg-primary/60 ml-1 animate-pulse" />
                                    )}

                                    {/* Action Cards */}
                                    {m.actions && m.actions.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                                            {m.actions.map((action, j) => (
                                                <button
                                                    key={j}
                                                    onClick={() => handleActionCard(action)}
                                                    className="w-full text-left px-3 py-2 bg-primary/5 hover:bg-primary/10 rounded-lg transition-colors flex items-center gap-2"
                                                >
                                                    <span className="text-primary font-medium text-sm">
                                                        {action.title}
                                                    </span>
                                                    <span className="text-xs text-muted-foreground">
                                                        →
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {/* Typing indicator when loading but no streaming content yet */}
                    {isLoading && messages[messages.length - 1]?.content === "" && (
                        <div className="flex justify-start">
                            <div className="bg-white px-5 py-3 rounded-2xl rounded-bl-sm flex gap-1.5 items-center shadow-sm border border-gray-100">
                                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce" />
                                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce [animation-delay:0.1s]" />
                                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce [animation-delay:0.2s]" />
                            </div>
                        </div>
                    )}
                </div>

                {/* Quick Actions */}
                {messages.length <= 2 && (
                    <div className="mb-4 relative z-10">
                        <div className="flex gap-2 flex-wrap justify-center">
                            {QUICK_ACTIONS.map((action, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleQuickAction(action.message)}
                                    disabled={isLoading}
                                    className="px-4 py-2 bg-white/80 hover:bg-white border border-gray-100 rounded-full text-sm font-medium transition-all hover:shadow-md disabled:opacity-50 flex items-center gap-1.5"
                                >
                                    <span>{action.icon}</span>
                                    <span>{action.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Input */}
                <div className="mt-4 relative z-10">
                    <div className="relative flex items-center gap-2">
                        <input
                            ref={inputRef}
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && !isLoading && handleSend()}
                            placeholder="问问我关于今天的计划..."
                            disabled={isLoading}
                            className="w-full h-14 pl-6 pr-14 rounded-full bg-white/50 border-2 border-transparent focus:border-primary/20 focus:bg-white outline-none transition-all shadow-inner disabled:opacity-60"
                        />
                        <button
                            onClick={() => handleSend()}
                            disabled={!input.trim() || isLoading}
                            className="absolute right-2 w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center shadow-lg hover:scale-110 active:scale-95 transition-all disabled:opacity-50 disabled:scale-100"
                        >
                            {isLoading ? (
                                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <span className="text-lg">↑</span>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

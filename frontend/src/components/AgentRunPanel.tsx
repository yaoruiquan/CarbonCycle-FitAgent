"use client";

import {
  AlertTriangle,
  Check,
  ChevronDown,
  ClipboardCheck,
  Gauge,
  ListChecks,
  Play,
  ShieldCheck,
  Sparkles,
  Wrench,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { agentApi } from "@/lib/api";
import { AgentRunResult, AgentActionCard } from "@/lib/types";

type Props = {
  run: AgentRunResult | null;
  userId?: string | null;
  onClose?: () => void;
};

const formatValue = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(1);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
};

export function AgentRunPanel({ run, userId, onClose }: Props) {
  const [expandedStep, setExpandedStep] = useState<number | null>(0);
  const [actionStatus, setActionStatus] = useState<string>("");
  const [runningAction, setRunningAction] = useState<string | null>(null);

  const evaluationRuns = useMemo(() => {
    const summary = run?.evaluation_summary as { latest_runs?: unknown[] } | undefined;
    return Array.isArray(summary?.latest_runs) ? summary.latest_runs : [];
  }, [run]);

  if (!run) {
    return (
      <div className="rounded-lg border border-dashed border-border/70 p-6 text-center text-sm text-muted-foreground">
        还没有 Agent 运行结果
      </div>
    );
  }

  const executeAction = async (action: AgentActionCard) => {
    if (!userId) return;
    setRunningAction(action.type);
    setActionStatus("");
    try {
      const response = await agentApi.executeAction(userId, action.type, action.data || {});
      setActionStatus(response.message);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "动作执行失败");
    } finally {
      setRunningAction(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto rounded-lg border border-border bg-white shadow-xl">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-white px-5 py-4">
        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-primary">
            <Sparkles className="h-4 w-4" />
            Agent Run
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {run.run_id.slice(0, 8)} · {run.status} · {run.latency_ms || 0}ms
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            aria-label="关闭 Agent 面板"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="space-y-6 p-5">
        {(run.reflection_summary || run.motivation) && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <Gauge className="h-4 w-4 text-primary" />
              本次判断
            </h3>
            <div className="rounded-lg bg-secondary/50 p-4 text-sm leading-relaxed">
              <p>{run.reflection_summary || "暂无反思摘要"}</p>
              {run.motivation && <p className="mt-2 font-semibold text-primary">{run.motivation}</p>}
            </div>
          </section>
        )}

        {run.safety_warnings.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <ShieldCheck className="h-4 w-4 text-amber-600" />
              安全护栏
            </h3>
            <div className="space-y-2">
              {run.safety_warnings.map((warning, index) => (
                <div key={`${warning.rule}-${index}`} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{warning.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {run.plan_diff.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <ClipboardCheck className="h-4 w-4 text-primary" />
              计划变更 Diff
            </h3>
            <div className="overflow-hidden rounded-lg border border-border">
              {run.plan_diff.map((item, index) => (
                <div key={`${item.field}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 border-b border-border px-3 py-3 text-sm last:border-b-0">
                  <div>
                    <div className="font-bold">{item.label}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{item.reason}</div>
                  </div>
                  <div className="text-right text-muted-foreground">{formatValue(item.before)}</div>
                  <div className="text-right font-black text-primary">{formatValue(item.after)}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {run.action_cards.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <Play className="h-4 w-4 text-primary" />
              可执行动作
            </h3>
            <div className="space-y-2">
              {run.action_cards.map((action) => (
                <button
                  key={`${action.type}-${action.title}`}
                  onClick={() => action.type === "open_agent_trace" ? setExpandedStep(0) : executeAction(action)}
                  disabled={!userId || runningAction === action.type}
                  className="w-full rounded-lg border border-border px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/5 disabled:opacity-60"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-bold text-sm">{action.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{action.description}</div>
                    </div>
                    {runningAction === action.type ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
                    ) : (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </div>
                </button>
              ))}
            </div>
            {actionStatus && <div className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{actionStatus}</div>}
          </section>
        )}

        {run.missions.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <ListChecks className="h-4 w-4 text-primary" />
              Agent 任务
            </h3>
            <div className="space-y-2">
              {run.missions.map((mission) => (
                <div key={mission.id} className="rounded-lg bg-secondary/40 p-3 text-sm">
                  <div className="font-bold">{mission.title}</div>
                  <div className="mt-1 text-muted-foreground">{mission.description}</div>
                  <div className="mt-2 text-xs font-semibold text-primary">{mission.next_action}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
            <Sparkles className="h-4 w-4 text-primary" />
            运行轨迹
          </h3>
          <div className="space-y-2">
            {run.trace.map((step, index) => (
              <div key={`${step.node}-${index}`} className="rounded-lg border border-border">
                <button
                  onClick={() => setExpandedStep(expandedStep === index ? null : index)}
                  className="flex w-full items-center justify-between px-4 py-3 text-left"
                >
                  <div>
                    <div className="text-sm font-bold">{index + 1}. {step.title || step.node}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{step.decision} · {step.duration_ms || 0}ms</div>
                  </div>
                  <ChevronDown className={`h-4 w-4 transition-transform ${expandedStep === index ? "rotate-180" : ""}`} />
                </button>
                {expandedStep === index && (
                  <div className="border-t border-border px-4 py-3 text-sm">
                    <p className="leading-relaxed">{step.reasoning}</p>
                    <div className="mt-3 grid gap-2 text-xs md:grid-cols-2">
                      <pre className="overflow-x-auto rounded-md bg-secondary/60 p-2">{JSON.stringify(step.input_summary || {}, null, 2)}</pre>
                      <pre className="overflow-x-auto rounded-md bg-secondary/60 p-2">{JSON.stringify(step.output_summary || {}, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {run.tool_trace.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <Wrench className="h-4 w-4 text-primary" />
              工具调用
            </h3>
            <div className="space-y-2">
              {run.tool_trace.map((tool, index) => (
                <div key={`${tool.tool_name}-${index}`} className="rounded-lg border border-border p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-bold">{tool.tool_name}</span>
                    <span className={`text-xs font-bold ${tool.status === "success" ? "text-emerald-600" : "text-rose-600"}`}>
                      {tool.status} · {tool.duration_ms || 0}ms
                    </span>
                  </div>
                  <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-secondary/60 p-2 text-xs">{JSON.stringify(tool.result || {}, null, 2)}</pre>
                </div>
              ))}
            </div>
          </section>
        )}

        {evaluationRuns.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold text-foreground">
              <Gauge className="h-4 w-4 text-primary" />
              Agent 评测
            </h3>
            <div className="space-y-2">
              {evaluationRuns.slice(0, 4).map((item, index) => (
                <pre key={index} className="overflow-x-auto rounded-lg bg-secondary/50 p-3 text-xs">
                  {JSON.stringify(item, null, 2)}
                </pre>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

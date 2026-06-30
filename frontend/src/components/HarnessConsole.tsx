"use client";

import {
  AlertTriangle,
  CheckCircle2,
  GitCompare,
  Gauge,
  ListChecks,
  Play,
  RotateCcw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { harnessApi } from "@/lib/api";
import {
  HarnessCase,
  HarnessDimensionScores,
  HarnessReplayResult,
  HarnessRunSummary,
} from "@/lib/types";

const pct = (value: number) => `${Math.round(value * 100)}%`;
const DIMENSION_LABELS: Record<string, string> = {
  safety_score: "安全",
  task_success_score: "任务",
  tool_use_score: "工具",
  actionability_score: "行动",
  stability_score: "稳定",
  observability_score: "观测",
};
const CATEGORY_LABELS: Record<string, string> = {
  nutrition_deviation: "营养偏差",
  training_behavior: "训练行为",
  safety_boundary: "安全边界",
  data_quality: "数据质量",
  tool_policy: "工具策略",
  memory_context: "记忆上下文",
};
const DIFFICULTY_LABELS: Record<string, string> = {
  smoke: "Smoke",
  regression: "Regression",
  adversarial: "Adversarial",
};

export default function HarnessConsole() {
  const [cases, setCases] = useState<HarnessCase[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [runSummary, setRunSummary] = useState<HarnessRunSummary | null>(null);
  const [replayResult, setReplayResult] = useState<HarnessReplayResult | null>(null);
  const [replayRunId, setReplayRunId] = useState("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    harnessApi
      .listCases()
      .then((data) => {
        setCases(data.cases);
        setSelected(data.cases.map((item) => item.id));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载 Harness cases 失败"))
      .finally(() => setLoading(false));
  }, []);

  const selectedCount = selected.length;
  const failedCases = useMemo(
    () => runSummary?.results.filter((item) => !item.passed) || [],
    [runSummary]
  );
  const selectedCategoryCounts = useMemo(() => {
    return selected.reduce<Record<string, number>>((counts, caseId) => {
      const item = cases.find((candidate) => candidate.id === caseId);
      if (!item) return counts;
      counts[item.category] = (counts[item.category] || 0) + 1;
      return counts;
    }, {});
  }, [cases, selected]);
  const modelIssue = useMemo(
    () => runSummary?.results.find((item) => item.model_status?.available === false)?.model_status,
    [runSummary]
  );

  const toggleCase = (caseId: string) => {
    setSelected((current) =>
      current.includes(caseId) ? current.filter((id) => id !== caseId) : [...current, caseId]
    );
  };

  const runCases = async () => {
    setRunning(true);
    setError("");
    try {
      const summary = await harnessApi.runCases(selected);
      setRunSummary(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "运行 Harness suite 失败");
    } finally {
      setRunning(false);
    }
  };

  const replay = async () => {
    if (!replayRunId.trim()) return;
    setReplaying(true);
    setError("");
    setReplayResult(null);
    try {
      const result = await harnessApi.replay(replayRunId.trim());
      setReplayResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replay 失败");
    } finally {
      setReplaying(false);
    }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center text-sm font-bold text-primary">加载 Harness 控制台...</div>;
  }

  return (
    <div className="h-full overflow-y-auto bg-background px-4 pb-28 pt-5">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-4 rounded-lg border border-border bg-white p-5 shadow-sm md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-black text-primary">
              <ShieldCheck className="h-4 w-4" />
              Agent Harness
            </div>
            <h1 className="mt-2 text-2xl font-black text-foreground">健康营养 Agent 驭缰控制台</h1>
            <p className="mt-1 text-sm text-muted-foreground">运行领域 case、查看安全验证、回放历史 episode。</p>
          </div>
          <button
            onClick={runCases}
            disabled={running || selectedCount === 0}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-3 text-sm font-bold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {running ? "运行中..." : `运行 ${selectedCount} 个 Case`}
          </button>
        </header>

        <section className="rounded-lg border border-border bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2 text-sm font-black text-primary">
              <ListChecks className="h-4 w-4" />
              Case Matrix
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-bold text-muted-foreground">
              {Object.entries(selectedCategoryCounts).map(([category, count]) => (
                <span key={category} className="rounded-md bg-secondary/70 px-2 py-1">
                  {labelFor(CATEGORY_LABELS, category)} {count}
                </span>
              ))}
            </div>
          </div>
        </section>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {modelIssue && (
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-black">模型供应商不可用</div>
              <div className="mt-1">
                {String(modelIssue.message || "请检查模型服务配置、额度或账单状态。")}
              </div>
              <div className="mt-2 text-xs font-semibold text-amber-800">
                provider {String(modelIssue.provider || "unknown")} · code {String(modelIssue.code || "unknown")}
              </div>
            </div>
          </div>
        )}

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {cases.map((item) => {
            const active = selected.includes(item.id);
            return (
              <button
                key={item.id}
                onClick={() => toggleCase(item.id)}
                className={`rounded-lg border p-4 text-left transition ${
                  active ? "border-primary bg-primary/5" : "border-border bg-white hover:border-primary/40"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-black text-foreground">{item.title}</span>
                  {active ? <CheckCircle2 className="h-4 w-4 text-primary" /> : <XCircle className="h-4 w-4 text-muted-foreground" />}
                </div>
                <div className="mt-2 text-xs font-semibold text-muted-foreground">{item.id}</div>
                <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] font-bold text-muted-foreground">
                  <span className="rounded bg-secondary/80 px-2 py-1">
                    {labelFor(CATEGORY_LABELS, item.category)}
                  </span>
                  <span className="rounded bg-secondary/80 px-2 py-1">
                    {labelFor(DIFFICULTY_LABELS, item.difficulty)}
                  </span>
                  {item.tags.slice(0, 2).map((tag) => (
                    <span key={tag} className="rounded bg-white px-2 py-1">
                      {tag}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </section>

        {runSummary && (
          <section className="grid gap-4 lg:grid-cols-[320px_1fr]">
            <div className="rounded-lg border border-border bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 text-sm font-black text-primary">
                <Gauge className="h-4 w-4" />
                Suite Summary
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                <Metric label="通过率" value={pct(runSummary.pass_rate)} />
                <Metric label="平均分" value={String(runSummary.average_harness_score)} />
                <Metric label="通过" value={String(runSummary.passed)} />
                <Metric label="失败" value={String(runSummary.failed)} />
              </div>
              <DimensionScoreList scores={runSummary.average_dimension_scores} />
              <SummaryGroupList
                title="类别"
                items={runSummary.category_summary}
                labels={CATEGORY_LABELS}
              />
              <SummaryGroupList
                title="难度"
                items={runSummary.difficulty_summary}
                labels={DIFFICULTY_LABELS}
              />
              {failedCases.length > 0 && (
                <div className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-800">
                  {failedCases.length} 个 case 未通过，右侧可查看失败原因。
                </div>
              )}
            </div>

            <div className="space-y-3">
              {runSummary.results.map((item) => (
                <div key={item.case_id} className="rounded-lg border border-border bg-white p-4 shadow-sm">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        {item.passed ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-rose-600" />}
                        <span className="text-sm font-black">{item.title}</span>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">{item.case_id} · {item.verification_status || "unknown"} · score {item.harness_score}</div>
                      <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] font-bold text-muted-foreground">
                        <span className="rounded bg-secondary/80 px-2 py-1">
                          {labelFor(CATEGORY_LABELS, item.category)}
                        </span>
                        <span className="rounded bg-secondary/80 px-2 py-1">
                          {labelFor(DIFFICULTY_LABELS, item.difficulty)}
                        </span>
                        {item.hard_failures && item.hard_failures.length > 0 && (
                          <span className="rounded bg-rose-100 px-2 py-1 text-rose-700">
                            hard fail {item.hard_failures.length}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-right text-xs">
                      <span>trace {item.summary.trace_count}</span>
                      <span>tool {item.summary.tool_call_count}</span>
                      <span>warn {item.summary.warning_rules.filter(Boolean).length}</span>
                    </div>
                  </div>
                  <DimensionScoreList scores={item.dimension_scores} compact />
                  {item.failures.length > 0 && (
                    <div className="mt-3 rounded-md bg-rose-50 p-3 text-xs text-rose-700">
                      {item.failures.join(" / ")}
                    </div>
                  )}
                  {item.expectation_failures && item.expectation_failures.length > 0 && (
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      {item.expectation_failures.slice(0, 6).map((failure, index) => (
                        <div
                          key={`${failure.code}-${index}`}
                          className="rounded-md border border-border bg-secondary/30 p-2 text-xs"
                        >
                          <div className="font-black text-foreground">{failure.code}</div>
                          <div className="mt-1 text-muted-foreground">{failure.message}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {item.error && (
                    <div className="mt-2 rounded-md bg-secondary/60 p-3 text-xs text-muted-foreground">
                      {item.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-black text-primary">
            <GitCompare className="h-4 w-4" />
            Replay & Compare
          </div>
          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <input
              value={replayRunId}
              onChange={(event) => setReplayRunId(event.target.value)}
              placeholder="输入已有 Agent run_id"
              className="min-h-11 flex-1 rounded-md border border-border px-3 text-sm outline-none focus:border-primary"
            />
            <button
              onClick={replay}
              disabled={replaying || !replayRunId.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-border px-4 py-3 text-sm font-bold transition hover:border-primary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RotateCcw className="h-4 w-4" />
              {replaying ? "回放中..." : "回放"}
            </button>
          </div>

          {replayResult && (
            <div className="mt-4 space-y-3">
              <div
                className={`rounded-md border p-3 text-sm font-bold ${
                  replayResult.comparison.regression
                    ? "border-rose-200 bg-rose-50 text-rose-700"
                    : "border-emerald-200 bg-emerald-50 text-emerald-700"
                }`}
              >
                {replayResult.comparison.regression ? "检测到回归" : "未检测到回归"} · score delta{" "}
                {replayResult.comparison.harness_score_delta}
              </div>
              <DimensionDeltaList deltas={replayResult.comparison.score_delta_by_dimension} />
              <pre className="max-h-80 overflow-auto rounded-md bg-secondary/60 p-3 text-xs">
                {JSON.stringify(replayResult.comparison, null, 2)}
              </pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function labelFor(labels: Record<string, string>, value: string) {
  return labels[value] || value;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-secondary/50 p-3">
      <div className="text-xs font-bold text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-black text-foreground">{value}</div>
    </div>
  );
}

function DimensionScoreList({
  scores,
  compact = false,
}: {
  scores?: HarnessDimensionScores;
  compact?: boolean;
}) {
  const entries = dimensionEntries(scores);
  if (entries.length === 0) return null;

  return (
    <div className={compact ? "mt-3 grid gap-2 md:grid-cols-3" : "mt-4 grid gap-2"}>
      {entries.map(([key, value]) => (
        <div key={key} className="min-w-0">
          <div className="mb-1 flex items-center justify-between gap-2 text-[11px] font-bold text-muted-foreground">
            <span>{labelFor(DIMENSION_LABELS, key)}</span>
            <span>{value}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
            <div
              className={`h-full rounded-full ${scoreColor(value)}`}
              style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function DimensionDeltaList({ deltas }: { deltas?: Record<string, number> }) {
  const entries = Object.entries(deltas || {});
  if (entries.length === 0) return null;

  return (
    <div className="grid gap-2 md:grid-cols-3">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-md bg-secondary/50 p-3 text-xs">
          <div className="font-bold text-muted-foreground">{labelFor(DIMENSION_LABELS, key)}</div>
          <div className={`mt-1 text-lg font-black ${value < 0 ? "text-rose-600" : "text-emerald-600"}`}>
            {value > 0 ? `+${value}` : value}
          </div>
        </div>
      ))}
    </div>
  );
}

function SummaryGroupList({
  title,
  items,
  labels,
}: {
  title: string;
  items?: Record<string, { total: number; passed: number; failed: number; average_harness_score: number }>;
  labels: Record<string, string>;
}) {
  const entries = Object.entries(items || {});
  if (entries.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="mb-2 text-xs font-black text-muted-foreground">{title}</div>
      <div className="space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center justify-between gap-3 rounded-md bg-secondary/40 px-3 py-2 text-xs">
            <span className="font-bold text-foreground">{labelFor(labels, key)}</span>
            <span className="text-muted-foreground">
              {value.passed}/{value.total} · {value.average_harness_score}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function dimensionEntries(scores?: HarnessDimensionScores) {
  return Object.entries(scores || {}).filter((entry): entry is [string, number] => (
    typeof entry[1] === "number"
  ));
}

function scoreColor(value: number) {
  if (value >= 85) return "bg-emerald-500";
  if (value >= 70) return "bg-amber-500";
  return "bg-rose-500";
}

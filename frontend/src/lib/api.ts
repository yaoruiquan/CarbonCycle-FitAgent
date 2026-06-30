import { userStorage } from "./storage";
import {
  CarbonCyclePlan,
  DayPlan,
  HistoricalReport,
  AgentRunResult,
  HarnessCase,
  HarnessReplayResult,
  HarnessRunSummary,
  LogStats,
  UserProfile,
  WeightLog,
  WeeklyReportSummary,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const API_PREFIX = `${API_BASE}/api`;

class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

const isFormData = (body: unknown): body is FormData =>
  typeof FormData !== "undefined" && body instanceof FormData;

type RequestBody = BodyInit | Record<string, unknown> | unknown[] | null;

async function request<T>(
  path: string,
  options: Omit<RequestInit, "body"> & { body?: RequestBody } = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});

  const token = userStorage.getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let body = options.body;
  if (body && !isFormData(body) && typeof body === "object") {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    body = JSON.stringify(body);
  }

  const res = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    headers,
    body,
  });

  if (!res.ok) {
    let errorMessage = `Request failed: ${res.status}`;
    let detail: string | undefined;
    try {
      const data = await res.json();
      detail = data?.detail || data?.message;
      if (detail) errorMessage = detail;
    } catch {
      // ignore JSON parse error
    }
    throw new ApiError(errorMessage, res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export const authApi = {
  register(data: Record<string, unknown>) {
    return request<UserProfile>("/auth/register", {
      method: "POST",
      body: data,
    });
  },
  login(data: { email: string; password: string }) {
    return request<{
      access_token: string;
      token_type: string;
      user_id: string;
      user_name: string;
    }>("/auth/login", {
      method: "POST",
      body: data,
    });
  },
};

export const userApi = {
  get(id: string) {
    return request<UserProfile>(`/users/${id}`);
  },
  create(data: Record<string, unknown>) {
    return request<UserProfile>("/users/", {
      method: "POST",
      body: data,
    });
  },
  update(id: string, data: Record<string, unknown>) {
    return request<UserProfile>(`/users/${id}`, {
      method: "PATCH",
      body: data,
    });
  },
};

export const planApi = {
  create(data: Record<string, unknown>) {
    return request<CarbonCyclePlan>("/plans/", {
      method: "POST",
      body: data,
    });
  },
  get(id: string) {
    return request<CarbonCyclePlan>(`/plans/${id}`);
  },
  getActive(userId: string) {
    return request<CarbonCyclePlan>(`/plans/user/${userId}/active`);
  },
  update(planId: string, data: Record<string, unknown>) {
    return request<CarbonCyclePlan>(`/plans/${planId}`, {
      method: "PATCH",
      body: data,
    });
  },
  regenerateDay(planId: string, dayDate: string) {
    return request<DayPlan>(`/plans/${planId}/days/${dayDate}/regenerate`, {
      method: "POST",
    });
  },
};

export const logApi = {
  getStats(userId: string, days: number = 7) {
    return request<LogStats>(`/logs/user/${userId}/stats?days=${days}`);
  },
  getRecent(userId: string, limit: number = 7) {
    return request(`/logs/user/${userId}?limit=${limit}`);
  },
};

export const reportApi = {
  getById(reportId: string) {
    return request<HistoricalReport>(`/reports/${reportId}`);
  },
  listByUser(userId: string) {
    return request<WeeklyReportSummary[]>(`/reports/user/${userId}`);
  },
  getWeightHistory(userId: string) {
    return request<{ date: string; value: number }[]>(
      `/reports/user/${userId}/weights`
    );
  },
};

export const weightApi = {
  create(data: {
    user_id: string;
    date: string;
    weight_kg: number;
    body_fat_pct?: number;
    notes?: string;
  }) {
    return request<WeightLog>("/weights/", {
      method: "POST",
      body: data,
    });
  },
  getHistory(userId: string, limit: number = 30) {
    return request<WeightLog[]>(`/weights/user/${userId}?limit=${limit}`);
  },
  getLatest(userId: string) {
    return request<WeightLog | null>(`/weights/user/${userId}/latest`);
  },
  getRange(userId: string, start: string, end: string) {
    return request<WeightLog[]>(
      `/weights/user/${userId}/range?start=${start}&end=${end}`
    );
  },
  delete(logId: string) {
    return request(`/weights/${logId}`, { method: "DELETE" });
  },
};

export type ChatStreamChunk =
  | { type: "session"; session_id: string }
  | { type: "content"; content: string }
  | { type: "actions"; actions: AgentActionCardPayload[] }
  | { type: "done"; message_id: string };

export interface AgentActionCardPayload {
  type: string;
  title: string;
  description: string;
  data?: Record<string, unknown>;
  confirmation_required?: boolean;
}

export const chatApi = {
  async *streamMessage(
    userId: string,
    content: string,
    sessionId?: string
  ): AsyncGenerator<ChatStreamChunk, void, void> {
    const res = await fetch(
      `${API_PREFIX}/chat/stream?user_id=${encodeURIComponent(userId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, session_id: sessionId || null }),
      }
    );

    if (!res.ok || !res.body) {
      throw new Error(`Chat stream failed: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const line = part
          .split("\n")
          .find((l) => l.startsWith("data:"));
        if (!line) continue;

        const jsonText = line.replace(/^data:\s*/, "").trim();
        if (!jsonText) continue;

        try {
          const data = JSON.parse(jsonText) as ChatStreamChunk;
          yield data;
        } catch {
          // ignore malformed chunks
        }
      }
    }
  },
};

export const agentApi = {
  run(userId: string, trigger: string = "manual") {
    return request<AgentRunResult>("/agent/run", {
      method: "POST",
      body: { user_id: userId, trigger },
    });
  },
  getStatus(runId: string) {
    return request<AgentRunResult>(`/agent/status/${runId}`);
  },
  listRuns(userId: string, limit: number = 10) {
    return request<AgentRunResult[]>(`/agent/runs/${userId}?limit=${limit}`);
  },
  listMissions(userId: string, limit: number = 20) {
    return request<{ missions: unknown[] }>(`/agent/missions/${userId}?limit=${limit}`);
  },
  getEvaluationSummary() {
    return request<Record<string, unknown>>("/agent/evaluations/summary");
  },
  getModelHealth() {
    return request<Record<string, unknown>>("/agent/model-health");
  },
  executeAction(userId: string, actionType: string, data: Record<string, unknown> = {}) {
    return request<{ status: string; message: string; result: Record<string, unknown> }>(
      "/agent/actions/execute",
      {
        method: "POST",
        body: { user_id: userId, action_type: actionType, data },
      }
    );
  },
};

export const harnessApi = {
  listCases() {
    return request<{ cases: HarnessCase[] }>("/harness/cases");
  },
  runCases(caseIds?: string[]) {
    return request<HarnessRunSummary>("/harness/run", {
      method: "POST",
      body: { case_ids: caseIds && caseIds.length > 0 ? caseIds : null },
    });
  },
  getRun(runId: string) {
    return request<HarnessRunSummary>(`/harness/runs/${runId}`);
  },
  replay(runId: string) {
    return request<HarnessReplayResult>(`/harness/replay/${runId}`, {
      method: "POST",
    });
  },
};

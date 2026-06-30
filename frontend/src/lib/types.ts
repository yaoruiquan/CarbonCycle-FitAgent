export type DayType = "high_carb" | "medium_carb" | "low_carb" | "refeed";

export interface MacroNutrients {
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g?: number;
}

export interface DayPlan {
  date: string;
  day_type: DayType;
  macros: MacroNutrients;
  training_scheduled: boolean;
  training_type?: string | null;
  notes?: string | null;
  target_calories?: number;
}

export interface CarbonCyclePlan {
  id: string;
  user_id: string;
  name: string;
  start_date: string;
  end_date: string;
  cycle_length_days: number;
  days: DayPlan[];
  base_calories?: number;
  goal_deficit?: number;
  created_at?: string;
  updated_at?: string;
  is_active?: boolean;
  notes?: string | null;
  average_daily_calories?: number;
}

export interface LogStats {
  days_logged: number;
  avg_calories: number;
  avg_protein: number;
  avg_carbs: number;
  avg_fat: number;
  training_completion_rate: number;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  gender: "male" | "female";
  birth_date: string;
  height_cm: number;
  weight_kg: number;
  target_weight_kg?: number | null;
  goal: "muscle_gain" | "fat_loss" | "maintenance" | "recomposition";
  activity_level: "sedentary" | "light" | "moderate" | "active" | "very_active";
  training_days_per_week: number;
  dietary_preferences?: string[];
}

export interface WeightLog {
  id: string;
  user_id: string;
  date: string;
  weight_kg: number;
  body_fat_pct?: number | null;
  notes?: string | null;
  created_at: string;
}

export interface WeeklyReportSummary {
  id: string;
  week_start: string;
  week_end: string;
  overall_adherence: number;
  weight_change_kg: number | null;
  trend: string;
  created_at: string;
}

export interface HistoricalReport {
  id: string;
  user_id: string;
  week_start: string;
  week_end: string;
  calorie_rate: number;
  training_rate: number;
  weight_change: number | null;
  avg_protein: number;
  avg_carbs: number;
  avg_fat: number;
  summary: string | null;
  recommendations: string[];
  created_at: string;
}

export interface AgentStepTrace {
  node: string;
  title: string;
  status: string;
  decision?: string | null;
  reasoning?: string | null;
  input_summary?: Record<string, unknown>;
  output_summary?: Record<string, unknown>;
  confidence?: number;
  duration_ms?: number;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ToolTrace {
  tool_name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  status: string;
  duration_ms?: number;
  error?: string | null;
}

export interface PlanDiffItem {
  field: string;
  label: string;
  before: unknown;
  after: unknown;
  delta?: unknown;
  reason?: string;
  requires_confirmation?: boolean;
}

export interface SafetyWarning {
  level: "info" | "warning" | "danger" | string;
  message: string;
  rule: string;
}

export interface AgentMission {
  id: string;
  run_id?: string | null;
  title: string;
  description?: string | null;
  status: string;
  due_date?: string | null;
  next_action?: string | null;
  evidence?: string[];
  created_at?: string | null;
}

export interface AgentActionCard {
  type: string;
  title: string;
  description: string;
  data?: Record<string, unknown>;
  confirmation_required?: boolean;
}

export interface AgentRunResult {
  run_id: string;
  status: string;
  latency_ms?: number;
  planner_output?: Record<string, unknown> | null;
  actor_output?: Record<string, unknown> | null;
  reflection?: Record<string, unknown> | null;
  adjustment?: Record<string, unknown> | null;
  reflection_summary?: string | null;
  motivation?: string | null;
  trends?: Record<string, unknown> | null;
  trace: AgentStepTrace[];
  tool_trace: ToolTrace[];
  plan_diff: PlanDiffItem[];
  safety_warnings: SafetyWarning[];
  missions: AgentMission[];
  action_cards: AgentActionCard[];
  memory_context: Record<string, unknown>;
  evaluation_summary: Record<string, unknown>;
  model_status?: Record<string, unknown>;
  verification_status?: string | null;
  verification_findings?: Record<string, unknown>[];
  harness_score?: number;
  harness_episode?: Record<string, unknown>;
  error?: string | null;
}

export interface HarnessDimensionScores {
  safety_score?: number;
  task_success_score?: number;
  tool_use_score?: number;
  actionability_score?: number;
  stability_score?: number;
  observability_score?: number;
  [key: string]: number | undefined;
}

export interface HarnessFinding {
  dimension: string;
  code: string;
  message: string;
  evidence?: Record<string, unknown>;
}

export interface HarnessCase {
  id: string;
  title: string;
  category: string;
  difficulty: string;
  tags: string[];
  trigger: string;
  user_context: Record<string, unknown>;
  plan_context: Record<string, unknown>;
  logs: Record<string, unknown>[];
  expectations: Record<string, unknown>;
}

export interface HarnessCaseResult {
  case_id: string;
  title: string;
  category: string;
  difficulty: string;
  tags: string[];
  passed: boolean;
  failures: string[];
  expectation_failures?: HarnessFinding[];
  hard_failures?: HarnessFinding[];
  run_id?: string | null;
  status?: string | null;
  verification_status?: string | null;
  harness_score: number;
  agent_harness_score?: number;
  dimension_scores?: HarnessDimensionScores;
  error?: string | null;
  model_status?: Record<string, unknown>;
  verification_findings?: Record<string, unknown>[];
  summary: {
    trace_count: number;
    tool_call_count: number;
    warning_rules: (string | null | undefined)[];
    tool_names?: (string | null | undefined)[];
    action_types: (string | null | undefined)[];
    trace_nodes?: (string | null | undefined)[];
  };
}

export interface HarnessGroupSummary {
  total: number;
  passed: number;
  failed: number;
  average_harness_score: number;
}

export interface HarnessRunSummary {
  run_id: string;
  created_at: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  average_harness_score: number;
  average_dimension_scores?: HarnessDimensionScores;
  category_summary?: Record<string, HarnessGroupSummary>;
  difficulty_summary?: Record<string, HarnessGroupSummary>;
  results: HarnessCaseResult[];
  report_path?: string;
}

export interface HarnessReplayResult {
  status: string;
  original_run_id: string;
  replay_run_id: string;
  comparison: {
    trace_nodes_match: boolean;
    original_trace_nodes: (string | null | undefined)[];
    replay_trace_nodes: (string | null | undefined)[];
    tool_call_delta: number;
    plan_diff_delta: number;
    warning_rules_added: string[];
    warning_rules_removed: string[];
    harness_score_delta: number;
    score_delta_by_dimension?: Record<string, number>;
    regression?: boolean;
  };
  replayed?: AgentRunResult;
}

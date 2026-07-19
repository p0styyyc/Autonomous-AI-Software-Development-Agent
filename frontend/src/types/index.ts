/** WebSocket 事件类型 */
export type WSEventType =
  | "task_started"
  | "task_completed"
  | "task_failed"
  | "planning_started"
  | "planning_completed"
  | "step_started"
  | "step_completed"
  | "coding_started"
  | "code_generated"
  | "coding_completed"
  | "executing_started"
  | "execution_success"
  | "execution_error"
  | "reviewing_started"
  | "review_pass"
  | "review_fail"
  | "retry_started"
  | "log"
  | "error";

/** WebSocket 事件 */
export interface WSEvent {
  type: WSEventType;
  data: Record<string, unknown>;
  timestamp: string;
}

/** 开发步骤 */
export interface Step {
  id: number;
  description: string;
  files_to_create: string[];
  files_to_modify: string[];
  expected_output: string;
  complexity: number;
  depends_on: number[];
}

/** 任务计划 */
export interface Plan {
  task_summary: string;
  tech_stack: Record<string, string>;
  steps: Step[];
  estimated_total_time: string;
}

/** 任务状态 */
export interface TaskStatus {
  task_id: string;
  status: string;
  plan?: Plan | null;
  files_created: string[];
  files_modified: string[];
  final_report?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

/** 文件信息 */
export interface FileInfo {
  path: string;
  content: string;
  size_bytes: number;
  language: string;
}

/** 创建任务响应 */
export interface TaskCreateResponse {
  task_id: string;
  status: string;
  created_at: string;
}

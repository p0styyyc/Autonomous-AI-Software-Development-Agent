import type { WSEvent } from "../types";
import { CodeBlock } from "./CodeBlock";

interface MessageBubbleProps {
  event: WSEvent;
}

const EVENT_LABELS: Record<string, { label: string; color: string }> = {
  task_started: { label: "Task Started", color: "text-green-400" },
  task_completed: { label: "Task Complete", color: "text-green-400" },
  task_failed: { label: "Task Failed", color: "text-red-400" },
  planning_started: { label: "Planning...", color: "text-yellow-400" },
  planning_completed: { label: "Plan Ready", color: "text-green-400" },
  step_started: { label: "Step", color: "text-blue-400" },
  coding_started: { label: "Coding...", color: "text-purple-400" },
  code_generated: { label: "Code Generated", color: "text-purple-400" },
  executing_started: { label: "Executing...", color: "text-orange-400" },
  execution_success: { label: "Execution OK", color: "text-green-400" },
  execution_error: { label: "Execution Failed", color: "text-red-400" },
  reviewing_started: { label: "Reviewing...", color: "text-cyan-400" },
  review_pass: { label: "Review Passed", color: "text-green-400" },
  review_fail: { label: "Review Failed", color: "text-red-400" },
  retry_started: { label: "Retrying...", color: "text-yellow-400" },
  error: { label: "Error", color: "text-red-400" },
  log: { label: "Log", color: "text-gray-400" },
};

export function MessageBubble({ event }: MessageBubbleProps) {
  const meta = EVENT_LABELS[event.type] || { label: event.type, color: "text-gray-400" };
  const data = event.data;

  return (
    <div className="flex gap-3 py-2 animate-fadeIn">
      {/* Avatar / Icon */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center text-sm">
        {getEventIcon(event.type)}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-semibold ${meta.color}`}>{meta.label}</span>
          <span className="text-xs text-gray-500">
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
        </div>

        {/* Event-specific rendering */}
        {renderEventContent(event, data)}
      </div>
    </div>
  );
}

function getEventIcon(type: string): string {
  switch (type) {
    case "planning_started":
    case "planning_completed":
      return "📋";
    case "coding_started":
    case "code_generated":
      return "💻";
    case "executing_started":
    case "execution_success":
    case "execution_error":
      return "⚡";
    case "reviewing_started":
    case "review_pass":
    case "review_fail":
      return "🔍";
    case "task_completed":
      return "✅";
    case "task_failed":
    case "error":
      return "❌";
    case "retry_started":
      return "🔄";
    default:
      return "•";
  }
}

function renderEventContent(event: WSEvent, data: Record<string, unknown>) {
  switch (event.type) {
    case "planning_completed":
      return (
        <div className="text-sm text-gray-300">
          <p className="font-medium">{data.task_summary as string}</p>
          <p className="text-gray-500 text-xs mt-1">
            {data.steps_count as number} steps ·{" "}
            {JSON.stringify(data.tech_stack)}
          </p>
        </div>
      );

    case "step_started":
      return (
        <div className="text-sm text-gray-300">
          <span className="text-blue-400 font-medium">
            Step {data.step_id as number}/{data.total_steps as number}
          </span>
          : {data.description as string}
        </div>
      );

    case "code_generated":
      return (
        <div className="text-sm text-gray-400">
          {((data.files_created as string[]) || []).length > 0 && (
            <span className="text-green-400">
              +{((data.files_created as string[]) || []).join(", ")}
            </span>
          )}
          {((data.files_modified as string[]) || []).length > 0 && (
            <span className="text-yellow-400 ml-2">
              ~{((data.files_modified as string[]) || []).join(", ")}
            </span>
          )}
        </div>
      );

    case "execution_success":
    case "execution_error":
      return (
        <div className="text-sm">
          {data.exit_code !== undefined && (
            <span
              className={
                data.exit_code === 0 ? "text-green-400" : "text-red-400"
              }
            >
              Exit: {data.exit_code as number}
            </span>
          )}
          {(data.stdout as string) && (
            <CodeBlock
              code={(data.stdout as string).slice(0, 500)}
              language="text"
            />
          )}
          {(data.stderr as string) && (
            <CodeBlock
              code={(data.stderr as string).slice(0, 500)}
              language="text"
            />
          )}
        </div>
      );

    case "review_pass":
    case "review_fail":
      return (
        <div className="text-sm text-gray-300">
          <span
            className={
              data.passed ? "text-green-400" : "text-red-400"
            }
          >
            Score: {data.overall_score as number}/100
          </span>
          {(data.summary as string) && (
            <p className="text-gray-400 text-xs mt-1">{data.summary as string}</p>
          )}
        </div>
      );

    case "task_completed":
      return (
        <div className="text-sm text-green-400 font-medium">
          🎉 Task completed successfully!
        </div>
      );

    case "task_failed":
    case "error":
      return (
        <div className="text-sm text-red-400">
          {(data.message || data.error || "Unknown error") as string}
        </div>
      );

    case "log":
      if (data.message === "heartbeat") return null;
      return (
        <div className="text-xs text-gray-500">{data.message as string}</div>
      );

    default:
      return null;
  }
}

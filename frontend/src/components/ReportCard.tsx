import type { TaskStatus } from "../types";

interface ReportCardProps {
  task: TaskStatus;
}

export function ReportCard({ task }: ReportCardProps) {
  if (!task.final_report) return null;

  const isSuccess = task.status === "done" && !task.error_message;

  return (
    <div
      className={`rounded-lg p-4 mb-4 border ${
        isSuccess
          ? "bg-green-500/5 border-green-500/20"
          : "bg-red-500/5 border-red-500/20"
      }`}
    >
      <h3 className={`text-lg font-semibold mb-2 ${isSuccess ? "text-green-400" : "text-red-400"}`}>
        {isSuccess ? "🎉 Task Complete" : "❌ Task Failed"}
      </h3>
      <div className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
        {task.final_report}
      </div>

      {/* File summary */}
      <div className="mt-4 flex gap-4 text-sm">
        {task.files_created.length > 0 && (
          <div>
            <span className="text-gray-500">Created: </span>
            <span className="text-green-400">
              {task.files_created.join(", ")}
            </span>
          </div>
        )}
        {task.files_modified.length > 0 && (
          <div>
            <span className="text-gray-500">Modified: </span>
            <span className="text-yellow-400">
              {task.files_modified.join(", ")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

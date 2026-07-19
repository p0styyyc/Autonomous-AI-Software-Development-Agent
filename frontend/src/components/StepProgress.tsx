import type { WSEvent } from "../types";

interface StepProgressProps {
  events: WSEvent[];
}

interface StepState {
  id: number;
  description: string;
  status: "pending" | "active" | "done" | "failed";
  files: string[];
}

export function StepProgress({ events }: StepProgressProps) {
  const steps = extractSteps(events);
  if (steps.length === 0) return null;

  const doneCount = steps.filter((s) => s.status === "done").length;

  return (
    <div className="bg-surface-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-300">Progress</h3>
        <span className="text-xs text-gray-400">
          {doneCount}/{steps.length} steps
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-surface-700 rounded-full h-1.5 mb-3">
        <div
          className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${steps.length > 0 ? (doneCount / steps.length) * 100 : 0}%` }}
        />
      </div>

      {/* Step list */}
      <div className="space-y-1">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center gap-2 text-sm">
            <span className="w-4 text-center">
              {step.status === "done" && "✅"}
              {step.status === "active" && "⏳"}
              {step.status === "failed" && "❌"}
              {step.status === "pending" && "⏸"}
            </span>
            <span
              className={
                step.status === "active"
                  ? "text-blue-400"
                  : step.status === "done"
                  ? "text-gray-300"
                  : step.status === "failed"
                  ? "text-red-400"
                  : "text-gray-500"
              }
            >
              {step.description}
            </span>
            {step.files.length > 0 && (
              <span className="text-xs text-gray-500">
                ({step.files.join(", ")})
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function extractSteps(events: WSEvent[]): StepState[] {
  const steps: StepState[] = [];

  for (const event of events) {
    if (event.type === "step_started") {
      const data = event.data;
      const id = data.step_id as number;
      // Mark previous steps as done
      steps.forEach((s) => {
        if (s.id < id && s.status === "active") s.status = "done";
      });
      steps.push({
        id,
        description: data.description as string,
        status: "active",
        files: [],
      });
    }

    if (event.type === "code_generated") {
      const currentStep = steps[steps.length - 1];
      if (currentStep) {
        currentStep.files = [
          ...((event.data.files_created as string[]) || []),
          ...((event.data.files_modified as string[]) || []),
        ];
      }
    }

    if (event.type === "review_pass") {
      const currentStep = steps[steps.length - 1];
      if (currentStep) currentStep.status = "done";
    }

    if (event.type === "review_fail") {
      const currentStep = steps[steps.length - 1];
      if (currentStep && events.filter((e) => e.type === "retry_started").length >= 3) {
        currentStep.status = "failed";
      }
    }
  }

  return steps;
}

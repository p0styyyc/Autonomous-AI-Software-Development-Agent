import { useState, useRef, useEffect, useCallback } from "react";
import { useTask } from "../hooks/useTask";
import { useWebSocket } from "../hooks/useWebSocket";
import { getTask } from "../utils/api";
import { MessageBubble } from "./MessageBubble";
import { StepProgress } from "./StepProgress";
import { FileTree } from "./FileTree";
import { CodeBlock } from "./CodeBlock";
import { ReportCard } from "./ReportCard";
import type { WSEvent, TaskStatus } from "../types";

export function ChatWindow() {
  const [input, setInput] = useState("");
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    taskId,
    loading,
    error,
    files,
    selectedFile,
    submitRequest,
    loadFiles,
    openFile,
    clearTask,
    clearError,
  } = useTask();

  const { events: wsEvents, connected } = useWebSocket(taskId);

  // Collect WebSocket events
  useEffect(() => {
    setEvents(wsEvents);
  }, [wsEvents]);

  // Poll task status when task completes
  useEffect(() => {
    if (!taskId) return;

    const lastEvent = wsEvents[wsEvents.length - 1];
    if (
      lastEvent?.type === "task_completed" ||
      lastEvent?.type === "task_failed"
    ) {
      getTask(taskId).then(setTask).catch(console.error);
      loadFiles();
    }
  }, [wsEvents, taskId, loadFiles]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || loading) return;

      const request = input.trim();
      setInput("");
      setEvents([]);
      setTask(null);

      // Add user message
      const userEvent: WSEvent = {
        type: "log",
        data: { message: `🧑 You: ${request}` },
        timestamp: new Date().toISOString(),
      };
      setEvents([userEvent]);

      try {
        await submitRequest(request);
      } catch {
        // error handled by useTask
      }
    },
    [input, loading, submitRequest]
  );

  return (
    <div className="flex h-screen">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-surface-800 border-b border-surface-700 px-6 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-white">
                🤖 Autonomous AI Software Development Agent
              </h1>
              <p className="text-xs text-gray-500">
                {connected && taskId
                  ? `🟢 Connected · ${taskId}`
                  : taskId
                  ? "🟡 Connecting..."
                  : "Describe your coding task below"}
              </p>
            </div>
            {taskId && (
              <button
                onClick={clearTask}
                className="text-sm text-gray-400 hover:text-gray-200 px-3 py-1 rounded hover:bg-surface-700 transition-colors"
              >
                New Task
              </button>
            )}
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-1 scrollbar-thin">
          {events.length === 0 && !loading && (
            <div className="text-center text-gray-500 mt-20">
              <p className="text-4xl mb-4">🤖</p>
              <p className="text-lg font-medium mb-2">
                Autonomous AI Software Development Agent
              </p>
              <p className="text-sm">
                Describe what you want to build and I&apos;ll code it for you.
              </p>
              <div className="mt-6 text-xs text-gray-600 space-y-1">
                <p>Example: &quot;Create a Python weather API with Flask&quot;</p>
                <p>Example: &quot;Build a CLI todo app with SQLite&quot;</p>
              </div>
            </div>
          )}

          <StepProgress events={events} />

          {events
            .filter((e) => e.data?.message !== "heartbeat")
            .map((event, i) => (
              <MessageBubble key={i} event={event} />
            ))}

          {task && <ReportCard task={task} />}

          {loading && (
            <div className="flex items-center gap-2 text-gray-400 py-2">
              <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full" />
              <span className="text-sm">Agent is working...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error */}
        {error && (
          <div className="mx-6 mb-2 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 text-sm text-red-400">
            {error}
            <button onClick={clearError} className="ml-2 text-red-300 underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="border-t border-surface-700 p-4"
        >
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                taskId
                  ? "Agent is running..."
                  : "Describe your coding task (e.g., Create a weather API)..."
              }
              disabled={loading}
              className="flex-1 bg-surface-800 border border-surface-700 rounded-lg px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50 transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? "⏳" : "Send"}
            </button>
          </div>
        </form>
      </div>

      {/* Sidebar: File viewer */}
      <aside className="w-80 bg-surface-800 border-l border-surface-700 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-surface-700">
          <h2 className="text-sm font-semibold text-gray-300">Files</h2>
          <button
            onClick={loadFiles}
            className="text-xs text-blue-400 hover:text-blue-300 mt-1"
          >
            Refresh
          </button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin p-4">
          <FileTree files={files} selectedFile={selectedFile} onSelect={openFile} />
        </div>

        {selectedFile && (
          <div className="border-t border-surface-700 p-4 max-h-96 overflow-y-auto scrollbar-thin">
            <CodeBlock
              code={selectedFile.content}
              language={selectedFile.language}
              filename={selectedFile.path}
            />
          </div>
        )}
      </aside>
    </div>
  );
}

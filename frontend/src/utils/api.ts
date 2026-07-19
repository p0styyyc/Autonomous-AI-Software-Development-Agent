import type { TaskCreateResponse, TaskStatus, FileInfo } from "../types";

const BASE = "/api/v1";

export async function createTask(
  request: string,
  provider = "openai"
): Promise<TaskCreateResponse> {
  const res = await fetch(`${BASE}/task/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request, provider }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create task");
  }
  return res.json();
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  const res = await fetch(`${BASE}/task/${taskId}`);
  if (!res.ok) throw new Error("Task not found");
  return res.json();
}

export async function getTaskFiles(taskId: string): Promise<string[]> {
  const res = await fetch(`${BASE}/task/${taskId}/files`);
  if (!res.ok) return [];
  return res.json();
}

export async function getTaskFile(
  taskId: string,
  path: string
): Promise<FileInfo> {
  const res = await fetch(`${BASE}/task/${taskId}/file/${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error("File not found");
  return res.json();
}

export async function deleteTask(taskId: string): Promise<void> {
  await fetch(`${BASE}/task/${taskId}`, { method: "DELETE" });
}

export function getWebSocketUrl(taskId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${BASE}/task/${taskId}/stream`;
}

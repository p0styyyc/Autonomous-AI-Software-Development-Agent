import { useState, useCallback } from "react";
import { createTask, getTaskFiles, getTaskFile, deleteTask } from "../utils/api";
import type { FileInfo } from "../types";

interface UseTaskReturn {
  taskId: string | null;
  loading: boolean;
  error: string | null;
  files: string[];
  selectedFile: FileInfo | null;
  submitRequest: (request: string) => Promise<string>;
  loadFiles: () => Promise<void>;
  openFile: (path: string) => Promise<void>;
  clearTask: () => Promise<void>;
  clearError: () => void;
}

export function useTask(): UseTaskReturn {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);

  const submitRequest = useCallback(async (request: string): Promise<string> => {
    setLoading(true);
    setError(null);
    try {
      const res = await createTask(request);
      setTaskId(res.task_id);
      return res.task_id;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFiles = useCallback(async () => {
    if (!taskId) return;
    try {
      const fileList = await getTaskFiles(taskId);
      setFiles(fileList);
    } catch {
      // files not ready yet
    }
  }, [taskId]);

  const openFile = useCallback(async (path: string) => {
    if (!taskId) return;
    try {
      const fileInfo = await getTaskFile(taskId, path);
      setSelectedFile(fileInfo);
    } catch (e) {
      setSelectedFile({
        path,
        content: `// Error loading file: ${e}`,
        size_bytes: 0,
        language: "text",
      });
    }
  }, [taskId]);

  const clearTask = useCallback(async () => {
    if (taskId) {
      try {
        await deleteTask(taskId);
      } catch {
        // ignore
      }
    }
    setTaskId(null);
    setFiles([]);
    setSelectedFile(null);
  }, [taskId]);

  const clearError = useCallback(() => setError(null), []);

  return {
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
  };
}

import { useState } from "react";

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
}

export function CodeBlock({ code, language = "text", filename }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2 rounded-lg border border-surface-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-800 px-4 py-2 text-sm">
        <span className="text-gray-400 font-mono">
          {filename && <span className="text-blue-400">{filename}</span>}
          {filename && language !== "text" && " · "}
          {language !== "text" && <span className="text-gray-500">{language}</span>}
        </span>
        <button
          onClick={handleCopy}
          className="text-gray-500 hover:text-gray-300 text-xs px-2 py-1 rounded hover:bg-surface-700 transition-colors"
        >
          {copied ? "✓ Copied" : "📋 Copy"}
        </button>
      </div>
      {/* Code */}
      <pre className="bg-surface-900 p-4 overflow-x-auto text-sm font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

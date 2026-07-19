import { FileInfo } from "../types";

interface FileTreeProps {
  files: string[];
  selectedFile: FileInfo | null;
  onSelect: (path: string) => void;
}

export function FileTree({ files, selectedFile, onSelect }: FileTreeProps) {
  if (files.length === 0) return null;

  const tree = buildTree(files);

  return (
    <div className="bg-surface-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-2">
        Files ({files.length})
      </h3>
      <div className="space-y-0.5">
        {renderTree(tree, "", onSelect, selectedFile?.path)}
      </div>
    </div>
  );
}

interface TreeNode {
  name: string;
  children: Record<string, TreeNode>;
  isFile: boolean;
}

function buildTree(files: string[]): TreeNode {
  const root: TreeNode = { name: "", children: {}, isFile: false };

  for (const file of files) {
    const parts = file.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;

      if (!current.children[part]) {
        current.children[part] = {
          name: part,
          children: {},
          isFile,
        };
      }
      current = current.children[part];
    }
  }

  return root;
}

function renderTree(
  node: TreeNode,
  prefix: string,
  onSelect: (path: string) => void,
  selectedPath: string | undefined,
  currentPath = ""
): React.ReactNode[] {
  const entries = Object.entries(node.children).sort(([a], [b]) => {
    // 目录优先
    const aIsDir = Object.keys(node.children[a].children).length > 0;
    const bIsDir = Object.keys(node.children[b].children).length > 0;
    if (aIsDir && !bIsDir) return -1;
    if (!aIsDir && bIsDir) return 1;
    return a.localeCompare(b);
  });

  return entries.map(([name, child]) => {
    const fullPath = currentPath ? `${currentPath}/${name}` : name;
    const isSelected = selectedPath === fullPath;

    if (child.children && Object.keys(child.children).length > 0) {
      // Directory
      return (
        <div key={fullPath}>
          <div className="text-sm text-gray-400 font-medium py-0.5">
            📁 {name}/
          </div>
          <div className="ml-4">
            {renderTree(child, prefix, onSelect, selectedPath, fullPath)}
          </div>
        </div>
      );
    }

    // File
    return (
      <button
        key={fullPath}
        onClick={() => onSelect(fullPath)}
        className={`block w-full text-left text-sm py-0.5 px-1 rounded transition-colors ${
          isSelected
            ? "bg-blue-500/20 text-blue-400"
            : "text-gray-400 hover:text-gray-200 hover:bg-surface-700"
        }`}
      >
        {getFileIcon(name)} {name}
      </button>
    );
  });
}

function getFileIcon(filename: string): string {
  const ext = filename.split(".").pop() || "";
  switch (ext) {
    case "py":
      return "🐍";
    case "js":
    case "ts":
      return "📜";
    case "json":
      return "📋";
    case "md":
      return "📝";
    case "html":
      return "🌐";
    case "css":
      return "🎨";
    case "txt":
      return "📄";
    case "yaml":
    case "yml":
      return "⚙️";
    case "toml":
      return "🔧";
    default:
      return "📄";
  }
}

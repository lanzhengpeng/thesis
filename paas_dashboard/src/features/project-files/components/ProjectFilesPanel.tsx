import {
  BranchesOutlined,
  CaretRightOutlined,
  CopyOutlined,
  DownloadOutlined,
  FileAddOutlined,
  FileTextOutlined,
  FolderAddOutlined,
  FolderOutlined,
  LoadingOutlined,
  OrderedListOutlined,
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useEffect, useState } from "react";
import "../styles/project-files-panel.css";
import {
  useProjectFiles,
  type ProjectFileNode,
} from "../hooks/useProjectFiles";

interface ProjectFilesPanelProps {
  isOpen: boolean;
  onClose?: () => void;
  onOpenFile?: (path: string, name: string) => void;
}

export function ProjectFilesPanel({ isOpen, onOpenFile }: ProjectFilesPanelProps) {
  const [activeTab, setActiveTab] = useState<"files" | "search" | "git">("files");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const { tree, loading, error, load, expand } = useProjectFiles();

  useEffect(() => {
    if (isOpen && tree.length === 0) {
      void load();
    }
  }, [isOpen, tree.length, load]);

  const toggleFolder = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
        const node = findNode(tree, path);
        if (node && node.type === "directory" && !node.loaded && !node.loading) {
          void expand(path);
        }
      }
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="project-files-panel">
      <div className="project-files-panel__card">
        <div className="project-files-panel__tabs">
          <TabButton
            active={activeTab === "files"}
            onClick={() => setActiveTab("files")}
            icon={<FolderOutlined />}
            label="文件"
          />
          <TabButton
            active={activeTab === "search"}
            onClick={() => setActiveTab("search")}
            icon={<SearchOutlined />}
            label="搜索"
          />
          <TabButton
            active={activeTab === "git"}
            onClick={() => setActiveTab("git")}
            icon={<BranchesOutlined />}
            label="Git"
          />
        </div>

        {activeTab === "files" && (
          <div className="project-files-panel__body">
            <div className="project-files-panel__header">
              <span className="project-files-panel__title">Projects</span>
              <div className="project-files-panel__actions">
                <button className="project-files-panel__icon-btn" title="下载">
                  <DownloadOutlined />
                </button>
                <div className="project-files-panel__action-group">
                  <button
                    className="project-files-panel__icon-btn"
                    title="新建文件"
                  >
                    <FileAddOutlined />
                  </button>
                  <button
                    className="project-files-panel__icon-btn"
                    title="新建文件夹"
                  >
                    <FolderAddOutlined />
                  </button>
                  <button className="project-files-panel__icon-btn" title="上传">
                    <UploadOutlined />
                  </button>
                  <button className="project-files-panel__icon-btn" title="复制">
                    <CopyOutlined />
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <div className="project-files-panel__error">{error}</div>
            )}

            <div className="project-files-panel__tree">
              {tree.length === 0 && !loading && !error && (
                <div className="project-files-panel__empty">暂无文件</div>
              )}
              {tree.map((node) => (
                <TreeItem
                  key={node.path}
                  node={node}
                  expanded={expanded}
                  onToggle={toggleFolder}
                  onOpenFile={onOpenFile}
                  depth={0}
                />
              ))}
            </div>
          </div>
        )}

        {activeTab === "search" && <SearchTab />}
        {activeTab === "git" && <GitTab />}
      </div>
    </div>
  );
}

function findNode(
  nodes: ProjectFileNode[],
  path: string
): ProjectFileNode | null {
  for (const node of nodes) {
    if (node.path === path) return node;
    if (node.children) {
      const found = findNode(node.children, path);
      if (found) return found;
    }
  }
  return null;
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      className={`project-files-panel__tab ${
        active ? "project-files-panel__tab--active" : ""
      }`}
      onClick={onClick}
      title={label}
    >
      {icon}
    </button>
  );
}

function TreeItem({
  node,
  expanded,
  onToggle,
  onOpenFile,
  depth,
}: {
  node: ProjectFileNode;
  expanded: Set<string>;
  onToggle: (path: string) => void;
  onOpenFile?: (path: string, name: string) => void;
  depth: number;
}) {
  const isFolder = node.type === "directory";
  const isExpanded = expanded.has(node.path);

  const handleClick = () => {
    if (isFolder) {
      onToggle(node.path);
    } else {
      onOpenFile?.(node.path, node.name);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div className="project-files-panel__tree-node">
      <div
        className="project-files-panel__tree-row"
        style={{ paddingLeft: 8 + depth * 16 }}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {isFolder ? (
          <CaretRightOutlined
            className={`project-files-panel__chevron ${
              isExpanded ? "project-files-panel__chevron--open" : ""
            }`}
          />
        ) : (
          <span className="project-files-panel__chevron-placeholder" />
        )}
        <span className="project-files-panel__row-icon">
          {isFolder ? <FolderOutlined /> : <FileTextOutlined />}
        </span>
        <span className="project-files-panel__row-name">{node.name}</span>
        {node.loading && (
          <span className="project-files-panel__row-loading">
            <LoadingOutlined />
          </span>
        )}
      </div>
      {isFolder &&
        isExpanded &&
        node.children?.map((child) => (
          <TreeItem
            key={child.path}
            node={child}
            expanded={expanded}
            onToggle={onToggle}
            onOpenFile={onOpenFile}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}

function SearchTab() {
  return (
    <div className="project-files-panel__body">
      <div className="project-files-panel__header">
        <span className="project-files-panel__title">搜索</span>
        <div className="project-files-panel__actions">
          <button className="project-files-panel__icon-btn" disabled title="刷新">
            <ReloadOutlined />
          </button>
          <button className="project-files-panel__icon-btn" disabled title="清除">
            ×
          </button>
        </div>
      </div>
      <div className="project-files-panel__search-fields">
        <div className="project-files-panel__field">
          <label>搜索</label>
          <input placeholder="搜索" className="project-files-panel__input" />
        </div>
        <div className="project-files-panel__field">
          <label>包含的文件</label>
          <input className="project-files-panel__input" />
        </div>
        <div className="project-files-panel__field">
          <label>排除的文件</label>
          <input className="project-files-panel__input" />
        </div>
      </div>
    </div>
  );
}

function GitTab() {
  return (
    <div className="project-files-panel__body">
      <div className="project-files-panel__header">
        <span className="project-files-panel__title">源代码管理</span>
        <div className="project-files-panel__actions">
          <button className="project-files-panel__icon-btn" title="刷新">
            <ReloadOutlined />
          </button>
          <button className="project-files-panel__icon-btn" disabled title="列表">
            <OrderedListOutlined />
          </button>
        </div>
      </div>
      <div className="project-files-panel__git-form">
        <input placeholder="消息" className="project-files-panel__input" />
        <button className="project-files-panel__commit-btn" disabled>
          提交
        </button>
      </div>
      <div className="project-files-panel__git-empty">暂无变更</div>
    </div>
  );
}

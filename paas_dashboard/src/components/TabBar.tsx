import type { ReactNode } from "react";
import { AppWindow, Bookmark, FileText, Network, Package, Plus, X } from "lucide-react";
import { useState } from "react";
import type { TabItem } from "../types/tabs";
import "./TabBar.css";

const iconMap: Record<string, React.ComponentType<{ size?: number }>> = {
  "app-window": AppWindow,
  bookmark: Bookmark,
  "file-text": FileText,
  network: Network,
  package: Package,
};

interface TabBarProps {
  tabs: TabItem[];
  activeTabId: string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onAdd: () => void;
  onReorder: (tabs: TabItem[]) => void;
  rightActions?: ReactNode;
}

export function TabBar({
  tabs,
  activeTabId,
  onSelect,
  onClose,
  onAdd,
  onReorder,
  rightActions,
}: TabBarProps) {
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  const handleDragStart = (e: React.DragEvent, id: string) => {
    e.dataTransfer.setData("text/plain", id);
    e.dataTransfer.effectAllowed = "move";
    setDraggingId(id);
  };

  const handleDragOver = (e: React.DragEvent, id: string) => {
    e.preventDefault();
    if (id !== draggingId) {
      setDragOverId(id);
    }
  };

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    const sourceId = e.dataTransfer.getData("text/plain");
    if (!sourceId || sourceId === targetId) return;

    const sourceIndex = tabs.findIndex((t) => t.id === sourceId);
    const targetIndex = tabs.findIndex((t) => t.id === targetId);
    if (sourceIndex === -1 || targetIndex === -1) return;

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const insertAfter = e.clientX > rect.left + rect.width / 2;

    const adjustedTargetIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
    const insertIndex = insertAfter ? adjustedTargetIndex + 1 : adjustedTargetIndex;

    const newTabs = [...tabs];
    const [moved] = newTabs.splice(sourceIndex, 1);
    newTabs.splice(insertIndex, 0, moved);

    onReorder(newTabs);
    setDragOverId(null);
    setDraggingId(null);
  };

  const handleDragEnd = () => {
    setDraggingId(null);
    setDragOverId(null);
  };

  return (
    <header className="tab-bar">
      <div className="tab-bar__container">
        <div className="tab-bar__add">
          <button
            type="button"
            className="tab-bar__action-btn"
            aria-label="新标签页"
            title="新标签页"
            onClick={onAdd}
          >
            <Plus size={16} />
          </button>
        </div>

        <div className="tab-bar__scroll">
          <ul className="tab-bar__list" role="tablist" aria-orientation="horizontal">
            {tabs.map((tab) => (
              <TabItemView
                key={tab.id}
                tab={tab}
                active={tab.id === activeTabId}
                dragging={tab.id === draggingId}
                dragOver={tab.id === dragOverId}
                onSelect={() => onSelect(tab.id)}
                onClose={() => onClose(tab.id)}
                onDragStart={(e) => handleDragStart(e, tab.id)}
                onDragOver={(e) => handleDragOver(e, tab.id)}
                onDrop={(e) => handleDrop(e, tab.id)}
                onDragEnd={handleDragEnd}
              />
            ))}
          </ul>
        </div>

        <div className="tab-bar__actions">{rightActions}</div>
      </div>
    </header>
  );
}

function TabItemView({
  tab,
  active,
  dragging,
  dragOver,
  onSelect,
  onClose,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  tab: TabItem;
  active: boolean;
  dragging: boolean;
  dragOver: boolean;
  onSelect: () => void;
  onClose: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onDragEnd: () => void;
}) {
  const Icon = iconMap[tab.icon] ?? Bookmark;

  return (
    <li
      className={`tab-bar__tab ${active ? "tab-bar__tab--active" : ""} ${
        dragging ? "tab-bar__tab--dragging" : ""
      } ${dragOver ? "tab-bar__tab--drag-over" : ""}`}
      role="tab"
      aria-selected={active}
      draggable
      onClick={onSelect}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
    >
      <div className="tab-bar__tab-content">
        <span className="tab-bar__tab-icon">
          <Icon size={14} />
        </span>
        <span className="tab-bar__tab-label">{tab.title}</span>
      </div>
      {tab.closable && (
        <button
          type="button"
          className="tab-bar__tab-close"
          aria-label={`关闭 ${tab.title}`}
          title={`关闭 ${tab.title}`}
          draggable={false}
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
        >
          <X size={12} />
        </button>
      )}
    </li>
  );
}

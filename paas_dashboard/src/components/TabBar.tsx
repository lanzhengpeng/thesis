import type { ReactNode } from "react";
import { AppWindow, Bookmark, Plus, X } from "lucide-react";
import type { TabItem } from "../types/tabs";
import "./TabBar.css";

const iconMap: Record<string, React.ComponentType<{ size?: number }>> = {
  "app-window": AppWindow,
  bookmark: Bookmark,
};

interface TabBarProps {
  tabs: TabItem[];
  activeTabId: string;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onAdd: () => void;
  rightActions?: ReactNode;
}

export function TabBar({
  tabs,
  activeTabId,
  onSelect,
  onClose,
  onAdd,
  rightActions,
}: TabBarProps) {
  return (
    <header className="tab-bar">
      <div className="tab-bar__scroll">
        <ul className="tab-bar__list" role="tablist" aria-orientation="horizontal">
          {tabs.map((tab) => (
            <TabItemView
              key={tab.id}
              tab={tab}
              active={tab.id === activeTabId}
              onSelect={() => onSelect(tab.id)}
              onClose={() => onClose(tab.id)}
            />
          ))}
        </ul>
      </div>

      <div className="tab-bar__actions">
        <button
          type="button"
          className="tab-bar__action-btn"
          aria-label="新标签页"
          title="新标签页"
          onClick={onAdd}
        >
          <Plus size={16} />
        </button>
        {rightActions}
      </div>
    </header>
  );
}

function TabItemView({
  tab,
  active,
  onSelect,
  onClose,
}: {
  tab: TabItem;
  active: boolean;
  onSelect: () => void;
  onClose: () => void;
}) {
  const Icon = iconMap[tab.icon] ?? Bookmark;

  return (
    <li
      className={`tab-bar__tab ${active ? "tab-bar__tab--active" : ""}`}
      role="tab"
      aria-selected={active}
      onClick={onSelect}
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

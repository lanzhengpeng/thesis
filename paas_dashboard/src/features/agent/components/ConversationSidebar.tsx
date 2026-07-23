import {
  ChevronLeft,
  GitBranch,
  MessageSquare,
  MoreHorizontal,
  PanelLeft,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import "../styles/conversation-sidebar.css";

interface Conversation {
  id: string;
  title: string;
  createdAt: number;
}

interface ConversationSidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

function generateConversations(count: number): Conversation[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `conv-${i + 1}`,
    title: `新对话 ${i + 1}`,
    createdAt: Date.now() - i * 60_000,
  }));
}

export function ConversationSidebar({ isOpen, onClose }: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    generateConversations(4)
  );
  const [selectedId, setSelectedId] = useState<string>(conversations[0]?.id ?? "");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpenId(null);
      }
    }
    if (menuOpenId) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [menuOpenId]);

  const handleNewConversation = useCallback(() => {
    const nextIndex = conversations.length + 1;
    const newConversation: Conversation = {
      id: `conv-${Date.now()}`,
      title: `新对话 ${nextIndex}`,
      createdAt: Date.now(),
    };
    setConversations((prev) => [newConversation, ...prev]);
    setSelectedId(newConversation.id);
  }, [conversations.length]);

  const handleDelete = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    setSelectedId((current) => {
      if (current !== id) return current;
      const remaining = conversations.filter((c) => c.id !== id);
      return remaining[0]?.id ?? "";
    });
    setMenuOpenId(null);
  }, [conversations]);

  const handleRename = useCallback((id: string) => {
    const title = window.prompt("重命名对话");
    if (title?.trim()) {
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: title.trim() } : c))
      );
    }
    setMenuOpenId(null);
  }, []);

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="conversation-sidebar">
      <div className="flex shrink-0 items-center gap-2 px-3 pb-3 pt-2">
        <button
          type="button"
          className="conversation-sidebar__action-btn"
          aria-label="返回"
          title="返回"
          onClick={() => onClose?.()}
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="conversation-sidebar__action-btn ml-auto"
          aria-label="搜索对话"
          title="搜索对话"
          onClick={() => setSearchOpen((v) => !v)}
        >
          <Search size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="conversation-sidebar__action-btn"
          aria-label="收起侧边栏"
          title="收起侧边栏"
          onClick={() => onClose?.()}
        >
          <PanelLeft size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        <div className="flex h-full flex-col gap-3 px-2 pb-3">
          {searchOpen && (
            <div className="px-0.5">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索对话…"
                className="conversation-sidebar__search"
                autoFocus
              />
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              className="conversation-sidebar__new-btn"
              onClick={handleNewConversation}
            >
              <Plus size={16} aria-hidden="true" />
              新建对话
            </button>
            <button
              type="button"
              className="conversation-sidebar__icon-btn"
              aria-label="分支"
              title="分支（未实现）"
              disabled
            >
              <GitBranch size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="relative h-0 flex-1 overflow-hidden">
            <div className="conversation-sidebar__scroll size-full rounded-[inherit] outline-none focus-visible:ring-[0.1875rem] focus-visible:ring-sidebar-ring">
              <div className="min-w-full">
                <div className="flex flex-col gap-1 pr-1">
                  {filteredConversations.map((conversation) => {
                    const isActive = conversation.id === selectedId;
                    return (
                      <div
                        key={conversation.id}
                        className={`conversation-sidebar__item ${
                          isActive ? "conversation-sidebar__item--active" : ""
                        }`}
                      >
                        <button
                          type="button"
                          className="conversation-sidebar__item-btn"
                          onClick={() => setSelectedId(conversation.id)}
                          title={conversation.title}
                        >
                          <MessageSquare
                            size={16}
                            className={`shrink-0 ${
                              isActive
                                ? "text-sidebar-fg"
                                : "text-sidebar-fg-muted"
                            }`}
                            aria-hidden="true"
                          />
                          <span
                            className={`min-w-0 flex-1 truncate leading-5 ${
                              isActive
                                ? "font-medium text-sidebar-fg"
                                : "font-normal text-sidebar-fg"
                            }`}
                          >
                            {conversation.title}
                          </span>
                        </button>
                        <span className="relative flex shrink-0 items-center gap-1.5" ref={menuOpenId === conversation.id ? menuRef : undefined}>
                          <button
                            type="button"
                            className="conversation-sidebar__item-more"
                            aria-label="更多操作"
                            title="更多操作"
                            onClick={() =>
                              setMenuOpenId((current) =>
                                current === conversation.id ? null : conversation.id
                              )
                            }
                          >
                            <MoreHorizontal size={16} aria-hidden="true" />
                          </button>
                          {menuOpenId === conversation.id && (
                            <div className="conversation-sidebar__dropdown">
                              <button
                                type="button"
                                className="conversation-sidebar__dropdown-item"
                                onClick={() => handleRename(conversation.id)}
                              >
                                <Pencil size={14} aria-hidden="true" />
                                重命名
                              </button>
                              <button
                                type="button"
                                className="conversation-sidebar__dropdown-item text-error"
                                onClick={() => handleDelete(conversation.id)}
                              >
                                <Trash2 size={14} aria-hidden="true" />
                                删除
                              </button>
                            </div>
                          )}
                        </span>
                      </div>
                    );
                  })}
                  {filteredConversations.length === 0 && (
                    <div className="px-2 py-4 text-center text-sm text-sidebar-fg-muted">
                      未找到对话
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import {
  ChevronLeft,
  GitBranch,
  MessageSquareMore,
  MoreHorizontal,
  PanelLeft,
  Plus,
  Search,
} from "lucide-react";
import "../styles/conversation-sidebar.css";

interface ConversationSidebarProps {
  isOpen: boolean;
}

export function ConversationSidebar({ isOpen }: ConversationSidebarProps) {
  if (!isOpen) return null;

  return (
    <div className="conversation-sidebar">
      <div className="flex shrink-0 items-center gap-2 px-3 pb-3 pt-2">
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-9 [&_svg:not([class*='size-'])]:size-4.5 focus-visible:border-ring focus-visible:ring-outline focus-visible:ring-[0.1875rem]"
          aria-label="返回"
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-9 [&_svg:not([class*='size-'])]:size-4.5 focus-visible:border-ring focus-visible:ring-outline focus-visible:ring-[0.1875rem] ml-auto"
          aria-label="搜索对话"
        >
          <Search size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-9 [&_svg:not([class*='size-'])]:size-4.5 focus-visible:border-ring focus-visible:ring-outline focus-visible:ring-[0.1875rem]"
          aria-label="收起侧边栏"
        >
          <PanelLeft size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        <div className="flex h-full flex-col gap-3 px-2 pb-3">
          <div className="flex gap-2">
            <button
              type="button"
              className="inline-flex items-center whitespace-nowrap text-sm outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition border shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50 dark:backdrop-blur-md-compat px-4 py-2 has-[>svg]:px-3 [&_svg:not([class*='size-'])]:size-4.5 focus-visible:border-ring focus-visible:ring-outline focus-visible:ring-[0.1875rem] h-9 flex-1 justify-center gap-2 rounded-md bg-background text-mini font-medium leading-5"
            >
              <Plus size={16} aria-hidden="true" />
              新建对话
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition border shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50 dark:backdrop-blur-md-compat has-[>svg]:px-3 [&_svg:not([class*='size-'])]:size-4.5 focus-visible:border-ring focus-visible:ring-outline focus-visible:ring-[0.1875rem] h-9 w-9 shrink-0 rounded-[10px] bg-background p-0"
              aria-label="分支"
            >
              <GitBranch size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="relative h-0 flex-1 overflow-hidden">
            <div className="conversation-sidebar__scroll size-full rounded-[inherit] outline-none focus-visible:ring-[0.1875rem] focus-visible:ring-outline">
              <div className="min-w-full">
                <div className="flex flex-col gap-1 pr-1">
                  <div className="group flex h-8 w-full items-center gap-1.5 overflow-hidden rounded-sm px-2 py-1.5 text-left transition-colors bg-input">
                    <button
                      type="button"
                      className="inline-flex items-center whitespace-nowrap text-sm outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition h-8 px-3 has-[>svg]:px-2.5 [&_svg:not([class*='size-'])]:size-4 !h-auto min-w-0 flex-1 !shrink justify-start gap-1.5 rounded-none !p-0 text-left font-normal"
                    >
                      <MessageSquareMore
                        size={16}
                        className="shrink-0 text-sidebar-foreground"
                        aria-hidden="true"
                      />
                      <span className="min-w-0 flex-1 truncate leading-5 text-sidebar-foreground font-medium">
                        新对话 2
                      </span>
                    </button>
                    <span className="flex shrink-0 items-center gap-1.5">
                      <button
                        type="button"
                        className="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer h-8 gap-1.5 px-3 has-[>svg]:px-2.5 [&_svg:not([class*='size-'])]:size-4 !h-4 !w-4 shrink-0 !gap-0 rounded-sm !p-0 text-sidebar-foreground/60 opacity-0 transition-opacity hover:text-text-1 focus-within:text-text-1 group-hover:opacity-100 group-focus-within:opacity-100 disabled:cursor-wait"
                        aria-label="更多操作"
                        title="更多操作"
                      >
                        <MoreHorizontal size={16} aria-hidden="true" />
                      </button>
                    </span>
                  </div>

                  <div className="group flex h-8 w-full items-center gap-1.5 overflow-hidden rounded-sm px-2 py-1.5 text-left transition-colors hover:bg-input">
                    <button
                      type="button"
                      className="inline-flex items-center whitespace-nowrap text-sm outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer transition h-8 px-3 has-[>svg]:px-2.5 [&_svg:not([class*='size-'])]:size-4 !h-auto min-w-0 flex-1 !shrink justify-start gap-1.5 rounded-none !p-0 text-left font-normal"
                    >
                      <MessageSquareMore
                        size={16}
                        className="shrink-0 text-sidebar-foreground/60"
                        aria-hidden="true"
                      />
                      <span className="min-w-0 flex-1 truncate leading-5 text-sidebar-foreground font-normal">
                        新对话 2
                      </span>
                    </button>
                    <span className="flex shrink-0 items-center gap-1.5">
                      <button
                        type="button"
                        className="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 cursor-pointer h-8 gap-1.5 px-3 has-[>svg]:px-2.5 [&_svg:not([class*='size-'])]:size-4 !h-4 !w-4 shrink-0 !gap-0 rounded-sm !p-0 text-sidebar-foreground/60 opacity-0 transition-opacity hover:text-text-1 focus-within:text-text-1 group-hover:opacity-100 group-focus-within:opacity-100 disabled:cursor-wait"
                        aria-label="更多操作"
                        title="更多操作"
                      >
                        <MoreHorizontal size={16} aria-hidden="true" />
                      </button>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

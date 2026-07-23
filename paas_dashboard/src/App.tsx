import { useEffect, useState } from "react";
import { Network } from "lucide-react";
import { ModuleDetailPanel } from "./features/architecture";
import { AgentChatPanel, ConversationSidebar } from "./features/agent";
import { ProjectFilesPanel } from "./features/project-files";
import type { ModuleNodeData } from "./features/architecture";
import { ArchitectureCanvas } from "./components/ArchitectureCanvas";
import { FileEditor } from "./components/FileEditor";
import { ScalarPanel } from "./components/ScalarPanel";
import { SqliteEditor } from "./components/SqliteEditor";
import { TabBar } from "./components/TabBar";
import { EmptyTabPanel } from "./components/EmptyTabPanel";
import { useCheatSheet } from "./hooks/useCheatSheet";
import type { CheatSheetResponse } from "./types/cheatSheet";
import { fetchFinderRead, fetchFinderReadBinary } from "./services/api";
import { isSqliteFile } from "./utils/fileTypes";
import type { TabItem } from "./types/tabs";
import "./App.css";

export interface SelectedMethod {
  componentId: string;
  methodName: string;
}

function buildModuleData(moduleName: string, response: CheatSheetResponse): ModuleNodeData {
  const failed = response.modules.failed.find((f) => f.module === moduleName);
  const components = response.call_graph[moduleName] || {
    controller: [],
    service: [],
    mapper: [],
  };

  return {
    label: moduleName,
    status: failed ? "failed" : "ok",
    error: failed?.error,
    components,
    apiList: response.api_map.filter((api) => api.module === moduleName),
    counts: {
      controllers: components.controller?.length || 0,
      services: components.service?.length || 0,
      mappers: components.mapper?.length || 0,
    },
  };
}

function App() {
  const { data, loading, error, refetch } = useCheatSheet();
  const [isDetailPanelOpen, setIsDetailPanelOpen] = useState(false);
  const [isProjectFilesOpen, setIsProjectFilesOpen] = useState(false);
  const [isConversationSidebarOpen, setIsConversationSidebarOpen] = useState(false);
  const [selectedNodeData, setSelectedNodeData] = useState<ModuleNodeData | null>(null);
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<SelectedMethod | null>(null);
  const [tabs, setTabs] = useState<TabItem[]>([
    { id: "preview", type: "architecture", title: "预览", icon: "app-window", closable: false },
  ]);
  const [activeTabId, setActiveTabId] = useState("preview");
  const [fileContents, setFileContents] = useState<Record<string, string>>({});
  const [fileBuffers, setFileBuffers] = useState<Record<string, ArrayBuffer>>({});
  const [scalarMounted, setScalarMounted] = useState(false);

  useEffect(() => {
    setTabs((prev) => {
      const activeTab = prev.find((t) => t.id === activeTabId);
      if (activeTab?.type === "empty") return prev;
      const hasEmpty = prev.some((t) => t.type === "empty");
      if (!hasEmpty) return prev;
      return prev.filter((t) => t.type !== "empty");
    });
  }, [activeTabId]);

  const handleAddTab = () => {
    const id = `tab-${Date.now()}`;
    const newTab: TabItem = {
      id,
      type: "empty",
      title: "新标签页",
      icon: "bookmark",
      closable: true,
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(id);
  };

  const handleCloseTab = (id: string) => {
    setTabs((prev) => {
      const index = prev.findIndex((t) => t.id === id);
      if (index === -1) return prev;
      const next = prev.filter((t) => t.id !== id);
      if (activeTabId === id) {
        const nextActive = prev[index - 1] ?? next[0];
        if (nextActive) {
          setActiveTabId(nextActive.id);
        }
      }
      return next;
    });
  };

  const handleOpenFile = async (path: string, name: string) => {
    const existing = tabs.find((t) => t.type === "file" && t.path === path);
    if (existing) {
      setActiveTabId(existing.id);
      return;
    }

    const id = `tab-${Date.now()}`;
    const newTab: TabItem = {
      id,
      type: "file",
      title: name,
      icon: "file-text",
      closable: true,
      path,
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(id);

    if (isSqliteFile(path)) {
      try {
        const { buffer } = await fetchFinderReadBinary(path);
        setFileBuffers((prev) => ({ ...prev, [path]: buffer }));
      } catch (err) {
        setFileBuffers((prev) => ({
          ...prev,
          // Placeholder so the tab stops showing "加载中..."
          [path]: new ArrayBuffer(0),
        }));
        setFileContents((prev) => ({
          ...prev,
          [path]: `无法读取文件：${err instanceof Error ? err.message : String(err)}`,
        }));
      }
      return;
    }

    try {
      const content = await fetchFinderRead(path);
      setFileContents((prev) => ({ ...prev, [path]: content }));
    } catch (err) {
      setFileContents((prev) => ({
        ...prev,
        [path]: `无法读取文件：${err instanceof Error ? err.message : String(err)}`,
      }));
    }
  };

  const handleOpenArchitectureTab = () => {
    const existing = tabs.find((t) => t.type === "architecture");
    if (existing) {
      setActiveTabId(existing.id);
      return;
    }

    const id = `tab-${Date.now()}`;
    const newTab: TabItem = {
      id,
      type: "architecture",
      title: "预览",
      icon: "app-window",
      closable: true,
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(id);
  };

  const handleOpenProjectFiles = () => {
    setIsProjectFilesOpen(true);
  };

  const handleOpenScalarTab = () => {
    const existing = tabs.find((t) => t.type === "scalar");
    if (existing) {
      setActiveTabId(existing.id);
      return;
    }

    setScalarMounted(true);
    const id = `tab-${Date.now()}`;
    const newTab: TabItem = {
      id,
      type: "scalar",
      title: "API 客户端",
      icon: "network",
      closable: true,
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(id);
  };

  const handleReorderTabs = (newTabs: TabItem[]) => {
    setTabs(newTabs);
  };

  const layoutKey = `${isDetailPanelOpen}-${isProjectFilesOpen}`;

  const activeTab = tabs.find((t) => t.id === activeTabId) ?? tabs[0];

  const refreshButton = (
    <button
      onClick={refetch}
      disabled={loading}
      className="app__primary-btn"
    >
      立即刷新
    </button>
  );

  return (
    <div className="app">
      <ConversationSidebar
        isOpen={isConversationSidebarOpen}
        onClose={() => setIsConversationSidebarOpen(false)}
      />

      <AgentChatPanel
        isConversationSidebarOpen={isConversationSidebarOpen}
        onFolderClick={() => setIsProjectFilesOpen((v) => !v)}
        onConversationToggle={() =>
          setIsConversationSidebarOpen((v) => !v)
        }
      />

      <ProjectFilesPanel isOpen={isProjectFilesOpen} onOpenFile={handleOpenFile} />

      <div className="app__main">
        <TabBar
          tabs={tabs}
          activeTabId={activeTabId}
          onSelect={setActiveTabId}
          onClose={handleCloseTab}
          onAdd={handleAddTab}
          onReorder={handleReorderTabs}
          rightActions={
            <>
              <button
                type="button"
                className="tab-bar__action-btn"
                aria-label="API 客户端"
                title="API 客户端"
                onClick={handleOpenScalarTab}
              >
                <Network size={16} />
              </button>
              {activeTab?.type === "architecture" ? refreshButton : null}
            </>
          }
        />

        <div className="app__content">
          {scalarMounted && (
            <div
              className="app__scalar-wrapper"
              style={{ display: activeTab?.type === "scalar" ? "flex" : "none" }}
            >
              <ScalarPanel />
            </div>
          )}
          {activeTab?.type === "architecture" ? (
            <>
              <ArchitectureCanvas
                data={data}
                loading={loading}
                error={error}
                layoutKey={layoutKey}
                onRefresh={refetch}
                onNodeClick={() => {
                  setIsDetailPanelOpen(true);
                }}
                onPaneClick={() => {
                  setIsDetailPanelOpen(false);
                }}
                onSelectModule={(moduleData) => {
                  setSelectedNodeData(moduleData);
                  setSelectedComponentId(null);
                  setSelectedMethod(null);
                  setIsDetailPanelOpen(true);
                }}
                onSelectComponent={(componentId) => {
                  const component = data?.components.find(
                    (c) => `${c.module}::${c.type}::${c.name}` === componentId
                  );
                  if (component && data) {
                    setSelectedNodeData(buildModuleData(component.module, data));
                  }
                  setSelectedComponentId(componentId);
                  setSelectedMethod(null);
                  setIsDetailPanelOpen(true);
                }}
                onSelectMethod={(method) => {
                  if (method === null) {
                    setSelectedMethod(null);
                  } else {
                    setSelectedMethod({ componentId: method.componentId, methodName: method.methodName });
                    const component = data?.components.find(
                      (c) => `${c.module}::${c.type}::${c.name}` === method.componentId
                    );
                    if (component && data) {
                      setSelectedNodeData(buildModuleData(component.module, data));
                    }
                  }
                  setSelectedComponentId(null);
                  setIsDetailPanelOpen(true);
                }}
              />

              <ModuleDetailPanel
                isOpen={isDetailPanelOpen}
                onClose={() => setIsDetailPanelOpen(false)}
                data={selectedNodeData}
                components={data?.components ?? []}
                selectedComponentId={selectedComponentId}
                selectedMethod={selectedMethod}
                onSelectComponent={setSelectedComponentId}
                onSelectMethod={setSelectedMethod}
                onModuleChanged={() => refetch()}
                onModuleDeleted={() => {
                  setIsDetailPanelOpen(false);
                  refetch();
                }}
              />
            </>
          ) : activeTab?.type === "file" ? (
            <div className="app__file-viewer">
              {activeTab.path && isSqliteFile(activeTab.path) ? (
                activeTab.path in fileBuffers ? (
                  <SqliteEditor
                    key={activeTab.path}
                    path={activeTab.path}
                    buffer={fileBuffers[activeTab.path]}
                  />
                ) : (
                  <div className="app__empty-tab">加载中...</div>
                )
              ) : activeTab.path && activeTab.path in fileContents ? (
                <FileEditor
                  key={activeTab.path}
                  path={activeTab.path}
                  content={fileContents[activeTab.path]}
                  onChange={(value) =>
                    setFileContents((prev) => ({
                      ...prev,
                      [activeTab.path!]: value,
                    }))
                  }
                />
              ) : (
                <div className="app__empty-tab">加载中...</div>
              )}
            </div>
          ) : activeTab?.type === "scalar" ? null : (
            <EmptyTabPanel
              onOpenPreview={handleOpenArchitectureTab}
              onOpenEditor={handleOpenProjectFiles}
              onOpenScalar={handleOpenScalarTab}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;

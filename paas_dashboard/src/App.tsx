import { useState } from "react";
import { ModuleDetailPanel } from "./features/architecture";
import { AgentChatPanel } from "./features/agent";
import { ProjectFilesPanel } from "./features/project-files";
import type { ModuleNodeData } from "./features/architecture";
import { ArchitectureCanvas } from "./components/ArchitectureCanvas";
import { TabBar } from "./components/TabBar";
import { useCheatSheet } from "./hooks/useCheatSheet";
import type { CheatSheetResponse } from "./types/cheatSheet";
import type { TabItem } from "./types/tabs";

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
  const [selectedNodeData, setSelectedNodeData] = useState<ModuleNodeData | null>(null);
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<SelectedMethod | null>(null);
  const [tabs, setTabs] = useState<TabItem[]>([
    { id: "preview", type: "architecture", title: "预览", icon: "app-window", closable: false },
  ]);
  const [activeTabId, setActiveTabId] = useState("preview");

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

  // 右侧详情面板/项目文件面板展开折叠时触发 React Flow 的 fitView
  const layoutKey = `${isDetailPanelOpen}-${isProjectFilesOpen}`;

  const activeTab = tabs.find((t) => t.id === activeTabId) ?? tabs[0];

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        background: "#ffffff",
      }}
    >
      <TabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onSelect={setActiveTabId}
        onClose={handleCloseTab}
        onAdd={handleAddTab}
        rightActions={
          <button
            onClick={refetch}
            disabled={loading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              whiteSpace: "nowrap",
              height: 32,
              padding: "0 12px",
              borderRadius: 6,
              border: "none",
              background: "#0f172a",
              color: "#ffffff",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: 14,
              fontWeight: 500,
              transition: "background 150ms ease",
              outline: "none",
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.background = "#000000";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "#0f172a";
            }}
          >
            立即刷新
          </button>
        }
      />

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {activeTab?.type === "architecture" ? (
          <>
            <AgentChatPanel
              onFolderClick={() => setIsProjectFilesOpen((v) => !v)}
            />

            <ProjectFilesPanel isOpen={isProjectFilesOpen} />

            <ArchitectureCanvas
              data={data}
              loading={loading}
              error={error}
              layoutKey={layoutKey}
              onRefresh={refetch}
              onNodeClick={() => {
                // 点击节点时展开右侧面板，具体数据由 onSelect* 回调填充
                setIsDetailPanelOpen(true);
              }}
              onPaneClick={() => {
                // 点击画布空白处收起右侧面板
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
        ) : (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#64748b",
              fontSize: 14,
            }}
          >
            新标签页
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

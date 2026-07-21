import { useState } from "react";
import { ArchitectureGraph, ModuleDetailPanel } from "./features/architecture";
import { AgentChatPanel } from "./features/agent";
import type { ModuleNodeData } from "./features/architecture";
import { StatusHeader } from "./components/StatusHeader";
import { useCheatSheet } from "./hooks/useCheatSheet";
import type { CheatSheetResponse } from "./types/cheatSheet";

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
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [isDetailPanelOpen, setIsDetailPanelOpen] = useState(false);
  const [selectedNodeData, setSelectedNodeData] = useState<ModuleNodeData | null>(null);
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<SelectedMethod | null>(null);

  // 只要任意侧边栏的展开/折叠状态变化，就触发 React Flow 的 fitView
  const layoutKey = `${isChatOpen}-${isDetailPanelOpen}`;

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        background: "#F4F5F7",
      }}
    >
      <StatusHeader
        counts={data?.counts ?? { controllers: 0, services: 0, mappers: 0 }}
        modules={data?.modules ?? { loaded: [], failed: [] }}
        loading={loading}
        error={error}
        onRefresh={refetch}
        isChatOpen={isChatOpen}
        onToggleChat={() => setIsChatOpen((open) => !open)}
      />

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <AgentChatPanel
          isOpen={isChatOpen}
          onToggle={() => setIsChatOpen((open) => !open)}
        />

        <div
          style={{
            flex: 1,
            minWidth: 0,
            margin: 16,
            background: "#ffffff",
            borderRadius: 16,
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.08)",
            overflow: "hidden",
            display: "flex",
          }}
        >
          {!data ? (
            <div
              style={{
                flex: 1,
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                color: "#64748b",
                gap: 12,
              }}
            >
              {loading ? (
                <div>正在加载系统架构...</div>
              ) : (
                <>
                  <div>无法加载系统架构</div>
                  {error && <div style={{ color: "#ef4444" }}>{error}</div>}
                  <button onClick={refetch} style={{ padding: "8px 16px" }}>
                    重试
                  </button>
                </>
              )}
            </div>
          ) : (
            <ArchitectureGraph
              data={data}
              layoutKey={layoutKey}
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
                const component = data.components.find(
                  (c) => `${c.module}::${c.type}::${c.name}` === componentId
                );
                if (component) {
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
                  const component = data.components.find(
                    (c) => `${c.module}::${c.type}::${c.name}` === method.componentId
                  );
                  if (component) {
                    setSelectedNodeData(buildModuleData(component.module, data));
                  }
                }
                setSelectedComponentId(null);
                setIsDetailPanelOpen(true);
              }}
            />
          )}
        </div>

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
      </div>
    </div>
  );
}

export default App;

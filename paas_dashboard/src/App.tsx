import { useState } from "react";
import { ArchitectureGraph, ModuleDetailPanel } from "./features/architecture";
import { AgentChatPanel } from "./features/agent";
import type { ModuleNodeData } from "./features/architecture";
import { StatusHeader } from "./components/StatusHeader";
import { useCheatSheet } from "./hooks/useCheatSheet";

export interface SelectedMethod {
  componentId: string;
  methodName: string;
}

function App() {
  const { data, loading, error, refetch } = useCheatSheet();
  const [selectedModule, setSelectedModule] = useState<ModuleNodeData | null>(null);
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<SelectedMethod | null>(null);

  const mainContent = !data ? (
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
        background: "#f8fafc",
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
    <>
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <ArchitectureGraph
          data={data}
          onSelectModule={(moduleData) => {
            setSelectedModule(moduleData);
            setSelectedComponentId(null);
            setSelectedMethod(null);
          }}
          onSelectComponent={(componentId) => {
            setSelectedComponentId(componentId);
            setSelectedMethod(null);
          }}
          onSelectMethod={(method) => {
            if (method === null) {
              setSelectedMethod(null);
            } else {
              setSelectedMethod({ componentId: method.componentId, methodName: method.methodName });
            }
            setSelectedComponentId(null);
          }}
        />
      </div>
      <ModuleDetailPanel
        data={selectedModule}
        components={data.components}
        selectedComponentId={selectedComponentId}
        selectedMethod={selectedMethod}
        onSelectComponent={setSelectedComponentId}
        onSelectMethod={setSelectedMethod}
      />
    </>
  );

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <StatusHeader
        counts={data?.counts ?? { controllers: 0, services: 0, mappers: 0 }}
        modules={data?.modules ?? { loaded: [], failed: [] }}
        loading={loading}
        error={error}
        onRefresh={refetch}
      />

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <AgentChatPanel />
        {mainContent}
      </div>
    </div>
  );
}

export default App;

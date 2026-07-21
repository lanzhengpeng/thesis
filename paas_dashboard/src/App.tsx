import { useState } from "react";
import { ArchitectureGraph, ModuleDetailPanel } from "./features/architecture";
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

  if (!data && loading) {
    return (
      <div
        style={{
          width: "100vw",
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
        }}
      >
        正在加载系统架构...
      </div>
    );
  }

  if (!data) {
    return (
      <div
        style={{
          width: "100vw",
          height: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
          gap: 12,
        }}
      >
        <div>无法加载系统架构</div>
        {error && <div style={{ color: "#ef4444" }}>{error}</div>}
        <button onClick={refetch} style={{ padding: "8px 16px" }}>
          重试
        </button>
      </div>
    );
  }

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
        counts={data.counts}
        modules={data.modules}
        loading={loading}
        error={error}
        onRefresh={refetch}
      />

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
        <ModuleDetailPanel
          data={selectedModule}
          components={data.components}
          selectedComponentId={selectedComponentId}
          selectedMethod={selectedMethod}
          onSelectComponent={setSelectedComponentId}
          onSelectMethod={setSelectedMethod}
        />
      </div>
    </div>
  );
}

export default App;

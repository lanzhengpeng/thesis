import { useState } from "react";
import { ArchitectureGraph } from "./components/ArchitectureGraph";
import { ModuleDetailPanel } from "./components/ModuleDetailPanel";
import { StatusHeader } from "./components/StatusHeader";
import { useCheatSheet } from "./hooks/useCheatSheet";
import type { ModuleNodeData } from "./lib/graphBuilder";

function App() {
  const { data, loading, error, refetch } = useCheatSheet();
  const [selectedModule, setSelectedModule] = useState<ModuleNodeData | null>(null);

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
        <ArchitectureGraph data={data} onSelectModule={setSelectedModule} />
        <ModuleDetailPanel data={selectedModule} />
      </div>
    </div>
  );
}

export default App;

import { ArchitectureGraph } from "../features/architecture";
import type { ModuleNodeData } from "../features/architecture";
import type { CheatSheetResponse } from "../types/cheatSheet";

interface ArchitectureCanvasProps {
  data: CheatSheetResponse | null;
  loading: boolean;
  error: string | null;
  layoutKey: string;
  onRefresh: () => void;
  onNodeClick?: () => void;
  onPaneClick?: () => void;
  onSelectModule: (data: ModuleNodeData) => void;
  onSelectComponent: (componentId: string) => void;
  onSelectMethod?: (method: { componentId: string; methodName: string } | null) => void;
}

export function ArchitectureCanvas({
  data,
  loading,
  error,
  layoutKey,
  onRefresh,
  onNodeClick,
  onPaneClick,
  onSelectModule,
  onSelectComponent,
  onSelectMethod,
}: ArchitectureCanvasProps) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          position: "relative",
          overflow: "hidden",
          background: "#f5f5f5",
          borderRadius: 10,
          border: "1px solid #e2e8f0",
        }}
      >
        {!data ? (
          <div
            style={{
              width: "100%",
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
                <button onClick={onRefresh} style={{ padding: "8px 16px" }}>
                  重试
                </button>
              </>
            )}
          </div>
        ) : (
          <ArchitectureGraph
            data={data}
            loading={loading}
            error={error}
            layoutKey={layoutKey}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onSelectModule={onSelectModule}
            onSelectComponent={onSelectComponent}
            onSelectMethod={onSelectMethod}
          />
        )}
      </div>
    </div>
  );
}

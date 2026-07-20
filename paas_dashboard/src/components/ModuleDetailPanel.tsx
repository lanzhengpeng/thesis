import type { ModuleNodeData } from "../lib/graphBuilder";

interface ModuleDetailPanelProps {
  data: ModuleNodeData | null;
}

export function ModuleDetailPanel({ data }: ModuleDetailPanelProps) {
  if (!data) {
    return (
      <div style={panelStyle}>
        <h3 style={{ margin: 0, color: "#64748b" }}>详情面板</h3>
        <p style={{ color: "#94a3b8" }}>点击画布上的节点查看详细信息</p>
      </div>
    );
  }

  const isFailed = data.status === "failed";

  return (
    <div style={panelStyle}>
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ margin: 0, color: "#1e293b" }}>{data.label}</h3>
        <span
          style={{
            display: "inline-block",
            marginTop: 6,
            padding: "4px 10px",
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 600,
            background: isFailed ? "#fee2e2" : "#dcfce7",
            color: isFailed ? "#991b1b" : "#166534",
          }}
        >
          {isFailed ? "加载失败" : "运行中"}
        </span>
      </div>

      {!isFailed && (
        <>
          <Section title="组件统计">
            <Stat label="Controller" value={data.counts.controllers} />
            <Stat label="Service" value={data.counts.services} />
            <Stat label="Mapper" value={data.counts.mappers} />
          </Section>

          <Section title="组件与依赖">
            {Object.entries(data.components).map(([type, entries]) => (
              <div key={type} style={{ marginBottom: 10 }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    color: "#64748b",
                    marginBottom: 4,
                  }}
                >
                  {type}
                </div>
                {entries.map((entry) => (
                  <div
                    key={entry}
                    style={{
                      fontSize: 13,
                      color: "#334155",
                      fontFamily: "monospace",
                      padding: "2px 0",
                    }}
                  >
                    {entry}
                  </div>
                ))}
              </div>
            ))}
          </Section>

          <Section title="API 列表">
            {data.apiList.length === 0 ? (
              <span style={{ color: "#94a3b8" }}>暂无 API</span>
            ) : (
              data.apiList.map((api) => (
                <div
                  key={`${api.method}${api.path}`}
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    padding: "6px 0",
                    borderBottom: "1px solid #e2e8f0",
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#fff",
                      background: methodColor(api.method),
                      padding: "2px 6px",
                      borderRadius: 4,
                    }}
                  >
                    {api.method}
                  </span>
                  <span
                    style={{
                      fontSize: 13,
                      color: "#334155",
                      fontFamily: "monospace",
                      wordBreak: "break-all",
                    }}
                  >
                    {api.path}
                  </span>
                </div>
              ))
            )}
          </Section>
        </>
      )}

      {isFailed && data.error && (
        <Section title="错误信息">
          <div
            style={{
              background: "#fee2e2",
              color: "#991b1b",
              padding: 10,
              borderRadius: 6,
              fontSize: 13,
              wordBreak: "break-all",
            }}
          >
            {data.error}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <h4
        style={{
          margin: "0 0 8px 0",
          fontSize: 14,
          color: "#0f172a",
          borderBottom: "1px solid #e2e8f0",
          paddingBottom: 4,
        }}
      >
        {title}
      </h4>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "2px 0" }}>
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ fontWeight: 700, color: "#1e293b" }}>{value}</span>
    </div>
  );
}

function methodColor(method: string): string {
  switch (method.toUpperCase()) {
    case "GET":
      return "#3b82f6";
    case "POST":
      return "#22c55e";
    case "PUT":
      return "#f59e0b";
    case "DELETE":
      return "#ef4444";
    case "PATCH":
      return "#8b5cf6";
    default:
      return "#64748b";
  }
}

const panelStyle: React.CSSProperties = {
  width: 340,
  height: "100%",
  background: "#ffffff",
  borderLeft: "1px solid #e2e8f0",
  padding: 20,
  overflowY: "auto",
  boxSizing: "border-box",
};

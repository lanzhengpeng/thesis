import type { ModuleNodeData } from "../lib/graphBuilder";
import type { CheatSheetComponentItem, CheatSheetMethodItem } from "../../../types/cheatSheet";
import { parseComponentEntry } from "../lib/graphBuilder";

interface ModuleDetailPanelProps {
  data: ModuleNodeData | null;
  components?: CheatSheetComponentItem[];
  selectedComponentId?: string | null;
  selectedMethod?: { componentId: string; methodName: string } | null;
  onSelectComponent?: (componentId: string) => void;
  onSelectMethod?: (method: { componentId: string; methodName: string } | null) => void;
}

export function ModuleDetailPanel({
  data,
  components = [],
  selectedComponentId,
  selectedMethod,
  onSelectComponent,
  onSelectMethod,
}: ModuleDetailPanelProps) {
  if (!data) {
    return (
      <div style={panelStyle}>
        <h3 style={{ margin: 0, color: "#64748b" }}>详情面板</h3>
        <p style={{ color: "#94a3b8" }}>点击画布上的节点查看详细信息</p>
      </div>
    );
  }

  const isFailed = data.status === "failed";

  const selectedComponent = selectedComponentId
    ? components.find(
        (c) =>
          selectedComponentId === `${c.module}::${c.type}::${c.name}`
      )
    : undefined;

  const selectedMethodComponent = selectedMethod
    ? components.find(
        (c) =>
          selectedMethod.componentId === `${c.module}::${c.type}::${c.name}`
      )
    : undefined;
  const selectedMethodInfo = selectedMethodComponent
    ? selectedMethodComponent.methods.find((m) => m.name === selectedMethod?.methodName)
    : undefined;

  return (
    <div style={panelStyle}>
      {selectedMethod && selectedMethodInfo && selectedMethodComponent && !isFailed && (
        <MethodDetail
          method={selectedMethodInfo}
          component={selectedMethodComponent}
          onBack={() => onSelectMethod?.(null)}
        />
      )}

      {selectedComponent && !isFailed && (
        <ComponentDetail
          component={selectedComponent}
          onBack={() => onSelectComponent?.("")}
        />
      )}

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
                {entries.map((entry) => {
                  const { name } = parseComponentEntry(entry);
                  const componentId = `${data.label}::${type}::${name}`;
                  const isSelected = selectedComponentId === componentId;

                  return (
                    <div
                      key={entry}
                      onClick={() => onSelectComponent?.(componentId)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "#f1f5f9";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = isSelected
                          ? "#e2e8f0"
                          : "transparent";
                      }}
                      style={{
                        fontSize: 13,
                        color: "#334155",
                        fontFamily: "monospace",
                        padding: "4px 8px",
                        borderRadius: 4,
                        cursor: "pointer",
                        background: isSelected ? "#e2e8f0" : "transparent",
                        marginBottom: 2,
                      }}
                    >
                      {entry}
                    </div>
                  );
                })}
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

function MethodDetail({
  method,
  component,
  onBack,
}: {
  method: CheatSheetMethodItem;
  component: CheatSheetComponentItem;
  onBack: () => void;
}) {
  return (
    <div
      style={{
        marginBottom: 20,
        padding: 12,
        borderRadius: 8,
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 10,
        }}
      >
        <h4 style={{ margin: 0, color: "#0f172a", fontSize: 16 }}>
          {method.feature || method.name}
        </h4>
        <button
          onClick={onBack}
          style={{
            fontSize: 12,
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #cbd5e1",
            background: "#ffffff",
            cursor: "pointer",
          }}
        >
          返回模块
        </button>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <Badge color={typeColor(component.type)}>{component.type}</Badge>
        <Badge color="#64748b">{component.module}</Badge>
        <Badge color="#3b82f6">{component.name}</Badge>
      </div>

      {component.type === "controller" && method.http_method && (
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            marginBottom: 12,
            fontSize: 12,
          }}
        >
          <span
            style={{
              fontWeight: 700,
              color: "#fff",
              background: methodColor(method.http_method),
              padding: "2px 6px",
              borderRadius: 4,
            }}
          >
            {method.http_method}
          </span>
          <span style={{ fontFamily: "monospace", color: "#334155" }}>{method.path}</span>
        </div>
      )}

      <DetailTable
        title="方法签名"
        columns={["名称", "类型"]}
        rows={[[method.name, component.type]]}
      />

      {method.params.length > 0 && (
        <DetailTable
          title="参数"
          columns={["参数名"]}
          rows={method.params.map((p) => [p])}
        />
      )}

      {method.calls.length > 0 && (
        <DetailTable
          title="下游调用"
          columns={["目标"]}
          rows={method.calls.map((c) => [c])}
        />
      )}

      {method.sql && (
        <div style={{ marginTop: 12 }}>
          <h5 style={{ margin: "0 0 6px 0", fontSize: 13, color: "#0f172a" }}>SQL</h5>
          <pre
            style={{
              margin: 0,
              padding: 10,
              borderRadius: 6,
              background: "#f1f5f9",
              fontSize: 12,
              fontFamily: "monospace",
              color: "#334155",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {method.sql}
          </pre>
        </div>
      )}
    </div>
  );
}

function ComponentDetail({
  component,
  onBack,
}: {
  component: CheatSheetComponentItem;
  onBack: () => void;
}) {
  return (
    <div
      style={{
        marginBottom: 20,
        padding: 12,
        borderRadius: 8,
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 10,
        }}
      >
        <h4 style={{ margin: 0, color: "#0f172a", fontSize: 16 }}>
          {component.name}
        </h4>
        <button
          onClick={onBack}
          style={{
            fontSize: 12,
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #cbd5e1",
            background: "#ffffff",
            cursor: "pointer",
          }}
        >
          返回模块
        </button>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <Badge color={typeColor(component.type)}>{component.type}</Badge>
        <Badge color="#64748b">{component.module}</Badge>
        <Badge color={component.assembled ? "#22c55e" : "#ef4444"}>
          {component.assembled ? "已组装" : "未组装"}
        </Badge>
      </div>

      {component.base_path && (
        <div
          style={{
            fontSize: 12,
            color: "#64748b",
            marginBottom: 12,
            fontFamily: "monospace",
          }}
        >
          base_path: {component.base_path}
        </div>
      )}

      <DetailTable
        title="构造参数"
        columns={["名称", "类型"]}
        rows={component.constructor_params.map((p) => [p.name, p.type])}
      />

      {component.inject_fields.length > 0 && (
        <DetailTable
          title="字段注入"
          columns={["名称", "类型"]}
          rows={component.inject_fields.map((p) => [p.name, p.type])}
        />
      )}

      {component.type === "controller" && component.methods.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h5 style={{ margin: "0 0 6px 0", fontSize: 13, color: "#0f172a" }}>
            HTTP 方法
          </h5>
          {component.methods.map((m) => (
            <div
              key={`${m.http_method}${m.path}${m.name}`}
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                padding: "4px 0",
                fontSize: 12,
                borderBottom: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontWeight: 700,
                  color: "#fff",
                  background: methodColor(m.http_method || ""),
                  padding: "2px 6px",
                  borderRadius: 4,
                }}
              >
                {m.http_method || ""}
              </span>
              <span style={{ fontFamily: "monospace", color: "#334155" }}>
                {m.path}
              </span>
              <span style={{ color: "#64748b", marginLeft: "auto" }}>
                {m.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DetailTable({
  title,
  columns,
  rows,
}: {
  title: string;
  columns: string[];
  rows: string[][];
}) {
  return (
    <div style={{ marginTop: 12 }}>
      <h5 style={{ margin: "0 0 6px 0", fontSize: 13, color: "#0f172a" }}>
        {title}
      </h5>
      {rows.length === 0 ? (
        <span style={{ color: "#94a3b8", fontSize: 12 }}>无</span>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "#f1f5f9" }}>
              {columns.map((col) => (
                <th
                  key={col}
                  style={{
                    textAlign: "left",
                    padding: "4px 8px",
                    borderBottom: "1px solid #e2e8f0",
                    color: "#64748b",
                    fontWeight: 600,
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {row.map((cell, cidx) => (
                  <td
                    key={cidx}
                    style={{
                      padding: "4px 8px",
                      borderBottom: "1px solid #f1f5f9",
                      fontFamily: cidx === 1 ? "monospace" : undefined,
                      color: "#334155",
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color: string;
}) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        color: "#fff",
        background: color,
      }}
    >
      {children}
    </span>
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

function typeColor(type: string): string {
  switch (type) {
    case "controller":
      return "#3b82f6";
    case "service":
      return "#22c55e";
    case "mapper":
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

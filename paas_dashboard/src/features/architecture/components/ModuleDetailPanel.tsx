import type { ModuleNodeData } from "../lib/graphBuilder";
import type { CheatSheetComponentItem, CheatSheetMethodItem } from "../../../types/cheatSheet";
import { parseComponentEntry } from "../lib/graphBuilder";
import { ModuleSourceEditor } from "./ModuleSourceEditor";
import "./ModuleDetailPanel.css";

interface ModuleDetailPanelProps {
  isOpen: boolean;
  onClose?: () => void;
  data: ModuleNodeData | null;
  components?: CheatSheetComponentItem[];
  selectedComponentId?: string | null;
  selectedMethod?: { componentId: string; methodName: string } | null;
  onSelectComponent?: (componentId: string) => void;
  onSelectMethod?: (method: { componentId: string; methodName: string } | null) => void;
  onModuleChanged?: () => void;
  onModuleDeleted?: () => void;
}

function PanelHeader({
  title,
  onClose,
}: {
  title: string;
  onClose?: () => void;
}) {
  return (
    <div className="module-detail-panel__header">
      <h3 className="module-detail-panel__title">{title}</h3>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="关闭"
          className="module-detail-panel__close"
        >
          ✕
        </button>
      )}
    </div>
  );
}

export function ModuleDetailPanel({
  isOpen,
  onClose,
  data,
  components = [],
  selectedComponentId,
  selectedMethod,
  onSelectComponent,
  onSelectMethod,
  onModuleChanged,
  onModuleDeleted,
}: ModuleDetailPanelProps) {
  const isFailed = data?.status === "failed";

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
    <div className={`module-detail-panel ${isOpen ? "module-detail-panel--open" : ""}`}>
      <div className="module-detail-panel__inner">
        {!isOpen || !data ? (
          <>
            <PanelHeader title="详情面板" onClose={onClose} />
            <p className="module-detail-panel__empty">点击画布上的节点查看详细信息</p>
          </>
        ) : (
          <>
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
              <PanelHeader title={data.label} onClose={onClose} />
              <span
                className={`module-detail-panel__status ${
                  isFailed ? "module-detail-panel__status--failed" : "module-detail-panel__status--ok"
                }`}
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
                      <div className="module-detail-panel__component-type">{type}</div>
                      {entries.map((entry) => {
                        const { name } = parseComponentEntry(entry);
                        const componentId = `${data.label}::${type}::${name}`;
                        const isSelected = selectedComponentId === componentId;

                        return (
                          <div
                            key={entry}
                            onClick={() => onSelectComponent?.(componentId)}
                            className={`module-detail-panel__component-item ${
                              isSelected ? "module-detail-panel__component-item--selected" : ""
                            }`}
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
                    <span className="module-detail-panel__empty">暂无 API</span>
                  ) : (
                    data.apiList.map((api) => (
                      <div key={`${api.method}${api.path}`} className="module-detail-panel__api-row">
                        <span
                          className="module-detail-panel__api-method"
                          style={{ background: methodColor(api.method) }}
                        >
                          {api.method}
                        </span>
                        <span className="module-detail-panel__api-path">{api.path}</span>
                      </div>
                    ))
                  )}
                </Section>
                <Section title="源码管理">
                  <ModuleSourceEditor
                    pluginName={data.label}
                    onChanged={onModuleChanged}
                    onDeleted={onModuleDeleted}
                  />
                </Section>
              </>
            )}

            {isFailed && data.error && (
              <Section title="错误信息">
                <div className="module-detail-panel__error-box">{data.error}</div>
              </Section>
            )}
          </>
        )}
      </div>
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
    <div className="module-detail-panel__card">
      <div className="module-detail-panel__card-header">
        <h4 className="module-detail-panel__card-title">{method.feature || method.name}</h4>
        <button onClick={onBack} className="module-detail-panel__back-btn">
          返回模块
        </button>
      </div>

      <div className="module-detail-panel__badges">
        <Badge color={typeColor(component.type)}>{component.type}</Badge>
        <Badge color="#64748b">{component.module}</Badge>
        <Badge color="#3b82f6">{component.name}</Badge>
      </div>

      {component.type === "controller" && method.http_method && (
        <div className="module-detail-panel__http-row">
          <span
            className="module-detail-panel__http-method"
            style={{ background: methodColor(method.http_method) }}
          >
            {method.http_method}
          </span>
          <span className="module-detail-panel__http-path">{method.path}</span>
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
          <h5 className="module-detail-panel__sub-title">SQL</h5>
          <pre className="module-detail-panel__pre">{method.sql}</pre>
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
    <div className="module-detail-panel__card">
      <div className="module-detail-panel__card-header">
        <h4 className="module-detail-panel__card-title">{component.name}</h4>
        <button onClick={onBack} className="module-detail-panel__back-btn">
          返回模块
        </button>
      </div>

      <div className="module-detail-panel__badges">
        <Badge color={typeColor(component.type)}>{component.type}</Badge>
        <Badge color="#64748b">{component.module}</Badge>
        <Badge color={component.assembled ? "#22c55e" : "#ef4444"}>
          {component.assembled ? "已组装" : "未组装"}
        </Badge>
      </div>

      {component.base_path && (
        <div className="module-detail-panel__meta">base_path: {component.base_path}</div>
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
          <h5 className="module-detail-panel__sub-title">HTTP 方法</h5>
          {component.methods.map((m) => (
            <div
              key={`${m.http_method}${m.path}${m.name}`}
              className="module-detail-panel__http-list-row"
            >
              <span
                className="module-detail-panel__http-list-method"
                style={{ background: methodColor(m.http_method || "") }}
              >
                {m.http_method || ""}
              </span>
              <span className="module-detail-panel__http-list-path">{m.path}</span>
              <span className="module-detail-panel__http-list-name">{m.name}</span>
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
      <h5 className="module-detail-panel__sub-title">{title}</h5>
      {rows.length === 0 ? (
        <span className="module-detail-panel__empty">无</span>
      ) : (
        <table className="module-detail-panel__table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {row.map((cell, cidx) => (
                  <td
                    key={cidx}
                    className={cidx === 1 ? "module-detail-panel__table-cell--mono" : undefined}
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
    <span className="module-detail-panel__badge" style={{ background: color }}>
      {children}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="module-detail-panel__section">
      <h4 className="module-detail-panel__section-title">{title}</h4>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="module-detail-panel__stat">
      <span className="module-detail-panel__stat-label">{label}</span>
      <span className="module-detail-panel__stat-value">{value}</span>
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

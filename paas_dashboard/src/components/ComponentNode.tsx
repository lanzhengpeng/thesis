import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ComponentNodeData, ComponentType } from "../lib/graphBuilder";
import {
  COMPONENT_HEADER_HEIGHT,
  COMPONENT_PADDING,
  MAPPER_METHOD_ROW_HEIGHT,
  METHOD_ROW_HEIGHT,
} from "../lib/graphBuilder";

const TYPE_STYLES: Record<
  ComponentNodeData["componentType"],
  { background: string; border: string; color: string }
> = {
  controller: {
    background: "#eff6ff",
    border: "#3b82f6",
    color: "#1d4ed8",
  },
  service: {
    background: "#f0fdf4",
    border: "#22c55e",
    color: "#15803d",
  },
  mapper: {
    background: "#faf5ff",
    border: "#8b5cf6",
    color: "#7e22ce",
  },
};

const METHOD_COLORS: Record<ComponentNodeData["componentType"], string> = {
  controller: "#3b82f6",
  service: "#22c55e",
  mapper: "#8b5cf6",
};

export function ComponentNode(props: NodeProps) {
  const data = props.data as ComponentNodeData;
  const styles = TYPE_STYLES[data.componentType];
  const methods = data.methods || [];

  const methodHeights =
    data.methodHeights ||
    methods.map(() =>
      data.componentType === "mapper" ? MAPPER_METHOD_ROW_HEIGHT : METHOD_ROW_HEIGHT
    );

  // 计算每个方法行左右 handle 的垂直中心位置
  let cursorY = COMPONENT_HEADER_HEIGHT + COMPONENT_PADDING;
  const handleTops = methods.map((_, index) => {
    const h = methodHeights[index] ?? METHOD_ROW_HEIGHT;
    const top = cursorY + h / 2;
    cursorY += h;
    return top;
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        borderRadius: 12,
        background: styles.background,
        border: `2px solid ${styles.border}`,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        overflow: "visible",
        boxShadow: "0 6px 18px rgba(0, 0, 0, 0.12)",
        position: "relative",
      }}
    >
      {methods.map((method, index) => {
        const top = handleTops[index] - 4;
        const color = METHOD_COLORS[data.componentType];
        return (
          <span key={`handles-${method.name}`}>
            <Handle
              type="target"
              position={Position.Left}
              id={`method-${method.name}-left`}
              style={{
                ...handleStyle(color),
                top,
                left: -6,
              }}
            />
            <Handle
              type="source"
              position={Position.Right}
              id={`method-${method.name}-right`}
              style={{
                ...handleStyle(color),
                top,
                right: -6,
              }}
            />
          </span>
        );
      })}

      <div
        style={{
          height: COMPONENT_HEADER_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: `0 ${COMPONENT_PADDING}px`,
          borderBottom: `1px solid ${styles.border}33`,
          background: `${styles.border}15`,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: styles.color,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {data.label}
        </span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: "uppercase",
            color: "#fff",
            background: styles.border,
            padding: "3px 7px",
            borderRadius: 4,
            flexShrink: 0,
          }}
        >
          {data.componentType}
        </span>
      </div>

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: `10px ${COMPONENT_PADDING}px 14px`,
          gap: 4,
        }}
      >
        {methods.map((method, index) => (
          <MethodRow
            key={method.name}
            method={method}
            componentType={data.componentType}
            height={methodHeights[index] ?? METHOD_ROW_HEIGHT}
          />
        ))}
      </div>
    </div>
  );
}

function MethodRow({
  method,
  componentType,
  height,
}: {
  method: ComponentNodeData["methods"][number];
  componentType: ComponentType;
  height: number;
}) {
  const signature = `${method.name}(${method.params.join(", ")})`;

  return (
    <div
      style={{
        height,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 4,
        borderBottom: "1px solid #e2e8f033",
        padding: "4px 0",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 12,
          color: "#334155",
          fontFamily: "monospace",
          minHeight: 20,
        }}
      >
        {method.http_method && (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "#fff",
              background: methodColor(method.http_method),
              padding: "2px 6px",
              borderRadius: 4,
              flexShrink: 0,
            }}
          >
            {method.http_method}
          </span>
        )}
        {method.path && (
          <span
            style={{
              fontSize: 11,
              color: "#64748b",
              flexShrink: 0,
              maxWidth: 140,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {method.path}
          </span>
        )}
        <span
          style={{
            fontWeight: 600,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {signature}
        </span>
      </div>

      {componentType === "mapper" && method.sql && (
        <pre
          style={{
            margin: 0,
            fontSize: 10,
            color: "#7e22ce",
            background: "#f3e8ff",
            padding: "4px 8px",
            borderRadius: 4,
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            overflow: "auto",
            maxHeight: Math.max(24, height - 32),
          }}
        >
          {method.sql}
        </pre>
      )}
    </div>
  );
}

function handleStyle(color: string): React.CSSProperties {
  return {
    position: "absolute",
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: color,
    border: "2px solid #fff",
    zIndex: 1,
  };
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

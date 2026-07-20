import type { NodeProps } from "@xyflow/react";
import type { ModuleNodeData } from "../lib/graphBuilder";

export function GatewayNode(props: NodeProps) {
  const data = props.data as ModuleNodeData;

  return (
    <div
      style={{
        width: 180,
        height: 80,
        borderRadius: 12,
        background: "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
        color: "#f8fafc",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 16,
        fontWeight: 700,
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.2)",
        border: "2px solid #475569",
      }}
    >
      {data.label}
    </div>
  );
}

import { useEffect, useRef } from "react";
import { useApiClient } from "@scalar/api-client-react";
import "@scalar/api-client-react/style.css";
import "./ScalarPanel.css";

const SERVICE_BASE_URL =
  (import.meta.env.VITE_SERVICE_BASE_URL as string | undefined) ||
  "http://localhost:8001";

interface ScalarPanelProps {
  active?: boolean;
}

export function ScalarPanel({ active = false }: ScalarPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const movedRef = useRef(false);

  const client = useApiClient({
    configuration: {
      url: `${SERVICE_BASE_URL}/openapi.json`,
      servers: [{ url: SERVICE_BASE_URL }],
    },
  });

  // 将 Scalar 创建的 DOM 节点移入本组件容器
  useEffect(() => {
    if (!client || movedRef.current) return;

    const moveScalarApp = () => {
      const app = document.querySelector<HTMLElement>(".scalar-app");
      if (!app || !containerRef.current) return;
      if (app.parentElement === containerRef.current) {
        movedRef.current = true;
        return;
      }

      app.style.display = "";
      containerRef.current.appendChild(app);
      movedRef.current = true;
    };

    moveScalarApp();
    const timeout = setTimeout(moveScalarApp, 50);
    const observer = new MutationObserver(moveScalarApp);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      clearTimeout(timeout);
      observer.disconnect();

      // 组件真正卸载时把 scalar app 还回 body 并隐藏
      const app = document.querySelector<HTMLElement>(".scalar-app");
      if (app) {
        app.style.display = "none";
        document.body.appendChild(app);
      }
      movedRef.current = false;
    };
  }, [client]);

  // 根据标签页激活状态打开/关闭 Scalar 客户端
  useEffect(() => {
    if (!client) return;
    if (active) {
      client.open({ path: "/health", method: "get" });
    } else {
      client.modalState.open = false;
    }
  }, [client, active]);

  return <div ref={containerRef} className="scalar-panel" />;
}

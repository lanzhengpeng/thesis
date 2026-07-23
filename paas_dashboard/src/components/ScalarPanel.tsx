import { useEffect, useRef } from "react";
import { useApiClient } from "@scalar/api-client-react";
import "@scalar/api-client-react/style.css";
import "./ScalarPanel.css";

const SERVICE_BASE_URL =
  (import.meta.env.VITE_SERVICE_BASE_URL as string | undefined) ||
  "http://localhost:8001";

export function ScalarPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const movedRef = useRef(false);

  const client = useApiClient({
    configuration: {
      url: `${SERVICE_BASE_URL}/openapi.json`,
      servers: [{ url: SERVICE_BASE_URL }],
    },
  });

  useEffect(() => {
    if (!client || movedRef.current) return;

    client.open({ path: "/health", method: "get" });

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

      // 卸载时把 scalar app 还回 body 并隐藏，这样下次打开可以再次移入容器
      const app = document.querySelector<HTMLElement>(".scalar-app");
      if (app) {
        app.style.display = "none";
        document.body.appendChild(app);
      }
      movedRef.current = false;
    };
  }, [client]);

  return <div ref={containerRef} className="scalar-panel" />;
}

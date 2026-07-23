import { useEffect, useRef } from "react";
import { useApiClient } from "@scalar/api-client-react";
import "@scalar/api-client-react/style.css";
import "./ScalarPanel.css";

export function ScalarPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const movedRef = useRef(false);

  const client = useApiClient({
    configuration: {
      url: "/openapi.json",
      servers: [{ url: "/" }],
    },
  });

  useEffect(() => {
    if (!client || movedRef.current) return;

    client.open({ path: "/health", method: "get" });

    const moveScalarApp = () => {
      const app = document.querySelector<HTMLElement>(".scalar-app");
      if (!app || !containerRef.current) return;
      if (app.parentElement === containerRef.current) return;

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
    };
  }, [client]);

  return <div ref={containerRef} className="scalar-panel" />;
}

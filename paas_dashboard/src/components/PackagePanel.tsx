import { useEffect, useRef, useState } from "react";
import { Box, CheckCircle, Download, Loader2, Package, XCircle } from "lucide-react";
import {
  fetchPackageJob,
  getPackageDownloadUrl,
  triggerPackageBuild,
  type PackageJobResponse,
} from "../services/api";
import "./PackagePanel.css";

export function PackagePanel() {
  const [job, setJob] = useState<PackageJobResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isTerminal = (status: string) =>
    status === "completed" || status === "failed";

  const pollJob = async (jobId: string) => {
    try {
      const data = await fetchPackageJob(jobId);
      setJob(data);
      if (isTerminal(data.status) && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setLoading(false);
    }
  };

  const handleBuild = async () => {
    setLoading(true);
    setError(null);
    setJob(null);

    try {
      const data = await triggerPackageBuild("current");
      setJob({
        job_id: data.job_id,
        target: "current",
        status: data.status,
        artifact_path: data.artifact_path,
        created_at: new Date().toISOString(),
        completed_at: null,
        error: null,
        log: [],
      });

      intervalRef.current = setInterval(() => {
        pollJob(data.job_id);
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const canDownload = job?.status === "completed" && job.artifact_path;

  return (
    <div className="package-panel">
      <div className="package-panel__content">
        <div className="package-panel__header">
          <div className="package-panel__icon">
            <Package size={32} />
          </div>
          <h2 className="package-panel__title">打包服务口</h2>
          <p className="package-panel__desc">
            将 8001 业务口打包为单文件可执行程序，产物可在对应操作系统上直接运行。
          </p>
        </div>

        <button
          type="button"
          className="package-panel__build-btn"
          onClick={handleBuild}
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 size={18} className="package-panel__spin" />
              正在打包…
            </>
          ) : (
            <>
              <Box size={18} />
              开始打包
            </>
          )}
        </button>

        {error && (
          <div className="package-panel__alert package-panel__alert--error">
            <XCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {job && (
          <div className="package-panel__status">
            <div className="package-panel__status-row">
              <span className="package-panel__status-label">任务 ID</span>
              <span className="package-panel__status-value">{job.job_id}</span>
            </div>
            <div className="package-panel__status-row">
              <span className="package-panel__status-label">状态</span>
              <span className={`package-panel__status-badge package-panel__status-badge--${job.status}`}>
                {job.status === "completed" && <CheckCircle size={14} />}
                {job.status === "failed" && <XCircle size={14} />}
                {job.status === "building" && <Loader2 size={14} className="package-panel__spin" />}
                {job.status}
              </span>
            </div>
          </div>
        )}

        {canDownload && (
          <a
            href={getPackageDownloadUrl(job.job_id)}
            download
            className="package-panel__download-btn"
          >
            <Download size={18} />
            下载产物
          </a>
        )}

        {job && job.log.length > 0 && (
          <div className="package-panel__log">
            <div className="package-panel__log-header">构建日志</div>
            <pre className="package-panel__log-body">
              {job.log.join("\n")}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Clock3,
  Download,
  FileDown,
  History,
  LoaderCircle,
  Play,
  RefreshCw,
  Search,
  Sparkles,
  Users,
} from "lucide-react";

import {
  createAnalysis,
  createDownload,
  createExport,
  getErrorMessage,
  getHistory,
  getTask,
  resolveAssetUrl,
} from "./api";


const KeywordChart = lazy(() => import("./components/Charts").then((module) => ({
  default: module.KeywordChart,
})));
const TimelineChart = lazy(() => import("./components/Charts").then((module) => ({
  default: module.TimelineChart,
})));


const initialOptions = {
  top_n: 20,
  bucket_seconds: 10,
  window_seconds: 3,
  peak_count: 5,
};

function formatTime(totalSeconds = 0) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 })
    .format(Number(value || 0));
}

function Metric({ icon: Icon, label, value, accent }) {
  return (
    <div className="metric">
      <span className={`metric-icon ${accent}`}><Icon size={18} /></span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function App() {
  const [url, setUrl] = useState("");
  const [options, setOptions] = useState(initialOptions);
  const [task, setTask] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await getHistory());
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const pollTask = useCallback(async (taskId) => {
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const nextTask = await getTask(taskId);
      setTask(nextTask);
      if (nextTask.status === "success") return nextTask;
      if (nextTask.status === "failed") throw new Error(nextTask.error);
      await new Promise((resolve) => window.setTimeout(resolve, 1_000));
    }
    throw new Error("任务处理超时，请稍后在历史记录中查看");
  }, []);

  const handleAnalyze = async (event) => {
    event.preventDefault();
    setError("");
    setResult(null);
    setBusyAction("analysis");
    try {
      const createdTask = await createAnalysis({ url, ...options });
      setTask(createdTask);
      const completedTask = createdTask.status === "success"
        ? createdTask
        : await pollTask(createdTask.id);
      setResult(completedTask.result);
      await loadHistory();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyAction("");
    }
  };

  const handleExport = async () => {
    if (!result?.video?.id) return;
    setBusyAction("export");
    setError("");
    try {
      const exported = await createExport(result.video.id);
      window.open(resolveAssetUrl(exported.file_url), "_blank", "noopener,noreferrer");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyAction("");
    }
  };

  const handleDownload = async () => {
    if (!result?.video?.url) return;
    setBusyAction("download");
    setError("");
    try {
      const createdTask = await createDownload(result.video.url);
      const completedTask = createdTask.status === "success"
        ? createdTask
        : await pollTask(createdTask.id);
      window.open(resolveAssetUrl(completedTask.file_url), "_blank", "noopener,noreferrer");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyAction("");
    }
  };

  const video = result?.video;
  const analysis = result?.analysis;
  const metadata = video?.metadata || {};
  const peak = analysis?.peak_segments?.[0];
  const progress = task?.status === "success" ? 100 : task?.progress || 0;
  const taskActive = busyAction === "analysis" && task && !["success", "failed"].includes(task.status);

  const metricItems = useMemo(() => {
    if (!analysis) return [];
    return [
      { icon: Activity, label: "分析弹幕", value: formatNumber(analysis.total_danmaku), accent: "cyan" },
      { icon: BarChart3, label: "分钟均值", value: analysis.metrics.average_per_minute, accent: "pink" },
      { icon: Sparkles, label: "峰值密度", value: `${analysis.metrics.peak_per_second}/s`, accent: "green" },
      { icon: Users, label: "视频播放", value: formatNumber(metadata.views), accent: "gold" },
    ];
  }, [analysis, metadata.views]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img src="/img/about.png" alt="" />
          <div>
            <strong>Bili Danmaku Insight</strong>
            <span>弹幕洞察工作台</span>
          </div>
        </div>
        <a className="github-link" href="https://github.com/burtshann/bili-danmaku-insight" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </header>

      <main>
        <section className="query-band" aria-labelledby="query-title">
          <div className="section-heading">
            <div>
              <span className="eyebrow">NEW ANALYSIS</span>
              <h1 id="query-title">分析 Bilibili 视频弹幕</h1>
            </div>
            <span className="api-status"><i /> API v1</span>
          </div>

          <form className="analysis-form" onSubmit={handleAnalyze}>
            <label className="url-field">
              <Search size={19} />
              <span className="sr-only">Bilibili 视频链接或 BV 号</span>
              <input
                type="text"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="粘贴视频链接或输入 BV 号"
                required
                disabled={busyAction === "analysis"}
              />
            </label>
            <button className="primary-button" type="submit" disabled={Boolean(busyAction)}>
              {busyAction === "analysis" ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
              {busyAction === "analysis" ? "分析中" : "开始分析"}
            </button>
          </form>

          <details className="advanced-options">
            <summary>分析参数</summary>
            <div className="option-grid">
              {[
                ["top_n", "关键词数量", 5, 50],
                ["bucket_seconds", "时间桶（秒）", 5, 60],
                ["window_seconds", "峰值窗口（秒）", 1, 15],
                ["peak_count", "精彩片段数量", 1, 10],
              ].map(([key, label, min, max]) => (
                <label key={key}>
                  <span>{label}</span>
                  <input
                    type="number"
                    min={min}
                    max={max}
                    value={options[key]}
                    onChange={(event) => setOptions((current) => ({
                      ...current,
                      [key]: Number(event.target.value),
                    }))}
                  />
                </label>
              ))}
            </div>
          </details>

          {taskActive && (
            <div className="progress-row" role="status">
              <span>任务处理中</span>
              <div className="progress-track"><i style={{ width: `${progress}%` }} /></div>
              <strong>{progress}%</strong>
            </div>
          )}
          {error && <div className="error-banner" role="alert">{error}</div>}
        </section>

        {analysis ? (
          <>
            <section className="video-strip">
              <div className="video-identity">
                {video.cover_url ? <img src={video.cover_url} alt="" /> : <div className="cover-placeholder"><Play /></div>}
                <div>
                  <span>{video.bvid}</span>
                  <h2>{video.title}</h2>
                  <p>{video.owner_name || "未知 UP 主"} · {formatTime(video.duration_seconds)}</p>
                </div>
              </div>
              <div className="action-row">
                <button className="icon-text-button" type="button" onClick={handleExport} disabled={Boolean(busyAction)}>
                  <FileDown size={17} /> 导出 Excel
                </button>
                <button className="icon-text-button" type="button" onClick={handleDownload} disabled={Boolean(busyAction)}>
                  <Download size={17} /> 下载视频
                </button>
              </div>
            </section>

            <section className="metric-grid" aria-label="核心指标">
              {metricItems.map((item) => <Metric key={item.label} {...item} />)}
            </section>

            <section className="dashboard-grid">
              <article className="panel keyword-panel">
                <div className="panel-title">
                  <div><BarChart3 size={18} /><h3>高频关键词</h3></div>
                  <span>Top {Math.min(10, analysis.top_words.length)}</span>
                </div>
                <Suspense fallback={<div className="chart-loading">图表载入中</div>}>
                  <KeywordChart items={analysis.top_words} />
                </Suspense>
              </article>

              <article className="panel timeline-panel">
                <div className="panel-title">
                  <div><Activity size={18} /><h3>弹幕密度时间轴</h3></div>
                  <span>{analysis.metrics.bucket_seconds}s / 桶</span>
                </div>
                <Suspense fallback={<div className="chart-loading">图表载入中</div>}>
                  <TimelineChart items={analysis.timeline} peaks={analysis.peak_segments} />
                </Suspense>
              </article>

              <article className="panel peaks-panel">
                <div className="panel-title">
                  <div><Sparkles size={18} /><h3>精彩片段</h3></div>
                  <span>{analysis.metrics.window_seconds}s 窗口</span>
                </div>
                <ol className="peak-list">
                  {analysis.peak_segments.map((item, index) => (
                    <li key={`${item.start}-${item.end}`}>
                      <span className="peak-rank">{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <strong>{formatTime(item.start)} - {formatTime(item.end)}</strong>
                        <span>{item.count} 条弹幕</span>
                      </div>
                      {index === 0 && <span className="peak-label">最高峰</span>}
                    </li>
                  ))}
                </ol>
              </article>
            </section>
          </>
        ) : (
          <section className="empty-state">
            <div className="empty-mark"><Activity size={28} /></div>
            <h2>等待首次分析</h2>
            <p>关键词、密度时间轴与精彩片段将在这里呈现。</p>
          </section>
        )}

        <section className="history-section">
          <div className="panel-title history-title">
            <div><History size={18} /><h3>最近分析</h3></div>
            <button className="icon-button" type="button" onClick={loadHistory} title="刷新历史记录">
              <RefreshCw size={17} />
            </button>
          </div>
          {history.length ? (
            <div className="history-list">
              {history.map((item) => (
                <button
                  className="history-item"
                  key={item.video.id}
                  type="button"
                  onClick={() => {
                    setResult(item);
                    setUrl(item.video.url);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  <span className="history-cover">
                    {item.video.cover_url ? <img src={item.video.cover_url} alt="" /> : <Play size={18} />}
                  </span>
                  <span className="history-copy">
                    <strong>{item.video.title}</strong>
                    <span>{item.video.owner_name || item.video.bvid}</span>
                  </span>
                  <span className="history-count">{formatNumber(item.analysis.total_danmaku)} 条</span>
                  <Clock3 size={16} />
                </button>
              ))}
            </div>
          ) : (
            <p className="history-empty">暂无分析记录</p>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;

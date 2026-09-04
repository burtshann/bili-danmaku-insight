import axios from "axios";


const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const client = axios.create({
  baseURL,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  withXSRFToken: true,
  timeout: 30_000,
});

let csrfReady = false;

async function ensureCsrf() {
  if (!csrfReady) {
    await client.get("/api/v1/csrf/");
    csrfReady = true;
  }
}

export async function createAnalysis(payload) {
  await ensureCsrf();
  return (await client.post("/api/v1/analyses/", payload)).data.task;
}

export async function getTask(taskId) {
  return (await client.get(`/api/v1/tasks/${taskId}/`)).data.task;
}

export async function getHistory(limit = 12) {
  return (await client.get("/api/v1/analyses/history/", { params: { limit } })).data.items;
}

export async function createExport(videoId) {
  await ensureCsrf();
  return (await client.post("/api/v1/exports/", { video_id: videoId })).data.export;
}

export async function createDownload(url) {
  await ensureCsrf();
  return (await client.post("/api/v1/downloads/", { url })).data.task;
}

export function resolveAssetUrl(path) {
  if (!path) return "";
  return new URL(path, baseURL || window.location.origin).toString();
}

export function getErrorMessage(error) {
  return (
    error?.response?.data?.error
    || error?.message
    || "请求失败，请稍后重试"
  );
}

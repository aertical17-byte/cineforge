/** Typed fetch client for the CineForge API (bearer JWT; no provider keys ever reach the browser). */
import {useAuthStore} from "./store";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(`API ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export async function jsonApi<T = unknown>(path: string, method: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {Accept: "application/json"};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = useAuthStore.getState().token;
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }).catch((): never => {
    throw new ApiError(0, "network error");
  });
  return parse<T>(res);
}

async function parse<T>(res: Response): Promise<T> {
  const type = res.headers.get("content-type") || "";
  const payload = type.includes("json") ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as Record<string, unknown>).detail : payload;
    throw new ApiError(res.status, detail ?? res.statusText);
  }
  return payload as T;
}

export async function rawUpload(path: string, file: File, purpose = "reference"): Promise<Response> {
  const fd = new FormData();
  fd.append("file", file);
  const token = useAuthStore.getState().token;
  return fetch(`${API_URL}${path}?purpose=${purpose}`, {
    method: "POST",
    headers: {Accept: "application/json", Authorization: `Bearer ${token}`},
    body: fd,
  });
}

/**
 * Resolve an asset media URL for the <img>/<video>/<a> src.
 * Local/CI storage returns app-relative "/files/…" paths — those must point at the
 * API origin (the web app cannot serve them). S3/CDN returns absolute URLs untouched.
 */
export function assetSrc(url: string): string {
  return url.startsWith("/") ? `${API_URL}${url}` : url;
}

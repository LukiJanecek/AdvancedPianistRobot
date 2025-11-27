// utils/api.ts
import { SERVER_URL } from "../constants/config";

export async function apiGet(path: string) {
  const res = await fetch(`${SERVER_URL}${path}`, { credentials: "include" });
  return parseOrThrow(res);
}

export async function apiPost(path: string, body?: any) {
  const res = await fetch(`${SERVER_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body ?? {}),
  });
  return parseOrThrow(res);
}

type HttpError = Error & {
  status?: number;
  body?: any;
};

async function parseOrThrow(res: Response) {
  const text = await res.text();

  if (!res.ok) {
    let body: any = null;
    let message = text || `HTTP ${res.status}`;

    try {
      body = text ? JSON.parse(text) : null;
      if (body?.detail) message = body.detail;
      else if (body?.message) message = body.message;
    } catch {
      // text není JSON, necháme default message
    }

    const err: HttpError = new Error(message);
    err.status = res.status;
    err.body = body;
    throw err;
  }

  return text ? JSON.parse(text) : null;
}

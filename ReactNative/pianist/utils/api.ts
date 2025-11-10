import {SERVER_URL} from "../constants/config";

export async function apiGet(path : string) {
  const res = await fetch(`${SERVER_URL}${path}`, { credentials: 'include' });
  return parseOrThrow(res);
}

export async function apiPost(path : string, body : any) {
  const res = await fetch(`${SERVER_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body ?? {}),
  });
  return parseOrThrow(res);
}

async function parseOrThrow(res : Response) {
  const text = await res.text();
  if (!res.ok) {
    try {
      const j = JSON.parse(text);
      throw new Error(j.message || JSON.stringify(j));
    } catch {
      throw new Error(text || `HTTP ${res.status}`);
    }
  }
  return text ? JSON.parse(text) : null;
}
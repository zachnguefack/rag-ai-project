const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

type RequestOptions = RequestInit & { auth?: boolean };

class HttpError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, payload: unknown) {
    const detail = typeof payload === 'object' && payload && 'detail' in payload ? String((payload as { detail: unknown }).detail) : `Request failed with status ${status}`;
    super(detail);
    this.status = status;
    this.payload = payload;
  }
}

export const tokenStorage = {
  get: () => localStorage.getItem('admin_token'),
  set: (token: string) => localStorage.setItem('admin_token', token),
  clear: () => localStorage.removeItem('admin_token'),
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', options.body instanceof FormData ? '' : 'application/json');
  if (options.body instanceof FormData) {
    headers.delete('Content-Type');
  }
  if (API_KEY) headers.set('x-api-key', API_KEY);
  if (options.auth !== false) {
    const token = tokenStorage.get();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (res.status === 204) return undefined as T;
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new HttpError(res.status, payload);
  return payload as T;
}

export { HttpError, API_BASE_URL };

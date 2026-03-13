import { apiRequest } from './client';

export const documentsApi = {
  list: (limit = 25, offset = 0) => apiRequest<any>(`/documents?limit=${limit}&offset=${offset}`),
  search: (query: string, limit = 25, offset = 0) => apiRequest<any>(`/documents/search?query=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`),
  detail: (id: string) => apiRequest<any>(`/documents/${id}`),
  metadata: (id: string) => apiRequest<any>(`/documents/${id}/metadata`),
  content: (id: string) => apiRequest<any>(`/documents/${id}/content`),
  acl: (id: string) => apiRequest<any>(`/documents/${id}/acl`),
  access: (id: string) => apiRequest<any>(`/documents/${id}/access`),
  versions: (id: string) => apiRequest<any>(`/documents/${id}/versions`),
  index: (force_reindex = false) => apiRequest<any>('/documents/index', { method: 'POST', body: JSON.stringify({ force_reindex }) }),
};

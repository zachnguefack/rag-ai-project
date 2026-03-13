import { apiRequest } from './client';

export const ragApi = {
  query: (payload: any) => apiRequest<any>('/rag/query', { method: 'POST', body: JSON.stringify(payload) }),
  chatAsk: (payload: any) => apiRequest<any>('/chat/ask', { method: 'POST', body: JSON.stringify(payload) }),
};

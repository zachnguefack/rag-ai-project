import { apiRequest } from './client';
import type { AuthTokenResponse, MeResponse } from '../../types/api';

export const authApi = {
  login: (username: string, password: string) => apiRequest<AuthTokenResponse>('/auth/login', { method: 'POST', auth: false, body: JSON.stringify({ username, password }) }),
  logout: () => apiRequest<{ message: string }>('/auth/logout', { method: 'POST' }),
  me: () => apiRequest<MeResponse>('/auth/me'),
};

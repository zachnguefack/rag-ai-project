import { apiRequest } from './client';

export const systemApi = {
  health: () => apiRequest<any>('/health', { auth: false }),
};

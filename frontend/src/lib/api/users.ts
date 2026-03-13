import { apiRequest } from './client';
import type { MeResponse, UserPermissionsResponse } from '../../types/api';

export const usersApi = {
  me: () => apiRequest<MeResponse>('/users/me'),
  permissions: () => apiRequest<UserPermissionsResponse>('/users/permissions'),
};

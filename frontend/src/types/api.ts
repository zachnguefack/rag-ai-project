export type ApiError = { detail?: string; message?: string };

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
};

export type MeResponse = {
  user_id: string;
  username: string;
  email: string;
  is_active: boolean;
  department_id: string;
  department_ids: string[];
  roles: string[];
};

export type UserPermissionsResponse = {
  permissions: string[];
  roles: string[];
};

export type ListResponse<T> = {
  items: T[];
  count: number;
  total: number;
  limit: number;
  offset: number;
};

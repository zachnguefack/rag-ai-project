import { apiRequest } from './client';

export const adminApi = {
  users: () => apiRequest<any>('/admin/users'),
  userDetail: (id: string) => apiRequest<any>(`/admin/users/${id}`),
  userRoles: (id: string) => apiRequest<any>(`/admin/users/${id}/roles`),
  addUserRole: (id: string, role: string) => apiRequest<any>(`/admin/users/${id}/roles/${role}`, { method: 'POST' }),
  removeUserRole: (id: string, role: string) => apiRequest<any>(`/admin/users/${id}/roles/${role}`, { method: 'DELETE' }),
  userDepartments: (id: string) => apiRequest<any>(`/admin/users/${id}/departments`),
  addUserDepartment: (id: string, deptId: string) => apiRequest<any>(`/admin/users/${id}/departments/${deptId}`, { method: 'POST' }),
  removeUserDepartment: (id: string, deptId: string) => apiRequest<any>(`/admin/users/${id}/departments/${deptId}`, { method: 'DELETE' }),
  userDocAccess: (id: string) => apiRequest<any>(`/admin/users/${id}/document-access`),
  grantDocAccess: (id: string, document_id: string) => apiRequest<any>(`/admin/users/${id}/document-access`, { method: 'POST', body: JSON.stringify({ document_id }) }),
  revokeDocAccess: (id: string, documentId: string) => apiRequest<any>(`/admin/users/${id}/document-access/${documentId}`, { method: 'DELETE' }),
  userDocumentScope: (id: string) => apiRequest<any>(`/admin/users/${id}/document-scope`),
  departments: () => apiRequest<any[]>('/admin/departments'),
  createDepartment: (payload: { department_id: string; name: string; description?: string }) => apiRequest<any>('/admin/departments', { method: 'POST', body: JSON.stringify(payload) }),
  department: (id: string) => apiRequest<any>(`/admin/departments/${id}`),
  departmentUsers: (id: string) => apiRequest<any>(`/admin/departments/${id}/users`),
  departmentDocuments: (id: string) => apiRequest<any>(`/admin/departments/${id}/documents`),
  departmentFiles: (id: string) => apiRequest<any>(`/admin/departments/${id}/files`),
  deleteDepartmentFile: (id: string, filename: string) => apiRequest<any>(`/admin/departments/${id}/files/${filename}`, { method: 'DELETE' }),
  uploadDepartmentFile: (id: string, files: File | File[]) => {
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];
    for (const file of fileArray) {
      formData.append('files', file);
    }
    return apiRequest<any>(`/admin/departments/${id}/upload`, { method: 'POST', body: formData });
  },
  ingestFilePath: (id: string, file_path: string) => apiRequest<any>(`/admin/departments/${id}/ingest-file-path`, { method: 'POST', body: JSON.stringify({ file_path }) }),
  ingestFolderPath: (id: string, folder_path: string) => apiRequest<any>(`/admin/departments/${id}/ingest-folder-path`, { method: 'POST', body: JSON.stringify({ folder_path }) }),
  roles: () => apiRequest<any>('/admin/roles'),
  roleDetail: (role: string) => apiRequest<any>(`/admin/roles/${role}`),
  permissions: () => apiRequest<any>('/admin/permissions'),
  rbacMatrix: () => apiRequest<any>('/admin/rbac/matrix'),
  validatePermission: (payload: any) => apiRequest<any>('/admin/rbac/validate', { method: 'POST', body: JSON.stringify(payload) }),
  setRolePermissions: (role: string, permissions: string[]) => apiRequest<any>(`/admin/roles/${role}/permissions`, { method: 'PUT', body: JSON.stringify({ permissions }) }),
  adminDocuments: () => apiRequest<any>('/admin/documents'),
  adminDocumentDetail: (id: string) => apiRequest<any>(`/admin/documents/${id}`),
  setDocumentDepartment: (id: string, department_id: string) => apiRequest<any>(`/admin/documents/${id}/department`, { method: 'PUT', body: JSON.stringify({ department_id }) }),
  documentAudit: (id: string) => apiRequest<any>(`/admin/documents/${id}/audit`),
  auditLogs: (limit = 25, offset = 0) => apiRequest<any>(`/admin/audit-logs?limit=${limit}&offset=${offset}`),
  auditLogDetail: (eventId: string) => apiRequest<any>(`/admin/audit-logs/${eventId}`),
};

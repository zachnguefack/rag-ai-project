import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import { AuditPage } from './pages/AuditPage';
import { DashboardPage } from './pages/DashboardPage';
import { DepartmentDetailPage } from './pages/DepartmentDetailPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { DocumentDetailPage } from './pages/DocumentDetailPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { LoginPage } from './pages/LoginPage';
import { ProfilePage } from './pages/ProfilePage';
import { RagPage } from './pages/RagPage';
import { RbacPage } from './pages/RbacPage';
import { SystemPage } from './pages/SystemPage';
import { UploadPage } from './pages/UploadPage';
import { UserDetailPage } from './pages/UserDetailPage';
import { UsersPage } from './pages/UsersPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="users/:userId" element={<UserDetailPage />} />
        <Route path="departments" element={<DepartmentsPage />} />
        <Route path="departments/:departmentId" element={<DepartmentDetailPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="documents/:documentId" element={<DocumentDetailPage />} />
        <Route path="rbac" element={<RbacPage />} />
        <Route path="rag" element={<RagPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="system" element={<SystemPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

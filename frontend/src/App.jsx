import React from 'react';
import { RouterProvider, createBrowserRouter, Navigate, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

import DashboardLayout from './components/DashboardLayout';
import Dashboard from './pages/Dashboard';
import ApiSettings from './pages/ApiSettings';
import MediaLibraryPage from './pages/MediaLibraryPage';
import ContactsPage from './pages/ContactsPage';
import Conversation from './pages/Conversation';
import LoginPage from './pages/LoginPage';
import InstallationRequestsPage from './pages/InstallationRequestsPage';
import OrdersPage from './pages/OrdersPage';
import SiteAssessmentsPage from './pages/SiteAssessmentsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ProductsPage from './pages/ProductsPage';

const NotFoundPage = () => (
  <div className="p-10 text-center">
    <h1 className="text-3xl font-bold text-red-600 dark:text-red-400">404 - Page Not Found</h1>
    <p className="mt-4 text-gray-700 dark:text-gray-300">The page you are looking for does not exist.</p>
    <Link
      to="/dashboard"
      className="mt-6 inline-block px-6 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
    >
      Go to Dashboard
    </Link>
  </div>
);

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'api-settings', element: <ApiSettings /> },
      { path: 'media-library', element: <MediaLibraryPage /> },
      { path: 'contacts', element: <ContactsPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'installation-requests', element: <InstallationRequestsPage /> },
      { path: 'orders', element: <OrdersPage /> },
      { path: 'site-assessments', element: <SiteAssessmentsPage /> },
      { path: 'conversation', element: <Conversation /> },
      { path: 'products', element: <ProductsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}

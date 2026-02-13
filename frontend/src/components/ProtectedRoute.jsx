import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Skeleton } from '@/components/ui/skeleton';
import { FiLoader } from 'react-icons/fi';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <FiLoader className="h-12 w-12 animate-spin text-primary mb-6" />
        <p className="text-lg text-foreground mb-2">Authenticating...</p>
        <div className="w-full max-w-sm space-y-3">
          <Skeleton className="h-8 w-full rounded-md" />
          <Skeleton className="h-8 w-3/4 rounded-md" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

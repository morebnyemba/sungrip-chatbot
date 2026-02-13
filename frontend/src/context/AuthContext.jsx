import React, { createContext, useContext, useEffect, useCallback } from 'react';
import { useAtom } from 'jotai';
import { toast } from 'sonner';
import { jwtDecode } from 'jwt-decode';

import apiClient from '@/lib/api';
import { authService } from '../services/auth';
import {
  userAtom,
  accessTokenAtom,
  refreshTokenAtom,
  isAuthenticatedAtom,
  isLoadingAuthAtom,
} from '../atoms/authAtoms';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useAtom(userAtom);
  const [accessToken, setAccessToken] = useAtom(accessTokenAtom);
  const [, setRefreshToken] = useAtom(refreshTokenAtom);
  const [isAuthenticated] = useAtom(isAuthenticatedAtom);
  const [isLoading, setIsLoading] = useAtom(isLoadingAuthAtom);

  useEffect(() => {
    const token = authService.getAccessToken();
    const refreshToken = authService.getRefreshToken();
    if (token && refreshToken && token !== 'undefined' && refreshToken !== 'undefined') {
      if (typeof token === 'string' && token.split('.').length === 3) {
        try {
          const decodedUser = jwtDecode(token);
          if (decodedUser.exp * 1000 > Date.now()) {
            setAccessToken(token);
            setRefreshToken(refreshToken);
            setUser(decodedUser);
            apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          } else {
            authService.logout(false);
            setAccessToken(null);
            setRefreshToken(null);
            setUser(null);
          }
        } catch (e) {
          authService.logout(false);
          setAccessToken(null);
          setRefreshToken(null);
          setUser(null);
        }
      } else {
        authService.logout(false);
        setAccessToken(null);
        setRefreshToken(null);
        setUser(null);
      }
    } else {
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
    }
    setIsLoading(false);
  }, [setAccessToken, setRefreshToken, setUser, setIsLoading]);

  const login = async (username, password) => {
    const result = await authService.login(username, password);
    if (result.success) {
      const accessToken = result.user ? authService.getAccessToken() : null;
      const refreshToken = authService.getRefreshToken();
      if (!accessToken || !refreshToken) {
        await logout({ showInfoToast: false });
        return { success: false, error: "Login failed due to a configuration issue." };
      }
      setAccessToken(accessToken);
      setRefreshToken(refreshToken);
      setUser(result.user);
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
      return { success: true, user: result.user };
    } else {
      return { success: false, error: result.error };
    }
  };

  const logout = useCallback(async (options = {}) => {
    const { showInfoToast = true } = options;
    await authService.logout(true);
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    delete apiClient.defaults.headers.common['Authorization'];
    if (showInfoToast) {
      toast.info("You have been logged out.");
    }
  }, [setAccessToken, setRefreshToken, setUser]);

  useEffect(() => {
    const handleAuthError = async () => {
      if (authService.getAccessToken()) {
        toast.error("Your session has expired. Please log in again.");
        try {
          await logout({ showInfoToast: false });
        } catch (e) {
          console.error("Error during automated logout:", e);
        }
      }
    };

    window.addEventListener('auth-error', handleAuthError);
    return () => window.removeEventListener('auth-error', handleAuthError);
  }, [logout]);

  const value = {
    user,
    accessToken,
    isAuthenticated,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

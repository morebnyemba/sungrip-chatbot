import { jwtDecode } from 'jwt-decode';
import apiClient from '@/lib/api';

const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

export const authService = {
  storeTokens(accessToken, refreshToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  },
  clearTokens() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem('user');
  },
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),

  async login(username, password) {
    try {
      const response = await apiClient.post('/api/auth/token/', { username, password });
      const { access, refresh } = response.data;
      this.storeTokens(access, refresh);
      const user = jwtDecode(access);
      return { success: true, user };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Login failed. Please check credentials.';
      return { success: false, error: errorMessage };
    }
  },

  async logout(notifyBackend = true) {
    const refreshToken = this.getRefreshToken();
    if (notifyBackend && refreshToken) {
      try {
        await apiClient.post('/api/auth/token/blacklist/', { refresh: refreshToken }, { suppressErrorToast: true });
      } catch (error) {
        console.warn("Could not blacklist token on server.", error);
      }
    }
    this.clearTokens();
  },
};

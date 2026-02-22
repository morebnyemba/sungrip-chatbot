import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://sungripapi.slykertech.co.zw';
const AUTH_ERROR_EVENT = 'auth-error';

// Token keys — must match the keys used in services/auth.js and atoms/authAtoms.js
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const raw = localStorage.getItem(ACCESS_TOKEN_KEY);
  let token = null;
  if (raw && raw !== 'null' && raw !== 'undefined') {
    try { token = JSON.parse(raw); } catch { token = raw; }
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      const rawRefresh = localStorage.getItem(REFRESH_TOKEN_KEY);
      let refreshToken = null;
      if (rawRefresh && rawRefresh !== 'null' && rawRefresh !== 'undefined') {
        try { refreshToken = JSON.parse(rawRefresh); } catch { refreshToken = rawRefresh; }
      }
      if (refreshToken) {
        try {
          if (!refreshPromise) {
            refreshPromise = axios.post(`${API_BASE_URL}/api/auth/token/refresh/`, {
              refresh: refreshToken,
            }).finally(() => { refreshPromise = null; });
          }
          const { data } = await refreshPromise;
          localStorage.setItem(ACCESS_TOKEN_KEY, JSON.stringify(data.access));
          error.config.headers.Authorization = `Bearer ${data.access}`;
          return apiClient(error.config);
        } catch (refreshError) {
          localStorage.removeItem(ACCESS_TOKEN_KEY);
          localStorage.removeItem(REFRESH_TOKEN_KEY);
          localStorage.removeItem('user');
          window.dispatchEvent(new Event(AUTH_ERROR_EVENT));
          return Promise.reject(refreshError);
        }
      } else {
        window.dispatchEvent(new Event(AUTH_ERROR_EVENT));
      }
    }
    return Promise.reject(error);
  }
);

// ─── Dashboard Stats ──────────────────────────────────────────────────────────
export const dashboardStatsApi = {
  get() {
    return apiClient.get('/api/conversations/dashboard-stats/');
  },
};

// ─── Contacts / Conversations ────────────────────────────────────────────────
export const contactsApi = {
  list(params = {}) {
    return apiClient.get('/api/conversations/contacts/', { params });
  },
  get(id) {
    return apiClient.get(`/api/conversations/contacts/${id}/`);
  },
  retrieve(id) {
    return this.get(id);
  },
  update(id, data) {
    return apiClient.patch(`/api/conversations/contacts/${id}/`, data);
  },
  patch(id, data) {
    return this.update(id, data);
  },
  toggleIntervention(id) {
    return apiClient.post(`/api/conversations/contacts/${id}/toggle-intervention/`);
  },
  listMessages(contactId) {
    return apiClient.get(`/api/conversations/contacts/${contactId}/messages/`);
  },
  sendMessage(contactId, text) {
    return apiClient.post(`/api/conversations/contacts/${contactId}/send-message/`, { message: text });
  },
};

// ─── Customers ───────────────────────────────────────────────────────────────
export const customersApi = {
  list(params = {}) {
    return apiClient.get('/api/customers/', { params });
  },
  get(id) {
    return apiClient.get(`/api/customers/${id}/`);
  },
  create(data) {
    return apiClient.post('/api/customers/', data);
  },
  update(id, data) {
    return apiClient.patch(`/api/customers/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/customers/${id}/`);
  },
};

// ─── Orders ──────────────────────────────────────────────────────────────────
export const ordersApi = {
  list(params = {}) {
    return apiClient.get('/api/orders/', { params });
  },
  get(id) {
    return apiClient.get(`/api/orders/${id}/`);
  },
  create(data) {
    return apiClient.post('/api/orders/', data);
  },
  update(id, data) {
    return apiClient.patch(`/api/orders/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/orders/${id}/`);
  },
};

// ─── Product Orders ───────────────────────────────────────────────────────────
export const productOrdersApi = {
  list(params = {}) {
    return apiClient.get('/api/product-orders/', { params });
  },
  get(id) {
    return apiClient.get(`/api/product-orders/${id}/`);
  },
  create(data) {
    return apiClient.post('/api/product-orders/', data);
  },
  update(id, data) {
    return apiClient.patch(`/api/product-orders/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/product-orders/${id}/`);
  },
};

// ─── Installation Requests ────────────────────────────────────────────────────
export const installationRequestsApi = {
  list(params = {}) {
    return apiClient.get('/api/installation-requests/', { params });
  },
  get(id) {
    return apiClient.get(`/api/installation-requests/${id}/`);
  },
  create(data) {
    return apiClient.post('/api/installation-requests/', data);
  },
  update(id, data) {
    return apiClient.patch(`/api/installation-requests/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/installation-requests/${id}/`);
  },
};

// ─── Products ─────────────────────────────────────────────────────────────────
export const productsApi = {
  list(params = {}) {
    return apiClient.get('/api/products/', { params });
  },
  get(id) {
    return apiClient.get(`/api/products/${id}/`);
  },
  create(data) {
    return apiClient.post('/api/products/', data);
  },
  update(id, data) {
    return apiClient.patch(`/api/products/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/products/${id}/`);
  },
};

// ─── Solar Packages ───────────────────────────────────────────────────────────
export const solarPackagesApi = {
  list(params = {}) {
    return apiClient.get('/api/solar-packages/', { params });
  },
  get(id) {
    return apiClient.get(`/api/solar-packages/${id}/`);
  },
  create(data) {
    return apiClient.post('/api/solar-packages/', data);
  },
  update(id, data) {
    return apiClient.patch(`/api/solar-packages/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/solar-packages/${id}/`);
  },
};

// ─── Support Requests ─────────────────────────────────────────────────────────
export const supportRequestsApi = {
  list(params = {}) {
    return apiClient.get('/api/support-requests/', { params });
  },
  get(id) {
    return apiClient.get(`/api/support-requests/${id}/`);
  },
  update(id, data) {
    return apiClient.patch(`/api/support-requests/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/support-requests/${id}/`);
  },
};

// ─── Quote Requests ───────────────────────────────────────────────────────────
export const quoteRequestsApi = {
  list(params = {}) {
    return apiClient.get('/api/quote-requests/', { params });
  },
  get(id) {
    return apiClient.get(`/api/quote-requests/${id}/`);
  },
  update(id, data) {
    return apiClient.patch(`/api/quote-requests/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/api/quote-requests/${id}/`);
  },
};

// ─── Meta App Configs (API Settings) ─────────────────────────────────────────
export const metaConfigsApi = {
  list(params = {}) {
    return apiClient.get('/meta/api/configs/', { params });
  },
  get(id) {
    return apiClient.get(`/meta/api/configs/${id}/`);
  },
  create(data) {
    return apiClient.post('/meta/api/configs/', data);
  },
  update(id, data) {
    return apiClient.patch(`/meta/api/configs/${id}/`, data);
  },
  delete(id) {
    return apiClient.delete(`/meta/api/configs/${id}/`);
  },
};

// ─── Webhook Event Logs ──────────────────────────────────────────────────────
export const webhookLogsApi = {
  list(params = {}) {
    return apiClient.get('/meta/api/webhook-logs/', { params });
  },
  get(id) {
    return apiClient.get(`/meta/api/webhook-logs/${id}/`);
  },
};

// ─── Installations (Site Assessments) ────────────────────────────────────────
export const installationsApi = {
  list(params = {}) {
    return apiClient.get('/api/installations/', { params });
  },
  get(id) {
    return apiClient.get(`/api/installations/${id}/`);
  },
  update(id, data) {
    return apiClient.patch(`/api/installations/${id}/`, data);
  },
};

export default apiClient;


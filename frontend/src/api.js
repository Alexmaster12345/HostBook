import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8080",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const login = (username, password) => {
  const form = new URLSearchParams({ username, password });
  return api.post("/api/v1/auth/login", form);
};

export const getAssets      = (params) => api.get("/api/v1/assets", { params });
export const getAsset       = (id) => api.get(`/api/v1/assets/${id}`);
export const createAsset    = (data) => api.post("/api/v1/assets", data);
export const updateAsset    = (id, data) => api.patch(`/api/v1/assets/${id}`, data);

export const getReservations   = () => api.get("/api/v1/reservations");
export const createReservation = (data) => api.post("/api/v1/reservations", data);
export const cancelReservation = (id) => api.delete(`/api/v1/reservations/${id}`);

export const getSummary     = () => api.get("/api/v1/reports/summary");
export const getUtilization = () => api.get("/api/v1/reports/utilization");
export const getIdleHosts   = () => api.get("/api/v1/reports/idle");
export const getMetrics     = (hostname) => api.get(`/api/v1/agent/metrics/${hostname}`);

export const getMe          = () => api.get("/api/v1/users/me");

export default api;

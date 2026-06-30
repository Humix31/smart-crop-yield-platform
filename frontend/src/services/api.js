import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001/api",
  timeout: 15000
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("smartCropToken");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function getWeather(district) {
  const { data } = await api.get(`/weather/${encodeURIComponent(district)}`);
  return data;
}

export async function predictYield(payload) {
  const { data } = await api.post("/predictions", payload);
  return data;
}

export async function getPredictionHistory() {
  const { data } = await api.get("/predictions/history");
  return data;
}

export async function getSensorData() {
  const { data } = await api.get("/sensors/latest");
  return data;
}

export async function loginUser(payload) {
  const { data } = await api.post("/auth/login", payload);
  return data;
}

export async function registerUser(payload) {
  const { data } = await api.post("/auth/register", payload);
  return data;
}

export async function getUsers() {
  const { data } = await api.get("/auth/users");
  return data;
}

export async function getCurrentUser() {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function getSensorCalibration() {
  const { data } = await api.get("/sensors/calibration");
  return data;
}

export async function saveSensorCalibration(payload) {
  const { data } = await api.post("/sensors/calibration", payload);
  return data;
}



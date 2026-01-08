import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000"
});

export const predictFlood = (lat, lon) =>
  API.post("/predict", { lat, lon });

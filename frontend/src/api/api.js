import axios from "axios";
import { APP_MODE } from "../config";
import { mockPredictResponse } from "../mock/mockPredictResponse";

const API = axios.create({
  baseURL: "http://localhost:8000"
});

export const predictFlood = async (lat, lon) => {
  if (APP_MODE === "offline") {
    return {
      data: mockPredictResponse
    };
  }

  return API.post("/predict", { lat, lon });
};

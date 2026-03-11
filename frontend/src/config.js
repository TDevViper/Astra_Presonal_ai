const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";
const WS_URL   = BASE_URL.replace("http://", "ws://").replace("https://", "wss://");

const API = {
  chat:        `${BASE_URL}/chat`,
  stream:      `${BASE_URL}/chat/stream`,
  ws:          `${WS_URL}/ws`,
  memory:      `${BASE_URL}/memory`,
  health:      `${BASE_URL}/health`,
  vision:      `${BASE_URL}/vision/analyze_b64`,
  voice:       `${BASE_URL}/voice/listen`,
  speak:       `${BASE_URL}/voice/say`,
  execute:     `${BASE_URL}/api/execute`,
  model:       `${BASE_URL}/model/switch`,
  knowledge:   `${BASE_URL}/knowledge/graph`,
};

export default API;
export { WS_URL };

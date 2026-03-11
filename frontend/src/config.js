const BASE_URL = import.meta.env.VITE_API_URL || "";
const WS_URL   = `ws://localhost:5050/ws`;

const API = {
  chat:      `${BASE_URL}/chat`,
  stream:    `${BASE_URL}/chat/stream`,
  ws:        WS_URL,
  memory:    `${BASE_URL}/memory`,
  health:    `${BASE_URL}/health`,
  vision:    `${BASE_URL}/vision/analyze_b64`,
  voice:     `${BASE_URL}/voice/listen`,
  speak:     `${BASE_URL}/voice/say`,
  execute:   `${BASE_URL}/execute`,
  model:     `${BASE_URL}/model`,
  knowledge: `${BASE_URL}/knowledge/graph`,
};

export default API;
export { WS_URL };
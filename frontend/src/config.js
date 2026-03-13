const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5050";
const WS_URL = (import.meta.env.VITE_API_URL || "ws://localhost:5050").replace("http", "ws") + "/ws";

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

API.modelList = `${BASE_URL}/model/list`;
API.modelSet  = `${BASE_URL}/model/set`;
API.modeList  = `${BASE_URL}/mode/list`;
API.modeSet   = `${BASE_URL}/mode/set`;
API.stats     = `${BASE_URL}/system/stats`;
API.capabilities = `${BASE_URL}/capabilities`;

export default API;
export { WS_URL };
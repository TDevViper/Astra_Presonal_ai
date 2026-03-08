// Auto-detects local vs Tailscale
const TAILSCALE_IP = "100.104.68.85";
const LOCAL        = "http://127.0.0.1:5001";
const REMOTE       = `http://${TAILSCALE_IP}:5001`;

// Use Tailscale if not on localhost
export const API = (window.location.hostname === "localhost" || 
                    window.location.hostname === "127.0.0.1")
    ? LOCAL
    : REMOTE;

export const WS = API.replace("http://", "ws://") + "/ws";

export default API;

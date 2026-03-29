import os
import requests

HASS_URL   = os.getenv("HASS_URL",  "http://localhost:8123")
HASS_TOKEN = os.getenv("HASS_TOKEN", "")

class SmartHome:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {HASS_TOKEN}",
            "Content-Type":  "application/json"
        }

    def get_all_entities(self):
        r = requests.get(f"{HASS_URL}/api/states", headers=self.headers, timeout=5)
        return r.json()

    def control_light(self, entity_id: str, on: bool, brightness=None, color=None):
        service = "turn_on" if on else "turn_off"
        data = {"entity_id": entity_id}
        if brightness: data["brightness_pct"] = brightness
        if color:      data["rgb_color"]      = color
        requests.post(f"{HASS_URL}/api/services/light/{service}",
                      headers=self.headers, json=data, timeout=5)

    def lock_door(self, entity_id: str):
        requests.post(f"{HASS_URL}/api/services/lock/lock",
                      headers=self.headers, json={"entity_id": entity_id}, timeout=5)

    def unlock_door(self, entity_id: str):
        requests.post(f"{HASS_URL}/api/services/lock/unlock",
                      headers=self.headers, json={"entity_id": entity_id}, timeout=5)

    def get_camera_feed(self, camera_entity: str):
        r = requests.get(f"{HASS_URL}/api/camera_proxy/{camera_entity}",
                         headers=self.headers, timeout=10)
        return r.content

    def run_automation(self, automation_id: str):
        requests.post(f"{HASS_URL}/api/services/automation/trigger",
                      headers=self.headers,
                      json={"entity_id": automation_id}, timeout=5)

    def get_sensor(self, entity_id: str):
        r = requests.get(f"{HASS_URL}/api/states/{entity_id}",
                         headers=self.headers, timeout=5)
        return r.json()

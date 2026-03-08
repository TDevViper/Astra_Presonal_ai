import os
import logging
import requests

logger = logging.getLogger(__name__)

HASS_URL   = os.getenv("HASS_URL", "http://localhost:8123")
HASS_TOKEN = os.getenv("HASS_TOKEN", "")


class SmartHome:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {HASS_TOKEN}",
            "Content-Type": "application/json"
        }
        self.available = bool(HASS_TOKEN)

    def is_online(self):
        if not self.available:
            return False
        try:
            r = requests.get(f"{HASS_URL}/api/", headers=self.headers, timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def get_all_entities(self):
        r = requests.get(f"{HASS_URL}/api/states", headers=self.headers, timeout=5)
        return r.json()

    def control_light(self, entity_id: str, on: bool,
                      brightness: int = None, color: list = None):
        service = "turn_on" if on else "turn_off"
        data = {"entity_id": entity_id}
        if brightness: data["brightness_pct"] = brightness
        if color:      data["rgb_color"] = color
        requests.post(f"{HASS_URL}/api/services/light/{service}",
                      headers=self.headers, json=data, timeout=5)
        return f"Light {entity_id} turned {'on' if on else 'off'}"

    def lock_door(self, entity_id: str):
        requests.post(f"{HASS_URL}/api/services/lock/lock",
                      headers=self.headers,
                      json={"entity_id": entity_id}, timeout=5)
        return f"Door {entity_id} locked"

    def unlock_door(self, entity_id: str):
        requests.post(f"{HASS_URL}/api/services/lock/unlock",
                      headers=self.headers,
                      json={"entity_id": entity_id}, timeout=5)
        return f"Door {entity_id} unlocked"

    def get_camera_feed(self, camera_entity: str) -> bytes:
        r = requests.get(f"{HASS_URL}/api/camera_proxy/{camera_entity}",
                         headers=self.headers, timeout=5)
        return r.content

    def run_automation(self, automation_id: str):
        requests.post(f"{HASS_URL}/api/services/automation/trigger",
                      headers=self.headers,
                      json={"entity_id": automation_id}, timeout=5)
        return f"Automation {automation_id} triggered"


def control_philips_hue(light_name: str, on: bool, brightness: int = 200):
    try:
        from phue import Bridge
        bridge_ip = os.getenv("HUE_BRIDGE_IP", "192.168.1.X")
        hue = Bridge(bridge_ip)
        hue.connect()
        hue.set_light(light_name, {"on": on, "bri": brightness})
        return f"Hue '{light_name}' {'on' if on else 'off'}"
    except ImportError:
        return "phue not installed: pip install phue"
    except Exception as e:
        return f"Hue error: {e}"

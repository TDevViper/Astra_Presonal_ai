import socket
import threading
import subprocess
import asyncio
from zeroconf import Zeroconf, ServiceBrowser
from bleak import BleakScanner


class DeviceDiscovery:
    def __init__(self):
        self.devices = {}
        self.zc = Zeroconf()

    def scan_mdns(self):
        ServiceBrowser(
            self.zc,
            [
                "_http._tcp.local.",
                "_hap._tcp.local.",
                "_googlecast._tcp.local.",
                "_airplay._tcp.local.",
            ],
            handlers=[self._on_service_found],
        )

    def _on_service_found(self, zeroconf, type, name, state_change):
        info = zeroconf.get_service_info(type, name)
        if info and info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])
            self.devices[name] = {"ip": ip, "type": type, "protocol": "mdns"}

    def scan_network(self):
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            for line in result.stdout.split("\n"):
                if "(" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        ip = parts[1].strip("()")
                        self.devices[name] = {"ip": ip, "protocol": "arp"}
        except Exception as e:
            print(f"[DeviceDiscovery] scan_network error: {e}")
        return self.devices

    async def _scan_bluetooth_async(self):
        try:
            devices = await BleakScanner.discover()
            for d in devices:
                if d.name:
                    self.devices[d.name] = {
                        "address": d.address,
                        "protocol": "bluetooth",
                    }
        except Exception as e:
            print(f"[DeviceDiscovery] bluetooth error: {e}")

    def scan_all(self):
        self.scan_network()
        self.scan_mdns()
        threading.Thread(
            target=lambda: asyncio.run(self._scan_bluetooth_async()), daemon=True
        ).start()
        return self.devices

    def get_all_devices(self):
        return self.devices

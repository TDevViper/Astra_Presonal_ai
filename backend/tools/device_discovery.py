import socket
import subprocess
import logging

logger = logging.getLogger(__name__)


class DeviceDiscovery:
    def __init__(self):
        self.devices = {}

    def scan_mdns(self):
        try:
            from zeroconf import Zeroconf, ServiceBrowser
            import time
            self.zc = Zeroconf()
            ServiceBrowser(
                self.zc,
                ["_http._tcp.local.", "_hap._tcp.local.",
                 "_googlecast._tcp.local.", "_airplay._tcp.local."],
                handlers=[self._on_service_found]
            )
            time.sleep(3)
        except ImportError:
            logger.warning("zeroconf not installed: pip install zeroconf")
        except Exception as e:
            logger.error(f"mDNS scan error: {e}")

    def _on_service_found(self, zeroconf, type, name, state_change):
        try:
            info = zeroconf.get_service_info(type, name)
            if info and info.addresses:
                ip = socket.inet_ntoa(info.addresses[0])
                self.devices[name] = {"ip": ip, "type": type, "protocol": "mdns"}
        except Exception:
            pass

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
            logger.error(f"Network scan error: {e}")

    async def scan_bluetooth(self):
        try:
            from bleak import BleakScanner
            devices = await BleakScanner.discover()
            for d in devices:
                if d.name:
                    self.devices[d.name] = {"address": d.address, "protocol": "bluetooth"}
        except ImportError:
            logger.warning("bleak not installed: pip install bleak")
        except Exception as e:
            logger.error(f"Bluetooth scan error: {e}")

    def get_all_devices(self):
        return self.devices

    def scan_all(self):
        self.scan_network()
        self.scan_mdns()
        return self.devices

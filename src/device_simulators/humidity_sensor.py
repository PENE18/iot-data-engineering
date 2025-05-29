import json
import time
import random
import paho.mqtt.client as mqtt
from datetime import datetime
import uuid
import math

class HumiditySensor:
    def __init__(self, device_id=None, location="Office"):
        self.device_id = device_id or str(uuid.uuid4())
        self.location = location
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.base_humidity = 45.0  # Base humidity percentage
        
    def generate_reading(self):
        # Simulate humidity variations with daily patterns
        noise = random.uniform(-5, 5)
        daily_pattern = 10 * math.sin(time.time() / 43200)  # 12-hour cycle
        humidity = max(0, min(100, self.base_humidity + daily_pattern + noise))
        
        return {
            "device_id": self.device_id,
            "device_type": "humidity_sensor",
            "location": self.location,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "humidity_percent": round(humidity, 2),
                "dew_point": round(humidity * 0.4, 2)  # Simplified dew point
            },
            "metadata": {
                "battery_level": random.randint(20, 100),
                "signal_strength": random.randint(-80, -30)
            }
        }
    
    def start_publishing(self, interval=10):
        print(f"Starting humidity sensor {self.device_id}")
        while True:
            reading = self.generate_reading()
            topic = f"sensors/humidity/{self.device_id}"
            self.mqtt_client.publish(topic, json.dumps(reading))
            print(f"Published: {reading['data']['humidity_percent']}%")
            time.sleep(interval)

if __name__ == "__main__":
    sensor = HumiditySensor(location="Warehouse")
    sensor.start_publishing()
import json
import time
import random
import paho.mqtt.client as mqtt
from datetime import datetime
import uuid
## 8l3kv3q4__PrBt06aEF8Ope_u5fvBtDYrgvdKxqX1gHs_wDLyTz8aNuIhsrjbNs8Ckuq8ifA9wvwwBRuSIOSjw==
class TemperatureSensor:
    def __init__(self, device_id=None, location="Office"):
        self.device_id = device_id or str(uuid.uuid4())
        self.location = location
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.base_temp = 22.0  # Base temperature in Celsius
        
    def generate_reading(self):
        # Simulate realistic temperature variations
        noise = random.uniform(-2, 2)
        time_factor = 5 * math.sin(time.time() / 3600)  # Hourly variation
        temperature = self.base_temp + time_factor + noise
        
        return {
            "device_id": self.device_id,
            "device_type": "temperature_sensor",
            "location": self.location,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "temperature_celsius": round(temperature, 2),
                "temperature_fahrenheit": round(temperature * 9/5 + 32, 2)
            },
            "metadata": {
                "battery_level": random.randint(20, 100),
                "signal_strength": random.randint(-80, -30)
            }
        }
    
    def start_publishing(self, interval=5):
        print(f"Starting temperature sensor {self.device_id}")
        while True:
            reading = self.generate_reading()
            topic = f"sensors/temperature/{self.device_id}"
            self.mqtt_client.publish(topic, json.dumps(reading))
            print(f"Published: {reading['data']['temperature_celsius']}°C")
            time.sleep(interval)

if __name__ == "__main__":
    import math
    sensor = TemperatureSensor(location="Server Room")
    sensor.start_publishing()
import json
import time
from kafka import KafkaConsumer
import pandas as pd
from collections import defaultdict, deque
import redis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamProcessor:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'sensor-data',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        # Redis for caching and real-time aggregations
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # In-memory sliding windows for each device
        self.device_windows = defaultdict(lambda: deque(maxlen=100))
        
    def process_temperature_data(self, data):
        """Process temperature sensor data"""
        device_id = data['device_id']
        temp_celsius = data['data']['temperature_celsius']
        timestamp = data['timestamp']
        
        # Add to sliding window
        self.device_windows[device_id].append({
            'temp': temp_celsius,
            'timestamp': timestamp
        })
        
        # Calculate moving average
        temps = [reading['temp'] for reading in self.device_windows[device_id]]
        moving_avg = sum(temps) / len(temps)
        
        # Store in Redis
        self.redis_client.setex(
            f"device:{device_id}:avg_temp", 
            300,  # 5 minutes TTL
            moving_avg
        )
        
        # Alert if temperature is abnormal
        if temp_celsius > 30 or temp_celsius < 10:
            alert = {
                'device_id': device_id,
                'alert_type': 'temperature_anomaly',
                'value': temp_celsius,
                'threshold': '10-30°C',
                'timestamp': timestamp
            }
            self.redis_client.lpush('alerts', json.dumps(alert))
            logger.warning(f"Temperature alert: {alert}")
    
    def process_humidity_data(self, data):
        """Process humidity sensor data"""
        device_id = data['device_id']
        humidity = data['data']['humidity_percent']
        timestamp = data['timestamp']
        
        # Store current reading
        self.redis_client.setex(
            f"device:{device_id}:humidity", 
            300,
            humidity
        )
        
        # Alert for extreme humidity
        if humidity > 80 or humidity < 20:
            alert = {
                'device_id': device_id,
                'alert_type': 'humidity_anomaly',
                'value': humidity,
                'threshold': '20-80%',
                'timestamp': timestamp
            }
            self.redis_client.lpush('alerts', json.dumps(alert))
            logger.warning(f"Humidity alert: {alert}")
    
    def calculate_device_health_score(self, data):
        """Calculate overall device health based on metadata"""
        battery = data['metadata']['battery_level']
        signal = data['metadata']['signal_strength']
        
        # Simple health score calculation
        battery_score = battery / 100
        signal_score = max(0, (signal + 100) / 70)  # Normalize signal strength
        health_score = (battery_score + signal_score) / 2
        
        device_id = data['device_id']
        self.redis_client.setex(
            f"device:{device_id}:health_score",
            300,
            health_score
        )
        
        return health_score
    
    def start_processing(self):
        logger.info("Starting stream processor...")
        
        for message in self.consumer:
            try:
                data = message.value
                device_type = data['device_type']
                
                logger.info(f"Processing {device_type} data from {data['device_id']}")
                
                # Route to appropriate processor
                if device_type == 'temperature_sensor':
                    self.process_temperature_data(data)
                elif device_type == 'humidity_sensor':
                    self.process_humidity_data(data)
                
                # Calculate device health for all devices
                health_score = self.calculate_device_health_score(data)
                
                if health_score < 0.3:
                    alert = {
                        'device_id': data['device_id'],
                        'alert_type': 'low_device_health',
                        'health_score': health_score,
                        'timestamp': data['timestamp']
                    }
                    self.redis_client.lpush('alerts', json.dumps(alert))
                    logger.warning(f"Device health alert: {alert}")
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")

if __name__ == "__main__":
    processor = StreamProcessor()
    processor.start_processing()
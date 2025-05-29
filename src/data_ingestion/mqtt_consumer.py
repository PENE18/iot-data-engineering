import json
import paho.mqtt.client as mqtt
from kafka import KafkaProducer
from influxdb_client import InfluxDBClient, Point
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTToKafkaBridge:
    def __init__(self):
        # MQTT Setup
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        # Kafka Setup
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        
        # InfluxDB Setup
        self.influx_client = InfluxDBClient(
            url="http://localhost:8086",
            token="wxT_XCSBIzDPx93_TGMNUZQt1gdLXidFb36Jo1h8B0a25i5Jqswiwofojyy3Div4ONzTcvLBH80zRaTwTy84Cw==",  # Get from InfluxDB setup
            org="iot-org"
        )
        self.write_api = self.influx_client.write_api()
        
    def on_mqtt_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe("sensors/+/+")  # Subscribe to all sensor topics
        
    def on_mqtt_message(self, client, userdata, msg):
        try:
            # Parse message
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.info(f"Received message from {topic}: {payload}")
            
            # Send to Kafka for stream processing
            self.kafka_producer.send('sensor-data', value=payload, key=payload['device_id'])
            
            # Write directly to InfluxDB for time-series storage
            self.write_to_influxdb(payload)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def write_to_influxdb(self, data):
        try:
            point = Point(data['device_type'])
            point.tag("device_id", data['device_id'])
            point.tag("location", data['location'])
            
            # Add data fields
            for key, value in data['data'].items():
                if isinstance(value, (int, float)):
                    point.field(key, value)
            
            # Add metadata fields
            for key, value in data['metadata'].items():
                if isinstance(value, (int, float)):
                    point.field(f"meta_{key}", value)
                    
            point.time(datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')))
            
            self.write_api.write(bucket="sensor-data", record=point)
            logger.info(f"Written to InfluxDB: {data['device_id']}")
            
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
    
    def start(self):
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.loop_forever()

if __name__ == "__main__":
    bridge = MQTTToKafkaBridge()
    bridge.start()
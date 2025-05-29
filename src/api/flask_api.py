from flask import Flask, jsonify, request
from flask_cors import CORS
import redis
import json
from influxdb_client import InfluxDBClient
import psycopg2
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
CORS(app)

# Initialize connections
redis_client = redis.Redis(host='localhost', port=6379, db=0)
influx_client = InfluxDBClient(url="http://localhost:8086", token="8l3kv3q4__PrBt06aEF8Ope_u5fvBtDYrgvdKxqX1gHs_wDLyTz8aNuIhsrjbNs8Ckuq8ifA9wvwwBRuSIOSjw==", org="iot-org")
query_api = influx_client.query_api()

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get all active devices"""
    try:
        # Get device IDs from Redis
        device_keys = redis_client.keys('device:*:health_score')
        devices = []
        
        for key in device_keys:
            device_id = key.decode().split(':')[1]
            health_score = redis_client.get(key)
            
            devices.append({
                'device_id': device_id,
                'health_score': float(health_score) if health_score else 0,
                'last_seen': datetime.now().isoformat()
            })
        
        return jsonify(devices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/device/<device_id>/latest', methods=['GET'])
def get_device_latest(device_id):
    """Get latest readings for a device"""
    try:
        data = {}
        
        # Get latest temperature if available
        temp_key = f"device:{device_id}:avg_temp"
        temp = redis_client.get(temp_key)
        if temp:
            data['temperature'] = float(temp)
        
        # Get latest humidity if available
        humidity_key = f"device:{device_id}:humidity"
        humidity = redis_client.get(humidity_key)
        if humidity:
            data['humidity'] = float(humidity)
        
        # Get health score
        health_key = f"device:{device_id}:health_score"
        health = redis_client.get(health_key)
        if health:
            data['health_score'] = float(health)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/device/<device_id>/history', methods=['GET'])
def get_device_history(device_id):
    """Get historical data for a device"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        query = f'''
        from(bucket: "sensor-data")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r["device_id"] == "{device_id}")
        |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
        |> yield(name: "mean")
        '''
        
        result = query_api.query(org="iot-org", query=query)
        
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    'timestamp': record.get_time().isoformat(),
                    'field': record.get_field(),
                    'value': record.get_value()
                })
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts"""
    try:
        alerts = []
        alert_data = redis_client.lrange('alerts', 0, 50)  # Get last 50 alerts
        
        for alert_json in alert_data:
            alert = json.loads(alert_json)
            alerts.append(alert)
        
        return jsonify(alerts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Count active devices
        device_keys = redis_client.keys('device:*:health_score')
        active_devices = len(device_keys)
        
        # Count alerts in last 24 hours
        alert_count = redis_client.llen('alerts')
        
        # Average health score
        health_scores = []
        for key in device_keys:
            score = redis_client.get(key)
            if score:
                health_scores.append(float(score))
        
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
        
        return jsonify({
            'active_devices': active_devices,
            'total_alerts': alert_count,
            'average_health_score': round(avg_health, 2),
            'system_status': 'healthy' if avg_health > 0.7 else 'warning'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
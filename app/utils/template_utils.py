from datetime import datetime
from bson import ObjectId
from .json_encoder import mongo_json_dumps

def process_template_data(data: dict) -> dict:
    """Process data before sending to template to ensure JSON serialization."""
    def process_value(value):
        if isinstance(value, dict):
            return {k: process_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [process_value(item) for item in value]
        elif isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        return value

    processed = {}
    for k, v in data.items():
        processed[k] = process_value(v)

    # Ensure nested structures are processed
    if 'current_register' in processed and processed['current_register']:
        register = processed['current_register']
        
        # Process main datetime fields
        for field in ['date', 'initial_count_time', 'final_verification_time']:
            if field in register and isinstance(register[field], datetime):
                register[field] = register[field].strftime("%Y-%m-%dT%H:%M:%S")
        
        # Process transactions
        if 'transactions' in register:
            for trans in register['transactions']:
                if 'time' in trans:
                    trans['time'] = trans['time'].strftime("%Y-%m-%dT%H:%M:%S") if isinstance(trans['time'], datetime) else trans['time']
        
        # Process logs
        if 'logs' in register:
            for log in register['logs']:
                if 'timestamp' in log:
                    log['timestamp'] = log['timestamp'].strftime("%Y-%m-%dT%H:%M:%S") if isinstance(log['timestamp'], datetime) else log['timestamp']

    return processed
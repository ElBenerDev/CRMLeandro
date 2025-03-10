from bson import ObjectId
import json
from datetime import datetime

class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def mongo_json_dumps(obj):
    return json.dumps(obj, cls=MongoJSONEncoder)
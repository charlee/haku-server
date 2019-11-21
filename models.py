from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, JSONAttribute, BinaryAttribute

from .config import settings



class ConnectionModel(Model):

    class Meta:
        table_name = settings['DYNAMODB_TABLE_NAME']
        region = settings['AWS_REGION']

    pk = UnicodeAttribute(hash_key=True)
    connectionId = UnicodeAttribute(range_key=True)
    name = UnicodeAttribute()
    whiteboardId = NumberAttribute()


class WhiteboardConnectionModel(Model):

    class Meta:
        table_name = settings['DYNAMODB_TABLE_NAME']
        region = settings['AWS_REGION']

    pk = UnicodeAttribute(hash_key=True)
    connectionId = UnicodeAttribute(range_key=True)



class WhiteboardLineModel(Model):
    class Meta:
        table_name = settings['DYNAMODB_TABLE_NAME']
        region = settings['AWS_REGION']
    pk = UnicodeAttribute(hash_key=True)
    created_ts = NumberAttribute(range_key=True)
    data = JSONAttribute()


class WhiteboardImageModel(Model):
    class Meta:
        table_name = settings['DYNAMODB_TABLE_NAME']
        region = settings['AWS_REGION']

    pk = UnicodeAttribute(hash_key=True)
    created_ts = NumberAttribute(range_key=True)
    image = BinaryAttribute()


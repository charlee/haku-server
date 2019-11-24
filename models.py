import boto3
import gzip
import json
import random
import time
from boto3.dynamodb.conditions import Key, Attr
from config import settings


PREFIX_MAP = {
    'board': 'b',
    'board_conn': 'bc',
    'conn': 'c',
    'line': 'l',
    'image': 'i',
}


class DynamoDB:
    def __init__(self):
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table(settings['DYNAMODB_TABLE_NAME'])

    def query(self, pk, after=None):
        """Query all items from partition pk.
        """

        q = Key('pk').eq(pk)

        if after is not None:
            q = q & Key('created_ts').gt(after)

        res = self.table.query(KeyConditionExpression=q)
        return res['Items']

    def create_item(self, pk, created_ts, **kwargs):
        """Create an item.
        """
        res = self.table.put_item(
            Item={
                'pk': pk,
                'created_ts': created_ts,
                **kwargs,
            }
        )

        return res

    def delete_item(self, pk, created_ts):
        self.table.delete_item(Key={'pk': pk, 'created_ts': created_ts})

    def delete_items_before_or_equal(self, pk, before_or_equal):
        """Delete items from partition pk that are before or equal to given timestamp.
        """
        res = self.table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('created_ts').lte(before_or_equal)
        )
        items = res['Items']

        with self.table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={'pk': item['pk'], 'created_ts': item['created_ts']})

    def update_item(self, pk, created_ts, update_expression, values):
        self.table.update_item(
            Key={'pk': pk, 'created_ts': created_ts},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=values,
        )


class Model:
    def __init__(self):
        self.db = DynamoDB()

    def ts(self):
        """Get current timestamp.
        """
        return int(time.time() * 1000)

    def pk(self, board_id, type):
        """Generate pk for given type.
        """
        prefix = PREFIX_MAP.get(type)
        if not prefix:
            return None

        return '%s:%s' % (prefix, board_id)


    def get_board(self, board_id):
        pk = self.pk(board_id, 'board')
        board = self.db.query(pk)
        if board:
            return board[0]
        else:
            return None

    def create_board(self):
        board_id = str(random.randint(1000000000, 9999999999))
        pk = self.pk(board_id, 'board')
        self.db.create_item(pk, self.ts(), board_id=board_id)
        return board_id

    def create_connection(self, conn_id, board_id=None):
        if board_id is None:
            board_id = self.create_board()
        else:
            board = self.get_board(board_id)
            if board is None:
                raise ValueError('Board %s does not exist' % board_id)

        ts = self.ts()

        pk = self.pk(conn_id, 'conn')
        self.db.create_item(pk, ts, board_id=board_id)

        bc_pk = self.pk(board_id, 'board_conn')
        self.db.create_item(bc_pk, ts, conn_id=conn_id)

        return conn_id

    def query_connections(self, board_id):
        """Query connections in a given board.
        """
        pk = self.pk(board_id, 'board_conn')
        return self.db.query(pk)

    def create_line(self, board_id, line_data):
        """Create a line in a board.
        """
        # Make sure the board exists.
        board = self.get_board(board_id)
        if board is None:
            raise ValueError('Board %s does not exist' % board_id)

        pk = self.pk(board_id, 'line')
        gzipped_line = gzip.compress(json.dumps(line_data).encode())
        self.db.create_item(pk, self.ts(), line_data=gzipped_line)

    def query_lines(self, board_id, after=None):
        """Return lines after given timestamp.
        """
        pk = self.pk(board_id, 'line')
        lines = self.db.query(pk, after)
        return [{
            'pk': line['pk'],
            'created_ts': line['created_ts'],
            'line_data': json.loads(gzip.decompress(line['line_data'].value)),
        } for line in lines]

    def delete_lines_before_or_equal(self, board_id, before_or_equal):
        """Delete lines before or equal given timestamp.
        """
        pk = self.pk(board_id, 'line')
        self.db.delete_items_before_or_equal(pk, before_or_equal)

    def get_connection(self, conn_id):
        pk = self.pk(conn_id, 'conn')
        conns = self.db.query(pk)
        if conns:
            return conns[0]
        else:
            return None

    def delete_connection(self, conn_id):
        """Delete specified connection.
        """
        conn = self.get_connection(conn_id)

        if conn:
            self.db.delete_item(conn['pk'], conn['created_ts'])

            bc_pk = self.pk(conn['board_id'], 'board_conn')
            self.db.delete_item(bc_pk, conn['created_ts'])

            return True
        
        return False

    def update_compressed_image(self, board_id, board_created_ts, last_image_ts, compressed_image):
        """Update the board info with given last_image_ts and compressed_image.
        :param board_id: string, board id
        :param board_created_ts: number, the created_ts of the board info. Since this info is likely already owned by
                                 the caller, passing this argument could reduce one dynamodb call.
        :param last_image_ts: number
        :param compressed_image: bytes
        """
        pk = self.pk(board_id, 'board')
        self.db.update_item(
            pk,
            board_created_ts,
            update_expression='SET last_image_ts=:last_image_ts, compressed_image=:compressed_image',
            values={
                ':last_image_ts': last_image_ts,
                ':compressed_image': compressed_image,
            }
        )
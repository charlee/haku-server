import json
import logging

from models import Model

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_connection_id(event):
    return event['requestContext'].get('connectionId')

def get_body(event):
    try:
        return json.loads(event.get('body', ''))
    except:
        logger.debug('event body could not be decoded')
        return {}


def get_query_params(event):
    return event.get('queryStringParameters')

def get_event_type(event):
    return event['requestContext'].get('eventType')

def send_to_connection(event, conn_id, data):
    gatewayapi = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url='https://%s/%s' % (event['requestContext']['domainName'], event['requestContext']['stage'])
    )
    return gatewayapi.post_to_connection(ConnectionId=conn_id, Data=json.dumps(data).encode('utf-8'))


def success(data):
    return {
        'statusCode': 200,
        'body': data,
    }

def error400(data):
    return {
        'statusCode': 400,
        'body': data,
    }

def onconnect(event):
    conn_id = get_connection_id(event)
    q = get_query_params(event)

    if 'bid' not in q:
        return error400('board id not defined')

    model = Model()
    board_id = q['bid']

    if board_id == 'new':
        board_id = None
        model.create_connection(conn_id)
    else:
        board = model.get_board(board_id)
        if board is None:
            return error400('board %s does not exist' % board_id)

        model.create_connection(conn_id, board_id)

    return success('success')


def ondisconnect(event):
    conn_id = get_connection_id(event)
    model = Model()
    model.delete_connection(conn_id)

    return success('success')

def websocket_connection_manager(event, context):
    """Connection manager for websocket $connect and $disconnect.
    """

    event_type = get_event_type(event)
    if event_type == 'CONNECT':
        return onconnect(event)
    elif event_type == 'DISCONNECT':
        return ondisconnect(event)

    else:
        logger.info('unrecognized eventType')
        return error400('unknown event type')

def add_line(event, context):
    """Add a line to the board.
    """
    body = get_body(event)
    logger.info('body = ' + json.dumps(body))

    model = Model()

    return success('success')


def compress_board(event, context):
    """Compress the board periodically.
    """
    logger.info('compress_board called')

    return success('success')
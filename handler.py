import json
import logging

from models import Model

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_connection_id(event):
    return event['requestContext'].get('connectionId')


def get_query_params(event):
    return event.get('queryStringParameters')

def get_event_type(event):
    return event['requestContext'].get('eventType')

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

    event_type = get_event_type(event)
    if event_type == 'CONNECT':
        return onconnect(event)
    elif event_type == 'DISCONNECT':
        return ondisconnect(event)

    else:
        logger.info('unrecognized eventType')
        return error400('unknown event type')



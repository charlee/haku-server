import json
import logging

from models import Model

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def onconnect(request_context):
    conn_id = request_context.get('connectionId')
    model = Model()
    model.create_connection(conn_id)


def ondisconnect(request_context):
    conn_id = request_context.get('connectionId')
    model = Model()
    model.delete_connection(conn_id)


def websocket(event, context):
    request_context = event['requestContext']
    event_type = request_context.get('eventType')

    if event_type == 'CONNECT':
        onconnect(request_context)
    elif event_type == 'DISCONNECT':
        ondisconnect(request_context)

    else:
        logger.info('unrecognized eventType')



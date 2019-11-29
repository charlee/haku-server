import json
import boto3
import logging
import io
import base64

from models import Model
from PIL import Image, ImageDraw
from config import settings

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


def send_to_connection(event, conn_id, action, payload):
    """Send message to conn_id.
    """
    gatewayapi = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url='https://%s/%s' % (event['requestContext']['domainName'], event['requestContext']['stage'])
    )

    message = {
        'action': action,
        'payload': payload,
    }

    try:
        return gatewayapi.post_to_connection(ConnectionId=conn_id, Data=json.dumps(message).encode('utf-8'))
    except Exception as e:
        logger.error(e)

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

    logger.info('[CONNECT] connection %s connected' % conn_id)

    # notify other connections
    conns = model.query_connections(board_id)
    all_conn_ids = [conn['conn_id'] for conn in conns]
    other_conn_ids = [cid for cid in all_conn_ids if cid != conn_id]

    # send board data to other connections
    board_data = {
        'boardId': board_id,
        'myConnectionId': None,
        'image': {},
        'lines': [],
        'connections': all_conn_ids,
    }

    for cid in other_conn_ids:
        send_to_connection(event, cid, 'boardData', board_data)

    return success('success')


def ondisconnect(event):
    conn_id = get_connection_id(event)
    model = Model()
    conn = model.get_connection(conn_id)
    board_id = conn['board_id']
    model.delete_connection(conn_id)

    logger.info('[DISCONNECT] connection %s disconnected' % conn_id)

    # notify other connections
    conns = model.query_connections(board_id)
    all_conn_ids = [conn['conn_id'] for conn in conns if conn['conn_id'] != conn_id]

    # send board data to other connections
    board_data = {
        'boardId': board_id,
        'myConnectionId': None,
        'image': {},
        'lines': [],
        'connections': all_conn_ids,
    }

    for cid in all_conn_ids:
        send_to_connection(event, cid, 'boardData', board_data)

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
    my_conn_id = get_connection_id(event)
    body = get_body(event)
    line = body['payload']

    logger.debug('Line created, data = ' + json.dumps(line))

    board_id = line['boardId']

    # save line to db
    model = Model()
    model.create_line(board_id, line)

    # find other connections in this board
    conns = model.query_connections(board_id)
    other_conn_ids = [conn['conn_id'] for conn in conns if conn['conn_id'] != my_conn_id]

    logger.debug('Sending to other connections, conn_ids = ' + json.dumps(other_conn_ids))

    # send line to other connections
    for conn_id in other_conn_ids:
        send_to_connection(event, conn_id, 'lineAdded', line)

    return success('success')

def init(event, context):
    """Init request. Return board image, lines, and connections.
    """
    conn_id = get_connection_id(event)

    model = Model()

    # Get current board id from the connection
    conn = model.get_connection(conn_id)
    board_id = conn['board_id']

    # Get all connections from this board, so that UI can show the user list
    connections = model.query_connections(board_id)
    conn_ids = [conn['conn_id'] for conn in connections]

    # TODO: get board information(include the last_image_ts)
    current_board_info = model.get_board(board_id)
    last_ts = current_board_info.get('last_image_ts')

    # TODO: get the lastest image
    current_img = current_board_info.get('compressed_image')

    # TODO: get the lines from last_image_ts to now
    current_lines = model.query_lines(board_id, last_ts)

    if current_img == None:
        img_decode = None
    else:
        img_decode = base64.b64encode(current_img.value).decode()

    # Assemble the board data
    board_data = {
        'boardId': board_id,
        'myConnectionId': conn_id,
        'image': img_decode,
        'lines': [line['line_data'] for line in current_lines],
        'connections': conn_ids,
    }

    send_to_connection(event, conn_id, 'boardData', board_data)

    return success('success')

def draw_from_lines(im, lines_data):
    """Draw image from lines
    """

    if im == None:
        # create a new image when nothing exists
        # 1920 * 1080
        logger.info('Create a new image')
        image = Image.new(mode = 'RGB',
                          size = (1920, 1080),
                          color = (255, 255, 255)) 
    else:
        # open existing one
        f = io.BytesIO(im.value)
        image = Image.open(f)
    
    # start draw lines
    draw = ImageDraw.Draw(image)
    for data in lines_data:
        
        line = data['line_data']['data']
        draw.line(  xy = line['points'],
                    fill = line['color'],
                    width = line['width'] )
    
    output = io.BytesIO()
    image.save(output, format='PNG')

    # image.save("test.PNG")

    return output.getvalue()

def local_test(event, context):
    model = Model()
    logger.debug('test')

    board_ids = model.get_all_boards()
    logger.debug(board_ids)

    return success('success')

def get_board_id(event, context):
    conn_id = get_connection_id(event)
    model = Model()
    conn = model.get_connection(conn_id)

    send_to_connection(event, conn_id, 'boardId', {'boardId': conn['board_id']})

    return success('success')


def compress_board(event, context):
    """Compress the board periodically.
    """
    logger.info('compress_board called')

    # get all boards
    model = Model()
    board_ids = model.get_all_boards()
    logger.info(board_ids)

    # for each board:
    for id in board_ids:

        logger.info("Board -->" + str(id))
                    
        # get board information(including the last_image_ts)
        item = model.get_board(id)
        
        # get the latest image and time stamp
        last_ts = item.get('last_image_ts')
        image = item.get('compressed_image')

        logger.info('Last compressed time: ' + str(last_ts))

        # read all lines from last_image_ts to now
        lines_data = model.query_lines(id, last_ts)
        
        if len(lines_data) < settings['MIN_NUM_LINES_COMPRESS']:
            # not enough lines to be compressed
            logger.info("Not enough lines to compress " + 
                        str(len(lines_data)) + "<" +
                        str(settings['MIN_NUM_LINES_COMPRESS']))
            continue

        logger.debug(lines_data[0])

        # draw each line onto the latest image
        # save the image to bytes io
        image_bytes = draw_from_lines(image, lines_data)

        # update the board.last_image_ts and compressed_image
        model.update_compressed_image(
            id, item.get('created_ts'),
            lines_data[-1]['created_ts'],
            image_bytes)

    return success('success')

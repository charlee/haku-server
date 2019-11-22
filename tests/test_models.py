import unittest
from models import Model

class ModelTestCase(unittest.TestCase):

    def setUp(self):
        self.model = Model()

    # def test_create_board(self):
    #     board_id = self.model.create_board()
    #     board = self.model.get_board(board_id)
    #     self.assertEqual(board['board_id'], board_id)

    # def test_create_connection(self):
    #     self.model.create_connection('conn-2', board_id='1128562306')
    #     self.model.create_connection('conn-3', board_id='1128562306')

    # def test_create_line(self):
    #     self.model.create_line('4663076407', {'color': '#ff0000', 'points': [1, 2, 3, 4]})

    # def test_query_lines(self):
    #     lines = self.model.query_lines('4663076407')
    #     print(lines)

    # def test_delete_lines(self):
    #     self.model.delete_lines_before_or_equal('4663076407', 1574391422405)

    # def test_delete_connection(self):
    #     self.model.delete_connection('conn-2')

    def test_query_connections(self):
        print(self.model.query_connections('1128562306'))
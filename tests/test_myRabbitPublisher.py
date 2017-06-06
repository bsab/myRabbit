from context import myrabbit
from context import json, logging, pika, pymysql
from context import SafeConfigParser
from unittest import TestCase

def get_myrabbit_publisher_client():
    # reading configuration file
    parser = SafeConfigParser()
    parser.read('config.ini')

    # rabbit connection parameters
    rabbit_url = str(parser.get('rabbitmq', 'rabbit_url'))

    # mysql connection parameters
    mysql_url = str(parser.get('mysql', 'mysql_url'))
    mysql_username = str(parser.get('mysql', 'mysql_username'))
    mysql_psw = str(parser.get('mysql', 'mysql_psw'))
    mysql_dbname = str(parser.get('mysql', 'mysql_dbname'))
    mysql_table_list = json.loads(str(parser.get('mysql', 'mysql_table_list')))

    return myrabbit.MyRabbitPublisher(rabbit_url,
                             mysql_url,
                             mysql_username,
                             mysql_psw,
                             mysql_dbname,
                             mysql_table_list)


class TestMyRabbitPublisher(TestCase):

    def test_can_instantiate_instance_of_myrabbit_publisher(self):
        mpc = get_myrabbit_publisher_client()
        assert isinstance(mpc, myrabbit.MyRabbitPublisher)

    def test_rabbitmq_connect(self):
        mpc = get_myrabbit_publisher_client()
        result = mpc.rabbitmq_connect()
        assert isinstance(result, pika.adapters.select_connection.SelectConnection)

    def test_mysql_connect(self):
        mpc = get_myrabbit_publisher_client()
        result = mpc.mysql_connect()
        assert isinstance(result, pymysql.connections.Connection)

    def test_rabbitmq_connect_fail(self):
        """this test must be fail"""
        mpc = get_myrabbit_publisher_client()
        mpc._url = "amqp://abcdef:defghi@sab.com/xsdxsd?connection_attempts=3&heartbeat_interval=3600"
        try:
            result = mpc.run()
        except pika.exceptions.AMQPConnectionError:
            return True
        return False

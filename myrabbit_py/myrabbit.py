import logging
import pika
import json
import pymysql.cursors
import pymysql

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

logger = logging.getLogger(__name__)


class MyRabbitPublisher(object):
    """This is a mysql publisher that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.

    It uses delivery confirmations and illustrates one way to keep track of
    messages that have been sent and if they've been confirmed by RabbitMQ.

    """
    EXCHANGE = 'message'
    EXCHANGE_TYPE = 'topic'
    PUBLISH_INTERVAL = 60
    QUEUE = 'text'
    ROUTING_KEY = 'myrabbit_py.text'

    def __init__(self, amqp_url, mysql_url, mysql_username, mysql_psw, mysql_dbname, mysql_table_list):
        """Setup the example publisher object, passing in the URL we will use
        to connect to RabbitMQ.

        :param int station_id: The ID of the current station

        :param str amqp_url: The URL for connecting to RabbitMQ
        :param str mysql_url: The URL for connecting to MySQL
        :param str mysql_username: The username for connecting to MySQL
        :param str mysql_psw: The password for connecting to MySQL
        :param str mysql_dbname: The database name for connecting to MySQL
        """

        self._rabbitmq_connection = None
        self._channel = None
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._stopping = False
        self._url = amqp_url
        self._closing = False

        # mysql parameters connections
        self._mysql_connection = None;
        self._mysql_url = mysql_url;
        self._mysql_username = mysql_username;
        self._mysql_psw = mysql_psw;
        self._mysql_dbname = mysql_dbname;
        self._mysql_table_list = mysql_table_list;

    def rabbitmq_connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika. If you want the reconnection to work, make
        sure you set stop_ioloop_on_close to False, which is not the default
        behavior of this adapter.

        :rtype: pika.SelectConnection

        """
        logger.info('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open,
                                     stop_ioloop_on_close=False)

    def mysql_connect(self):
        """This method connects to MySQL, returning the connection handle.

        :rtype: pymysql.Connection

        """
        logger.info('Connecting to MySQL %s', self._mysql_url)

        # Connect to the database
        return pymysql.connect(host=self._mysql_url,
                               user=self._mysql_username,
                               password=self._mysql_psw,
                               db=self._mysql_dbname,
                               charset='utf8mb4',
                               cursorclass=pymysql.cursors.DictCursor)


    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        logger.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        """This method adds an on close callback that will be invoked by pika
        when RabbitMQ closes the connection to the publisher unexpectedly.

        """
        logger.info('Adding connection close callback')
        self._rabbitmq_connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._rabbitmq_connection.ioloop.stop()
        else:
            logger.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                           reply_code, reply_text)
            self._rabbitmq_connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0

        # This is the old connection IOLoop instance, stop its ioloop
        self._rabbitmq_connection.ioloop.stop()

        # Create a new connection
        self._rabbitmq_connection = self.rabbitmq_connect()

        # There is now a new connection, needs a new ioloop to run
        self._rabbitmq_connection.ioloop.start()

    def open_channel(self):
        """This method will open a new channel with RabbitMQ by issuing the
        Channel.Open RPC command. When RabbitMQ confirms the channel is open
        by sending the Channel.OpenOK RPC reply, the on_channel_open method
        will be invoked.

        """
        logger.info('Creating a new channel')
        self._rabbitmq_connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        logger.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        logger.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        logger.warning('Channel was closed: (%s) %s', reply_code, reply_text)
        if not self._closing:
            self._rabbitmq_connection.close()

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare

        """
        logger.info('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       exchange_name,
                                       self.EXCHANGE_TYPE)

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

        """
        logger.info('Exchange declared')
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.

        """
        logger.info('Declaring queue %s', queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name)

    def on_queue_declareok(self, method_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame

        """
        logger.info('Binding %s to %s with %s',
                    self.EXCHANGE, self.QUEUE, self.ROUTING_KEY)
        self._channel.queue_bind(self.on_bindok, self.QUEUE,
                                 self.EXCHANGE, self.ROUTING_KEY)

    def on_bindok(self, unused_frame):
        """This method is invoked by pika when it receives the Queue.BindOk
        response from RabbitMQ. Since we know we're now setup and bound, it's
        time to start publishing."""
        logger.info('Queue bound')
        self.start_publishing()

    def start_publishing(self):
        """This method will enable delivery confirmations and schedule the
        first message to be sent to RabbitMQ

        """
        logger.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        """Send the Confirm.Select RPC method to RabbitMQ to enable delivery
        confirmations on the channel. The only way to turn this off is to close
        the channel and create a new one.

        When the message is confirmed from RabbitMQ, the
        on_delivery_confirmation method will be invoked passing in a Basic.Ack
        or Basic.Nack method from RabbitMQ that will indicate which messages it
        is confirming or rejecting.

        """
        logger.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        """Invoked by pika when RabbitMQ responds to a Basic.Publish RPC
        command, passing in either a Basic.Ack or Basic.Nack frame with
        the delivery tag of the message that was published. The delivery tag
        is an integer counter indicating the message number that was sent
        on the channel via Basic.Publish. Here we're just doing house keeping
        to keep track of stats and remove message numbers that we expect
        a delivery confirmation of from the list used to keep track of messages
        that are pending confirmation.

        :param pika.frame.Method method_frame: Basic.Ack or Basic.Nack frame

        """
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        logger.info('Received %s for delivery tag: %i',
                    confirmation_type,
                    method_frame.method.delivery_tag)
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        logger.info('Published %i messages, %i have yet to be confirmed, '
                    '%i were acked and %i were nacked',
                    self._message_number, len(self._deliveries),
                    self._acked, self._nacked)

    def schedule_next_message(self):
        """If we are not closing our connection to RabbitMQ, schedule another
        message to be delivered in PUBLISH_INTERVAL seconds.

        """
        if self._stopping:
            return
        logger.info('Scheduling next message for %0.1f seconds',
                    self.PUBLISH_INTERVAL)
        self._rabbitmq_connection.add_timeout(self.PUBLISH_INTERVAL,
                                              self.publish_message)

    def get_message_from_selected_data(self):
        """Select the data from the Remocean Database"""
        packet = {};
        try:

            cursor = self._mysql_connection.cursor()

            #
            # The definition of the cursor is it will store the data until its change.
            # So you have to give the indication to the cursor by begining or commiting
            # your connection. This will inform cursor that you have to read new data
            # from the database.
            #
            self._mysql_connection.begin()

            # select the last row from table
            for table_name in self._mysql_table_list:
                #print table_name
                cursor.execute("SELECT * FROM " + table_name)
                packet[table_name] = [];
                for row in cursor.fetchall():
                    #print row
                    packet[table_name].append(row)

            cursor.close();
        except Exception as e:
            self.close_connection()
            return packet;

        return packet;

    def publish_message(self):
        """If the class is not stopping, publish a message to RabbitMQ,
        appending a list of deliveries with the message number that was sent.
        This list will be used to check for delivery confirmations in the
        on_delivery_confirmations method.

        Once the message has been sent, schedule another message to be sent.
        The main reason I put scheduling in was just so you can get a good idea
        of how the process is flowing by slowing down and speeding up the
        delivery intervals by changing the PUBLISH_INTERVAL constant in the
        class.

        """
        if self._stopping:
            return

        # controllo che il servizio di acquisizione sia attivo ...
        # if not self._winservice.isRunning():
        #    LOGGER.info('Win Service is not running...')
        #    print 'Win Service is not running...'
        #    return

        message = self.get_message_from_selected_data();
        #print "***************************************"
        #print json.dumps(message, ensure_ascii=False)
        #print "***************************************"

        properties = pika.BasicProperties(app_id='myrabbit_py-publisher',
                                          content_type='application/json')

        self._channel.basic_publish(self.EXCHANGE,
                                    self.ROUTING_KEY,
                                    json.dumps(message, ensure_ascii=False),
                                    properties)

        self._message_number += 1
        self._deliveries.append(self._message_number)
        logger.info('Published message # %i', self._message_number)
        self.schedule_next_message()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending
        the Channel.Close RPC command.

        """
        logger.info('Closing the channel')
        if self._channel:
            self._channel.close()

    def run(self):
        """Run the code by connecting and then starting the IOLoop.

        """
        self._rabbitmq_connection = self.rabbitmq_connect()
        self._mysql_connection = self.mysql_connect()

        self._rabbitmq_connection.ioloop.start()

    def stop(self):
        """Stop the example by closing the channel and connection. We
        set a flag here so that we stop scheduling new messages to be
        published. The IOLoop is started because this method is
        invoked by the Try/Catch below when KeyboardInterrupt is caught.
        Starting the IOLoop again will allow the publisher to cleanly
        disconnect from RabbitMQ.

        """
        logger.info('Stopping')
        self._stopping = True
        self.close_channel()
        self.close_connection()
        self._rabbitmq_connection.ioloop.start()
        logger.info('Stopped')

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        logger.info('Closing connection')
        self._closing = True
        self._rabbitmq_connection.close()
        self._mysql_connection.close()
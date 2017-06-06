import json
from ConfigParser import SafeConfigParser
from myrabbit_py import MyRabbitPublisher

def main():

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

    myrabbitpublisher = MyRabbitPublisher(rabbit_url,
                                  mysql_url,
                                  mysql_username,
                                  mysql_psw,
                                  mysql_dbname,
                                  mysql_table_list)
    try:
        myrabbitpublisher.run()
    except KeyboardInterrupt:
        myrabbitpublisher.stop()

if __name__ == '__main__':
    main()
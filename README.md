# MyRabbit


![Preview](myrabbit.png)

MyRabbit is an asynchronous publisher app based on pika that dumps selected tables from a MySQL database and publish the output on a RabbitMQ.

## Install


There are a few different ways you can install myrabbit:

* Use setuptools: `easy_install -U myrabbit_py`
* Checkout the source: `git clone https://github.com/bsab/MyRabbit2.git` and install it yourself.


## Getting Started
 Prepare your custom config file 'config.ini':

```ini
    [rabbitmq]
    rabbit_url = amqp://abcdef:fqGUz27xRHZfWJ-D0H0w3ORxJ7O6@rmq.cloudamqp.com/xsdxsd?connection_attempts=3&heartbeat_interval=3600
    
    [mysql]
    mysql_url= 127.0.0.1
    mysql_username= root
    mysql_psw= admin
    mysql_dbname= mydb
    mysql_table_list=[ "tab1", "tab2", "tab3" ]
```

Then include this snippet of code at the beginning of your python scripts:

```python
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
```

## Contributing

Contributions welcome; Please submit all pull requests against the master branch. If your pull request contains Python patches or features, you should include relevant unit tests.
Thanks!

## Author

[Sabatino Severino](https://about.me/the_sab), @bsab

## License

MyRabbit is available under the MIT license. See the LICENSE file for more info.
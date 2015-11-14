Cloudly
=======

[![Codacy Badge](https://api.codacy.com/project/badge/grade/da6052b0ab774f03ac5fe999bea91da5)](https://www.codacy.com/app/koon/cloudly)

Project Cloudly is "The Easiest To Setup" software to Monitor and to control your servers.  It's a first line of defence for your servers and also the ultimate Management Dashboard for your Cloud.
It saves you money and the energies by taking away most of the usual servers monitoring complexities allowing you to focus more on control and better use of your infrastructure.

Cloudly can scale to writing millions of data per 'second' on commodity servers with regular spinning hard drives.  This is due and thanks to the technologies it utilises (e.g. Hadoop/OpenTSDB to begin with).

Cloudly is fully automated and does the servers monitoring for you with close to nothing to setup.



Installation Instructions
-------------------------

In order to run this project in what we call the "Enterprise Mode", please follow the installation instructions below.


###### Install MySQL server and Python MySQLdb

<pre>
$ apt-get install mysql-server python-mysqldb
</pre>

Optionally configure your MySQL server to meet your specific requirements.

As for the user/password, this one needs to match the entries in the cloudly/cloudly/settings.py file.

###### Install various python modules and git

<pre>
$ apt-get install git
$ apt-get install python-dev
$ apt-get install python-django
$ apt-get install python-openssl
$ apt-get install python-pip
</pre>

###### Download the latest version of the Cloudly Project from github

<pre>
$ sudo adduser cloudly
$ su - cloudly
$ git clone https://github.com/ProjectCloudly/cloudly cloudly
$ cd cloudly
</pre>

###### Define project settings

We have prepared an example configuration, just copy it over and modify to meet your specific requirements.

<pre>
$ cp -f cloudly/settings.py.sample cloudly/settings.py
</pre>

###### Install the MongoDB and its python connectors

<pre>
$ apt-get install mongodb
$ pip install pymongo
$ mongoimport --db cloudly --collection services_tags services_tags.json
</pre>

..and configure your server to meet your specific requirements.

###### Create the ORM database and tables

<pre>
$ sudo pip install pymysql
$ mysql -u root -p
mysql> create database cloudly;
</pre>

<pre>
$ python manage.py syncdb
</pre>

If you get an error saying "Access denied for user 'root'@'localhost" then you'd need to edit the cloudly/settings.py and setup the DB section accordingly to your present DB settings.

Assuming this operation succeded, Django will ask you the following:

<pre>
You just installed Django's auth system, which means you don't have any superusers defined.
Would you like to create one now? (yes/no): no
</pre>

Answer "no" to this question.


###### Enable Unicode on the database

<pre>
$ mysql -u root -p
mysql> use cloudly;
mysql> ALTER DATABASE cloudly charset=utf8;
mysql> ALTER TABLE userprofile_profile CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;
</pre>

###### Run the MongoDB

<pre>
$ sudo mkdir /data
$ sudo mkdir /data/db
$ mongod
</pre>

..and configure your server to meet your specific requirements.

###### Install npm, bower and dependencies

<pre>
$ sudo apt-get install nodejs
$ nodejs install npm
$ sudo npm install bower -g
$ npm install
$ bower install
</pre>

###### Run the development server

At this point you should be able to run the administration dashboard (Django App):

<pre>
$ echo Never run this as user root!
$ ./run_devel.sh
</pre>

Now that you have the User Interface (Admin Dashboard) up and running you'd need to get the API started.  You can do so by following the instructions in the next step.


###### Run the API

API server runs off of Flask therefore you'd need to install Python Flask first.  To do so simply copy and paste the following into your terminal window:

<pre>
$ apt-get install python-flask
</pre>

Once you have the Flask installed, simply run the API like so:

<pre>
$ python api.py
</pre>


###### (optional) Configure the web server (NGINX without the SSL support)

First and foremost install the NGINX (and Python Flup module), like so:

<pre>
$ apt-get install nginx
$ apt-get install python-flup
</pre>

Open up your NGINX config file:

<pre>
$ vi /etc/nginx/nginx.conf
</pre>

..and paste in the following configuration:

<pre>
user cloudly cloudly;
worker_processes  2;

error_log /var/log/nginx/error_log info;

events {
    worker_connections  1024;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main
        '$remote_addr - $remote_user [$time_local]'
        '"$request" $status $bytes_sent'
        '"$http_referer" "$http_user_agent"'
        '"$gzip_ratio"';

    gzip on;
    gzip_min_length 1100;
    gzip_buffers 4 8k;
    gzip_types text/plain;
    output_buffers 1 32k;
    postpone_output 1460;
    sendfile on;
    tcp_nopush  on;
    tcp_nodelay on;
    keepalive_timeout 75 20;
    ignore_invalid_headers on;
    index index.xhtml;

    client_header_timeout 10m;
    client_body_timeout 10m;
    send_timeout 10m;
    connection_pool_size 256;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 2k;
    request_pool_size 4k;

    server {
        listen 80;
        server_name projectcloudly.com;
        location /site_media  {
            alias /static/;
            }
        location ~* ^.+\.(jpg|jpeg|gif|png|ico|css|zip|tgz|gz|rar|bz2|doc|xls||pdf|js|counters) {
            access_log   off;
            expires      30d;
            }
        location / {
            fastcgi_pass 127.0.0.1:8080;
            fastcgi_param SERVER_ADDR $server_addr;
            fastcgi_param SERVER_PORT $server_port;
            fastcgi_param SERVER_NAME $server_name;
            fastcgi_param SERVER_PROTOCOL $server_protocol;
            fastcgi_param PATH_INFO $fastcgi_script_name;
            fastcgi_param REQUEST_METHOD $request_method;
            fastcgi_param QUERY_STRING $query_string;
            fastcgi_param CONTENT_TYPE $content_type;
            fastcgi_param CONTENT_LENGTH $content_length;
            fastcgi_pass_header Authorization;
            fastcgi_param REMOTE_ADDR $remote_addr;
            fastcgi_param X_FORWADRD_FOR $proxy_add_x_forwarded_for;
            fastcgi_intercept_errors off;
            }
        access_log  /var/log/nginx/cloudly.access_log main;
        error_log   /var/log/nginx/cloudly.error_log;
        }
    }
</pre>

Great! Now you should be able to run the NGINX server using the WSGI protocol on your very own server (effectively a Django server with the MySQL for the user data and Mongodb for the graphs/logging DB).

For more information about the Django and NGINX configuration see the NGINX Wiki on <a>http://wiki.nginx.org/DjangoFastCGI</a>

For information about the MongoDB visit <a>http://www.mongodb.org/</a>

DB Backends
-----------

###### Install OpenTSDB

Cloudly runs off of Hadoop and is powered by the OpenTSBD.  Please refer to the official OpenTSDB documentation for installation instructions - http://opentsdb.net/docs/build/html/installation.html

..and that's that!  :)

Enjoy!


Screenshots & Live Demo
-----------------------

![alt screen0](https://raw.githubusercontent.com/jparicka/cloudly/master/static/screenshots/screenshot0.png)

![alt screen1](https://raw.githubusercontent.com/jparicka/cloudly/master/static/screenshots/screenshot1.png)

###### Demo

Project can be currently seen on https://projectcloudly.cz/demo

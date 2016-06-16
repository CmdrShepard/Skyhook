Wrapper for the Sonarr Skyhook (TVDB API Wrapper)

# How to install

###### Add Python 3.5 PPA
`sudo add-apt-repository ppa:fkrull/deadsnakes`

###### Install required packages
```
sudo apt-get update
sudo apt-get install git postgresql postgresql-contrib python3.5 python3.5-dev python-pip libpq-dev libxml2-dev libxslt1-dev
```

###### Grab source from GitHub
```
mkdir -p /opt/skyhook
git clone https://github.com/CmdrShepard/Skyhook.git /opt/skyhook
cd /opt/skyhook
```

###### Install virtualenv 
`sudo pip3 install virtualenv`

######Create a virtualenv
```
virtualenv -p `which python3.5` venv
```

###### Install Skyhook
*This might take a bit as LXML takes a while to build.*
```
source venv/bin/activate
pip install uwsgi
pip install -e .
```

###### Open Postgres server
```
sudo su postgres
psql
```

###### Create Skyhook Postgres user and database
```
postgres=# CREATE USER skyhook WITH PASSWORD 'skyhook';
CREATE ROLE
postgres=# CREATE DATABASE skyhook;
CREATE DATABASE
postgres=# GRANT ALL PRIVILEGES ON DATABASE skyhook TO skyhook;
GRANT
postgres=# \q
exit
```

##### Configure Skyhook
Use the Postgres settings you set above for the DB_ items.

Generate an API key from TVDB:http://thetvdb.com/?tab=apiregister

`sudo nano /opt/skyhook/src/instance/config.py`
```
# DATABASE
SEARCH_CACHE_TIME = 86400
DB_HOST = 'localhost'
DB_USERNAME = 'skyhook'
DB_PASSWORD = 'skyhook'
DB_NAME = 'skyhook'
DB_PORT = 5432

# TVDB
# Get TVDB API Key here: http://thetvdb.com/?tab=apiregister
TVDB_API_KEY = None
TVDB_LANGUAGES = ['no', 'en']
```

###### Create a startup script
`sudo nano /etc/init/skyhook.conf`

```
description "uWSGI instance to serve Skyhook"

start on runlevel [2345]
stop on runlevel [!2345]

setuid www-data
setgid www-data

script
  cd /opt/skyhook/src    
  . ../venv/bin/activate
  uwsgi --ini skyhook.ini
end script
```

###### Start Skyhook
`sudo start skyhook`

###### For Nginx (preferred)
`sudo nano /etc/nginx/sites-available/skyhook.sonarr.tv`

```  
server {
  listen 80;
  server_name skyhook.sonarr.tv;
  location / {
    include uwsgi_params;
    uwsgi_pass unix:/tmp/skyhook.sock;
  }
}
```

```
sudo ln -s /etc/nginx/sites-available/skyhook.sonarr.tv /etc/nginx/sites-enabled/skyhook.sonarr.tv
sudo service nginx reload
```

###### For Apache2
```
sudo apt-get install libapache2-mod-wsgi
sudo nano /etc/apache2/sites-available/skyhook.sonarr.tv
```

```
<VirtualHost *:80>
  ServerName skyhook.sonarr.tv

  WSGIDaemonProcess skyhook python-path=/opt/skyhook/src:/opt/skyhook/venv/lib/python3.5/site-packages
  WSGIProcessGroup skyhook
  WSGIScriptAlias / /opt/skyhook/src/wsgi.py
</VirtualHost>
```

```
sudo a2ensite skyhook.sonarr.tv
sudo service apache2 restart
```

###### Edit host file 
`sudo nano /etc/hosts`
```
# Sonarr
127.0.0.1 skyhook.sonarr.tv
```

###### Testing
**By ID TVDB:**

Game of Thrones: http://skyhook.sonarr.tv/v1/tvdb/shows/en/121361

Norske Rednecks: http://skyhook.sonarr.tv/v1/tvdb/shows/en/307674

**Search:**

Norske Rednecks: http://skyhook.sonarr.tv/v1/tvdb/search/en/?term=norske%20rednecks

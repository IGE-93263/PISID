import os
import mysql.connector

MYSQL_CONFIG = {
    "host":     os.environ.get("MYSQL_HOST",     "localhost"),
    "user":     os.environ.get("MYSQL_USER",     "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "root"),
    "database": os.environ.get("MYSQL_DATABASE", "labirinto"),
    "port":     int(os.environ.get("MYSQL_PORT", 3306)),
}

def get_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

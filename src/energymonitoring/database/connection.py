import os

import pymysql


def get_connection():
    return pymysql.connect(
        host=os.environ["ENERGY_DB_HOST"],
        port=int(os.getenv("ENERGY_DB_PORT", "3306")),
        user=os.environ["ENERGY_DB_USER"],
        password=os.environ["ENERGY_DB_PASSWORD"],
        database=os.environ["ENERGY_DB_NAME"],
        autocommit=False,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
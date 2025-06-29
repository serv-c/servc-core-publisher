import os

QUEUE_NAME = os.getenv("QUEUE_NAME", "publisher")
SQL_DIALECT = os.getenv("SQL_DIALECT", "sqlite")

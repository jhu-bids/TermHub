import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
# from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
# from pymysql.err import DataError

from backend.db.config import BRAND_NEW_DB_URL, DB_URL, DDL_PATH
# from backend.db.config import BRAND_NEW_DB_URL, DDL_PATH


def get_mysql_connection():
  engine = create_engine(DB_URL)
  return engine.connect()


def run_sql(con, command):
  statement = text(command)
  try:
    return con.execute(statement)
  except (ProgrammingError, OperationalError):
    raise RuntimeError(f'Got an error executing the following statement:\n{command}')


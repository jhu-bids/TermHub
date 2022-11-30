from typing import Any, Dict, List, Union, Set
import json
import pandas as pd
import sqlalchemy.engine.base
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
# from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
# from pymysql.err import DataError

from backend.db.config import DB_URL #, BRAND_NEW_DB_URL, DDL_PATH
# from backend.db.config import BRAND_NEW_DB_URL, DDL_PATH


def get_mysql_connection():
  engine = create_engine(DB_URL)
  return engine.connect()


def sql_query(con: sqlalchemy.engine.base.Connection,
              query: Union[sqlalchemy.sql.text, str],
              params: Dict = {}):
  """
  https://stackoverflow.com/a/39414254/1368860:
  query = "SELECT * FROM my_table t WHERE t.id = ANY(:ids);"
  conn.execute(sqlalchemy.text(query), ids=some_ids)
  """
  try:
    if type(query) != text:
      query = text(query)
    q = con.execute(query, **params)
    return q.fetchall()
  except (ProgrammingError, OperationalError) as err:
    raise RuntimeError(f'Got an error executing the following statement:\n{query}, {json.dumps(params, indent=2)}')



def run_sql(con, command):
  statement = text(command)
  try:
    return con.execute(statement)
  except (ProgrammingError, OperationalError):
    raise RuntimeError(f'Got an error executing the following statement:\n{command}')


"""Initialize database"""
from sqlalchemy import create_engine
# from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text

# from backend.db.config import BRAND_NEW_DB_URL, DB_URL, DDL_PATH
from backend.db.config import BRAND_NEW_DB_URL, DDL_PATH


def initialize(db_url: str):
    """Initialize set up of DB

    Resources
    - https://docs.sqlalchemy.org/en/20/core/engines.html
    - https://docs.sqlalchemy.org/en/20/dialects/mysql.html

    todo: (can do in ddl.sql): don't do anything if these tables exist & initialized
    """
    engine = create_engine(db_url)
    with engine.connect() as con:
        with open(DDL_PATH, 'r') as file:
            contents = file.read()
        statement = text(contents)
        # TODO: Fix syntax error
        # sqlalchemy.exc.ProgrammingError: (pymysql.err.ProgrammingError) (1064, "You have an error in your SQL syntax;
        con.execute(statement)

    return


if __name__ == '__main__':
    # May not ever need to connect directly to 'termhub' db, at least not in initialization
    # try:
    #     initialize(DB_URL)
    # except OperationalError:
    #     initialize(BRAND_NEW_DB_URL)
    initialize(BRAND_NEW_DB_URL)

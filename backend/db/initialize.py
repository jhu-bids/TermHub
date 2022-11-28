"""Initialize database"""
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
# from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text

from backend.db.config import BRAND_NEW_DB_URL, DB_URL, DDL_PATH
# from backend.db.config import BRAND_NEW_DB_URL, DDL_PATH


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
            contents: str = file.read()
        # Attempt 2: pandas
        # (moved down)

        # Attempt 1: execute sql text
        # commands: List[str] = [x + ';' for x in contents.split(';\n')]
        # for command in commands:
        #     statement = text(command)
        #     try:
        #         con.execute(statement)
        #     except (ProgrammingError, OperationalError):
        #         raise RuntimeError(f'Got an error executing the following statement:\n{command}')

        # Insert data
        import pandas as pd
        df = pd.read_csv('/Users/joeflack4/projects/TermHub/termhub-csets/datasets/prepped_files/code_sets.csv')
        # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
        # df.to_sql(name, con, schema=None, if_exists='fail', index=True, index_label=None, chunksize=None, dtype=None, method=None)
        # todo: fix
        # sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (1054, "Unknown column 'index' in 'field list'")
        con.execute(text('TRUNCATE code_sets;'))
        df.to_sql('code_sets', con, if_exists='append', index=False)
        # xxx = df.iloc[0]['A']

    return


# pymysql.err.OperationalError: (1290, 'The MySQL server is running with the --secure-file-priv option so it cannot execute this statement')


if __name__ == '__main__':
    # May not ever need to connect directly to 'termhub' db, at least not in initialization
    # try:
    #     initialize(DB_URL)
    # except OperationalError:
    #     initialize(BRAND_NEW_DB_URL)
    initialize(DB_URL)

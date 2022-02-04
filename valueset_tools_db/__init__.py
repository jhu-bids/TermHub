"""TODO: Set up code to:
1. create the db (optional if we want to automate this)
2. read from db
3. write to db
We can re-use this 'package' in both 'enclave_wrangler' and 'vsac_wrangler'.

# Use cases
1. OID::ID mappings: It looks like we probably don't need to do this.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from valueset_tools_db.config import APP_ROOT, config


db_create_file = os.path.join(APP_ROOT, 'db_create.sql')


engine = create_engine(
    f"postgresql://{config['db_user']}:{config['db_pass']}@{config['db_host']}:{config['db_port']}/{config['db_db']}",
    echo=True)
with engine.connect() as con:
    file = open("src/models/query.sql")
    query = text(file.read())

    con.execute(query)


def create_db():
    """Create db"""
    pass

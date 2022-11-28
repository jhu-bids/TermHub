import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import inspect
from sqlalchemy.sql import text

engine = create_engine('sqlite:///bookstore.db')
with engine.connect() as con:
    pass
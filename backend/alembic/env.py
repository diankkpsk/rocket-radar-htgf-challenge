from alembic import context
from sqlalchemy import create_engine
from backend.store import dbpath

path = dbpath()
path.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine("sqlite:///" + str(path))
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()

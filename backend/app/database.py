import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    # make a connection to the database
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "nittany_auction"),
        cursorclass=pymysql.cursors.DictCursor,  # return rows as dicts
    )
    return connection


def get_db():
    """
    FastAPI dependency that gives a pymysql connection
    automatically closes the connection when the request is done so we dont have to worry about that

    usage in a route that i got from docs/previous project:
        @router.get("/example")
        def example(db=Depends(get_db)):
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM User")
                return cursor.fetchall()
    """
    connection = get_db_connection()
    try:
        yield connection
    finally:
        connection.close()

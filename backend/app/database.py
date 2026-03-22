import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """
    Create and return a raw pymysql connection using environment variables.
    """
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
    FastAPI dependency that yields a pymysql connection.
    Automatically closes the connection when the request is done.

    Usage in a route:
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

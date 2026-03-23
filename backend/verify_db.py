import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "nittany_auction")
        )
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    tables = [
        "User", "ZipCode", "Bidder", "Seller", "LocalVendor", 
        "HelpDesk", "CreditCard", "Category", "Product", 
        "Bid", "Transaction", "Rating", "Request"
    ]
    
    print("----- Database Row Counts -----")
    with conn.cursor() as cursor:
        for t in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                count = cursor.fetchone()[0]
                print(f"{t.ljust(15)}: {count} rows")
            except Exception as e:
                print(f"{t.ljust(15)}: Error ({e})")
                
        print("\n----- Checking Password Hashing -----")
        cursor.execute("SELECT email, password FROM User LIMIT 3")
        for row in cursor.fetchall():
            print(f"User: {row[0]}")
            print(f"Hash: {row[1][:20]}... (Length: {len(row[1])})")

    conn.close()

if __name__ == "__main__":
    main()

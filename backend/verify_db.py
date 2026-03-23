"""
verify_db.py — Quick check that the database was populated correctly.
Usage:  python verify_db.py
"""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# Connect to the database
conn = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "nittany_auction"),
)
cursor = conn.cursor()

# Print row counts for each table
print("--- Table Row Counts ---")
tables = ["User", "ZipCode", "Bidder", "Seller", "LocalVendor",
          "HelpDesk", "CreditCard", "Category", "Product",
          "Bid", "Transaction", "Rating", "Request", "Sessions"]

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")
    except:
        print(f"  {table}: (table not found)")

# Show a few users to confirm passwords are hashed
print("\n--- Sample Users (password should be a 64-char SHA-256 hash) ---")
cursor.execute("SELECT email, password FROM User LIMIT 3")
for email, password in cursor.fetchall():
    print(f"  {email}  ->  {password[:20]}... (length: {len(password)})")

cursor.close()
conn.close()

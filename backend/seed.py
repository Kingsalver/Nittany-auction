import csv
import hashlib
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "nittany_auction"),
        autocommit=True
    )
    
    csv_file_path = "/Users/benparr/Downloads/NittanyAuctionDataset_v1/Users.csv"
    
    with connection.cursor() as cursor:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                email = row['email'].strip()
                raw_password = row['password'].strip()
                hashed_password = hash_password(raw_password)
                
                # Derive a name from the email
                name = email.split('@')[0]
                
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO User (email, password, name) VALUES (%s, %s, %s)",
                        (email, hashed_password, name)
                    )
                    
                    # Distribute users into Seller, HelpDesk, and Bidder
                    if i % 3 == 0:
                        cursor.execute("INSERT IGNORE INTO Seller (email) VALUES (%s)", (email,))
                    elif i % 3 == 1:
                        cursor.execute("INSERT IGNORE INTO HelpDesk (email, staff_role) VALUES (%s, 'Support Representative')", (email,))
                    else:
                        cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (email,))
                except Exception as e:
                    print(f"Error inserting {email}: {e}")
                    
        print(f"Data population complete! Checked rows up to index {i}.")
    connection.close()

if __name__ == "__main__":
    main()

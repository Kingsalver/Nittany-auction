"""
setup_db.py — Populates the NittanyAuction database from the CSV dataset.
Run this after creating the schema:  mysql -u root -p < schema.sql
Usage:  python setup_db.py
"""

import os
import csv
import hashlib
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def hash_password(password):
    """Hash a password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def parse_date(date_str):
    """Convert a date like '03/15/26' to '2026-03-15 00:00:00'."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%y").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def main():
    # Connect to MySQL
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "nittany_auction"),
        autocommit=True
    )
    cursor = conn.cursor()

    # Path to CSV files
    data_dir = os.path.join(os.path.dirname(__file__), "resources", "NittanyAuctionDataset_v1")

    # ---- Load addresses into a dictionary so we can look them up later ----
    print("Loading addresses...")
    addresses = {}
    with open(os.path.join(data_dir, "Address.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            addr_id = row["address_id"]
            street = (row.get("street_num", "") + " " + row.get("street_name", "")).strip()
            addresses[addr_id] = {"zip": row.get("zipcode"), "street": street}

    # ---- Load names from Bidders CSV so we can put a name on each User ----
    print("Loading bidder names...")
    names = {}
    with open(os.path.join(data_dir, "Bidders.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip()
            names[email] = (row.get("first_name", "") + " " + row.get("last_name", "")).strip()

    # ---- 1. ZipCode ----
    print("Inserting ZipCode...")
    with open(os.path.join(data_dir, "Zipcode_Info.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cursor.execute(
                "INSERT IGNORE INTO ZipCode (zip, city, state) VALUES (%s, %s, %s)",
                (row["zipcode"], row["city"], row["state"])
            )

    # ---- 2. User (passwords are hashed with SHA-256) ----
    print("Inserting User...")
    with open(os.path.join(data_dir, "Users.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip()
            hashed = hash_password(row["password"].strip())
            name = names.get(email, email.split("@")[0])  # use bidder name if available
            cursor.execute(
                "INSERT IGNORE INTO User (email, password, name) VALUES (%s, %s, %s)",
                (email, hashed, name)
            )

    # Helper: make sure a user exists before inserting into a child table
    def ensure_user(email, name=""):
        cursor.execute("SELECT email FROM User WHERE email = %s", (email,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT IGNORE INTO User (email, password, name) VALUES (%s, %s, %s)",
                (email, hash_password("default123"), name or email.split("@")[0])
            )

    # ---- 3. Bidder ----
    print("Inserting Bidder...")
    with open(os.path.join(data_dir, "Bidders.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip()
            addr = addresses.get(row.get("home_address_id", "").strip(), {})
            ensure_user(email, (row.get("first_name", "") + " " + row.get("last_name", "")).strip())
            cursor.execute(
                "INSERT IGNORE INTO Bidder (email, street, zip, major, age) VALUES (%s, %s, %s, %s, %s)",
                (email, addr.get("street"), addr.get("zip"), row.get("major") or None, row.get("age") or None)
            )

    # ---- 4. Seller ----
    print("Inserting Seller...")
    with open(os.path.join(data_dir, "Sellers.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip()
            ensure_user(email)
            cursor.execute(
                "INSERT IGNORE INTO Seller (email, bank_routing_no, bank_account_no, account_balance) VALUES (%s, %s, %s, %s)",
                (email, row.get("bank_routing_number"), row.get("bank_account_number"), row.get("balance", 0))
            )

    # ---- 5. LocalVendor ----
    print("Inserting LocalVendor...")
    with open(os.path.join(data_dir, "Local_Vendors.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = row["Email"].strip()
            ensure_user(email, row.get("Business_Name"))
            cursor.execute("INSERT IGNORE INTO Seller (email) VALUES (%s)", (email,))
            addr = addresses.get(row.get("Business_Address_ID", "").strip(), {})
            cursor.execute(
                "INSERT IGNORE INTO LocalVendor (email, business_name, business_address, customer_service_phone) VALUES (%s, %s, %s, %s)",
                (email, row.get("Business_Name"), addr.get("street"), row.get("Customer_Service_Phone_Number"))
            )

    # ---- 6. HelpDesk ----
    print("Inserting HelpDesk...")
    with open(os.path.join(data_dir, "Helpdesk.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip()
            ensure_user(email)
            cursor.execute(
                "INSERT IGNORE INTO HelpDesk (email, staff_role) VALUES (%s, %s)",
                (email, row.get("Position", "Support"))
            )

    # ---- 7. CreditCard ----
    print("Inserting CreditCard...")
    with open(os.path.join(data_dir, "Credit_Cards.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            month = row.get("expire_month", "1").zfill(2)
            year = row.get("expire_year", "2025")
            cursor.execute(
                "INSERT IGNORE INTO CreditCard (card_number, email, card_type, expiration_date) VALUES (%s, %s, %s, %s)",
                (row["credit_card_num"].strip(), row["Owner_email"].strip(), row.get("card_type"), f"{year}-{month}-01")
            )

    # ---- 8. Category ----
    print("Inserting Category...")
    with open(os.path.join(data_dir, "Categories.csv"), encoding="utf-8-sig") as f:
        cat_rows = list(csv.DictReader(f))

    # First pass: insert all unique category names
    all_names = set()
    for row in cat_rows:
        if row.get("category_name"):
            all_names.add(row["category_name"].strip())
        if row.get("parent_category"):
            all_names.add(row["parent_category"].strip())
    for name in all_names:
        cursor.execute("INSERT IGNORE INTO Category (category_name) VALUES (%s)", (name,))

    # Build a name -> id lookup
    cursor.execute("SELECT category_id, category_name FROM Category")
    cat_ids = {}
    for row in cursor.fetchall():
        cat_ids[row[1]] = row[0]

    # Second pass: set parent_category_id
    for row in cat_rows:
        cname = row.get("category_name", "").strip()
        pname = row.get("parent_category", "").strip()
        if cname and pname:
            cursor.execute(
                "UPDATE Category SET parent_category_id = %s WHERE category_id = %s",
                (cat_ids[pname], cat_ids[cname])
            )

    # ---- 9. Product (from Auction_Listings) ----
    print("Inserting Product...")
    with open(os.path.join(data_dir, "Auction_Listings.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            seller = row["Seller_Email"].strip()
            ensure_user(seller)
            cursor.execute("INSERT IGNORE INTO Seller (email) VALUES (%s)", (seller,))
            cat_id = cat_ids.get(row["Category"].strip())
            price = row.get("Reserve_Price", "0").replace("$", "").replace(",", "").strip() or "0"
            status = "active" if row.get("Status") == "1" else "inactive"
            cursor.execute(
                "INSERT IGNORE INTO Product (product_id, seller_email, category_id, title, description, reserve_price, auction_end_time, listing_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (row["Listing_ID"], seller, cat_id, row.get("Auction_Title", row.get("Product_Name")), row.get("Product_Description"), price, "2026-12-31 23:59:59", status)
            )

    # ---- 10. Bid ----
    print("Inserting Bid...")
    with open(os.path.join(data_dir, "Bids.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            bidder = row["Bidder_Email"].strip()
            ensure_user(bidder)
            cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (bidder,))
            cursor.execute(
                "INSERT IGNORE INTO Bid (bid_id, product_id, bidder_email, bid_amount) VALUES (%s, %s, %s, %s)",
                (row["Bid_ID"], row["Listing_ID"], bidder, row["Bid_Price"])
            )

    # ---- 11. Transaction ----
    print("Inserting Transaction...")
    with open(os.path.join(data_dir, "Transactions.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            # Find the matching bid
            cursor.execute(
                "SELECT bid_id FROM Bid WHERE product_id = %s AND bidder_email = %s ORDER BY bid_amount DESC LIMIT 1",
                (row["Listing_ID"], row["Bidder_Email"])
            )
            bid = cursor.fetchone()
            if bid:
                pay_date = parse_date(row.get("Date")) or "2026-01-01 00:00:00"
                cursor.execute(
                    "INSERT IGNORE INTO Transaction (transaction_id, bid_id, product_id, bidder_email, seller_email, final_amount, payment_status, payment_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (row["Transaction_ID"], bid[0], row["Listing_ID"], row["Bidder_Email"], row["Seller_Email"], row["Payment"], "completed", pay_date)
                )

    # ---- 12. Rating ----
    print("Inserting Rating...")
    with open(os.path.join(data_dir, "Ratings.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cursor.execute(
                "SELECT transaction_id FROM Transaction WHERE bidder_email = %s AND seller_email = %s LIMIT 1",
                (row["Bidder_Email"], row["Seller_Email"])
            )
            txn = cursor.fetchone()
            if txn:
                cursor.execute(
                    "INSERT IGNORE INTO Rating (transaction_id, score, comment) VALUES (%s, %s, %s)",
                    (txn[0], row["Rating"], row.get("Rating_Desc"))
                )

    # ---- 13. Request ----
    print("Inserting Request...")
    with open(os.path.join(data_dir, "Requests.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ensure_user(row["sender_email"].strip())
            status = "resolved" if row.get("request_status") == "1" else "pending"
            cursor.execute(
                "INSERT IGNORE INTO Request (request_id, submitted_by_email, request_type, status) VALUES (%s, %s, %s, %s)",
                (row["request_id"], row["sender_email"], row["request_type"], status)
            )

    cursor.close()
    conn.close()
    print("Done! Database is fully populated.")


if __name__ == "__main__":
    main()

import os
import csv
import hashlib
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# load the env vars
load_dotenv()

# where the data is
DATA_DIR = os.path.join(os.path.dirname(__file__), "resources", "NittanyAuctionDataset_v1")

# hashing function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def csv_path(filename):
    return os.path.join(DATA_DIR, filename)

# converts the date format for mysql
def parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def read_csv(filename):
    with open(csv_path(filename), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

# helper to make sure a user exists before we add related rows
def ensure_user(cursor, email, name=""):
    cursor.execute("SELECT 1 FROM User WHERE email = %s", (email,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT IGNORE INTO User (email, password, name) VALUES (%s, %s, %s)",
            (email, hash_password("default123"), name or email.split("@")[0]),
        )

# -- SEEDING STUFF --

def seed_zipcodes(cursor):
    print("loading zipcodes...")
    rows = read_csv("Zipcode_Info.csv")
    inserted = 0
    for row in rows:
        cursor.execute(
            "INSERT IGNORE INTO ZipCode (zipcode, city, state) VALUES (%s, %s, %s)",
            (row["zipcode"].strip(), row["city"].strip(), row["state"].strip()),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_users(cursor):
    print("loading users...")
    names = {}
    for row in read_csv("Bidders.csv"):
        email = row["email"].strip()
        names[email] = (row.get("first_name", "") + " " + row.get("last_name", "")).strip()

    rows = read_csv("Users.csv")
    inserted = 0
    for row in rows:
        email = row["email"].strip()
        hashed = hash_password(row["password"].strip())
        name = names.get(email, email.split("@")[0])
        cursor.execute(
            "INSERT IGNORE INTO User (email, password, name) VALUES (%s, %s, %s)",
            (email, hashed, name),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_addresses(cursor):
    print("loading addresses...")
    rows = read_csv("Address.csv")
    inserted = 0
    for row in rows:
        cursor.execute(
            "INSERT IGNORE INTO Address (address_id, zipcode, street_num, street_name) "
            "VALUES (%s, %s, %s, %s)",
            (
                row["address_id"].strip(),
                row["zipcode"].strip() or None,
                row["street_num"].strip() or None,
                row["street_name"].strip() or None,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_bidders(cursor):
    print("loading bidders...")
    rows = read_csv("Bidders.csv")
    inserted = 0
    for row in rows:
        email = row["email"].strip()
        ensure_user(cursor, email,
                    (row.get("first_name", "") + " " + row.get("last_name", "")).strip())

        addr_id = row.get("home_address_id", "").strip() or None
        if addr_id:
            cursor.execute("SELECT 1 FROM Address WHERE address_id = %s", (addr_id,))
            if not cursor.fetchone():
                addr_id = None

        cursor.execute(
            "INSERT IGNORE INTO Bidder "
            "(email, first_name, last_name, age, home_address_id, major) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                email,
                row.get("first_name", "").strip() or None,
                row.get("last_name", "").strip() or None,
                int(row["age"]) if row.get("age") else None,
                addr_id,
                row.get("major", "").strip() or None,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_sellers(cursor):
    print("loading sellers...")
    rows = read_csv("Sellers.csv")
    inserted = 0
    for row in rows:
        email = row["email"].strip()
        ensure_user(cursor, email)
        cursor.execute(
            "INSERT IGNORE INTO Seller "
            "(email, bank_routing_number, bank_account_number, balance) "
            "VALUES (%s, %s, %s, %s)",
            (
                email,
                row.get("bank_routing_number", "").strip() or None,
                row.get("bank_account_number", "").strip() or None,
                float(row["balance"]) if row.get("balance") else 0.0,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_local_vendors(cursor):
    print("loading local vendors...")
    rows = read_csv("Local_Vendors.csv")
    inserted = 0
    for row in rows:
        email = row["Email"].strip()
        ensure_user(cursor, email, row.get("Business_Name", ""))
        cursor.execute("INSERT IGNORE INTO Seller (email) VALUES (%s)", (email,))

        addr_id = row.get("Business_Address_ID", "").strip() or None
        if addr_id:
            cursor.execute("SELECT 1 FROM Address WHERE address_id = %s", (addr_id,))
            if not cursor.fetchone():
                addr_id = None

        cursor.execute(
            "INSERT IGNORE INTO LocalVendor "
            "(email, business_name, business_address_id, customer_service_phone) "
            "VALUES (%s, %s, %s, %s)",
            (
                email,
                row.get("Business_Name", "").strip(),
                addr_id,
                row.get("Customer_Service_Phone_Number", "").strip() or None,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_helpdesk(cursor):
    print("loading helpdesk...")
    ensure_user(cursor, "helpdeskteam@lsu.edu", "HelpDesk Team")

    rows = read_csv("Helpdesk.csv")
    inserted = 0
    for row in rows:
        email = row["email"].strip()
        ensure_user(cursor, email)
        cursor.execute(
            "INSERT IGNORE INTO HelpDesk (email, position) VALUES (%s, %s)",
            (email, row.get("Position", "Support").strip()),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_credit_cards(cursor):
    print("loading cards...")
    rows = read_csv("Credit_Cards.csv")
    inserted = 0
    for row in rows:
        owner = row["Owner_email"].strip()
        cursor.execute("SELECT 1 FROM Bidder WHERE email = %s", (owner,))
        if not cursor.fetchone():
            continue

        cursor.execute(
            "INSERT IGNORE INTO CreditCard "
            "(credit_card_num, card_type, expire_month, expire_year, "
            " security_code, owner_email) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                row["credit_card_num"].strip(),
                row.get("card_type", "").strip() or None,
                int(row["expire_month"]) if row.get("expire_month") else None,
                int(row["expire_year"]) if row.get("expire_year") else None,
                row.get("security_code", "").strip() or None,
                owner,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

# 2 pass approach to handle parents
def seed_categories(cursor):
    print("loading categories (pass 1)...")
    rows = read_csv("Categories.csv")

    all_names = set()
    for row in rows:
        if row.get("category_name", "").strip():
            all_names.add(row["category_name"].strip())
        if row.get("parent_category", "").strip():
            all_names.add(row["parent_category"].strip())

    inserted = 0
    for name in all_names:
        cursor.execute(
            "INSERT IGNORE INTO Category (category_name) VALUES (%s)", (name,)
        )
        inserted += cursor.rowcount

    print("loading categories (pass 2)...")
    updated = 0
    for row in rows:
        cname = row.get("category_name", "").strip()
        pname = row.get("parent_category", "").strip()
        if cname and pname:
            cursor.execute(
                "UPDATE Category SET parent_category = %s WHERE category_name = %s",
                (pname, cname),
            )
            updated += cursor.rowcount
    print(f"done.")

def seed_products(cursor):
    print("loading products...")
    rows = read_csv("Auction_Listings.csv")
    inserted = 0
    for row in rows:
        seller = row["Seller_Email"].strip()
        ensure_user(cursor, seller)
        cursor.execute("INSERT IGNORE INTO Seller (email) VALUES (%s)", (seller,))

        listing_id = int(row["Listing_ID"])
        category = row["Category"].strip()
        auction_title = (row.get("Auction_Title") or row.get("Product_Name") or "").strip()
        product_name = row.get("Product_Name", "").strip() or None
        description = row.get("Product_Description", "").strip() or None
        quantity = int(row["Quantity"]) if row.get("Quantity") else 1
        price = row.get("Reserve_Price", "0").replace("$", "").replace(",", "").strip() or "0"
        max_bids = int(row["Max_bids"]) if row.get("Max_bids") else 1
        status_val = row.get("Status", "1").strip()
        
        if status_val == "1":
            listing_status = "active"
        elif status_val == "2":
            listing_status = "sold"
        else:
            listing_status = "inactive"

        cursor.execute(
            "SELECT 1 FROM Category WHERE category_name = %s", (category,)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT IGNORE INTO Category (category_name) VALUES (%s)", (category,)
            )

        cursor.execute(
            "INSERT IGNORE INTO Product "
            "(seller_email, listing_id, category_name, auction_title, product_name, "
            " product_description, quantity, reserve_price, max_bids, listing_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                seller, listing_id, category, auction_title, product_name,
                description, quantity, float(price), max_bids, listing_status,
            ),
        )
        inserted += cursor.rowcount

    # need this lookup for bids and stuff
    cursor.execute("SELECT product_id, seller_email, listing_id FROM Product")
    lookup = {}
    for pid, semail, lid in cursor.fetchall():
        lookup[(semail, int(lid))] = pid
    print(f"done. {inserted} rows.")
    return lookup

def seed_bids(cursor, product_lookup):
    print("loading bids...")
    rows = read_csv("Bids.csv")
    inserted = 0
    for row in rows:
        seller = row["Seller_Email"].strip()
        listing_id = int(row["Listing_ID"])
        bidder = row["Bidder_Email"].strip()

        product_id = product_lookup.get((seller, listing_id))
        if product_id is None:
            continue

        ensure_user(cursor, bidder)
        cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (bidder,))

        price = row.get("Bid_Price", "0").replace("$", "").replace(",", "").strip() or "0"
        cursor.execute(
            "INSERT IGNORE INTO Bid "
            "(bid_id, product_id, listing_id, seller_email, bidder_email, bid_price) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (int(row["Bid_ID"]), product_id, listing_id, seller, bidder, float(price)),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_transactions(cursor, product_lookup):
    print("loading transactions...")
    rows = read_csv("Transactions.csv")
    inserted = 0
    for row in rows:
        seller = row["Seller_Email"].strip()
        listing_id = int(row["Listing_ID"])
        buyer = row["Bidder_Email"].strip()

        product_id = product_lookup.get((seller, listing_id))
        if product_id is None:
            continue

        ensure_user(cursor, buyer)
        cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (buyer,))

        payment = row.get("Payment", "0").replace("$", "").replace(",", "").strip() or "0"
        pay_date = parse_date(row.get("Date"))

        cursor.execute(
            "INSERT IGNORE INTO Transaction "
            "(transaction_id, product_id, listing_id, seller_email, buyer_email, "
            " payment_date, payment, payment_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                int(row["Transaction_ID"]),
                product_id,
                listing_id,
                seller,
                buyer,
                pay_date,
                float(payment),
                "completed",
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_ratings(cursor):
    print("loading ratings...")
    rows = read_csv("Ratings.csv")
    inserted = 0
    for row in rows:
        bidder = row["Bidder_Email"].strip()
        seller = row["Seller_Email"].strip()
        rating_date = parse_date(row.get("Date"))
        if not rating_date:
            continue

        score = row.get("Rating", "").strip()
        if not score:
            continue

        ensure_user(cursor, bidder)
        cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (bidder,))
        ensure_user(cursor, seller)
        cursor.execute("INSERT IGNORE INTO Seller (email) VALUES (%s)", (seller,))

        cursor.execute(
            "INSERT IGNORE INTO Rating "
            "(bidder_email, seller_email, rating_date, rating, rating_desc) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                bidder,
                seller,
                rating_date,
                int(score),
                row.get("Rating_Desc", "").strip() or None,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

def seed_requests(cursor):
    print("loading requests...")
    rows = read_csv("Requests.csv")
    inserted = 0
    for row in rows:
        sender = row["sender_email"].strip()
        ensure_user(cursor, sender)

        staff = row.get("helpdesk_staff_email", "helpdeskteam@lsu.edu").strip()
        if not staff:
            staff = "helpdeskteam@lsu.edu"
        status = 1 if row.get("request_status", "0").strip() == "1" else 0

        cursor.execute(
            "INSERT IGNORE INTO Request "
            "(request_id, sender_email, helpdesk_staff_email, request_type, "
            " request_desc, request_status) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                int(row["request_id"]),
                sender,
                staff,
                row.get("request_type", "").strip(),
                row.get("request_desc", "").strip() or None,
                status,
            ),
        )
        inserted += cursor.rowcount
    print(f"done. {inserted} rows.")

# stuff we have to do after loading
def post_process(cursor):
    print("running post-processing...")
    
    # categories is_leaf
    cursor.execute("UPDATE Category SET is_leaf = FALSE")
    cursor.execute("""
        UPDATE Category
        SET is_leaf = TRUE
        WHERE category_name NOT IN (
            SELECT parent_category FROM (
                SELECT DISTINCT parent_category
                FROM Category
                WHERE parent_category IS NOT NULL
            ) AS parents
        )
    """)

    # seller ratings
    cursor.execute("""
        UPDATE Seller s
        SET avg_rating = (
            SELECT ROUND(AVG(r.rating), 2)
            FROM Rating r
            WHERE r.seller_email = s.email
        )
    """)

    # mark products as sold
    cursor.execute("""
        UPDATE Product p
        JOIN Transaction t ON t.product_id = p.product_id
        SET p.listing_status = 'sold'
        WHERE t.payment_status = 'completed'
          AND p.listing_status != 'sold'
    """)
    print("post-processing done.")

def main():
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "nittany_auction"),
        autocommit=False,
    )
    cursor = conn.cursor()

    try:
        print("SEEDING START...")

        seed_zipcodes(cursor)
        seed_users(cursor)
        seed_addresses(cursor)
        seed_bidders(cursor)
        seed_sellers(cursor)
        seed_local_vendors(cursor)
        seed_helpdesk(cursor)
        seed_credit_cards(cursor)
        seed_categories(cursor)
        product_lookup = seed_products(cursor)
        seed_bids(cursor, product_lookup)
        seed_transactions(cursor, product_lookup)
        seed_ratings(cursor)
        seed_requests(cursor)

        post_process(cursor)

        conn.commit()
        print("DONE!")

    except Exception as e:
        conn.rollback()
        print(f"FAILED: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()

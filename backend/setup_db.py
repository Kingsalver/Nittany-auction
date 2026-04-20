"""
setup_db.py — Populates the NittanyAuction database from CSV dataset.

Usage:
    mysql -u root -p < schema.sql   # create tables first
    python setup_db.py              # then seed data

Load order (dependency-safe):
    1.  ZipCode        (no deps)
    2.  User           (no deps)
    3.  Address        (depends on ZipCode)
    4.  Bidder         (depends on User, Address)
    5.  Seller         (depends on User)
    6.  LocalVendor    (depends on Seller, Address)
    7.  HelpDesk       (depends on User)
    8.  CreditCard     (depends on Bidder)
    9.  Category       pass-1: insert names with NULL parent
    10. Category       pass-2: set parent_category relationships
    11. Product        (depends on Seller, Category)
    12. Bid            (depends on Product, Bidder, Seller)
    13. Transaction    (depends on Product, Seller, Bidder)
    14. Rating         (depends on Bidder, Seller)
    15. Request        (depends on User)
    --- post-processing ---
    16. UPDATE Category.is_leaf
    17. UPDATE Seller.avg_rating
    18. UPDATE Product.listing_status = 'sold' for completed transactions
"""

import os
import csv
import hashlib
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "resources", "NittanyAuctionDataset_v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def csv_path(filename):
    return os.path.join(DATA_DIR, filename)


def parse_date(date_str):
    """Convert '05/05/21' → '2021-05-05'. Returns None on failure."""
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


def ensure_user(cursor, email, name=""):
    """Insert a User row if one doesn't exist yet (used when a CSV table
    references an email that might not be in Users.csv)."""
    cursor.execute("SELECT 1 FROM User WHERE email = %s", (email,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT IGNORE INTO User (email, password, name) VALUES (%s, %s, %s)",
            (email, hash_password("default123"), name or email.split("@")[0]),
        )


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_zipcodes(cursor):
    print("  Loading ZipCode...")
    rows = read_csv("Zipcode_Info.csv")
    inserted = 0
    for row in rows:
        cursor.execute(
            "INSERT IGNORE INTO ZipCode (zipcode, city, state) VALUES (%s, %s, %s)",
            (row["zipcode"].strip(), row["city"].strip(), row["state"].strip()),
        )
        inserted += cursor.rowcount
    print(f"    {inserted} rows inserted")


def seed_users(cursor):
    """Insert User rows. Names come from Bidders.csv where available."""
    print("  Loading User...")
    # Build name lookup from Bidders
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
    print(f"    {inserted} rows inserted")


def seed_addresses(cursor):
    print("  Loading Address...")
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
    print(f"    {inserted} rows inserted")


def seed_bidders(cursor):
    print("  Loading Bidder...")
    rows = read_csv("Bidders.csv")
    inserted = 0
    for row in rows:
        email = row["email"].strip()
        ensure_user(cursor, email,
                    (row.get("first_name", "") + " " + row.get("last_name", "")).strip())

        addr_id = row.get("home_address_id", "").strip() or None
        # Verify address_id actually exists (data quality guard)
        if addr_id:
            cursor.execute("SELECT 1 FROM Address WHERE address_id = %s", (addr_id,))
            if not cursor.fetchone():
                addr_id = None  # orphan reference — drop the FK

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
    print(f"    {inserted} rows inserted")


def seed_sellers(cursor):
    print("  Loading Seller...")
    rows = read_csv("Sellers.csv")
    inserted = 0
    for row in rows:
        email = row["email"].strip()
        ensure_user(cursor, email)
        cursor.execute(
            "INSERT IGNORE INTO Seller "
            "(email, bank_routing_no, bank_account_no, account_balance) "
            "VALUES (%s, %s, %s, %s)",
            (
                email,
                row.get("bank_routing_number", "").strip() or None,
                row.get("bank_account_number", "").strip() or None,
                float(row["balance"]) if row.get("balance") else 0.0,
            ),
        )
        inserted += cursor.rowcount
    print(f"    {inserted} rows inserted")


def seed_local_vendors(cursor):
    print("  Loading LocalVendor...")
    rows = read_csv("Local_Vendors.csv")
    inserted = 0
    for row in rows:
        email = row["Email"].strip()
        ensure_user(cursor, email, row.get("Business_Name", ""))
        # Ensure a Seller row exists for this vendor
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
    print(f"    {inserted} rows inserted")


def seed_helpdesk(cursor):
    print("  Loading HelpDesk...")
    # Ensure the pseudo-staff account exists (used for unassigned requests)
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
    print(f"    {inserted} rows inserted")


def seed_credit_cards(cursor):
    print("  Loading CreditCard...")
    rows = read_csv("Credit_Cards.csv")
    inserted = 0
    for row in rows:
        owner = row["Owner_email"].strip()
        # CreditCard FK requires a Bidder row
        cursor.execute("SELECT 1 FROM Bidder WHERE email = %s", (owner,))
        if not cursor.fetchone():
            continue  # skip orphan cards

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
    print(f"    {inserted} rows inserted")


def seed_categories(cursor):
    """Two-pass approach:
    Pass 1 — insert every unique category name with NULL parent.
    Pass 2 — update parent_category for each row that has one.
    This avoids FK chicken-and-egg ordering issues.
    """
    print("  Loading Category (pass 1 — names)...")
    rows = read_csv("Categories.csv")

    # Collect every name that appears as either category_name or parent_category
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
    print(f"    {inserted} category names inserted")

    print("  Loading Category (pass 2 — parent links)...")
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
    print(f"    {updated} parent relationships set")


def seed_products(cursor):
    """Returns a dict mapping (seller_email, listing_id) → product_id
    for use by Bid and Transaction seeding."""
    print("  Loading Product...")
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
        # Status in CSV: 1 = active, 0 = inactive, 2 = sold
        if status_val == "1":
            listing_status = "active"
        elif status_val == "2":
            listing_status = "sold"
        else:
            listing_status = "inactive"

        # Verify category exists
        cursor.execute(
            "SELECT 1 FROM Category WHERE category_name = %s", (category,)
        )
        if not cursor.fetchone():
            # Insert unknown category without a parent (data quality fallback)
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

    print(f"    {inserted} rows inserted")

    # Build lookup: (seller_email, listing_id) → product_id
    cursor.execute("SELECT product_id, seller_email, listing_id FROM Product")
    lookup = {}
    for pid, semail, lid in cursor.fetchall():
        lookup[(semail, int(lid))] = pid
    return lookup


def seed_bids(cursor, product_lookup):
    print("  Loading Bid...")
    rows = read_csv("Bids.csv")
    inserted = 0
    skipped = 0
    for row in rows:
        seller = row["Seller_Email"].strip()
        listing_id = int(row["Listing_ID"])
        bidder = row["Bidder_Email"].strip()

        product_id = product_lookup.get((seller, listing_id))
        if product_id is None:
            skipped += 1
            continue

        ensure_user(cursor, bidder)
        cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (bidder,))

        price = row.get("Bid_Price", "0").replace("$", "").replace(",", "").strip() or "0"
        cursor.execute(
            "INSERT IGNORE INTO Bid "
            "(bid_id, product_id, seller_email, bidder_email, bid_price) "
            "VALUES (%s, %s, %s, %s, %s)",
            (int(row["Bid_ID"]), product_id, seller, bidder, float(price)),
        )
        inserted += cursor.rowcount

    print(f"    {inserted} rows inserted, {skipped} skipped (no matching product)")


def seed_transactions(cursor, product_lookup):
    print("  Loading Transaction...")
    rows = read_csv("Transactions.csv")
    inserted = 0
    skipped = 0
    for row in rows:
        seller = row["Seller_Email"].strip()
        listing_id = int(row["Listing_ID"])
        buyer = row["Bidder_Email"].strip()

        product_id = product_lookup.get((seller, listing_id))
        if product_id is None:
            skipped += 1
            continue

        ensure_user(cursor, buyer)
        cursor.execute("INSERT IGNORE INTO Bidder (email) VALUES (%s)", (buyer,))

        payment = row.get("Payment", "0").replace("$", "").replace(",", "").strip() or "0"
        pay_date = parse_date(row.get("Date"))

        cursor.execute(
            "INSERT IGNORE INTO Transaction "
            "(transaction_id, product_id, seller_email, buyer_email, "
            " payment_date, payment, payment_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                int(row["Transaction_ID"]),
                product_id,
                seller,
                buyer,
                pay_date,
                float(payment),
                "completed",
            ),
        )
        inserted += cursor.rowcount

    print(f"    {inserted} rows inserted, {skipped} skipped (no matching product)")


def seed_ratings(cursor):
    """[FIX-4] Rating PK is (bidder_email, seller_email, rating_date).
    No transaction_id FK — historical ratings exist beyond the Transaction table."""
    print("  Loading Rating...")
    rows = read_csv("Ratings.csv")
    inserted = 0
    skipped = 0
    for row in rows:
        bidder = row["Bidder_Email"].strip()
        seller = row["Seller_Email"].strip()
        rating_date = parse_date(row.get("Date"))
        if not rating_date:
            skipped += 1
            continue

        score = row.get("Rating", "").strip()
        if not score:
            skipped += 1
            continue

        # Ensure Bidder and Seller rows exist
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

    print(f"    {inserted} rows inserted, {skipped} skipped (missing date or score)")


def seed_requests(cursor):
    print("  Loading Request...")
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
    print(f"    {inserted} rows inserted")


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def update_is_leaf(cursor):
    """A category is a leaf if no other category names it as parent_category."""
    print("  Computing is_leaf flags...")
    # Reset all to FALSE first
    cursor.execute("UPDATE Category SET is_leaf = FALSE")
    # Mark leaves: categories that appear in no row's parent_category column.
    # Wrapped in a derived table to satisfy MySQL's restriction on updating
    # a table that is also referenced in the subquery's FROM clause (error 1093).
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
    cursor.execute("SELECT COUNT(*) FROM Category WHERE is_leaf = TRUE")
    n = cursor.fetchone()[0]
    print(f"    {n} leaf categories marked")


def update_avg_ratings(cursor):
    """Compute and cache avg_rating on each Seller row."""
    print("  Computing Seller avg_rating...")
    cursor.execute("""
        UPDATE Seller s
        SET avg_rating = (
            SELECT ROUND(AVG(r.rating), 2)
            FROM Rating r
            WHERE r.seller_email = s.email
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM Seller WHERE avg_rating IS NOT NULL")
    n = cursor.fetchone()[0]
    print(f"    avg_rating set for {n} sellers")


def mark_sold_products(cursor):
    """Products with a completed Transaction should be 'sold'."""
    print("  Marking sold products...")
    cursor.execute("""
        UPDATE Product p
        JOIN Transaction t ON t.product_id = p.product_id
        SET p.listing_status = 'sold'
        WHERE t.payment_status = 'completed'
          AND p.listing_status != 'sold'
    """)
    print(f"    {cursor.rowcount} products marked sold")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
        print("\n=== Seeding NittanyAuction Database ===\n")

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

        print("\n=== Post-processing ===\n")
        update_is_leaf(cursor)
        update_avg_ratings(cursor)
        mark_sold_products(cursor)

        conn.commit()
        print("\n=== Done! Database fully populated. ===\n")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

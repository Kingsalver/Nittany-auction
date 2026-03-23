import os
import csv
import hashlib
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def parse_date(date_str, fmt="%m/%d/%y"):
    if not date_str: return None
    try:
        return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def execute_schema(cursor, schema_path):
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    statements = sql.split(';')
    for statement in statements:
        if statement.strip():
            cursor.execute(statement)

def insert_ignore(cursor, table, data_dict):
    keys = data_dict.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['%s'] * len(keys))
    query = f"INSERT IGNORE INTO {table} ({columns}) VALUES ({placeholders})"
    cursor.execute(query, tuple(data_dict.values()))

def main():
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        autocommit=True
    )
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, "schema.sql")
    data_dir = os.path.join(base_dir, "resources", "NittanyAuctionDataset_v1")
    
    with connection.cursor() as cursor:
        print("Executing schema.sql...")
        execute_schema(cursor, schema_path)
        cursor.execute("USE nittany_auction;")
        
        # Load Addresses into memory
        print("Loading Address data...")
        addresses = {}
        with open(os.path.join(data_dir, "Address.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                addresses[row['address_id']] = {
                    'zip': row.get('zipcode'),
                    'street': f"{row.get('street_num', '').strip()} {row.get('street_name', '').strip()}"
                }
                
        # 1. ZipCode
        print("Populating ZipCode...")
        with open(os.path.join(data_dir, "Zipcode_Info.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                insert_ignore(cursor, 'ZipCode', {
                    'zip': row['zipcode'],
                    'city': row['city'],
                    'state': row['state']
                })

        # Pre-load Names from Bidders to improve User population
        user_names = {}
        with open(os.path.join(data_dir, "Bidders.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                user_names[row['email'].strip()] = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                
        # 2. User
        print("Populating User...")
        with open(os.path.join(data_dir, "Users.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                email = row['email'].strip()
                insert_ignore(cursor, 'User', {
                    'email': email,
                    'password': hash_password(row['password'].strip()),
                    'name': user_names.get(email, email.split('@')[0])
                })

        # Helper method for missing users
        def ensure_user(email, name_hint=""):
            cursor.execute("SELECT email FROM User WHERE email=%s", (email,))
            if not cursor.fetchone():
                insert_ignore(cursor, 'User', {
                    'email': email,
                    'password': hash_password("default123"),
                    'name': name_hint or email.split('@')[0]
                })

        # 3. Bidder
        print("Populating Bidder...")
        with open(os.path.join(data_dir, "Bidders.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                email = row['email'].strip()
                home_address_id = row.get('home_address_id', '').strip()
                ensure_user(email, f"{row.get('first_name', '')} {row.get('last_name', '')}".strip())
                insert_ignore(cursor, 'Bidder', {
                    'email': email,
                    'street': addresses.get(home_address_id, {}).get('street'),
                    'zip': addresses.get(home_address_id, {}).get('zip'),
                    'phone': None,
                    'major': row.get('major') or None,
                    'age': row.get('age') or None,
                    'annual_income': None
                })

        # 4. Seller
        print("Populating Seller...")
        with open(os.path.join(data_dir, "Sellers.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                email = row['email'].strip()
                ensure_user(email)
                insert_ignore(cursor, 'Seller', {
                    'email': email,
                    'bank_routing_no': row.get('bank_routing_number'),
                    'bank_account_no': row.get('bank_account_number'),
                    'account_balance': row.get('balance', 0)
                })

        # 5. LocalVendor
        print("Populating LocalVendor...")
        with open(os.path.join(data_dir, "Local_Vendors.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                email = row['Email'].strip()
                ensure_user(email, row.get('Business_Name'))
                insert_ignore(cursor, 'Seller', {'email': email})
                biz_address_id = row.get('Business_Address_ID', '').strip()
                insert_ignore(cursor, 'LocalVendor', {
                    'email': email,
                    'business_name': row.get('Business_Name'),
                    'business_address': addresses.get(biz_address_id, {}).get('street'),
                    'customer_service_phone': row.get('Customer_Service_Phone_Number')
                })

        # 6. HelpDesk
        print("Populating HelpDesk...")
        with open(os.path.join(data_dir, "Helpdesk.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                email = row['email'].strip()
                ensure_user(email)
                insert_ignore(cursor, 'HelpDesk', {
                    'email': email,
                    'staff_role': row.get('Position', 'Support')
                })

        # 7. CreditCard
        print("Populating CreditCard...")
        with open(os.path.join(data_dir, "Credit_Cards.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                month = row.get('expire_month', '1').zfill(2)
                year = row.get('expire_year', '2025')
                insert_ignore(cursor, 'CreditCard', {
                    'card_number': row['credit_card_num'].strip(),
                    'email': row['Owner_email'].strip(),
                    'card_type': row.get('card_type'),
                    'expiration_date': f"{year}-{month}-01"
                })

        # 8. Category
        print("Populating Category...")
        categories = {}
        with open(os.path.join(data_dir, "Categories.csv"), 'r', encoding='utf-8-sig') as f:
            cat_list = list(csv.DictReader(f))
            unique_cats = set()
            for row in cat_list:
                if row.get('category_name'): unique_cats.add(row['category_name'].strip())
                if row.get('parent_category'): unique_cats.add(row['parent_category'].strip())
            
            for c in unique_cats:
                insert_ignore(cursor, 'Category', {'category_name': c})
                
            cursor.execute("SELECT category_id, category_name FROM Category")
            for cid, cname in cursor.fetchall():
                categories[cname] = cid

            for row in cat_list:
                cname = row.get('category_name', '').strip()
                pname = row.get('parent_category', '').strip()
                if pname and cname:
                    cursor.execute("UPDATE Category SET parent_category_id = %s WHERE category_id = %s", (categories[pname], categories[cname]))

        # 9. Product
        print("Populating Product...")
        with open(os.path.join(data_dir, "Auction_Listings.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                seller_email = row['Seller_Email'].strip()
                ensure_user(seller_email)
                insert_ignore(cursor, 'Seller', {'email': seller_email})
                
                cat_name = row['Category'].strip()
                cat_id = categories.get(cat_name)
                
                price = row.get('Reserve_Price', '0').replace('$', '').replace(',', '').strip()
                
                insert_ignore(cursor, 'Product', {
                    'product_id': row['Listing_ID'],
                    'seller_email': seller_email,
                    'category_id': cat_id,
                    'title': row.get('Auction_Title', row.get('Product_Name')),
                    'description': row.get('Product_Description'),
                    'reserve_price': price if price else 0,
                    'auction_end_time': '2026-12-31 23:59:59',
                    'listing_status': 'active' if row.get('Status') == '1' else 'inactive'
                })

        # 10. Bid
        print("Populating Bid...")
        with open(os.path.join(data_dir, "Bids.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                ensure_user(row['Bidder_Email'].strip())
                insert_ignore(cursor, 'Bidder', {'email': row['Bidder_Email'].strip()})
                insert_ignore(cursor, 'Bid', {
                    'bid_id': row['Bid_ID'],
                    'product_id': row['Listing_ID'],
                    'bidder_email': row['Bidder_Email'],
                    'bid_amount': row['Bid_Price']
                })

        # 11. Transaction
        print("Populating Transaction...")
        with open(os.path.join(data_dir, "Transactions.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                cursor.execute("SELECT bid_id FROM Bid WHERE product_id=%s AND bidder_email=%s ORDER BY bid_amount DESC LIMIT 1", (row['Listing_ID'], row['Bidder_Email']))
                b = cursor.fetchone()
                if b:
                    pay_date = parse_date(row.get('Date')) or '2026-01-01 00:00:00'
                    insert_ignore(cursor, 'Transaction', {
                        'transaction_id': row['Transaction_ID'],
                        'bid_id': b[0],
                        'product_id': row['Listing_ID'],
                        'bidder_email': row['Bidder_Email'],
                        'seller_email': row['Seller_Email'],
                        'final_amount': row['Payment'],
                        'payment_status': 'completed',
                        'payment_date': pay_date
                    })

        # 12. Rating
        print("Populating Rating...")
        with open(os.path.join(data_dir, "Ratings.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                cursor.execute("SELECT transaction_id FROM Transaction WHERE bidder_email=%s AND seller_email=%s LIMIT 1", (row['Bidder_Email'], row['Seller_Email']))
                t = cursor.fetchone()
                if t:
                    insert_ignore(cursor, 'Rating', {
                        'transaction_id': t[0],
                        'score': row['Rating'],
                        'comment': row.get('Rating_Desc')
                    })

        # 13. Request
        print("Populating Request...")
        with open(os.path.join(data_dir, "Requests.csv"), 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                ensure_user(row['sender_email'].strip())
                insert_ignore(cursor, 'Request', {
                    'request_id': row['request_id'],
                    'submitted_by_email': row['sender_email'],
                    'request_type': row['request_type'],
                    'status': 'resolved' if row.get('request_status') == '1' else 'pending'
                })

    connection.close()
    print("Database setup complete.")

if __name__ == "__main__":
    main()

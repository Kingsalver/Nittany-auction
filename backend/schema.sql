-- ============================================================
-- Nittany Auction — Corrected MySQL Schema
-- CMPSC 431W Spring 2026
-- ============================================================
-- Changes from previous version:
--   [FIX-1] Address table added (was missing; required by spec)
--   [FIX-2] Bidder: home_address_id FK replaces flat street/zip;
--            first_name/last_name added per spec
--   [FIX-3] Product: max_bids INT added; auction_end_time removed
--            (spec is count-based, not time-based); listing_id column
--            added for per-seller natural key; UNIQUE(seller_email,
--            listing_id) enforces spec composite PK; removal audit
--            fields added for Phase 2 §3; category_name replaces
--            category_id to match spec FK shape
--   [FIX-4] Rating: PK changed to (bidder_email, seller_email,
--            rating_date) per spec; transaction_id FK dropped
--            (spec states ratings cover more than transactions)
--   [FIX-5] HelpDesk: column renamed staff_role → position (spec)
--   [FIX-6] CreditCard: column names aligned to spec
--            (credit_card_num, expire_month INT, expire_year INT,
--            security_code, owner_email)
--   [FIX-7] Category: UNIQUE(category_name) added; parent stored
--            as name string FK (matches spec structure); is_leaf
--            kept as computed extension, populated in setup_db.py
--   [EXT]   Seller.avg_rating cached column (Phase 2 §8)
--   [EXT]   Sessions, Watchlist, Notification, ListingQuestion
--            kept as app-layer extensions
-- ============================================================

DROP DATABASE IF EXISTS nittany_auction;
CREATE DATABASE nittany_auction;
USE nittany_auction;

-- Drop in reverse-dependency order for clean re-runs
DROP TABLE IF EXISTS Sessions;
DROP TABLE IF EXISTS ListingQuestion;
DROP TABLE IF EXISTS Notification;
DROP TABLE IF EXISTS Watchlist;
DROP TABLE IF EXISTS Request;
DROP TABLE IF EXISTS Rating;
DROP TABLE IF EXISTS Transaction;
DROP TABLE IF EXISTS Bid;
DROP TABLE IF EXISTS Product;
DROP TABLE IF EXISTS Category;
DROP TABLE IF EXISTS CreditCard;
DROP TABLE IF EXISTS HelpDesk;
DROP TABLE IF EXISTS LocalVendor;
DROP TABLE IF EXISTS Seller;
DROP TABLE IF EXISTS Bidder;
DROP TABLE IF EXISTS Address;
DROP TABLE IF EXISTS ZipCode;
DROP TABLE IF EXISTS User;


-- ============================================================
-- 1. User
--    Spec: Users(email, password)
--    name is our extension for display purposes
-- ============================================================
CREATE TABLE User (
    email    VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    name     VARCHAR(255) NOT NULL DEFAULT '',
    PRIMARY KEY (email)
);


-- ============================================================
-- 2. ZipCode
--    Spec: Zipcode_Info(zipcode, city, state)
-- ============================================================
CREATE TABLE ZipCode (
    zipcode VARCHAR(10)  NOT NULL,
    city    VARCHAR(100) NOT NULL,
    state   VARCHAR(50)  NOT NULL,
    PRIMARY KEY (zipcode)
);


-- ============================================================
-- 3. Address  [FIX-1: table was missing]
--    Spec: Address(address_ID, zipcode, street_num, street_name)
--    address_id values are UUIDs (hex strings) from the CSV dataset
-- ============================================================
CREATE TABLE Address (
    address_id  VARCHAR(64)  NOT NULL,
    zipcode     VARCHAR(10),
    street_num  VARCHAR(20),
    street_name VARCHAR(255),
    PRIMARY KEY (address_id),
    FOREIGN KEY (zipcode) REFERENCES ZipCode(zipcode)
);


-- ============================================================
-- 4. Bidder  [FIX-2: first_name/last_name, home_address_id]
--    Spec: Bidders(email, first_name, last_name, age,
--                  home_address_id, major)
--    phone, annual_income are extensions
-- ============================================================
CREATE TABLE Bidder (
    email           VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    age             INT,
    home_address_id VARCHAR(64),
    major           VARCHAR(100),
    phone           VARCHAR(20),
    annual_income   DECIMAL(12,2),
    PRIMARY KEY (email),
    FOREIGN KEY (email)           REFERENCES User(email),
    FOREIGN KEY (home_address_id) REFERENCES Address(address_id)
);


-- ============================================================
-- 5. Seller
--    Spec: Sellers(email, bank_routing_number,
--                  bank_account_number, balance)
--    avg_rating is an extension: cached and updated on each
--    new rating submission (Phase 2 §8)
-- ============================================================
CREATE TABLE Seller (
    email           VARCHAR(255)  NOT NULL,
    bank_routing_no VARCHAR(50),
    bank_account_no VARCHAR(50),
    account_balance DECIMAL(12,2) DEFAULT 0.00,
    avg_rating      DECIMAL(3,2),
    PRIMARY KEY (email),
    FOREIGN KEY (email) REFERENCES User(email)
);


-- ============================================================
-- 6. LocalVendor
--    Spec: Local_Vendors(Email, Business_Name,
--          Business_Address_ID, Customer_Service_Phone_Number)
--    Cascade-delete: removing a vendor removes their Seller row
--    which cascades to Product → Bid/Watchlist/etc.
-- ============================================================
CREATE TABLE LocalVendor (
    email                  VARCHAR(255) NOT NULL,
    business_name          VARCHAR(255) NOT NULL,
    business_address_id    VARCHAR(64),
    customer_service_phone VARCHAR(20),
    PRIMARY KEY (email),
    FOREIGN KEY (email)               REFERENCES Seller(email)  ON DELETE CASCADE,
    FOREIGN KEY (business_address_id) REFERENCES Address(address_id)
);


-- ============================================================
-- 7. HelpDesk  [FIX-5: column renamed to position]
--    Spec: Helpdesk(email, position)
-- ============================================================
CREATE TABLE HelpDesk (
    email    VARCHAR(255) NOT NULL,
    position VARCHAR(100) NOT NULL,
    PRIMARY KEY (email),
    FOREIGN KEY (email) REFERENCES User(email)
);


-- ============================================================
-- 8. CreditCard  [FIX-6: column names aligned to spec]
--    Spec: Credit_Cards(credit_card_num, card_type,
--          expire_month, expire_year, security_code, Owner_email)
-- ============================================================
CREATE TABLE CreditCard (
    credit_card_num VARCHAR(20)  NOT NULL,
    card_type       VARCHAR(50),
    expire_month    INT,
    expire_year     INT,
    security_code   VARCHAR(10),
    owner_email     VARCHAR(255) NOT NULL,
    PRIMARY KEY (credit_card_num),
    FOREIGN KEY (owner_email) REFERENCES Bidder(email) ON DELETE CASCADE
);


-- ============================================================
-- 9. Category  [FIX-7: UNIQUE(category_name), parent as name FK]
--    Spec: Categories(parent_category, category_name)
--    PK = category_name in spec; we use surrogate category_id
--    for efficient FK references but enforce the natural key
--    with UNIQUE(category_name).
--    parent_category stores the parent's name (self-referential).
--    is_leaf is an extension, computed in setup_db.py after load.
-- ============================================================
CREATE TABLE Category (
    category_id     INT          NOT NULL AUTO_INCREMENT,
    category_name   VARCHAR(255) NOT NULL,
    parent_category VARCHAR(255),
    is_leaf         BOOLEAN      NOT NULL DEFAULT FALSE,
    status          VARCHAR(50)  NOT NULL DEFAULT 'active',
    PRIMARY KEY (category_id),
    UNIQUE  (category_name),
    FOREIGN KEY (parent_category) REFERENCES Category(category_name)
);


-- ============================================================
-- 10. Product  [FIX-3: max_bids, listing_id, category_name FK,
--               removal audit; auction_end_time removed]
--    Spec: Auction_Listings(Seller_Email, Listing_ID, Category,
--          Auction_Title, Product_Name, Product_Description,
--          Quantity, Reserve_Price, Max_bids, Status)
--    Composite natural key UNIQUE(seller_email, listing_id)
--    matches spec's (Seller_Email, Listing_ID) composite PK.
--    product_id is our surrogate PK for FK references.
--    listing_status: 'active'=1, 'inactive'=0, 'sold'=2
-- ============================================================
CREATE TABLE Product (
    product_id          INT           NOT NULL AUTO_INCREMENT,
    seller_email        VARCHAR(255)  NOT NULL,
    listing_id          INT           NOT NULL,
    category_name       VARCHAR(255)  NOT NULL,
    auction_title       VARCHAR(255)  NOT NULL,
    product_name        VARCHAR(255),
    product_description TEXT,
    quantity            INT                    DEFAULT 1,
    reserve_price       DECIMAL(12,2) NOT NULL,
    max_bids            INT           NOT NULL,
    listing_status      VARCHAR(20)   NOT NULL DEFAULT 'active',
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Removal audit fields (Phase 2 §3)
    removal_reason      TEXT,
    bids_at_removal     INT,
    removal_timestamp   DATETIME,
    photo_path          VARCHAR(500),
    PRIMARY KEY (product_id),
    UNIQUE  (seller_email, listing_id),
    FOREIGN KEY (seller_email)  REFERENCES Seller(email)           ON DELETE CASCADE,
    FOREIGN KEY (category_name) REFERENCES Category(category_name),
    CHECK (listing_status IN ('active', 'inactive', 'sold'))
);


-- ============================================================
-- 11. Bid
--    Spec: Bids(Bid_ID, Seller_Email, Listing_ID,
--               Bidder_email, Bid_price)
--    product_id is our surrogate reference to Product.
--    seller_email is denormalized here per spec.
-- ============================================================
CREATE TABLE Bid (
    bid_id        INT           NOT NULL AUTO_INCREMENT,
    product_id    INT           NOT NULL,
    seller_email  VARCHAR(255)  NOT NULL,
    bidder_email  VARCHAR(255)  NOT NULL,
    bid_price     DECIMAL(12,2) NOT NULL,
    bid_timestamp DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bid_id),
    FOREIGN KEY (product_id)   REFERENCES Product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (seller_email) REFERENCES Seller(email),
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email)
);


-- ============================================================
-- 12. Transaction
--    Spec: Transactions(Transaction_ID, Seller_Email,
--          Listing_ID, Buyer_Email, Date, Payment)
--    product_id is our surrogate reference.
--    UNIQUE(product_id): a listing is sold at most once.
-- ============================================================
CREATE TABLE Transaction (
    transaction_id INT           NOT NULL AUTO_INCREMENT,
    product_id     INT           NOT NULL,
    seller_email   VARCHAR(255)  NOT NULL,
    buyer_email    VARCHAR(255)  NOT NULL,
    payment_date   DATE,
    payment        DECIMAL(12,2) NOT NULL,
    payment_status VARCHAR(50)   NOT NULL DEFAULT 'completed',
    PRIMARY KEY (transaction_id),
    UNIQUE  (product_id),
    FOREIGN KEY (product_id)   REFERENCES Product(product_id),
    FOREIGN KEY (seller_email) REFERENCES Seller(email),
    FOREIGN KEY (buyer_email)  REFERENCES Bidder(email)
);


-- ============================================================
-- 13. Rating  [FIX-4: composite PK per spec; no transaction FK]
--    Spec: Rating(Bidder_Email, Seller_Email, Date,
--                 Rating, Rating_Desc)
--    PK = (bidder_email, seller_email, rating_date)
--    Spec note: "covers more than what's in the transaction table"
--    — historical data exists without a Transaction row.
-- ============================================================
CREATE TABLE Rating (
    bidder_email VARCHAR(255) NOT NULL,
    seller_email VARCHAR(255) NOT NULL,
    rating_date  DATE         NOT NULL,
    rating       INT          NOT NULL,
    rating_desc  TEXT,
    PRIMARY KEY (bidder_email, seller_email, rating_date),
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email),
    FOREIGN KEY (seller_email) REFERENCES Seller(email),
    CHECK (rating >= 1 AND rating <= 5)
);


-- ============================================================
-- 14. Request
--    Spec: Requests(request_id, sender_email,
--          helpdesk_staff_email, request_type, request_desc,
--          request_status)
--    request_status: 0 = incomplete, 1 = complete
--    Default helpdesk_staff_email = helpdeskteam@lsu.edu
-- ============================================================
CREATE TABLE Request (
    request_id           INT          NOT NULL AUTO_INCREMENT,
    sender_email         VARCHAR(255) NOT NULL,
    helpdesk_staff_email VARCHAR(255) NOT NULL DEFAULT 'helpdeskteam@lsu.edu',
    request_type         VARCHAR(100) NOT NULL,
    request_desc         TEXT,
    request_status       TINYINT      NOT NULL DEFAULT 0,
    date_submitted       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_id),
    FOREIGN KEY (sender_email) REFERENCES User(email)
);


-- ============================================================
-- 15. Watchlist  [extension — Phase 2 optional §11]
-- ============================================================
CREATE TABLE Watchlist (
    bidder_email    VARCHAR(255) NOT NULL,
    product_id      INT          NOT NULL,
    date_time_added DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bidder_email, product_id),
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email)        ON DELETE CASCADE,
    FOREIGN KEY (product_id)   REFERENCES Product(product_id)  ON DELETE CASCADE
);


-- ============================================================
-- 16. Notification  [extension]
-- ============================================================
CREATE TABLE Notification (
    notification_id   INT          NOT NULL AUTO_INCREMENT,
    bidder_email      VARCHAR(255) NOT NULL,
    product_id        INT          NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    message           TEXT,
    sent_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read           BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (notification_id),
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email),
    FOREIGN KEY (product_id)   REFERENCES Product(product_id)  ON DELETE CASCADE
);


-- ============================================================
-- 17. ListingQuestion  [extension]
-- ============================================================
CREATE TABLE ListingQuestion (
    question_id    INT          NOT NULL AUTO_INCREMENT,
    product_id     INT          NOT NULL,
    bidder_email   VARCHAR(255) NOT NULL,
    question_text  TEXT         NOT NULL,
    answer_text    TEXT,
    asked_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (question_id),
    FOREIGN KEY (product_id)   REFERENCES Product(product_id)  ON DELETE CASCADE,
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email)
);


-- ============================================================
-- 18. Sessions  [extension — JWT session tracking]
-- ============================================================
CREATE TABLE Sessions (
    session_id INT          NOT NULL AUTO_INCREMENT,
    user_email VARCHAR(255) NOT NULL,
    token      TEXT         NOT NULL,
    created_at TIMESTAMP             DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP    NOT NULL,
    is_active  BOOLEAN               DEFAULT TRUE,
    PRIMARY KEY (session_id),
    FOREIGN KEY (user_email) REFERENCES User(email)
);

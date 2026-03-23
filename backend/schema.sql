-- ============================================================
-- Nittany Auction — Complete MySQL Schema
-- CMPSC 431W Spring 2026
-- ============================================================
-- Run this file against your MySQL server to create all tables:
--   mysql -u root -p nittany_auction < schema.sql
-- ============================================================

-- Create database if it doesn't exist
DROP DATABASE IF EXISTS nittany_auction;
CREATE DATABASE nittany_auction;
USE nittany_auction;

-- Drop tables in reverse-dependency order (for clean re-runs)
DROP TABLE IF EXISTS Sessions;
DROP TABLE IF EXISTS ListingQuestion;
DROP TABLE IF EXISTS Request;
DROP TABLE IF EXISTS Notification;
DROP TABLE IF EXISTS Watchlist;
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
DROP TABLE IF EXISTS ZipCode;
DROP TABLE IF EXISTS User;


-- ============================================================
-- 1. User
-- ============================================================
CREATE TABLE User (
    email       VARCHAR(255)    NOT NULL,
    password    VARCHAR(255)    NOT NULL,
    name        VARCHAR(255)    NOT NULL,
    PRIMARY KEY (email)
);


-- ============================================================
-- 2. ZipCode (lookup table for city/state)
-- ============================================================
CREATE TABLE ZipCode (
    zip     VARCHAR(10)     NOT NULL,
    city    VARCHAR(100)    NOT NULL,
    state   VARCHAR(50)     NOT NULL,
    PRIMARY KEY (zip)
);


-- ============================================================
-- 3. Bidder (ISA User — LSU students)
-- ============================================================
CREATE TABLE Bidder (
    email           VARCHAR(255)    NOT NULL,
    street          VARCHAR(255),
    zip             VARCHAR(10),
    phone           VARCHAR(20),
    major           VARCHAR(100),
    age             INT,
    annual_income   DECIMAL(12,2),
    PRIMARY KEY (email),
    FOREIGN KEY (email)  REFERENCES User(email),
    FOREIGN KEY (zip)    REFERENCES ZipCode(zip)
);


-- ============================================================
-- 4. Seller (ISA User)
-- ============================================================
CREATE TABLE Seller (
    email               VARCHAR(255)    NOT NULL,
    bank_routing_no     VARCHAR(50),
    bank_account_no     VARCHAR(50),
    account_balance     DECIMAL(12,2)   DEFAULT 0.00,
    PRIMARY KEY (email),
    FOREIGN KEY (email)  REFERENCES User(email)
);


-- ============================================================
-- 5. LocalVendor (ISA Seller — CASCADE DELETE)
--    When a vendor leaves, their Seller row is also deleted,
--    which cascades to Product → Bid/Watchlist/etc.
-- ============================================================
CREATE TABLE LocalVendor (
    email                   VARCHAR(255)    NOT NULL,
    business_name           VARCHAR(255)    NOT NULL,
    business_address        VARCHAR(500),
    customer_service_phone  VARCHAR(20),
    PRIMARY KEY (email),
    FOREIGN KEY (email)  REFERENCES Seller(email) ON DELETE CASCADE
);


-- ============================================================
-- 6. HelpDesk (ISA User — admin staff)
-- ============================================================
CREATE TABLE HelpDesk (
    email       VARCHAR(255)    NOT NULL,
    staff_role  VARCHAR(100)    NOT NULL,
    PRIMARY KEY (email),
    FOREIGN KEY (email)  REFERENCES User(email)
);


-- ============================================================
-- 7. CreditCard (belongs to Bidder)
-- ============================================================
CREATE TABLE CreditCard (
    card_number     VARCHAR(20)     NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    card_type       VARCHAR(50),
    expiration_date DATE,
    PRIMARY KEY (card_number),
    FOREIGN KEY (email)  REFERENCES Bidder(email) ON DELETE CASCADE
);


-- ============================================================
-- 8. Category (recursive / self-referential hierarchy)
-- ============================================================
CREATE TABLE Category (
    category_id         INT             NOT NULL AUTO_INCREMENT,
    category_name       VARCHAR(255)    NOT NULL,
    parent_category_id  INT,
    is_leaf             BOOLEAN         NOT NULL DEFAULT FALSE,
    status              VARCHAR(50)     NOT NULL DEFAULT 'active',
    PRIMARY KEY (category_id),
    FOREIGN KEY (parent_category_id)  REFERENCES Category(category_id)
);


-- ============================================================
-- 9. Product (listed by a Seller in a leaf Category)
--    CASCADE DELETE from Seller so vendor removal cleans up.
-- ============================================================
CREATE TABLE Product (
    product_id      INT             NOT NULL AUTO_INCREMENT,
    seller_email    VARCHAR(255)    NOT NULL,
    category_id     INT             NOT NULL,
    title           VARCHAR(255)    NOT NULL,
    description     TEXT,
    reserve_price   DECIMAL(12,2)   NOT NULL,
    auction_end_time DATETIME       NOT NULL,
    listing_status  VARCHAR(50)     NOT NULL DEFAULT 'active',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    photo_path      VARCHAR(500),
    PRIMARY KEY (product_id),
    FOREIGN KEY (seller_email)  REFERENCES Seller(email)   ON DELETE CASCADE,
    FOREIGN KEY (category_id)   REFERENCES Category(category_id)
);


-- ============================================================
-- 10. Bid
-- ============================================================
CREATE TABLE Bid (
    bid_id          INT             NOT NULL AUTO_INCREMENT,
    product_id      INT             NOT NULL,
    bidder_email    VARCHAR(255)    NOT NULL,
    bid_amount      DECIMAL(12,2)   NOT NULL,
    bid_timestamp   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bid_id),
    FOREIGN KEY (product_id)    REFERENCES Product(product_id)  ON DELETE CASCADE,
    FOREIGN KEY (bidder_email)  REFERENCES Bidder(email)
);


-- ============================================================
-- 11. Transaction (one-to-one with winning Bid)
-- ============================================================
CREATE TABLE Transaction (
    transaction_id      INT             NOT NULL AUTO_INCREMENT,
    bid_id              INT             NOT NULL,
    product_id          INT             NOT NULL,
    bidder_email        VARCHAR(255)    NOT NULL,
    seller_email        VARCHAR(255)    NOT NULL,
    final_amount        DECIMAL(12,2)   NOT NULL,
    payment_status      VARCHAR(50)     NOT NULL DEFAULT 'pending',
    payment_date        DATETIME,
    transaction_method  VARCHAR(50),
    PRIMARY KEY (transaction_id),
    UNIQUE (bid_id),
    FOREIGN KEY (bid_id)            REFERENCES Bid(bid_id),
    FOREIGN KEY (product_id)        REFERENCES Product(product_id)  ON DELETE CASCADE,
    FOREIGN KEY (bidder_email)      REFERENCES Bidder(email),
    FOREIGN KEY (seller_email)      REFERENCES Seller(email)
);


-- ============================================================
-- 12. Rating (one-to-one with Transaction)
-- ============================================================
CREATE TABLE Rating (
    rating_id       INT     NOT NULL AUTO_INCREMENT,
    transaction_id  INT     NOT NULL,
    score           INT     NOT NULL,
    comment         TEXT,
    PRIMARY KEY (rating_id),
    UNIQUE (transaction_id),
    FOREIGN KEY (transaction_id)  REFERENCES Transaction(transaction_id),
    CHECK (score >= 1 AND score <= 5)
);


-- ============================================================
-- 13. Watchlist (composite PK)
-- ============================================================
CREATE TABLE Watchlist (
    bidder_email    VARCHAR(255)    NOT NULL,
    product_id      INT             NOT NULL,
    date_time_added DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bidder_email, product_id),
    FOREIGN KEY (bidder_email)  REFERENCES Bidder(email)        ON DELETE CASCADE,
    FOREIGN KEY (product_id)    REFERENCES Product(product_id)  ON DELETE CASCADE
);


-- ============================================================
-- 14. Notification
-- ============================================================
CREATE TABLE Notification (
    notification_id     INT             NOT NULL AUTO_INCREMENT,
    bidder_email        VARCHAR(255)    NOT NULL,
    product_id          INT             NOT NULL,
    notification_type   VARCHAR(100)    NOT NULL,
    timestamp           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read             BOOLEAN         NOT NULL DEFAULT FALSE,
    PRIMARY KEY (notification_id),
    FOREIGN KEY (bidder_email)  REFERENCES Bidder(email),
    FOREIGN KEY (product_id)    REFERENCES Product(product_id)  ON DELETE CASCADE
);


-- ============================================================
-- 15. Request (seller applications, email changes, etc.)
-- ============================================================
CREATE TABLE Request (
    request_id          INT             NOT NULL AUTO_INCREMENT,
    submitted_by_email  VARCHAR(255)    NOT NULL,
    request_type        VARCHAR(100)    NOT NULL,
    date_submitted      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              VARCHAR(50)     NOT NULL DEFAULT 'pending',
    handled_by_email    VARCHAR(255),
    handled_timestamp   DATETIME,
    PRIMARY KEY (request_id),
    FOREIGN KEY (submitted_by_email)    REFERENCES User(email),
    FOREIGN KEY (handled_by_email)      REFERENCES HelpDesk(email)
);


-- ============================================================
-- 16. ListingQuestion (Q&A on product listings)
-- ============================================================
CREATE TABLE ListingQuestion (
    question_id     INT             NOT NULL AUTO_INCREMENT,
    product_id      INT             NOT NULL,
    bidder_email    VARCHAR(255)    NOT NULL,
    question_text   TEXT            NOT NULL,
    answer_text     TEXT,
    asked_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (question_id),
    FOREIGN KEY (product_id)    REFERENCES Product(product_id)  ON DELETE CASCADE,
    FOREIGN KEY (bidder_email)  REFERENCES Bidder(email)
);


-- ============================================================
-- 17. Sessions (JWT session tracking)
-- ============================================================
CREATE TABLE Sessions (
    session_id  INT             NOT NULL AUTO_INCREMENT,
    user_email  VARCHAR(255)    NOT NULL,
    token       TEXT            NOT NULL,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP       NOT NULL,
    is_active   BOOLEAN         DEFAULT TRUE,
    PRIMARY KEY (session_id),
    FOREIGN KEY (user_email) REFERENCES User(email)
);
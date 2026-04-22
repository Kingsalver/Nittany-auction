DROP DATABASE IF EXISTS nittany_auction;
CREATE DATABASE nittany_auction;
USE nittany_auction;

-- clear old tables if they exist
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

-- users table
CREATE TABLE User (
    email    VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    name     VARCHAR(255) NOT NULL DEFAULT '',
    PRIMARY KEY (email)
);

-- zip codes from the dataset
CREATE TABLE ZipCode (
    zipcode VARCHAR(10)  NOT NULL,
    city    VARCHAR(100) NOT NULL,
    state   VARCHAR(50)  NOT NULL,
    PRIMARY KEY (zipcode)
);

-- address table
CREATE TABLE Address (
    address_id  VARCHAR(64)  NOT NULL,
    zipcode     VARCHAR(10),
    street_num  VARCHAR(20),
    street_name VARCHAR(255),
    PRIMARY KEY (address_id),
    FOREIGN KEY (zipcode) REFERENCES ZipCode(zipcode)
);

-- bidders table
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

-- sellers table
CREATE TABLE Seller (
    email                VARCHAR(255)  NOT NULL,
    bank_routing_number  VARCHAR(50),
    bank_account_number  VARCHAR(50),
    balance              DECIMAL(12,2) DEFAULT 0.00,
    avg_rating           DECIMAL(3,2),
    PRIMARY KEY (email),
    FOREIGN KEY (email) REFERENCES User(email)
);

-- vendors
CREATE TABLE LocalVendor (
    email                  VARCHAR(255) NOT NULL,
    business_name          VARCHAR(255) NOT NULL,
    business_address_id    VARCHAR(64),
    customer_service_phone VARCHAR(20),
    PRIMARY KEY (email),
    FOREIGN KEY (email)               REFERENCES Seller(email)  ON DELETE CASCADE,
    FOREIGN KEY (business_address_id) REFERENCES Address(address_id)
);

-- help desk staff
CREATE TABLE HelpDesk (
    email    VARCHAR(255) NOT NULL,
    position VARCHAR(100) NOT NULL,
    PRIMARY KEY (email),
    FOREIGN KEY (email) REFERENCES User(email)
);

-- cards
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

-- category table
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

-- products / auction listings
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

-- bids
CREATE TABLE Bid (
    bid_id        INT           NOT NULL AUTO_INCREMENT,
    product_id    INT           NOT NULL,
    listing_id    INT           NOT NULL,
    seller_email  VARCHAR(255)  NOT NULL,
    bidder_email  VARCHAR(255)  NOT NULL,
    bid_price     DECIMAL(12,2) NOT NULL,
    bid_timestamp DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bid_id),
    FOREIGN KEY (product_id)   REFERENCES Product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (seller_email) REFERENCES Seller(email),
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email)
);

-- transactions
CREATE TABLE Transaction (
    transaction_id INT           NOT NULL AUTO_INCREMENT,
    product_id     INT           NOT NULL,
    listing_id     INT           NOT NULL,
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

-- ratings
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

-- request table
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

-- watchlist extension
CREATE TABLE Watchlist (
    bidder_email    VARCHAR(255) NOT NULL,
    product_id      INT          NOT NULL,
    date_time_added DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bidder_email, product_id),
    FOREIGN KEY (bidder_email) REFERENCES Bidder(email)        ON DELETE CASCADE,
    FOREIGN KEY (product_id)   REFERENCES Product(product_id)  ON DELETE CASCADE
);

-- notifications extension
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

-- questions extension
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

-- jwt sessions extension
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

"""
Pydantic schemas for request/response validation in the FastAPI layer.
These are NOT database models — they only validate API data shapes.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date



# User Model
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserOut(BaseModel):
    email: EmailStr
    name: str


# Auth Models
class LoginRequest(BaseModel):
    email: str
    password: str

# Model for signup page, this is what the frontend sends to the backend and keeps the structure of the data uniform
class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    age: Optional[int] = None
    major: Optional[str] = None
    street_num: Optional[str] = None   # e.g. "123"
    street_name: Optional[str] = None  # e.g. "Main St"
    zipcode: Optional[str] = None      # must exist in ZipCode table


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str


# HelpDesk Request model — matches professor's Request table schema
class RequestCreate(BaseModel):
    request_type: str          # e.g. "BidderRegistration", "ChangeID", "AddCategory"
    request_desc: Optional[str] = None


# ZipCode Model
class ZipCodeOut(BaseModel):
    zip: str
    city: str
    state: str


# Bidder Model
class BidderCreate(BaseModel):
    email: EmailStr
    street: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    major: Optional[str] = None
    age: Optional[int] = None
    annual_income: Optional[float] = None


class BidderOut(BidderCreate):
    name: str  # joined from User


# Seller Model
class SellerCreate(BaseModel):
    email: EmailStr
    bank_routing_no: Optional[str] = None
    bank_account_no: Optional[str] = None
    account_balance: float = 0.00


class SellerOut(SellerCreate):
    name: str


# LocalVendor Model
class LocalVendorCreate(BaseModel):
    email: EmailStr
    business_name: str
    business_address: Optional[str] = None
    customer_service_phone: Optional[str] = None


class LocalVendorOut(LocalVendorCreate):
    pass


# HelpDesk Model
class HelpDeskOut(BaseModel):
    email: EmailStr
    staff_role: str


# CreditCard Model
class CreditCardCreate(BaseModel):
    card_number: str
    email: EmailStr
    card_type: Optional[str] = None
    expiration_date: Optional[date] = None


class CreditCardOut(CreditCardCreate):
    pass


# Category Model
class CategoryCreate(BaseModel):
    category_name: str
    parent_category: Optional[str] = None  # name string, not an ID
    is_leaf: bool = False
    status: str = "active"


class CategoryOut(CategoryCreate):
    category_id: int


# Product Model
# auction_end_time removed — auctions end by max_bids count, not timestamp
class ProductCreate(BaseModel):
    category_name: str
    auction_title: str
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    quantity: int = 1
    reserve_price: float
    max_bids: int
    photo_path: Optional[str] = None


class ProductOut(BaseModel):
    product_id: int
    seller_email: str
    listing_id: int
    category_name: str
    auction_title: str
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    quantity: int
    reserve_price: float
    max_bids: int
    listing_status: str
    created_at: datetime
    photo_path: Optional[str] = None


# Bid Model
class BidCreate(BaseModel):
    product_id: int
    bid_price: float


class BidOut(BaseModel):
    bid_id: int
    product_id: int
    bidder_email: str
    bid_price: float
    bid_timestamp: datetime


# Transaction Model
class TransactionOut(BaseModel):
    transaction_id: int
    product_id: int
    seller_email: str
    buyer_email: str
    payment: float
    payment_date: Optional[date] = None
    payment_status: str


# Rating Model
class RatingCreate(BaseModel):
    seller_email: str
    rating_date: date
    rating: int = Field(ge=1, le=5)
    rating_desc: Optional[str] = None


class RatingOut(RatingCreate):
    bidder_email: str


# Watchlist Model
class WatchlistAdd(BaseModel):
    bidder_email: EmailStr
    product_id: int


class WatchlistOut(WatchlistAdd):
    date_time_added: datetime


# Notification Model
class NotificationOut(BaseModel):
    notification_id: int
    bidder_email: EmailStr
    product_id: int
    notification_type: str
    timestamp: datetime
    is_read: bool


# Request Model
class RequestCreate(BaseModel):
    submitted_by_email: EmailStr
    request_type: str


class RequestOut(RequestCreate):
    request_id: int
    date_submitted: datetime
    status: str
    handled_by_email: Optional[EmailStr] = None
    handled_timestamp: Optional[datetime] = None


# ListingQuestion Model
class QuestionCreate(BaseModel):
    product_id: int
    bidder_email: EmailStr
    question_text: str


class QuestionOut(QuestionCreate):
    question_id: int
    answer_text: Optional[str] = None
    asked_at: datetime

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
    parent_category_id: Optional[int] = None
    is_leaf: bool = False
    status: str = "active"


class CategoryOut(CategoryCreate):
    category_id: int


# Product Model
class ProductCreate(BaseModel):
    seller_email: EmailStr
    category_id: int
    title: str
    description: Optional[str] = None
    reserve_price: float
    auction_end_time: datetime
    photo_path: Optional[str] = None


class ProductOut(BaseModel):
    product_id: int
    seller_email: EmailStr
    category_id: int
    title: str
    description: Optional[str] = None
    reserve_price: float
    auction_end_time: datetime
    listing_status: str
    created_at: datetime
    photo_path: Optional[str] = None


# Bid Model
class BidCreate(BaseModel):
    product_id: int
    bidder_email: EmailStr
    bid_amount: float


class BidOut(BidCreate):
    bid_id: int
    bid_timestamp: datetime


# Transaction Model
class TransactionOut(BaseModel):
    transaction_id: int
    bid_id: int
    product_id: int
    bidder_email: EmailStr
    seller_email: EmailStr
    final_amount: float
    payment_status: str
    payment_date: Optional[datetime] = None
    transaction_method: Optional[str] = None


# Rating Model
class RatingCreate(BaseModel):
    transaction_id: int
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class RatingOut(RatingCreate):
    rating_id: int


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

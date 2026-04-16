from datetime import datetime, timezone
import pymysql

from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.schemas import ProductCreate, ProductOut, CategoryOut
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Products"])

@router.get("/categories/leaf", response_model=list[CategoryOut])
def get_leaf_categories(db=Depends(get_db)):
    """Fetch all leaf categories. Products can only be listed under these."""
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM Category WHERE is_leaf = 1 AND status = 'active'")
        categories = cursor.fetchall()
    return categories

@router.get("/products", response_model=list[ProductOut])
def get_products(db=Depends(get_db)):
    """Fetch all active product listings."""
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM Product WHERE listing_status = 'active' ORDER BY created_at DESC")
        products = cursor.fetchall()
    return products

@router.post("/products", response_model=dict)
def create_product(
    product: ProductCreate, 
    current_user: dict = Depends(get_current_user), 
    db=Depends(get_db)
):
    """
    Create a new product listing. 
    Only accessible by users with the 'Seller' or 'Helpdesk' role.
    """
    role = current_user.get("role", "").lower()
    if role not in ["seller", "helpdesk"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only approved sellers can create listings"
        )

    # Use the authenticated user's email, ignore anything set in the request body for security.
    seller_email = current_user["email"]

    # Verify category exists and is a leaf category
    with db.cursor() as cursor:
        cursor.execute("SELECT is_leaf FROM Category WHERE category_id = %s", (product.category_id,))
        category = cursor.fetchone()
        
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        if not category["is_leaf"]:
            raise HTTPException(status_code=400, detail="Products must be listed under a leaf category")

        # Insert Product
        try:
            cursor.execute(
                """
                INSERT INTO Product 
                (seller_email, category_id, title, description, reserve_price, auction_end_time, photo_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    seller_email,
                    product.category_id,
                    product.title,
                    product.description,
                    product.reserve_price,
                    product.auction_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    product.photo_path
                )
            )
            # The auto-increment product_id
            product_id = cursor.lastrowid
            db.commit()
            
            return {"detail": "Product created successfully", "product_id": product_id}
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/sellers/{email}/products", response_model=list[ProductOut])
def get_seller_products(email: str, db=Depends(get_db)):
    """Fetch all product listings for a specific seller, including inactive ones."""
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM Product WHERE seller_email = %s ORDER BY created_at DESC", (email,))
        products = cursor.fetchall()
    return products


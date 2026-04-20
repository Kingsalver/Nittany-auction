from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import ProductCreate, ProductOut, CategoryOut
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Products"])


@router.get("/categories/leaf", response_model=list[CategoryOut])
def get_leaf_categories(db=Depends(get_db)):
    """All leaf categories — the only valid targets for new product listings."""
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Category WHERE is_leaf = TRUE AND status = 'active'"
        )
        return cursor.fetchall()


@router.get("/categories/{category_name}", response_model=dict)
def get_category_node(category_name: str, db=Depends(get_db)):
    """Return a category's direct subcategories and its active product listings.
    This is the primary category-hierarchy traversal endpoint — no hardcoding."""
    with db.cursor() as cursor:
        # Confirm the category exists
        cursor.execute(
            "SELECT category_id, category_name, parent_category, is_leaf "
            "FROM Category WHERE category_name = %s",
            (category_name,),
        )
        cat = cursor.fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")

        # Direct children
        cursor.execute(
            "SELECT category_id, category_name, parent_category, is_leaf "
            "FROM Category WHERE parent_category = %s AND status = 'active'",
            (category_name,),
        )
        children = cursor.fetchall()

        # Products directly in this category (only if leaf)
        products = []
        if cat["is_leaf"]:
            cursor.execute(
                """
                SELECT p.product_id, p.seller_email, p.listing_id,
                       p.category_name, p.auction_title, p.product_name,
                       p.reserve_price, p.max_bids, p.listing_status,
                       p.created_at,
                       COALESCE(MAX(b.bid_price), 0) AS current_highest_bid,
                       COUNT(b.bid_id)               AS bid_count,
                       s.avg_rating                  AS seller_avg_rating
                FROM   Product p
                LEFT JOIN Bid  b ON b.product_id = p.product_id
                LEFT JOIN Seller s ON s.email = p.seller_email
                WHERE  p.category_name = %s
                  AND  p.listing_status = 'active'
                GROUP BY p.product_id
                ORDER BY p.created_at DESC
                """,
                (category_name,),
            )
            products = cursor.fetchall()

    return {"category": cat, "subcategories": children, "products": products}


@router.get("/products", response_model=list[ProductOut])
def get_products(db=Depends(get_db)):
    """All active product listings, newest first."""
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Product WHERE listing_status = 'active' ORDER BY created_at DESC"
        )
        return cursor.fetchall()


@router.post("/products", response_model=dict)
def create_product(
    product: ProductCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a new auction listing. Seller or HelpDesk only.
    listing_id is auto-assigned as max(existing listing_id for this seller) + 1."""
    role = current_user.get("role", "").lower()
    if role not in ["seller", "helpdesk"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approved sellers can create listings",
        )

    seller_email = current_user["email"]

    with db.cursor() as cursor:
        # Verify category exists and is a leaf
        cursor.execute(
            "SELECT is_leaf FROM Category WHERE category_name = %s",
            (product.category_name,),
        )
        cat = cursor.fetchone()
        if not cat:
            raise HTTPException(status_code=400, detail="Category not found")
        if not cat["is_leaf"]:
            raise HTTPException(
                status_code=400,
                detail="Products must be listed in a leaf category",
            )

        # Assign the next listing_id for this seller
        cursor.execute(
            "SELECT COALESCE(MAX(listing_id), 0) AS max_id "
            "FROM Product WHERE seller_email = %s",
            (seller_email,),
        )
        next_listing_id = cursor.fetchone()["max_id"] + 1

        try:
            cursor.execute(
                """
                INSERT INTO Product
                  (seller_email, listing_id, category_name, auction_title,
                   product_name, product_description, quantity,
                   reserve_price, max_bids, photo_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    seller_email,
                    next_listing_id,
                    product.category_name,
                    product.auction_title,
                    product.product_name,
                    product.product_description,
                    product.quantity,
                    product.reserve_price,
                    product.max_bids,
                    product.photo_path,
                ),
            )
            product_id = cursor.lastrowid
            db.commit()
            return {
                "detail": "Product created successfully",
                "product_id": product_id,
                "listing_id": next_listing_id,
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/sellers/{email}/products", response_model=list[ProductOut])
def get_seller_products(email: str, db=Depends(get_db)):
    """All listings for a seller, grouped by status, newest first."""
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Product WHERE seller_email = %s ORDER BY listing_status, created_at DESC",
            (email,),
        )
        return cursor.fetchall()

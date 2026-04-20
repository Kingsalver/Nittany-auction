from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.schemas import ProductCreate, ProductOut, CategoryOut
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Products"])


def _get_descendant_leaves(cursor, root_name: str) -> list[str]:
    """Walk the category tree downward, collecting all leaf category names.
    All DB values come from parameterized queries — no user input interpolated."""
    cursor.execute(
        "SELECT is_leaf FROM Category WHERE category_name = %s", (root_name,)
    )
    root = cursor.fetchone()
    if not root:
        return []
    if root["is_leaf"]:
        return [root_name]

    leaves: list[str] = []
    frontier: list[str] = [root_name]
    while frontier:
        placeholders = ",".join(["%s"] * len(frontier))
        cursor.execute(
            f"SELECT category_name, is_leaf FROM Category WHERE parent_category IN ({placeholders})",
            frontier,
        )
        rows = cursor.fetchall()
        frontier = []
        for r in rows:
            if r["is_leaf"]:
                leaves.append(r["category_name"])
            else:
                frontier.append(r["category_name"])
    return leaves


@router.get("/categories/leaf", response_model=list[CategoryOut])
def get_leaf_categories(db=Depends(get_db)):
    """All leaf categories — the only valid targets for new product listings."""
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Category WHERE is_leaf = TRUE AND status = 'active'"
        )
        return cursor.fetchall()


@router.get("/categories")
def get_top_categories(db=Depends(get_db)):
    """Top-level categories (no parent) — entry point for hierarchy browsing."""
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT category_name, is_leaf FROM Category "
            "WHERE parent_category = 'Root' AND status = 'active' ORDER BY category_name"
        )
        return cursor.fetchall()


@router.get("/categories/{category_name}/ancestors")
def get_category_ancestors(category_name: str, db=Depends(get_db)):
    """Return the ancestor chain from root down to this category for breadcrumb rendering.
    category_name is always passed as a parameterized value."""
    with db.cursor() as cursor:
        path = []
        current = category_name
        for _ in range(10):  # guard against cycles; max depth is 4
            cursor.execute(
                "SELECT category_name, parent_category, is_leaf FROM Category WHERE category_name = %s",
                (current,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Category '{current}' not found")
            path.append({"category_name": row["category_name"], "is_leaf": row["is_leaf"]})
            if row["parent_category"] is None:
                break
            current = row["parent_category"]
        path.reverse()
        return [p for p in path if p["category_name"] != "Root"]


@router.get("/products/search")
def search_products(
    q: Optional[str] = Query(None, max_length=200),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    category: Optional[str] = Query(None, max_length=255),
    db=Depends(get_db),
):
    """Keyword + price + category search. All filters use parameterized queries."""
    with db.cursor() as cursor:
        conditions = ["p.listing_status = 'active'"]
        params: list = []

        if q:
            conditions.append(
                "(p.auction_title LIKE %s OR p.product_name LIKE %s OR p.product_description LIKE %s)"
            )
            like = f"%{q}%"
            params += [like, like, like]

        if min_price is not None:
            conditions.append("p.reserve_price >= %s")
            params.append(min_price)

        if max_price is not None:
            conditions.append("p.reserve_price <= %s")
            params.append(max_price)

        if category:
            leaves = _get_descendant_leaves(cursor, category)
            if not leaves:
                return []
            placeholders = ",".join(["%s"] * len(leaves))
            conditions.append(f"p.category_name IN ({placeholders})")
            params += leaves

        where = " AND ".join(conditions)
        cursor.execute(
            f"""
            SELECT p.product_id, p.seller_email, p.listing_id, p.category_name,
                   p.auction_title, p.product_name, p.product_description,
                   p.quantity, p.reserve_price, p.max_bids, p.listing_status,
                   p.created_at, p.photo_path,
                   u.name AS seller_name,
                   COALESCE(MAX(b.bid_price), 0) AS current_highest_bid,
                   COUNT(b.bid_id)               AS bid_count
            FROM Product p
            JOIN User u ON p.seller_email = u.email
            LEFT JOIN Bid b ON b.product_id = p.product_id
            WHERE {where}
            GROUP BY p.product_id
            ORDER BY p.created_at DESC
            """,
            params,
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
            """
            SELECT p.*, u.name AS seller_name 
            FROM Product p
            JOIN User u ON p.seller_email = u.email
            WHERE p.listing_status = 'active'
            ORDER BY p.created_at DESC
            """
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

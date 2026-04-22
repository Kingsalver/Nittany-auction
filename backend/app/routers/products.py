from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.schemas import ProductCreate, ProductOut, CategoryOut, ProductUpdate, ListingDeactivate
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Products"])


def _get_descendant_leaves(cursor, root_name: str) -> list[str]:
    # get all leaf categories
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
    # these are the only valid categories users can put listings in
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Category WHERE is_leaf = TRUE AND status = 'active'"
        )
        return cursor.fetchall()


@router.get("/categories")
def get_top_categories(db=Depends(get_db)):
    # get parent categories for the homepage
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT category_name, is_leaf FROM Category "
            "WHERE parent_category = 'Root' AND status = 'active' ORDER BY category_name"
        )
        return cursor.fetchall()


@router.get("/categories/{category_name}/ancestors")
def get_category_ancestors(category_name: str, db=Depends(get_db)):
    # get the breadcrumb path for a category
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
    # search by keyword, price, category
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
    # get subcategories and active products inside this category
    with db.cursor() as cursor:
        # verify category exists
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
    # grab all active products and newest ones first
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, u.name AS seller_name,
                   COUNT(b.bid_id) AS bid_count, MAX(b.bid_price) AS highest_bid
            FROM Product p
            JOIN User u ON p.seller_email = u.email
            LEFT JOIN Bid b ON p.product_id = b.product_id
            WHERE p.listing_status = 'active'
            GROUP BY p.product_id
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
    # make a new auction listing (only sellers and helpdesk can do this)
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
    # get all products from a specific seller
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, u.name AS seller_name,
                   COUNT(b.bid_id) AS bid_count, MAX(b.bid_price) AS highest_bid
            FROM Product p
            JOIN User u ON p.seller_email = u.email
            LEFT JOIN Bid b ON p.product_id = b.product_id
            WHERE p.seller_email = %s
            GROUP BY p.product_id
            ORDER BY p.listing_status, p.created_at DESC
            """,
            (email,)
        )
        return cursor.fetchall()

@router.get("/products/{product_id}", response_model=dict)
def get_product(product_id: int, db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, u.name AS seller_name,
                   COUNT(b.bid_id) AS bid_count, MAX(b.bid_price) AS highest_bid
            FROM Product p
            JOIN User u ON p.seller_email = u.email
            LEFT JOIN Bid b ON p.product_id = b.product_id
            WHERE p.product_id = %s
            GROUP BY p.product_id
            """,
            (product_id,),
        )
        product = cursor.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    update: ProductUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT seller_email, listing_status FROM Product WHERE product_id = %s",
            (product_id,),
        )
        product = cursor.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["seller_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="You do not own this listing")
    if product["listing_status"] == "sold":
        raise HTTPException(status_code=403, detail="Sold listings cannot be edited")

    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM Bid WHERE product_id = %s", (product_id,))
        if cursor.fetchone()["cnt"] > 0:
            raise HTTPException(
                status_code=403,
                detail="This listing cannot be updated because bidding has already started",
            )

        fields = {k: v for k, v in update.model_dump().items() if v is not None}
        if not fields:
            return {"detail": "No changes provided"}

        if "category_name" in fields:
            cursor.execute(
                "SELECT is_leaf FROM Category WHERE category_name = %s", (fields["category_name"],)
            )
            cat = cursor.fetchone()
            if not cat or not cat["is_leaf"]:
                raise HTTPException(status_code=400, detail="Category must be an active leaf category")

        set_clause = ", ".join(f"{col} = %s" for col in fields)
        cursor.execute(
            f"UPDATE Product SET {set_clause} WHERE product_id = %s",
            (*fields.values(), product_id),
        )
    db.commit()
    return {"detail": "Listing updated successfully"}


@router.patch("/products/{product_id}/deactivate")
def deactivate_product(
    product_id: int,
    body: ListingDeactivate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT seller_email, listing_status FROM Product WHERE product_id = %s",
            (product_id,),
        )
        product = cursor.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["seller_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="You do not own this listing")
    if product["listing_status"] != "active":
        raise HTTPException(status_code=400, detail="Only active listings can be deactivated")

    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM Bid WHERE product_id = %s", (product_id,))
        bid_count = cursor.fetchone()["cnt"]
        cursor.execute(
            """
            UPDATE Product
            SET listing_status = 'inactive',
                removal_reason = %s,
                bids_at_removal = %s,
                removal_timestamp = NOW()
            WHERE product_id = %s
            """,
            (body.reason, bid_count, product_id),
        )
    db.commit()
    return {"detail": "Listing deactivated successfully"}


@router.get("/bidders/{email}/auctions", response_model=list[ProductOut])
def get_bidder_auctions(email: str, db=Depends(get_db)):
    # get active auctions that they put a bid on
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, u.name AS seller_name,
                   COUNT(b.bid_id) AS bid_count, MAX(b.bid_price) AS highest_bid
            FROM Product p
            JOIN User u ON p.seller_email = u.email
            LEFT JOIN Bid b ON p.product_id = b.product_id
            WHERE p.listing_status = 'active' AND p.product_id IN (
                SELECT product_id FROM Bid WHERE bidder_email = %s
            )
            GROUP BY p.product_id
            ORDER BY p.created_at DESC
            """,
            (email,),
        )
        return cursor.fetchall()


@router.get("/bidders/{email}/won")
def get_bidder_won_auctions(email: str, db=Depends(get_db)):
    # get all auctions this buyer won (sold + has a transaction record for them)
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.product_id, p.seller_email, p.listing_id, p.auction_title,
                   p.product_name, p.photo_path, p.listing_status, p.max_bids,
                   p.reserve_price, p.created_at,
                   u.name AS seller_name,
                   t.payment, t.payment_status, t.transaction_id,
                   COUNT(b.bid_id) AS bid_count,
                   MAX(b.bid_price) AS highest_bid,
                   EXISTS(
                       SELECT 1 FROM Rating r 
                       WHERE r.bidder_email = %s 
                         AND r.seller_email = p.seller_email
                   ) AS already_reviewed
            FROM Transaction t
            JOIN Product p ON t.product_id = p.product_id
            JOIN User u ON p.seller_email = u.email
            LEFT JOIN Bid b ON b.product_id = p.product_id
            WHERE t.buyer_email = %s
            GROUP BY p.product_id, p.seller_email, p.listing_id, p.auction_title,
                     p.product_name, p.photo_path, p.listing_status, p.max_bids,
                     p.reserve_price, p.created_at, u.name, t.payment, 
                     t.payment_status, t.transaction_id
            ORDER BY t.transaction_id DESC
            """,
            (email, email),
        )
        return cursor.fetchall()

from contextlib import asynccontextmanager
from pathlib import Path
import hashlib, hmac, secrets
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE = Path(__file__).resolve().parent
engine = create_engine(f"sqlite:///{BASE / 'shopease.db'}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    password_hash = Column(String(300), nullable=False)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    category = Column(String(60), nullable=False)
    price = Column(Float, nullable=False)
    old_price = Column(Float)
    stock = Column(Integer, default=10)
    description = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=False)
    rating = Column(Float, default=4.5)
    badge = Column(String(30), default="")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_name = Column(String(120), nullable=False)
    email = Column(String(160), nullable=False)
    address = Column(Text, nullable=False)
    total = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_name = Column(String(120), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    order = relationship("Order", back_populates="items")

SEED = [
("Apple iPhone 15","Mobiles",62999,69900,12,"6.1-inch display, A16 Bionic chip, advanced dual-camera system and all-day battery life.","https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=700",4.8,"Bestseller"),
("Samsung Galaxy S24","Mobiles",54999,74999,15,"Premium Android phone with vivid AMOLED display, versatile cameras and Galaxy AI features.","https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=700",4.7,"Popular"),
("OnePlus Nord CE 4","Mobiles",24999,27999,18,"Everyday smartphone with bright display, capable camera, fast charging and generous storage.","https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=700",4.5,"Value"),
("Sony Wireless Headphones","Electronics",8990,9990,20,"Comfortable wireless headphones with noise cancellation, clear sound and long battery life.","https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=700",4.6,"Sale"),
("boAt Stone Bluetooth Speaker","Electronics",1499,2499,25,"Portable Bluetooth speaker with punchy sound, compact design and splash-resistant build.","https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=700",4.4,"Deal"),
("Logitech Wireless Mouse","Accessories",7495,8995,10,"Ergonomic wireless mouse with precise tracking, customizable buttons and multi-device connectivity.","https://images.unsplash.com/photo-1527814050087-3793815479db?w=700",4.8,"Top rated"),
("Classic Cotton T-Shirt","Fashion",699,999,40,"Soft everyday cotton T-shirt with a comfortable regular fit for casual outfits.","https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=700",4.3,""),
("Everyday Sneakers","Fashion",2199,2999,16,"Lightweight casual sneakers with cushioned support and versatile everyday styling.","https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=700",4.5,"Trending"),
("Analog Wrist Watch","Accessories",1899,2499,14,"Minimal analog wristwatch with a clean dial, durable strap and classic styling.","https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=700",4.2,""),
("Travel Backpack","Accessories",1299,1799,22,"Spacious backpack with multiple compartments, padded straps and a laptop sleeve.","https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=700",4.4,""),
("Ceramic Coffee Mug","Home",399,599,30,"Sturdy ceramic mug for coffee or tea with a comfortable handle and modern finish.","https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=700",4.1,""),
("Modern Desk Lamp","Home",1199,1599,11,"Compact modern desk lamp for focused reading and work, with warm ambient light.","https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=700",4.5,"")
]

def seed():
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            for row in SEED:
                db.add(Product(name=row[0], category=row[1], price=row[2], old_price=row[3], stock=row[4],
                               description=row[5], image_url=row[6], rating=row[7], badge=row[8]))
            db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    seed()
    yield

app = FastAPI(title="ShopEase FastAPI Store", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="demo-secret-change-before-production")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

def cart_data(request, db):
    cart = request.session.get("cart", {})
    lines, total, count = [], 0, 0
    for pid, qty in cart.items():
        product = db.query(Product).filter(Product.id == int(pid)).first()
        if product:
            subtotal = product.price * int(qty)
            lines.append({"product": product, "quantity": int(qty), "subtotal": subtotal})
            total += subtotal
            count += int(qty)
    return lines, total, count

@app.get("/")
def home(request: Request, q: str = "", category: str = ""):
    db = SessionLocal()
    try:
        query = db.query(Product)
        if q: query = query.filter(Product.name.ilike(f"%{q}%"))
        if category: query = query.filter(Product.category == category)
        products = query.order_by(Product.id).all()
        categories = [x[0] for x in db.query(Product.category).distinct().all()]
        _, _, count = cart_data(request, db)
        return templates.TemplateResponse("index.html", {"request":request,"products":products,"categories":categories,"q":q,"selected_category":category,"cart_count":count})
    finally: db.close()

@app.get("/product/{pid}")
def detail(request: Request, pid: int):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p: raise HTTPException(404, "Product not found")
        _, _, count = cart_data(request, db)
        return templates.TemplateResponse("product.html", {"request":request,"product":p,"cart_count":count})
    finally: db.close()

@app.post("/cart/add/{pid}")
def add(request: Request, pid: int, quantity: int = Form(1)):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p: raise HTTPException(404, "Product not found")
        cart = request.session.get("cart", {})
        cart[str(pid)] = min(int(cart.get(str(pid), 0)) + max(1, quantity), p.stock)
        request.session["cart"] = cart
        return RedirectResponse("/cart", status_code=303)
    finally: db.close()

@app.get("/cart")
def cart_page(request: Request):
    db = SessionLocal()
    try:
        lines,total,count = cart_data(request,db)
        return templates.TemplateResponse("cart.html", {"request":request,"lines":lines,"total":total,"cart_count":count})
    finally: db.close()

@app.post("/cart/update/{pid}")
def update(request: Request, pid: int, quantity: int = Form(...)):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        cart = request.session.get("cart", {})
        if quantity <= 0: cart.pop(str(pid), None)
        elif p: cart[str(pid)] = min(quantity, p.stock)
        request.session["cart"] = cart
        return RedirectResponse("/cart", status_code=303)
    finally: db.close()

@app.post("/cart/remove/{pid}")
def remove(request: Request, pid: int):
    cart = request.session.get("cart", {})
    cart.pop(str(pid), None)
    request.session["cart"] = cart
    return RedirectResponse("/cart", status_code=303)



def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def logged_in_user(request: Request, db):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {
        "request": request, "cart_count": 0, "error": None
    })

@app.post("/register")
def register(request: Request, full_name: str = Form(...),
             email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        full_name = full_name.strip()
        email = email.strip().lower()
        if len(full_name) < 2 or len(password) < 8:
            return templates.TemplateResponse("register.html", {
                "request": request, "cart_count": 0,
                "error": "Enter a name and a password with at least 8 characters."
            }, status_code=400)
        if db.query(User).filter(User.email == email).first():
            return templates.TemplateResponse("register.html", {
                "request": request, "cart_count": 0,
                "error": "An account with this email already exists."
            }, status_code=400)
        user = User(full_name=full_name, email=email,
                    password_hash=hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        request.session["user_id"] = user.id
        request.session["user_name"] = user.full_name
        return RedirectResponse("/", status_code=303)
    finally:
        db.close()

@app.get("/login")
def login_page(request: Request, next: str = "/"):
    return templates.TemplateResponse("login.html", {
        "request": request, "cart_count": 0, "error": None,
        "next_url": next
    })

@app.post("/login")
def login(request: Request, email: str = Form(...),
          password: str = Form(...), next: str = Form("/")):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {
                "request": request, "cart_count": 0,
                "error": "Invalid email or password.", "next_url": next
            }, status_code=401)
        request.session["user_id"] = user.id
        request.session["user_name"] = user.full_name
        destination = next if next.startswith("/") and not next.startswith("//") else "/"
        return RedirectResponse(destination, status_code=303)
    finally:
        db.close()

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/orders")
def my_orders(request: Request):
    db = SessionLocal()
    try:
        user = logged_in_user(request, db)
        if not user:
            return RedirectResponse("/login?next=/orders", status_code=303)
        orders = (db.query(Order).filter(Order.user_id == user.id)
                  .order_by(Order.id.desc()).all())
        _, _, count = cart_data(request, db)
        return templates.TemplateResponse("orders.html", {
            "request": request, "orders": orders, "cart_count": count
        })
    finally:
        db.close()


@app.get("/checkout")
def checkout_page(request: Request):
    db = SessionLocal()
    try:
        user = logged_in_user(request, db)
        if not user: return RedirectResponse("/login?next=/checkout", status_code=303)
        lines,total,count = cart_data(request,db)
        if not lines: return RedirectResponse("/cart", status_code=303)
        return templates.TemplateResponse("checkout.html", {"request":request,"lines":lines,"total":total,"cart_count":count,"user":user})
    finally: db.close()

@app.post("/checkout")
def checkout(request: Request, address: str = Form(...)):
    db = SessionLocal()
    try:
        user = logged_in_user(request, db)
        if not user: return RedirectResponse("/login?next=/checkout", status_code=303)
        lines,total,count = cart_data(request,db)
        if not lines: return RedirectResponse("/cart", status_code=303)
        for line in lines:
            if line["quantity"] > line["product"].stock:
                raise HTTPException(400, f"Insufficient stock: {line['product'].name}")
        order = Order(customer_name=user.full_name,email=user.email,address=address,total=total,user_id=user.id)
        for line in lines:
            line["product"].stock -= line["quantity"]
            order.items.append(OrderItem(product_name=line["product"].name,quantity=line["quantity"],unit_price=line["product"].price))
        db.add(order); db.commit(); oid = order.id
        request.session["cart"] = {}
        return RedirectResponse(f"/order-success/{oid}", status_code=303)
    finally: db.close()

@app.get("/order-success/{oid}")
def success(request: Request, oid: int):
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == oid).first()
        if not order: raise HTTPException(404, "Order not found")
        if order.user_id and request.session.get("user_id") != order.user_id:
            raise HTTPException(403, "You cannot view this order.")
        return templates.TemplateResponse("success.html", {"request":request,"order":order,"cart_count":0})
    finally: db.close()

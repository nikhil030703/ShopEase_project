# ShopEase – FastAPI E-commerce Demo

A colorful sample e-commerce application built with FastAPI, SQLAlchemy, SQLite, Jinja2 and HTML/CSS.

## Features
- 12 sample products loaded automatically on first run
- Product search, category filtering and product detail pages
- Session-based shopping cart (add, update, remove)
- User registration, login and logout
- Password hashing with PBKDF2-HMAC-SHA256
- Login-protected checkout and user-specific order history
- Stock validation and inventory reduction after checkout
- FastAPI API documentation at `/docs`

## Run on Windows PowerShell

Open PowerShell in this folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --port 8001
```

Open http://127.0.0.1:8001

Register a new account, login, add products to cart and test checkout.

## Notes
- Keep the terminal running while using the website. Press Ctrl+C to stop the server.
- If port 8001 is busy, use `--port 8002` and open http://127.0.0.1:8002.
- The SQLite database `shopease.db` is created automatically beside `main.py`.
- This is a learning/demo project. Before production use, configure a strong secret key, HTTPS, CSRF protection, migrations and production-grade authentication.

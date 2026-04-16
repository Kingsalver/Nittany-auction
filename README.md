# Nittany-auction

CMPSC431W Spring 2026 - NittanyAuction Project

## Tech Stack

| Layer    | Technology                |
| -------- | ------------------------- |
| Frontend | React + Vite, TailwindCSS |
| Backend  | FastAPI (Python), raw SQL |
| Database | MySQL                     |

---

## Quick Start

### 1. Install & Start MySQL (Ubuntu/WSL)

If you haven't installed MySQL yet:
```bash
sudo apt update
sudo apt install mysql-server
sudo service mysql start
```

### 2. Set Up the Database Credentials

The backend needs your MySQL root password to connect. We store this securely in an `.env` file instead of in code.

```bash
cd ~/CMPSC431W/Nittany-auction/backend
cp .env.example .env
nano .env
```
Inside the `.env` file, change `DB_PASSWORD=your_password_here` to your actual MySQL root password (if you don't have one, leave it blank: `DB_PASSWORD=`).

### 3. Provision the Database Schema & Data

Provision the schema and seed data:

```bash
source app/venv/bin/activate
pip install -r requirements.txt
mysql -u root -p < schema.sql
python setup_db.py
```

### 3. Start the Backend

```bash
cd ~/CMPSC431W/Nittany-auction/backend
source app/venv/bin/activate
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 4. Start the Frontend

```bash
cd ~/CMPSC431W/NittanyAuctionFrontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## Test Login

Use any user from `Users.csv`. Example:

- **Email:** `arubertelli0@lsu.edu`
- **Password:** `TbIF16hoUqGl`

---

## Useful Commands

| Task          | Command                                 |
| ------------- | --------------------------------------- |
| Start MySQL   | `sudo service mysql start`              |
| Stop MySQL    | `sudo service mysql stop`               |
| MySQL CLI     | `mysql -u root -p nittany_auction`      |
| Reset schema  | `mysql -u root -p < backend/schema.sql` |
| Re-seed data  | `python backend/setup_db.py`            |
| Start API     | `uvicorn app.main:app --reload`         |
| Start frontend| `npm run dev`                           |
| Show 10 Users | `mysql -u root -p nittany_auction -e "SELECT * FROM User LIMIT 10;"` |

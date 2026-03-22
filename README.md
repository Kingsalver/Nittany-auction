# Nittany-auction

CMPSC431W Spring 2026 - NittanyAuction Project

## Project Report

[Phase 1 Report (SharePoint)](https://pennstateoffice365-my.sharepoint.com/:w:/r/personal/axb6513_psu_edu/Documents/Nittany%20Auction%20Phase%201%20Report1.docx?d=w1069a8dc526e4da09c66283cbe70cfce&csf=1&web=1&e=adKBhU)

## Tech Stack

| Layer    | Technology                |
| -------- | ------------------------- |
| Frontend | React + Vite, TailwindCSS |
| Backend  | FastAPI (Python), raw SQL |
| Database | MySQL                     |

## Project Structure

```
Nittany-auction/
├── backend/
│   ├── .env.example        # DB credentials template
│   ├── requirements.txt    # Python dependencies
│   ├── schema.sql          # MySQL schema (16 tables)
│   └── app/
│       ├── __init__.py
│       ├── database.py     # pymysql connection helper
│       ├── main.py         # FastAPI entrypoint
│       └── schemas.py      # Pydantic request/response models
└── frontend/               # (coming soon)
```

---

## First-Time Setup (WSL / Ubuntu)

### 1. Install MySQL

```bash
sudo apt update
sudo apt install mysql-server
sudo service mysql start
```

### 2. Set the MySQL Root Password

```bash
sudo mysql
```

Then inside the MySQL prompt:

```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_password';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Create the Database & Tables

```bash
cd ~/CMPSC431W/Nittany-auction/backend
mysql -u root -p < schema.sql
```

This creates the `nittany_auction` database and all 16 tables.

### 4. Set Up the Python Backend

```bash
cd ~/CMPSC431W/Nittany-auction/backend

# Create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in your MySQL credentials:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=nittany_auction
```

### 6. Run the API Server

```bash
cd ~/CMPSC431W/Nittany-auction/backend
source venv/bin/activate
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/health` to verify the DB connection.

---

## Useful Commands

| Task          | Command                                 |
| ------------- | --------------------------------------- |
| Start MySQL   | `sudo service mysql start`              |
| Stop MySQL    | `sudo service mysql stop`               |
| MySQL CLI     | `mysql -u root -p nittany_auction`      |
| Reset schema  | `mysql -u root -p < backend/schema.sql` |
| Start API     | `uvicorn app.main:app --reload`         |
| Activate venv | `source backend/venv/bin/activate`      |

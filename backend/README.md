# Backend Running Instructions

## Prerequisites
- Python 3.9+
- MySQL Database (or update `backend/app/database.py` to use SQLite)

## Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Database:
   - Open `app/database.py` and update `DATABASE_URL` with your MySQL credentials.
   - Example: `mysql+aiomysql://user:password@localhost/dbname`

## Running the Server

Start the FastAPI server using uvicorn:
```bash
uvicorn app.main:app --reload
```

The API will be available at: `http://127.0.0.1:8000`
Interactive Docs: `http://127.0.0.1:8000/docs`

## Testing

Run the tests using pytest:
```bash
pytest
```

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from datetime import datetime
from typing import List

# ==========================================
# ✅ PALITAN ITO NG TOTOONG NEON CONNECTION STRING MO
# ==========================================
DATABASE_URL = "postgresql://neondb_owner:npg_YSydq1E3ojbL@ep-odd-violet-b4wcfpk6-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

app = FastAPI()

# Para makakonekta ang website mo sa Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Koneksyon sa Database
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Gawin ang Table kung wala pa
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            sender_email VARCHAR(255) NOT NULL,
            receiver_email VARCHAR(255) NOT NULL,
            message_text TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables ready!")

# ==========================================
# DATA MODELS
# ==========================================
class User(BaseModel):
    email: str
    username: str

class MessageSend(BaseModel):
    sender_email: str
    receiver_email: str
    message_text: str

# ==========================================
# API ROUTES
# ==========================================

@app.get("/")
def home():
    return {"message": "✅ TaskHive Backend is running!"}

@app.post("/register")
def register_user(user: User):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, username) VALUES (%s, %s) RETURNING id",
            (user.email, user.username)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return {"success": True, "user_id": user_id, "message": "✅ Registered successfully!"}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="❌ Email already exists!")
    finally:
        cur.close()
        conn.close()

@app.post("/send-message")
def send_message(msg: MessageSend):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (sender_email, receiver_email, message_text)
        VALUES (%s, %s, %s)
        RETURNING id, sent_at
    """, (msg.sender_email, msg.receiver_email, msg.message_text))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {
        "success": True,
        "message_id": result[0],
        "sent_at": result[1].isoformat()
    }

@app.get("/messages/{user1}/{user2}")
def get_messages(user1: str, user2: str, limit: int = 50):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sender_email, receiver_email, message_text, sent_at
        FROM messages
        WHERE (sender_email = %s AND receiver_email = %s)
           OR (sender_email = %s AND receiver_email = %s)
        ORDER BY sent_at ASC
        LIMIT %s
    """, (user1, user2, user2, user1, limit))
    
    messages = []
    for row in cur.fetchall():
        messages.append({
            "sender_email": row[0],
            "receiver_email": row[1],
            "message_text": row[2],
            "sent_at": row[3].isoformat()
        })
    
    cur.close()
    conn.close()
    return {"messages": messages}

@app.get("/users")
def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, username, created_at FROM users ORDER BY created_at DESC")
    users = []
    for row in cur.fetchall():
        users.append({
            "id": row[0],
            "email": row[1],
            "username": row[2],
            "created_at": row[3].isoformat()
        })
    cur.close()
    conn.close()
    return {"users": users}

if __name__ == "__main__":
    print("🔄 Initializing database...")
    init_db()
    print("🚀 Server ready!")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

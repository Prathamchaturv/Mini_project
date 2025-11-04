from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import json
import logging
import time
from PIL import Image, ImageDraw
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Home Security System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

# Server configuration
PORT = 5501
HOST = "127.0.0.1"

# Configure CORS
origins = [
    "http://127.0.0.1:5501",
    "http://localhost:5501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Server configuration
PORT = 5501
HOST = "127.0.0.1"

# Configure CORS
origins = [
     "http://127.0.0.1:5501",
     "http://localhost:5501",
     "*"  # Allow all origins for testing
]

app.add_middleware(
     CORSMiddleware,
     allow_origins=origins,
     allow_credentials=True,
     allow_methods=["*"],
     allow_headers=["*"],
)

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/templates", StaticFiles(directory="templates"), name="templates")
# HTML templates
templates = Jinja2Templates(directory="templates")

# Ensure folders exist
os.makedirs("static/images", exist_ok=True)

# Database connection management
def get_db():
    """Get a database connection. Creates one if it doesn't exist."""
    if not hasattr(get_db, 'conn') or get_db.conn is None:
        get_db.conn = sqlite3.connect("security.db", check_same_thread=False)
    return get_db.conn

# Initialize database schema
try:
    conn = get_db()
    cur = conn.cursor()
    
    # Create alerts table with proper schema
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT DEFAULT CURRENT_TIMESTAMP,
        message TEXT NOT NULL,
        image TEXT,
        alert_type TEXT DEFAULT 'general',
        priority TEXT DEFAULT 'normal',
        status TEXT DEFAULT 'active',
        location TEXT,
        notes TEXT,
        action_taken TEXT,
        resolution_time TEXT
    )
    """)
    
    # Create settings table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}", exc_info=True)
    raise
conn.commit()
# Perform lightweight migrations: ensure required columns exist on alerts table
try:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('alerts')")
    cols = [r[1] for r in cur.fetchall()]
    required = {
        'alert_type': "TEXT DEFAULT 'general'",
        'priority': "TEXT DEFAULT 'normal'",
        'status': "TEXT DEFAULT 'active'",
        'location': "TEXT",
        'notes': "TEXT",
        'action_taken': "TEXT",
        'resolution_time': "TEXT"
    }
    for col, definition in required.items():
        if col not in cols:
            logger.info(f"Adding missing column to alerts: {col}")
            try:
                cur.execute(f"ALTER TABLE alerts ADD COLUMN {col} {definition}")
            except Exception as exc:
                logger.warning(f"Could not add column {col}: {exc}")
    conn.commit()
except Exception:
    # Don't block startup on migration failures; log and continue
    logger.exception("Error while ensuring alerts schema")
# Keep the DB connection open for the running app (get_db returns the same connection)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Get alert statistics
        stats = {
            "total": 0,
            "active": 0,
            "resolved": 0,
            "by_priority": {},
            "by_type": {},
        }
        
        # Get total alerts
        cur.execute("SELECT COUNT(*) FROM alerts")
        stats["total"] = cur.fetchone()[0]
        
        # Get status counts
        cur.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status")
        for status, count in cur.fetchall():
            stats[status.lower()] = count
        
        # Get priority distribution
        cur.execute("SELECT priority, COUNT(*) FROM alerts GROUP BY priority")
        stats["by_priority"] = dict(cur.fetchall())
        
        # Get type distribution
        cur.execute("SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type")
        stats["by_type"] = dict(cur.fetchall())
        
        # Get all alerts with enhanced details
        cur.execute("""
            SELECT id, time, message, image, alert_type, priority, status,
                   location, notes, action_taken, resolution_time
            FROM alerts 
            ORDER BY 
                CASE status 
                    WHEN 'active' THEN 1 
                    WHEN 'pending' THEN 2 
                    ELSE 3 
                END,
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'normal' THEN 2 
                    ELSE 3 
                END,
                time DESC
        """)
        rows = cur.fetchall()

        alerts = []
        for r in rows:
            alerts.append({
                "id": r[0],
                "time": r[1],
                "message": r[2],
                "image": r[3],
                "alert_type": r[4] or "general",
                "priority": r[5] or "normal",
                "status": r[6] or "active",
                "location": r[7],
                "notes": r[8],
                "action_taken": r[9],
                "resolution_time": r[10]
            })
            
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "alerts": alerts,
                "stats": stats,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    except Exception as e:
        logger.error(f"Error in home route: {e}", exc_info=True)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "alerts": [],
                "stats": {"total": 0, "active": 0, "resolved": 0, "by_priority": {}, "by_type": {}},
                "error": "Failed to load dashboard data"
            }
        )

    # read potion setting if present
    cur.execute("SELECT value FROM settings WHERE key = ?", ("potion",))
    row = cur.fetchone()
    potion_value = row[0] if row else None
    return templates.TemplateResponse("dashboard.html", {"request": request, "alerts": alerts, "potion_value": potion_value})


@app.post("/upload-alert/")
async def upload_alert(
    message: str = Form(...),
    file: UploadFile = None,
    alert_type: str = Form("general"),
    priority: str = Form("normal"),
    location: str = Form(None)
):
    try:
        # Validate input
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required"}
            )
            
        if alert_type not in ["general", "security", "environmental"]:
            alert_type = "general"
            
        if priority not in ["high", "normal", "low"]:
            priority = "normal"
            
        logger.info(f"Received alert: message={message}, type={alert_type}, priority={priority}")
        image_path = None
    
        if file:
            # Sanitize filename to avoid directory traversal
            filename = os.path.basename(file.filename)
            image_path = f"static/images/{filename}"
            logger.info(f"Processing uploaded image: {filename}")
            
            # Save the uploaded image
            with open(image_path, "wb") as f:
                content = await file.read()
                f.write(content)
        else:
            # Generate a simple placeholder image with message
            img = Image.new("RGB", (400, 100), color="#2f2f2f")
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), message, fill="#ffffff")
            filename = f"alert_{int(time.time())}.jpg"
            image_path = f"static/images/{filename}"
            img.save(image_path)
            logger.info(f"Generated placeholder image: {image_path}")
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alerts 
            (time, message, image, alert_type, priority, status, location)
            VALUES (datetime('now'), ?, ?, ?, ?, 'active', ?)
        """, (
            message,
            image_path,
            alert_type,
            priority,
            location
        ))
        conn.commit()
        logger.info("Alert saved to database")
        
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        logger.error("Error processing alert:", exc_info=True)
        raise


@app.post("/update-alert/")
async def update_alert(
    alert_id: int = Form(...),
    status: str = Form(None),
    notes: str = Form(None),
    action_taken: str = Form(None)
):
    """Update alert details."""
    conn = get_db()
    cur = conn.cursor()
    
    updates = []
    values = []
    
    if status:
        updates.append("status = ?")
        values.append(status)
        if status == "resolved":
            updates.append("resolution_time = ?")
            values.append(time.strftime("%Y-%m-%d %H:%M:%S"))
    
    if notes:
        updates.append("notes = ?")
        values.append(notes)
    
    if action_taken:
        updates.append("action_taken = ?")
        values.append(action_taken)
    
    if updates:
        values.append(alert_id)
        query = f"UPDATE alerts SET {', '.join(updates)} WHERE id = ?"
        cur.execute(query, values)
        conn.commit()
    
    return {"status": "ok"}

@app.get("/alert-stats/")
async def get_alert_stats():
    """Get alert statistics."""
    conn = get_db()
    cur = conn.cursor()
    
    # Get various statistics
    stats = {
        "total": 0,
        "active": 0,
        "resolved": 0,
        "by_priority": {},
        "by_type": {},
        "response_times": []
    }
    
    cur.execute("SELECT COUNT(*) FROM alerts")
    stats["total"] = cur.fetchone()[0]
    
    cur.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status")
    for status, count in cur.fetchall():
        stats[status.lower()] = count
    
    cur.execute("SELECT priority, COUNT(*) FROM alerts GROUP BY priority")
    stats["by_priority"] = dict(cur.fetchall())
    
    cur.execute("SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type")
    stats["by_type"] = dict(cur.fetchall())
    
    # Calculate average response times for resolved alerts
    cur.execute("""
        SELECT time, resolution_time 
        FROM alerts 
        WHERE status = 'resolved' 
        AND resolution_time IS NOT NULL
    """)
    for time_created, time_resolved in cur.fetchall():
        try:
            t1 = time.strptime(time_created, "%Y-%m-%d %H:%M:%S")
            t2 = time.strptime(time_resolved, "%Y-%m-%d %H:%M:%S")
            diff = time.mktime(t2) - time.mktime(t1)
            stats["response_times"].append(diff)
        except Exception:
            continue
    
    if stats["response_times"]:
        stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
    else:
        stats["avg_response_time"] = 0
    
    return stats


@app.get("/dashboard-data/")
async def get_dashboard_data():
    """Get all data needed for the dashboard."""
    stats = await get_alert_stats()
    
    conn = get_db()
    cur = conn.cursor()
    
    # Get recent alerts
    cur.execute("""
        SELECT id, time, message, status, priority
        FROM alerts
        WHERE status = 'active'
        ORDER BY 
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                ELSE 3
            END,
            time DESC
        LIMIT 5
    """)
    recent_alerts = [{
        "id": r[0],
        "time": r[1],
        "message": r[2],
        "status": r[3],
        "priority": r[4]
    } for r in cur.fetchall()]
    
    return {
        "stats": stats,
        "recent_alerts": recent_alerts
    }


@app.get('/api/alerts')
async def api_get_alerts(limit: int = 50):
    """Return a JSON list of recent alerts for the dashboard JS."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, time, message, image, alert_type, priority, status, location
        FROM alerts
        ORDER BY time DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    alerts = []
    for r in rows:
        alerts.append({
            'id': r[0],
            'time': r[1],
            'message': r[2],
            'image': r[3],
            'alert_type': r[4],
            'priority': r[5],
            'status': r[6],
            'location': r[7]
        })
    return {'alerts': alerts}


@app.get('/api/stats')
async def api_get_stats():
    """Return a compact stats object expected by the dashboard JS."""
    stats = await get_alert_stats()
    return {
        'total_alerts': stats.get('total', 0),
        'high_priority': stats.get('by_priority', {}).get('high', 0),
        'avg_response_time': stats.get('avg_response_time', 0),
        'raw': stats
    }


@app.get('/model-status/')
async def model_status():
    """Return a simple model status for the dashboard. Reads settings if available."""
    conn = get_db()
    cur = conn.cursor()
    def get_setting(key, default=None):
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

    model_type = get_setting('model_type', 'stub')
    try:
        confidence = float(get_setting('model_confidence', 0.5))
    except Exception:
        confidence = 0.5

    available = True if model_type and model_type != 'stub' else False
    return {
        'model_type': model_type,
        'confidence': confidence,
        'available': available
    }


if __name__ == '__main__':
    # Run with uvicorn on port 5500 by default for local development
    try:
        import uvicorn
        uvicorn.run("main:app", host="127.0.0.1", port=5500, reload=True)
    except Exception as e:
        logger.error(f"Failed to start server via uvicorn: {e}")

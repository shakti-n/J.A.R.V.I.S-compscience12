import os
import re
import sqlite3
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "jarvis.db")
app = Flask(__name__)

IDENTITY = "Hello. I am JARVIS, created by Divyanshi, originally in 2026."

SYLLABUS = {
    "Unit 1: Programming and Computational Thinking": [
        "Chapter 1: Python Revision Tour",
        "Chapter 2: Python Revision Tour II",
        "Chapter 3: Working with Functions",
        "Chapter 4: Using Python Libraries",
        "Chapter 5: File Handling",
        "Chapter 6: Recursion",
        "Chapter 7: Idea of Algorithmic Efficiency",
        "Chapter 8: Data Visualization (PyPlot)",
        "Chapter 9: Data Structures - I: Linear Lists",
        "Chapter 10: Data Structures - II: Stacks & Queues",
    ],
    "Unit 2: Computer Networks": [
        "Chapter 11: Computer Networks - I",
        "Chapter 12: Computer Networks - II",
    ],
    "Unit 3: Data Management": [
        "Chapter 13: MySQL SQL Revision Tour",
        "Chapter 14: More on SQL (Table Creation and Data Manipulation)",
        "Chapter 15: Creating a Django Based Basic Web Application",
        "Chapter 16: Interface Python with MySQL",
    ],
    "Unit 4: Society, Law and Ethics": [
        "Chapter 17: Society, Law and Ethics",
    ],
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id INTEGER NOT NULL,
        name TEXT NOT NULL UNIQUE,
        description TEXT DEFAULT '',
        FOREIGN KEY(unit_id) REFERENCES units(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS concepts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        keywords TEXT DEFAULT '',
        FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id INTEGER,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT DEFAULT 'medium',
        times_reviewed INTEGER DEFAULT 0,
        FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS study_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flashcard_id INTEGER,
        action TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(flashcard_id) REFERENCES flashcards(id) ON DELETE CASCADE
    );
    """)
    # Keep the database aligned with the supplied 17-chapter syllabus.
    for unit_name, chapter_names in SYLLABUS.items():
        conn.execute("INSERT OR IGNORE INTO units(name) VALUES (?)", (unit_name,))
        uid = conn.execute("SELECT id FROM units WHERE name=?", (unit_name,)).fetchone()["id"]
        for chapter_name in chapter_names:
            conn.execute(
                "INSERT OR IGNORE INTO chapters(unit_id,name,description) VALUES (?,?,?)",
                (uid, chapter_name, "Syllabus chapter. Add your own notes or permitted study material.")
            )

    # Add a few non-textbook, topic-level starter concepts to demonstrate the engine.
    starters = [
        ("Chapter 6: Recursion", "Recursion", "Recursion is a problem-solving technique where a function calls itself on a smaller version of a problem, with a base case that stops further calls.", "recursion,base case,function"),
        ("Chapter 13: MySQL SQL Revision Tour", "SELECT", "SELECT retrieves data from one or more database tables. WHERE can filter rows and ORDER BY can sort results.", "select,sql,where,order by"),
        ("Chapter 14: More on SQL (Table Creation and Data Manipulation)", "Primary key", "A primary key uniquely identifies each row in a relational table and does not allow duplicate values.", "primary key,keys,table"),
        ("Chapter 16: Interface Python with MySQL", "Database connection", "A Python program can connect to a MySQL database through a database connector, execute SQL statements and process returned results.", "python,mysql,connector,database"),
        ("Chapter 11: Computer Networks - I", "IP address", "An IP address identifies a device or network interface on an IP network.", "ip,address,network"),
    ]
    for chapter, title, content, keywords in starters:
        cid = conn.execute("SELECT id FROM chapters WHERE name=?", (chapter,)).fetchone()["id"]
        exists = conn.execute("SELECT id FROM concepts WHERE chapter_id=? AND title=?", (cid, title)).fetchone()
        if not exists:
            conn.execute("INSERT INTO concepts(chapter_id,title,content,keywords) VALUES (?,?,?,?)",
                         (cid, title, content, keywords))
            concept_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO flashcards(concept_id,question,answer,difficulty) VALUES (?,?,?,?)",
                (concept_id, f"What is {title}?", content, "medium")
            )
    conn.commit()
    conn.close()

def make_flashcards(concept_id, count=4):
    conn = get_db()
    concept = conn.execute("SELECT * FROM concepts WHERE id=?", (concept_id,)).fetchone()
    if not concept:
        conn.close()
        return []
    title, content = concept["title"], concept["content"]
    templates = [
        (f"What is {title}?", content),
        (f"Explain {title} in exam-ready language.", content),
        (f"What is the key point to remember about {title}?", content),
        (f"How would you explain {title} to a Class 12 student?", content),
    ]
    existing = {r["question"] for r in conn.execute(
        "SELECT question FROM flashcards WHERE concept_id=?", (concept_id,)
    ).fetchall()}
    created = []
    for q, a in templates[:count]:
        if q in existing:
            continue
        cur = conn.execute(
            "INSERT INTO flashcards(concept_id,question,answer,difficulty) VALUES (?,?,?,?)",
            (concept_id, q, a, "medium")
        )
        created.append({"id": cur.lastrowid, "question": q, "answer": a})
    conn.commit()
    conn.close()
    return created

def answer_query(query):
    conn = get_db()
    q = query.lower().strip()
    if any(x in q for x in ["who are you", "introduce yourself", "your identity", "who is jarvis"]):
        conn.close()
        return IDENTITY

    # Chapter-aware lookup, useful for commands such as "Chapter 14 SQL".
    numbers = re.findall(r"\b(?:chapter|ch)\s*(\d{1,2})\b", q)
    words = [w for w in re.findall(r"[a-zA-Z0-9_]+", q) if len(w) > 2]
    clauses, params = [], []
    for w in words[:10]:
        like = f"%{w}%"
        clauses.append("(LOWER(c.title) LIKE ? OR LOWER(c.content) LIKE ? OR LOWER(c.keywords) LIKE ? OR LOWER(ch.name) LIKE ?)")
        params.extend([like, like, like, like])

    if numbers:
        clauses.append("ch.name LIKE ?")
        params.append(f"Chapter {numbers[0]}:%")

    if not clauses:
        conn.close()
        return "Please give me a topic, chapter, Python term, SQL command, or networking concept."

    rows = conn.execute(f"""
        SELECT c.title, c.content, ch.name chapter
        FROM concepts c JOIN chapters ch ON ch.id=c.chapter_id
        WHERE {" OR ".join(clauses)}
        ORDER BY ch.id, c.title LIMIT 6
    """, params).fetchall()
    conn.close()
    if not rows:
        return "I couldn't find that in my current knowledge core. Add your notes in Knowledge Core and ask again."
    return "\n\n".join(f"{r['title']} · {r['chapter']}\n{r['content']}" for r in rows)

@app.route("/")
def index():
    conn = get_db()
    stats = {
        "units": conn.execute("SELECT COUNT(*) FROM units").fetchone()[0],
        "chapters": conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0],
        "concepts": conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
        "flashcards": conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0],
    }
    units = conn.execute("SELECT * FROM units ORDER BY id").fetchall()
    chapters = conn.execute("SELECT c.*, u.name unit FROM chapters c JOIN units u ON u.id=c.unit_id ORDER BY c.id").fetchall()
    conn.close()
    return render_template("index.html", identity=IDENTITY, stats=stats, units=units, chapters=chapters, syllabus=SYLLABUS)

@app.route("/flashcards")
def flashcards():
    conn = get_db()
    cards = conn.execute("""
        SELECT f.*, c.title concept, ch.name chapter
        FROM flashcards f
        LEFT JOIN concepts c ON c.id=f.concept_id
        LEFT JOIN chapters ch ON ch.id=c.chapter_id
        ORDER BY f.id DESC
    """).fetchall()
    conn.close()
    return render_template("flashcards.html", cards=cards)

@app.route("/knowledge")
def knowledge():
    conn = get_db()
    chapters = conn.execute("SELECT * FROM chapters ORDER BY id").fetchall()
    concepts = conn.execute("""
        SELECT c.*, ch.name chapter FROM concepts c JOIN chapters ch ON ch.id=c.chapter_id
        ORDER BY ch.id, c.title
    """).fetchall()
    conn.close()
    return render_template("knowledge.html", chapters=chapters, concepts=concepts)

@app.post("/api/ask")
def api_ask():
    data = request.get_json(silent=True) or {}
    return jsonify({"answer": answer_query(data.get("query", "")), "identity": IDENTITY})

@app.post("/api/review")
def api_review():
    data = request.get_json(silent=True) or {}
    fid, action = data.get("flashcard_id"), data.get("action", "reviewed")
    conn = get_db()
    if fid:
        conn.execute("UPDATE flashcards SET times_reviewed=times_reviewed+1 WHERE id=?", (fid,))
        conn.execute("INSERT INTO study_log(flashcard_id,action) VALUES (?,?)", (fid, action))
        conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.post("/api/add")
def api_add():
    data = request.get_json(silent=True) or {}
    chapter = data.get("chapter", "").strip()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    keywords = data.get("keywords", "").strip()
    if not chapter or not title or not content:
        return jsonify({"ok": False, "error": "Chapter, concept and notes are required."}), 400

    conn = get_db()
    # Put user-created chapters into a sensible custom unit if the name is not one of the 17.
    if not conn.execute("SELECT id FROM chapters WHERE name=?", (chapter,)).fetchone():
        uid = conn.execute("SELECT id FROM units WHERE name=?", ("Unit 3: Data Management",)).fetchone()["id"]
        conn.execute("INSERT INTO chapters(unit_id,name,description) VALUES (?,?,?)", (uid, chapter, "User-added study chapter."))
    cid = conn.execute("SELECT id FROM chapters WHERE name=?", (chapter,)).fetchone()["id"]
    cur = conn.execute("INSERT INTO concepts(chapter_id,title,content,keywords) VALUES (?,?,?,?)",
                        (cid, title, content, keywords))
    conn.commit()
    concept_id = cur.lastrowid
    conn.close()
    make_flashcards(concept_id)
    return jsonify({"ok": True, "message": "Knowledge ingested. Flashcards generated."})

@app.post("/api/generate/<int:concept_id>")
def api_generate(concept_id):
    cards = make_flashcards(concept_id)
    return jsonify({"ok": True, "cards": cards, "message": f"{len(cards)} flashcards generated."})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

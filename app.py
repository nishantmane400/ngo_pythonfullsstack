from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
import webbrowser
from threading import Timer
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "skillup_secure_99"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
    
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS site_content (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            banner TEXT, vision TEXT, mission TEXT, about TEXT,
            story TEXT, core_values TEXT, media_intro TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, description TEXT, image TEXT
        )
    ''')

   
    conn.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT, 
            url TEXT,
            type TEXT -- 'image' or 'video'
        )
    ''')

    conn.execute('''
        INSERT OR IGNORE INTO site_content (id, banner, vision, mission, about, story, core_values, media_intro) 
        VALUES (1, "", "Empowering communities.", "Creating sustainable change.", "About our NGO...", 
                "Founded in 2015...", "Integrity, Dedication", "Our gallery and videos.")
    ''')
    conn.commit()
    conn.close()

init_db()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        action = request.form.get("action")
        if not username or not password:
            flash("Essential credentials required!")
            return redirect(url_for("login"))
        conn = get_db_connection()
        if action == "register":
            try:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                conn.commit()
                flash("Registration successful! Please login.")
            except sqlite3.IntegrityError: flash("User exists")
        else:
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
            if user:
                session["user"] = username
                return redirect(url_for("home"))
            else: flash("Invalid credentials!")
        conn.close()
    return render_template("login.html")

@app.route("/home")
def home():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    content = conn.execute('SELECT * FROM site_content WHERE id = 1').fetchone()
    conn.close()
    return render_template("home.html", content=content)

@app.route("/about")
def about():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    content = conn.execute('SELECT * FROM site_content WHERE id = 1').fetchone()
    conn.close()
    return render_template("about.html", content=content)

@app.route("/our-work")
def our_work():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    conn.close()
    return render_template("our_work.html", projects=projects)

@app.route("/media")
def media():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    content = conn.execute('SELECT * FROM site_content WHERE id = 1').fetchone()
    images = conn.execute("SELECT * FROM media WHERE type='image'").fetchall()
    videos = conn.execute("SELECT * FROM media WHERE type='video'").fetchall()
    conn.close()
    return render_template("media.html", content=content, images=images, videos=videos)

# --- ADMIN ROUTES ---
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "admin123":
            session["admin_auth"] = True
            return redirect(url_for("admin_panel"))
        else: flash("Unauthorized Admin Access!")
    return render_template("admin_login.html")

@app.route("/admin/panel", methods=["GET", "POST"])
def admin_panel():
    if not session.get("admin_auth"): return redirect(url_for("admin_login"))
    
    conn = get_db_connection()
    content = conn.execute('SELECT * FROM site_content WHERE id = 1').fetchone()

    if request.method == "POST":
        # 1. Handle Home/About/Media Intro Content Updates
        if 'update_site_content' in request.form:
            vision = request.form.get("vision", content['vision'])
            mission = request.form.get("mission", content['mission'])
            about = request.form.get("about", content['about'])
            story = request.form.get("story", content['story'])
            core_values = request.form.get("core_values", content['core_values'])
            media_intro = request.form.get("media_intro", content['media_intro'])
            
            banner_file = request.files.get('banner')
            banner_name = content['banner']
            if banner_file and banner_file.filename != '':
                banner_name = secure_filename(banner_file.filename)
                banner_file.save(os.path.join(app.config['UPLOAD_FOLDER'], banner_name))

            conn.execute('''UPDATE site_content SET vision=?, mission=?, about=?, banner=?, 
                           story=?, core_values=?, media_intro=? WHERE id=1''', 
                         (vision, mission, about, banner_name, story, core_values, media_intro))
            flash("Site content updated!")

        # 2. Handle Projects (Add/Update/Delete)
        elif 'add_project' in request.form:
            title = request.form.get('project_title')
            desc = request.form.get('project_desc')
            file = request.files.get('project_image')
            img_name = ""
            if file and file.filename != '':
                img_name = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
            conn.execute('INSERT INTO projects (title, description, image) VALUES (?, ?, ?)', (title, desc, img_name))
            flash("New project added!")

        elif 'delete_project' in request.form:
            project_id = request.form.get('project_id')
            conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            flash("Project deleted!")

        # 3. Handle Gallery Images (Add & Delete)
        elif 'add_gallery_image' in request.form:
            file = request.files.get('gallery_file')
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                conn.execute("INSERT INTO media (filename, type) VALUES (?, 'image')", (filename,))
                flash("Image added to gallery!")

        elif 'delete_gallery_image' in request.form:
            image_id = request.form.get('image_id')
            conn.execute('DELETE FROM media WHERE id = ?', (image_id,))
            flash("Gallery image removed!")

        # 4. Handle Video Links (Add & Delete)
        elif 'add_video' in request.form:
            video_url = request.form.get('video_url')
            if video_url:
                # FIX: Automatically convert standard YouTube links to Embed links
                if "watch?v=" in video_url:
                    video_url = video_url.replace("watch?v=", "embed/")
                conn.execute("INSERT INTO media (url, type) VALUES (?, 'video')", (video_url,))
                flash("Video link added!")

        elif 'delete_video' in request.form:
            video_id = request.form.get('video_id')
            conn.execute('DELETE FROM media WHERE id = ?', (video_id,))
            flash("Video link deleted!")

        conn.commit()
        return redirect(url_for("admin_panel"))
        
    projects = conn.execute('SELECT * FROM projects').fetchall()
    images = conn.execute("SELECT * FROM media WHERE type='image'").fetchall()
    videos = conn.execute("SELECT * FROM media WHERE type='video'").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", content=content, projects=projects, images=images, videos=videos)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)
import os
import json
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

import markdown as md
from markupsafe import Markup
import frontmatter

load_dotenv()


# ---------- helpers ----------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("scrapbook_authed"):
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content"


def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def parse_date_ymd(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return datetime.min
    

def days_between(start_ymd: str, end_ymd: str) -> int:
    """Inclusive day count. Returns 0 if invalid."""
    try:
        s = datetime.strptime(start_ymd, "%Y-%m-%d").date()
        e = datetime.strptime(end_ymd, "%Y-%m-%d").date()
        return (e - s).days + 1 if e >= s else 0
    except Exception:
        return 0


def load_travel_stops():
    path = CONTENT_DIR / "travel" / "stops.json"
    stops = load_json(path, default=[])

    normalized = []
    for st in stops:
        start = str(st.get("start_date", ""))
        end = str(st.get("end_date", ""))

        raw_id = (st.get("id") or "").strip()
        place = (st.get("place") or "").strip()
        fallback_id = f"{place.lower().replace(' ', '-')}-{start}"
        stop_id = raw_id or fallback_id

        normalized.append(
            {
                "id": stop_id,
                "place": place,
                "country": (st.get("country") or "").strip(),
                "lat": st.get("lat"),
                "lng": st.get("lng"),
                "start_date": start,
                "end_date": end,
                "days": days_between(start, end),
                "type": (st.get("type") or "visited").strip(),
                "notes_md": st.get("notes_md") or "",
            }
        )

    normalized.sort(key=lambda x: parse_date_ymd(x["start_date"]), reverse=True)
    return normalized


def slugify(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1]
    stem = name.replace(".md", "")
    parts = stem.split("-", 3)
    return parts[-1] if len(parts) >= 4 else stem


def load_blog_posts():
    blog_dir = CONTENT_DIR / "blog"
    posts = []

    if not blog_dir.exists():
        return posts

    for path in sorted(blog_dir.glob("*.md"), reverse=True):
        post = frontmatter.load(path)
        meta = post.metadata or {}

        draft = bool(meta.get("draft", False))
        if draft:
            continue

        title = meta.get("title") or path.stem
        date_str = str(meta.get("date") or "")
        tags = meta.get("tags") or []
        excerpt = meta.get("excerpt") or ""

        posts.append(
            {
                "title": title,
                "date": date_str,
                "date_sort": parse_date_ymd(date_str),
                "tags": tags,
                "excerpt": excerpt,
                "slug": meta.get("slug") or slugify(path.name),
                "content_md": post.content,
            }
        )

    posts.sort(key=lambda p: p["date_sort"], reverse=True)
    return posts


def plain_excerpt(md_text: str, max_len: int = 120) -> str:
    if not md_text:
        return ""
    text = " ".join(md_text.replace("\n", " ").split())
    return (text[: max_len - 1] + "…") if len(text) > max_len else text


def load_portfolio_items():
    path = CONTENT_DIR / "portfolio" / "items.json"
    items = load_json(path, default=[])

    normalized = []
    for it in items:
        normalized.append(
            {
                "type": it.get("type", "").strip(),
                "title": it.get("title", "").strip(),
                "slug": it.get("slug", "").strip(),
                "year": it.get("year"),
                "tags": it.get("tags", []),
                "cover_image": it.get("cover_image", ""),
                "description_md": it.get("description_md", ""),
                "excerpt": plain_excerpt(it.get("description_md", "")),
                "images": it.get("images", []),
                "video_url": it.get("video_url", ""),
                "credits": it.get("credits", []),
            }
        )

    normalized.sort(key=lambda x: (x["year"] or 0), reverse=True)
    return normalized


# ---------- app factory ----------
def create_app() -> Flask:
    app = Flask(__name__)

    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY missing. Set it in .env")

    app.secret_key = secret

    @app.after_request
    def add_no_store(response):
        response.headers["Cache-Control"] = "no-store"
        return response
    
    @app.template_filter("markdown")
    def markdown_filter(text: str):
        if not text:
            return ""
        html = md.markdown(
            text,
            extensions=["fenced_code", "tables", "nl2br"],
        )
        return Markup(html)

    @app.context_processor
    def inject_globals():
        return {"now_year": datetime.now().year}

    @app.get("/")
    def home():
        return render_template("index.html", page_title="Home")

    @app.get("/portfolio/photography")
    def portfolio_photography():
        items = [i for i in load_portfolio_items() if i["type"] == "photo"]
        return render_template(
            "portfolio_list.html",
            page_title="Photography",
            heading="Photography",
            items=items,
        )

    @app.get("/portfolio/film")
    def portfolio_film():
        items = [i for i in load_portfolio_items() if i["type"] == "film"]
        return render_template(
            "portfolio_list.html",
            page_title="Film",
            heading="Film",
            items=items,
        )
    
    @app.get("/portfolio/<slug>")
    def portfolio_detail(slug: str):
        items = load_portfolio_items()
        item = next((i for i in items if i["slug"] == slug), None)
        if not item:
            return render_template("404.html", page_title="Not Found"), 404

        return render_template(
            "portfolio_detail.html",
            page_title=item["title"],
            item=item,
        )

    @app.get("/blog")
    def blog():
        posts = load_blog_posts()
        return render_template("blog.html", page_title="Blog", posts=posts)
    
    @app.get("/blog/<slug>")
    def blog_post(slug: str):
        posts = load_blog_posts()
        post = next((p for p in posts if p["slug"] == slug), None)
        if not post:
            return render_template("404.html", page_title="Not Found"), 404

        return render_template("blog_post.html", page_title=post["title"], post=post)

    @app.get("/travel")
    def travel():
        stops = load_travel_stops()
        return render_template("travel.html", page_title="Travel", stops=stops)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("scrapbook_authed"):
            return redirect(url_for("scrapbook"), code=303)

        if request.method == "POST":
            password = request.form.get("password", "")
            expected = os.getenv("SCRAPBOOK_PASSWORD", "")

            if expected and password == expected:
                session["scrapbook_authed"] = True
                next_url = request.form.get("next") or url_for("scrapbook")
                return redirect(next_url, code=303)

            flash("Incorrect password.", "danger")

        return render_template("login.html", page_title="Login")

    @app.get("/logout")
    def logout():
        session.pop("scrapbook_authed", None)
        return redirect(url_for("home"))

    @app.route("/scrapbook", methods=["GET", "POST"])
    @login_required
    def scrapbook():
        if request.method == "POST":
            return redirect(url_for("scrapbook"), code=303)

        entries_path = CONTENT_DIR / "scrapbook" / "entries.json"
        entries = load_json(entries_path, default=[])

        entries_sorted = sorted(
            entries,
            key=lambda e: parse_date_ymd(e.get("date", "")),
            reverse=True,
        )

        return render_template(
            "scrapbook.html",
            page_title="Scrapbook",
            entries=entries_sorted,
        )

    return app


# ---------- run ----------
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
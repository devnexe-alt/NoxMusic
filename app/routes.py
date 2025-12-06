from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, session
from .models import Track, Playlist, User, Genre, LikedTrack, ListeningHistory
from . import db
from .auth import require_admin, require_auth

main_bp = Blueprint("main", __name__)

def is_ajax():
    """Проверка AJAX запроса"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

@main_bp.route("/")
def index():
    """Главная страница"""
    tracks = Track.query.order_by(Track.id).limit(100).all()
    
    user_id = session.get("user_id")
    if user_id:
        playlists = Playlist.query.filter(
            db.or_(
                Playlist.is_public == True,
                Playlist.user_id == user_id
            )
        ).order_by(Playlist.id).all()
    else:
        playlists = Playlist.query.filter_by(is_public=True).order_by(Playlist.id).all()
    
    genres = Genre.query.all()
    
    template = "index_content.html" if is_ajax() else "index.html"
    
    return render_template(
        template,
        tracks=[t.to_dict() for t in tracks],
        playlists=[p.to_dict() for p in playlists],
        genres=[g.to_dict() for g in genres]
    )

@main_bp.route("/playlist/<int:playlist_id>")
def playlist_view(playlist_id):
    """Страница плейлиста"""
    pl = Playlist.query.get_or_404(playlist_id)
    
    user_id = session.get("user_id")
    if not pl.is_public and pl.user_id != user_id:
        if is_ajax():
            return "Access denied", 403
        flash("Access denied to this playlist", "error")
        return redirect(url_for("main.index"))
    
    template = "playlist_content.html" if is_ajax() else "playlist.html"
    
    return render_template(
        template,
        playlist=pl.to_dict(include_tracks=True)
    )

@main_bp.route("/search")
@require_auth(roles=['admin', 'user'])
def search_page():
    """Страница поиска"""
    query = request.args.get("q", "").strip()
    
    tracks = []
    playlists = []
    genres = []
    
    if query:
        tracks = Track.query.filter(
            db.or_(
                Track.title.ilike(f"%{query}%"),
                Track.artist.ilike(f"%{query}%"),
                Track.album.ilike(f"%{query}%")
            )
        ).limit(50).all()
        
        user_id = session.get("user_id")
        if user_id:
            playlists = Playlist.query.filter(
                db.or_(
                    Playlist.is_public == True,
                    Playlist.user_id == user_id
                ),
                Playlist.name.ilike(f"%{query}%")
            ).limit(20).all()
        else:
            playlists = Playlist.query.filter_by(is_public=True)\
                .filter(Playlist.name.ilike(f"%{query}%"))\
                .limit(20).all()
        
        genres = Genre.query.filter(Genre.name.ilike(f"%{query}%")).all()
    
    template = "search_content.html" if is_ajax() else "search.html"
    
    return render_template(
        template,
        query=query,
        tracks=[t.to_dict() for t in tracks],
        playlists=[p.to_dict() for p in playlists],
        genres=[g.to_dict() for g in genres],
        tracks_count=len(tracks),
        playlists_count=len(playlists),
        genres_count=len(genres)
    )

@main_bp.route("/library")
@require_auth(roles=['admin', 'user'])
def library_page():
    """Библиотека пользователя"""
    user_id = session.get("user_id")
    if not user_id:
        if is_ajax():
            return "Login required", 401
        flash("Please log in to access your library", "error")
        return redirect(url_for("auth.login", next=url_for("main.library_page")))
    
    user = User.query.get_or_404(user_id)
    user_playlists = Playlist.query.filter_by(user_id=user_id).all()
    
    liked_tracks = []
    liked = LikedTrack.query.filter_by(user_id=user_id).all()
    if liked:
        track_ids = [l.track_id for l in liked]
        liked_tracks = Track.query.filter(Track.id.in_(track_ids)).all()
    
    history = ListeningHistory.query.filter_by(user_id=user_id)\
        .order_by(ListeningHistory.played_at.desc())\
        .limit(20).all()
    
    template = "library_content.html" if is_ajax() else "library.html"
    
    return render_template(
        template,
        user=user,
        playlists=[p.to_dict() for p in user_playlists],
        liked_tracks=[t.to_dict() for t in liked_tracks],
        history=[h.to_dict() for h in history],
        playlists_count=len(user_playlists),
        liked_count=len(liked_tracks)
    )

@main_bp.route("/liked")
@require_auth(roles=['admin', 'user'])
def liked_songs_page():
    """Лайкнутые треки"""
    user_id = session.get("user_id")
    if not user_id:
        if is_ajax():
            return "Login required", 401
        flash("Please log in to view liked songs", "error")
        return redirect(url_for("auth.login", next=url_for("main.liked_songs_page")))
    
    liked = LikedTrack.query.filter_by(user_id=user_id).order_by(LikedTrack.liked_at.desc()).all()
    
    liked_tracks = []
    if liked:
        track_ids = [l.track_id for l in liked]
        liked_tracks = Track.query.filter(Track.id.in_(track_ids)).all()
    
    template = "liked_songs_content.html" if is_ajax() else "liked_songs.html"
    
    return render_template(
        template,
        liked_tracks=[t.to_dict() for t in liked_tracks],
        liked_count=len(liked_tracks)
    )

@main_bp.route("/admin")
@require_auth(roles=['admin'])
def admin_dashboard():
    """Панель администратора"""
    total_tracks = Track.query.count()
    total_playlists = Playlist.query.count()
    total_users = User.query.count()
    
    popular_tracks = Track.query.order_by(Track.plays.desc()).limit(10).all()
    
    return render_template(
        "admin_dashboard.html",
        total_tracks=total_tracks,
        total_playlists=total_playlists,
        total_users=total_users,
        popular_tracks=popular_tracks
    )

@main_bp.route("/admin/login", methods=["GET"])
def admin_login_page():
    """Страница входа для администраторов"""
    return render_template("admin_login.html")

@main_bp.route("/tracks")
def tracks_page():
    """Все треки"""
    page = int(request.args.get("page", 1))
    per = int(request.args.get("per", 50))
    genre = request.args.get("genre")
    search = request.args.get("search", "").strip()
    
    q = Track.query
    
    if genre:
        q = q.filter(Track.genre == genre)
    
    if search:
        q = q.filter(
            db.or_(
                Track.title.ilike(f"%{search}%"),
                Track.artist.ilike(f"%{search}%"),
                Track.album.ilike(f"%{search}%")
            )
        )
    
    q = q.order_by(Track.id)
    items = q.paginate(page=page, per_page=per, error_out=False)
    
    genres = Genre.query.all()
    
    return render_template(
        "tracks.html",
        items=items,
        genres=genres,
        current_genre=genre,
        search_query=search
    )

@main_bp.route("/track/<int:track_id>")
def track_view(track_id):
    """Отдельный трек"""
    t = Track.query.get_or_404(track_id)
    return render_template("track.html", track=t.to_dict())

@main_bp.route("/admin/bulk_upload", methods=["POST"])
@require_auth(roles=['admin'])
def admin_bulk_upload():
    """Массовая загрузка"""
    svc = current_app.media_service
    added_total = []
    
    if 'files' in request.files:
        files = request.files.getlist('files')
        res = svc.add_tracks_from_files(files)
        added_total.extend(res)
    
    if 'zipfile' in request.files and request.files['zipfile'].filename:
        zipf = request.files['zipfile']
        res_zip = svc.add_tracks_from_zip(zipf)
        added_total.extend(res_zip)
    
    flash(f"Bulk upload finished — added {len(added_total)} tracks.", "success")
    return redirect(url_for("main.admin_dashboard"))

@main_bp.route("/admin/rescan", methods=["POST"])
@require_auth(roles=['admin'])
def admin_rescan():
    """Пересканировать медиа"""
    svc = current_app.media_service
    summary = svc.scan_and_sync_db()
    flash(
        f"Rescan finished. Found {summary['found_files']} files, added {summary['added']} tracks.",
        "success"
    )
    return redirect(url_for("main.admin_dashboard"))

@main_bp.route("/admin/upload", methods=["GET", "POST"])
@require_auth(roles=['admin'])
def admin_upload():
    """Загрузка файла"""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part", "error")
            return redirect(url_for("main.admin_upload"))
        
        f = request.files["file"]
        if f.filename == "":
            flash("Empty filename", "error")
            return redirect(url_for("main.admin_upload"))
        
        svc = current_app.media_service
        track = svc.add_track_from_upload(f)
        flash(f"Uploaded: {track['title']}", "success")
        return redirect(url_for("main.admin_dashboard"))
    
    return render_template("admin_upload.html")

@main_bp.route("/admin/tracks")
@require_auth(roles=['admin'])
def admin_tracks():
    """Управление треками"""
    page = int(request.args.get("page", 1))
    per = int(request.args.get("per", 50))
    
    items = Track.query.order_by(Track.id.desc()).paginate(
        page=page,
        per_page=per,
        error_out=False
    )
    
    return render_template("admin_tracks.html", items=items)

@main_bp.route("/admin/track/<int:track_id>/edit", methods=["GET", "POST"])
@require_auth(roles=['admin'])
def admin_track_edit(track_id):
    """Редактирование трека"""
    track = Track.query.get_or_404(track_id)
    
    if request.method == "POST":
        track.title = request.form.get("title", track.title)
        track.artist = request.form.get("artist", track.artist)
        track.album = request.form.get("album", track.album)
        track.genre = request.form.get("genre", track.genre)
        track.year = request.form.get("year", type=int)
        track.cover = request.form.get("cover", track.cover)
        track.gradient = request.form.get("gradient", track.gradient)
        track.lyrics = request.form.get("lyrics", track.lyrics)
        
        db.session.commit()
        flash(f"Updated: {track.title}", "success")
        return redirect(url_for("main.admin_tracks"))
    
    genres = Genre.query.all()
    return render_template("admin_track_edit.html", track=track, genres=genres)

@main_bp.route("/admin/track/<int:track_id>/delete", methods=["POST"])
@require_auth(roles=['admin'])
def admin_track_delete(track_id):
    """Удаление трека"""
    track = Track.query.get_or_404(track_id)
    
    import os
    if track.media:
        file_path = os.path.join(
            current_app.config["MEDIA_DIR"],
            os.path.basename(track.media)
        )
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                flash(f"Error deleting file: {e}", "error")
    
    db.session.delete(track)
    db.session.commit()
    
    flash(f"Deleted: {track.title}", "success")
    return redirect(url_for("main.admin_tracks"))

@main_bp.route("/admin/genres")
@require_auth(roles=['admin'])
def admin_genres():
    """Управление жанрами"""
    genres = Genre.query.all()
    return render_template("admin_genres.html", genres=genres)

@main_bp.route("/admin/genre/new", methods=["GET", "POST"])
@require_auth(roles=['admin'])
def admin_genre_new():
    """Создание жанра"""
    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            flash("Genre name is required", "error")
            return redirect(url_for("main.admin_genre_new"))
        
        existing = Genre.query.filter_by(name=name).first()
        if existing:
            flash("Genre already exists", "error")
            return redirect(url_for("main.admin_genres"))
        
        genre = Genre(
            name=name,
            cover=request.form.get("cover", "🎵"),
            gradient=request.form.get("gradient", "linear-gradient(135deg,#667eea,#764ba2)")
        )
        db.session.add(genre)
        db.session.commit()
        
        flash(f"Created genre: {name}", "success")
        return redirect(url_for("main.admin_genres"))
    
    return render_template("admin_genre_new.html")

@main_bp.route("/admin/users")
@require_auth(roles=['admin'])
def admin_users():
    """Управление пользователями"""
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@main_bp.route("/genres")
def genres_page():
    """Жанры"""
    genres = Genre.query.all()
    return render_template("genres.html", genres=genres)

@main_bp.route("/genre/<int:genre_id>")
def genre_view(genre_id):
    """Жанр с треками"""
    genre = Genre.query.get_or_404(genre_id)
    tracks = Track.query.filter_by(genre=genre.name).order_by(Track.plays.desc()).all()
    
    return render_template(
        "genre.html",
        genre=genre,
        tracks=[t.to_dict() for t in tracks]
    )
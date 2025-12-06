from flask import Blueprint, jsonify, request, current_app, session
from .models import Track, Playlist, User, ListeningHistory, LikedTrack, Genre, playlist_tracks
from . import db
from .auth import require_api_key, require_login
from sqlalchemy import func, desc

api_bp = Blueprint("api", __name__)

@api_bp.route("/playlists/my", methods=["GET"])
@require_login
def get_my_playlists_only():  # ИЗМЕНИТЬ ИМЯ
    """Получить только плейлисты текущего пользователя"""
    user_id = session.get("user_id")
    pls = Playlist.query.filter_by(user_id=user_id).order_by(Playlist.id).all()
    return jsonify([p.to_dict() for p in pls])

# Tracks
@api_bp.route("/tracks", methods=["GET"])
def get_tracks():
    page = int(request.args.get("page", 1))
    per = int(request.args.get("per", 100))
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
    
    return jsonify({
        "items": [t.to_dict() for t in items.items],
        "page": page,
        "per": per,
        "total": items.total
    })

@api_bp.route("/tracks/<int:track_id>", methods=["GET"])
def get_track(track_id):
    t = Track.query.get_or_404(track_id)
    return jsonify(t.to_dict())

@api_bp.route("/queue/add/<int:track_id>", methods=["POST"])
@require_login
def add_to_queue(track_id):
    """Добавить трек в очередь"""
    if 'queue' not in session:
        session['queue'] = []
    
    if track_id not in session['queue']:
        session['queue'].append(track_id)
        session.modified = True
    
    return jsonify({"success": True, "queue": session['queue']})

@api_bp.route("/tracks/<int:track_id>/play", methods=["POST"])
def play_track(track_id):
    """Записать воспроизведение трека"""
    track = Track.query.get_or_404(track_id)
    track.plays += 1
    
    user_id = session.get("user_id")
    if user_id:
        history = ListeningHistory(user_id=user_id, track_id=track_id)
        db.session.add(history)
    
    db.session.commit()
    return jsonify({"success": True, "plays": track.plays})

@api_bp.route("/tracks/<int:track_id>/like", methods=["POST"])
def like_track(track_id):
    """Лайкнуть/анлайкнуть трек"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    track = Track.query.get_or_404(track_id)
    
    existing = LikedTrack.query.filter_by(user_id=user_id, track_id=track_id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"liked": False})
    else:
        liked = LikedTrack(user_id=user_id, track_id=track_id)
        db.session.add(liked)
        db.session.commit()
        return jsonify({"liked": True})

@api_bp.route("/tracks/trending", methods=["GET"])
def get_trending():
    """Популярные треки"""
    limit = int(request.args.get("limit", 20))
    tracks = Track.query.order_by(desc(Track.plays)).limit(limit).all()
    return jsonify([t.to_dict() for t in tracks])

@api_bp.route("/tracks/recent", methods=["GET"])
def get_recent():
    """Недавно добавленные"""
    limit = int(request.args.get("limit", 20))
    tracks = Track.query.order_by(desc(Track.created_at)).limit(limit).all()
    return jsonify([t.to_dict() for t in tracks])

# Playlists - ТОЛЬКО ОДНА ФУНКЦИЯ get_playlists
@api_bp.route("/playlists", methods=["GET"])
def get_playlists():  # ОСТАВЛЯЕМ ТОЛЬКО ЭТУ ФУНКЦИЮ
    user_id = session.get("user_id")
    
    if user_id:
        # Показываем публичные плейлисты + плейлисты пользователя
        pls = Playlist.query.filter(
            db.or_(
                Playlist.is_public == True,
                Playlist.user_id == user_id
            )
        ).order_by(Playlist.id).all()
    else:
        # Только публичные плейлисты
        pls = Playlist.query.filter_by(is_public=True).order_by(Playlist.id).all()
    
    return jsonify([p.to_dict() for p in pls])

@api_bp.route("/playlists/<int:playlist_id>", methods=["GET"])
def get_playlist(playlist_id):  # singular - get_playlist
    pl = Playlist.query.get_or_404(playlist_id)
    
    user_id = session.get("user_id")
    if not pl.is_public and pl.user_id != user_id:
        return jsonify({"error": "access_denied"}), 403
    
    return jsonify(pl.to_dict(include_tracks=True))

@api_bp.route("/playlists", methods=["POST"])
def create_playlist():  # Другое имя
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    data = request.get_json()
    pl = Playlist(
        name=data.get("name", "New Playlist"),
        description=data.get("description", ""),
        cover=data.get("cover", "🎵"),
        gradient=data.get("gradient", "linear-gradient(135deg,#7c3aed,#3b82f6)"),
        is_public=data.get("is_public", True),
        user_id=user_id
    )
    db.session.add(pl)
    db.session.commit()
    
    return jsonify(pl.to_dict()), 201

@api_bp.route("/playlists/<int:playlist_id>", methods=["PUT"])
def update_playlist(playlist_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    pl = Playlist.query.get_or_404(playlist_id)
    
    if pl.user_id != user_id and not session.get("is_admin"):
        return jsonify({"error": "access_denied"}), 403
    
    data = request.get_json()
    
    if "name" in data:
        pl.name = data["name"]
    if "description" in data:
        pl.description = data["description"]
    if "cover" in data:
        pl.cover = data["cover"]
    if "gradient" in data:
        pl.gradient = data["gradient"]
    if "is_public" in data:
        pl.is_public = data["is_public"]
    
    db.session.commit()
    return jsonify(pl.to_dict())

@api_bp.route("/playlists/<int:playlist_id>", methods=["DELETE"])
def delete_playlist(playlist_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    pl = Playlist.query.get_or_404(playlist_id)
    
    if pl.user_id != user_id and not session.get("is_admin"):
        return jsonify({"error": "access_denied"}), 403
    
    db.session.delete(pl)
    db.session.commit()
    
    return jsonify({"success": True})

@api_bp.route("/playlists/<int:playlist_id>/tracks", methods=["POST"])
def add_track_to_playlist(playlist_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    pl = Playlist.query.get_or_404(playlist_id)
    
    if pl.user_id != user_id and not session.get("is_admin"):
        return jsonify({"error": "access_denied"}), 403
    
    data = request.get_json()
    track_id = data.get("track_id")
    
    if not track_id:
        return jsonify({"error": "track_id required"}), 400
    
    track = Track.query.get_or_404(track_id)
    
    if track not in pl.tracks:
        pl.tracks.append(track)
        db.session.commit()
    
    return jsonify(pl.to_dict(include_tracks=True))

@api_bp.route("/playlists/<int:playlist_id>/tracks/<int:track_id>", methods=["DELETE"])
def remove_track_from_playlist(playlist_id, track_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    pl = Playlist.query.get_or_404(playlist_id)
    
    if pl.user_id != user_id and not session.get("is_admin"):
        return jsonify({"error": "access_denied"}), 403
    
    track = Track.query.get_or_404(track_id)
    
    if track in pl.tracks:
        pl.tracks.remove(track)
        db.session.commit()
    
    return jsonify(pl.to_dict(include_tracks=True))

# Genres
@api_bp.route("/genres", methods=["GET"])
def get_genres():
    genres = Genre.query.all()
    return jsonify([g.to_dict() for g in genres])

@api_bp.route("/genres/<int:genre_id>/tracks", methods=["GET"])
def get_genre_tracks(genre_id):
    genre = Genre.query.get_or_404(genre_id)
    tracks = Track.query.filter_by(genre=genre.name).limit(50).all()
    return jsonify({
        "genre": genre.to_dict(),
        "tracks": [t.to_dict() for t in tracks]
    })

# User
@api_bp.route("/user/history", methods=["GET"])
def get_user_history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    limit = int(request.args.get("limit", 50))
    
    history = ListeningHistory.query.filter_by(user_id=user_id)\
        .order_by(desc(ListeningHistory.played_at))\
        .limit(limit).all()
    
    return jsonify([h.to_dict() for h in history])

@api_bp.route("/user/liked", methods=["GET"])
def get_user_liked():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    
    liked = LikedTrack.query.filter_by(user_id=user_id).all()
    track_ids = [l.track_id for l in liked]
    tracks = Track.query.filter(Track.id.in_(track_ids)).all()
    
    return jsonify([t.to_dict() for t in tracks])

@api_bp.route("/user/recommendations", methods=["GET"])
def get_recommendations():
    """Простые рекомендации на основе истории"""
    user_id = session.get("user_id")
    if not user_id:
        tracks = Track.query.order_by(desc(Track.plays)).limit(20).all()
        return jsonify([t.to_dict() for t in tracks])
    
    history = ListeningHistory.query.filter_by(user_id=user_id)\
        .order_by(desc(ListeningHistory.played_at))\
        .limit(20).all()
    
    if not history:
        tracks = Track.query.order_by(desc(Track.plays)).limit(20).all()
        return jsonify([t.to_dict() for t in tracks])
    
    listened_track_ids = [h.track_id for h in history]
    listened_tracks = Track.query.filter(Track.id.in_(listened_track_ids)).all()
    genres = list(set([t.genre for t in listened_tracks if t.genre]))
    
    if genres:
        recommendations = Track.query.filter(
            Track.genre.in_(genres),
            ~Track.id.in_(listened_track_ids)
        ).order_by(desc(Track.plays)).limit(20).all()
    else:
        recommendations = Track.query.order_by(desc(Track.plays)).limit(20).all()
    
    return jsonify([t.to_dict() for t in recommendations])

# Добавить этот endpoint для проверки статуса
@api_bp.route("/user/status", methods=["GET"])
def user_status():
    """Проверить статус входа пользователя"""
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({
                "logged_in": True,
                "user": user.to_dict()
            })
    
    return jsonify({"logged_in": False})

# Admin
@api_bp.route("/upload", methods=["POST"])
@require_api_key
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no_file"}), 400
    f = request.files["file"]
    svc = current_app.media_service
    track = svc.add_track_from_upload(f)
    return jsonify(track), 201

@api_bp.route("/rescan", methods=["POST"])
@require_api_key
def rescan():
    svc = current_app.media_service
    summary = svc.scan_and_sync_db()
    return jsonify(summary)
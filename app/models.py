from . import db
from datetime import datetime

# Связующая таблица для треков в плейлистах
playlist_tracks = db.Table('playlist_tracks',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id'), primary_key=True),
    db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True),
    db.Column('position', db.Integer, default=0),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

class Track(db.Model):
    __tablename__ = "tracks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), default="Unknown")
    album = db.Column(db.String(255), default="")
    duration = db.Column(db.Integer, nullable=True)
    cover = db.Column(db.String(8), default="🎵")
    media = db.Column(db.String(512), unique=True, nullable=False)
    gradient = db.Column(db.String(255), default="linear-gradient(135deg,#374151,#1f2937)")
    genre = db.Column(db.String(100), default="Other")
    year = db.Column(db.Integer, nullable=True)
    plays = db.Column(db.Integer, default=0)
    lyrics = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    playlists = db.relationship('Playlist', secondary=playlist_tracks, back_populates='tracks')
    listening_history = db.relationship('ListeningHistory', back_populates='track', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "cover": self.cover,
            "media": self.media,
            "gradient": self.gradient,
            "genre": self.genre,
            "year": self.year,
            "plays": self.plays,
            "lyrics": self.lyrics,
            "created_at": self.created_at.isoformat()
        }

class Playlist(db.Model):
    __tablename__ = "playlists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    cover = db.Column(db.String(8), default="🎵")
    gradient = db.Column(db.String(255), default="linear-gradient(135deg,#7c3aed,#3b82f6)")
    is_public = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracks = db.relationship('Track', secondary=playlist_tracks, back_populates='playlists')
    user = db.relationship('User', back_populates='playlists')

    def to_dict(self, include_tracks=False):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cover": self.cover,
            "gradient": self.gradient,
            "is_public": self.is_public,
            "trackCount": len(self.tracks),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        if include_tracks:
            data["tracks"] = [t.to_dict() for t in self.tracks]
        return data

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    avatar = db.Column(db.String(8), default="👤")
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    playlists = db.relationship('Playlist', back_populates='user', cascade='all, delete-orphan')
    listening_history = db.relationship('ListeningHistory', back_populates='user', cascade='all, delete-orphan')
    liked_tracks = db.relationship('LikedTrack', back_populates='user', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "avatar": self.avatar,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat()
        }

class ListeningHistory(db.Model):
    __tablename__ = "listening_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='listening_history')
    track = db.relationship('Track', back_populates='listening_history')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "track": self.track.to_dict(),
            "played_at": self.played_at.isoformat()
        }

class LikedTrack(db.Model):
    __tablename__ = "liked_tracks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False)
    liked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='liked_tracks')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'track_id', name='unique_user_track_like'),)

class Genre(db.Model):
    __tablename__ = "genres"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    cover = db.Column(db.String(8), default="🎵")
    gradient = db.Column(db.String(255), default="linear-gradient(135deg,#667eea,#764ba2)")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cover": self.cover,
            "gradient": self.gradient
        }
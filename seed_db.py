"""
Seed database with sample data
Run: python seed_db.py
"""
from app import create_app, db
from app.models import Genre, Playlist, User

def seed_database():
    app = create_app()
    
    with app.app_context():
        print("🌱 Seeding database...")
        
        # Create genres
        genres_data = [
            {"name": "Pop", "cover": "🎤", "gradient": "linear-gradient(135deg,#f093fb,#f5576c)"},
            {"name": "Rock", "cover": "🎸", "gradient": "linear-gradient(135deg,#4facfe,#00f2fe)"},
            {"name": "Hip-Hop", "cover": "🎧", "gradient": "linear-gradient(135deg,#43e97b,#38f9d7)"},
            {"name": "Jazz", "cover": "🎷", "gradient": "linear-gradient(135deg,#fa709a,#fee140)"},
            {"name": "Electronic", "cover": "🎹", "gradient": "linear-gradient(135deg,#30cfd0,#330867)"},
            {"name": "Classical", "cover": "🎻", "gradient": "linear-gradient(135deg,#a8edea,#fed6e3)"},
            {"name": "R&B", "cover": "💿", "gradient": "linear-gradient(135deg,#ff9a9e,#fecfef)"},
            {"name": "Country", "cover": "🤠", "gradient": "linear-gradient(135deg,#ffecd2,#fcb69f)"},
            {"name": "Latin", "cover": "💃", "gradient": "linear-gradient(135deg,#ff6a00,#ee0979)"},
            {"name": "Indie", "cover": "🎵", "gradient": "linear-gradient(135deg,#667eea,#764ba2)"},
        ]
        
        for genre_data in genres_data:
            existing = Genre.query.filter_by(name=genre_data["name"]).first()
            if not existing:
                genre = Genre(**genre_data)
                db.session.add(genre)
                print(f"  ✓ Added genre: {genre_data['name']}")
        
        # Create default user (admin)
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@spotify.local",
                avatar="👨‍💼",
                is_admin=True
            )
            db.session.add(admin)
            print("  ✓ Created admin user")
        
        # Create sample playlists
        playlists_data = [
            {
                "name": "Today's Top Hits",
                "description": "The hottest tracks right now",
                "cover": "🔥",
                "gradient": "linear-gradient(135deg,#f093fb,#f5576c)",
                "is_public": True
            },
            {
                "name": "Chill Vibes",
                "description": "Relax and unwind with these chill tracks",
                "cover": "😌",
                "gradient": "linear-gradient(135deg,#4facfe,#00f2fe)",
                "is_public": True
            },
            {
                "name": "Workout Mix",
                "description": "Get pumped with these high-energy tracks",
                "cover": "💪",
                "gradient": "linear-gradient(135deg,#43e97b,#38f9d7)",
                "is_public": True
            },
            {
                "name": "Focus Flow",
                "description": "Instrumental tracks for deep work",
                "cover": "🧠",
                "gradient": "linear-gradient(135deg,#fa709a,#fee140)",
                "is_public": True
            },
            {
                "name": "Party Hits",
                "description": "Turn up the volume and dance!",
                "cover": "🎉",
                "gradient": "linear-gradient(135deg,#30cfd0,#330867)",
                "is_public": True
            },
            {
                "name": "Sleep Sounds",
                "description": "Peaceful tracks for a good night's sleep",
                "cover": "😴",
                "gradient": "linear-gradient(135deg,#a8edea,#fed6e3)",
                "is_public": True
            },
        ]
        
        for playlist_data in playlists_data:
            existing = Playlist.query.filter_by(name=playlist_data["name"]).first()
            if not existing:
                playlist = Playlist(**playlist_data, user_id=admin.id)
                db.session.add(playlist)
                print(f"  ✓ Added playlist: {playlist_data['name']}")
        
        db.session.commit()
        print("✅ Database seeded successfully!")
        print("\n📝 Next steps:")
        print("1. Start the server: python run.py")
        print("2. Upload some audio files through /admin")
        print("3. Enjoy your Spotify clone!")

if __name__ == "__main__":
    seed_database()
import re
import io
import zipfile
from pathlib import Path
from mutagen import File as MutagenFile
from werkzeug.utils import secure_filename
from ..models import Track
from .. import db

class MediaService:
    def __init__(self, app):
        self.app = app
        self.media_dir: Path = Path(app.config["MEDIA_DIR"])
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def start_watcher(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except Exception:
            # watchdog не установлен — пропустить
            return False

        class Handler(FileSystemEventHandler):
            def __init__(self, svc):
                self.svc = svc
            def on_created(self, event):
                if event.is_directory:
                    return
                # только аудио файлы
                if str(event.src_path).lower().endswith((".mp3", ".ogg", ".wav", ".m4a")):
                    # небольшая задержка, чтобы файл дописался
                    import time
                    time.sleep(0.3)
                    try:
                        self.svc.scan_and_sync_db()
                    except Exception:
                        pass

        observer = Observer()
        observer.schedule(Handler(self), str(self.media_dir), recursive=False)
        observer.daemon = True
        observer.start()
        self.observer = observer
        return True

    def _list_media_files(self):
        files = []
        for p in sorted(self.media_dir.glob("*")):
            if p.suffix.lower() in (".mp3", ".ogg", ".wav", ".m4a"):
                files.append(p)
        return files

    def _get_duration(self, path: Path):
        try:
            audio = MutagenFile(path)
            if audio is None or not hasattr(audio, "info"):
                return None
            return int(audio.info.length)
        except Exception:
            return None

    def _slug_to_title(self, fname: str) -> str:
        name = Path(fname).stem
        name = re.sub(r"[_\-]+", " ", name)
        return name.title()

    def scan_and_sync_db(self):
        found = self._list_media_files()
        existing_media = {t.media for t in Track.query.all()}
        added = []
        for p in found:
            web_path = f"/static/media/{p.name}"
            if web_path in existing_media:
                continue
            title = self._slug_to_title(p.name)
            duration = self._get_duration(p)
            t = Track(
                title=title,
                artist="Unknown",
                album="",
                duration=duration,
                cover="🎵",
                media=web_path
            )
            db.session.add(t)
            added.append(t)
        if added:
            db.session.commit()
        return {"found_files": len(found), "added": len(added)}

    def add_track_from_upload(self, file_storage):
        safe_name = file_storage.filename
        base = Path(safe_name).stem
        ext = Path(safe_name).suffix or ".mp3"
        counter = 0
        dest = self.media_dir / (base + ext)
        while dest.exists():
            counter += 1
            dest = self.media_dir / f"{base}-{counter}{ext}"
        file_storage.save(dest)
        web_path = f"/static/media/{dest.name}"
        duration = self._get_duration(dest)
        title = self._slug_to_title(dest.name)
        t = Track(
            title=title,
            artist="Unknown",
            album="",
            duration=duration,
            cover="🎵",
            media=web_path
        )
        db.session.add(t)
        db.session.commit()
        return t.to_dict()


    def add_tracks_from_files(self, file_storages):
        """
        Принимает список werkzeug FileStorage (input multiple),
        сохраняет файлы в media_dir и добавляет записи в БД.
        Возвращает список добавленных Track.to_dict().
        """
        allowed_ext = (".mp3", ".ogg", ".wav", ".m4a")
        added = []
        for fs in file_storages:
            if not fs or not fs.filename:
                continue
            name = secure_filename(fs.filename)
            if not name:
                continue
            if not name.lower().endswith(allowed_ext):
                # пропускаем не-аудио
                continue
            base = Path(name).stem
            ext = Path(name).suffix
            dest = self.media_dir / (base + ext)
            i = 0
            while dest.exists():
                i += 1
                dest = self.media_dir / f"{base}-{i}{ext}"
            fs.save(dest)
            duration = self._get_duration(dest)
            title = self._slug_to_title(dest.name)
            t = Track(
                title=title,
                artist="Unknown",
                album="",
                duration=duration,
                cover="🎵",
                media=f"/static/media/{dest.name}"
            )
            db.session.add(t)
            added.append(t)
        if added:
            db.session.commit()
        return [t.to_dict() for t in added]

    def add_tracks_from_zip(self, file_storage):
        """
        Принимает Zip (FileStorage), извлекает аудиофайлы в media_dir,
        добавляет записи в БД и возвращает список добавленных записей.
        """
        allowed_ext = (".mp3", ".ogg", ".wav", ".m4a")
        added = []
        # читаем zip в память (упрощённо)
        data = file_storage.read()
        bio = io.BytesIO(data)
        try:
            with zipfile.ZipFile(bio) as z:
                for member in z.infolist():
                    if member.is_dir():
                        continue
                    name = Path(member.filename).name  # убираем поддиректории
                    if not name:
                        continue
                    if not name.lower().endswith(allowed_ext):
                        continue
                    safe = secure_filename(name)
                    if not safe:
                        continue
                    base = Path(safe).stem
                    ext = Path(safe).suffix or ".mp3"
                    dest = self.media_dir / (base + ext)
                    i = 0
                    while dest.exists():
                        i += 1
                        dest = self.media_dir / f"{base}-{i}{ext}"
                    with z.open(member) as member_file, open(dest, "wb") as out_f:
                        out_f.write(member_file.read())
                    duration = self._get_duration(dest)
                    title = self._slug_to_title(dest.name)
                    t = Track(
                        title=title,
                        artist="Unknown",
                        album="",
                        duration=duration,
                        cover="🎵",
                        media=f"/static/media/{dest.name}"
                    )
                    db.session.add(t)
                    added.append(t)
                if added:
                    db.session.commit()
        except zipfile.BadZipFile:
            # плохой zip — ничего не делаем
            return []
        return [t.to_dict() for t in added]
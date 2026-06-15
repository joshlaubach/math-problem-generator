"""Tests for agents/lesson_store.py — the single lesson read/write path."""
import json

import pytest

from agents import lesson_store


@pytest.fixture()
def file_lessons_dir(tmp_path, monkeypatch):
    """Point the store's file cache at a temp dir, force file mode."""
    monkeypatch.setattr(lesson_store, "_LESSONS_DIR", tmp_path)
    monkeypatch.setattr(lesson_store, "_uses_database", lambda: False)
    return tmp_path


class TestFileMode:
    def test_round_trip(self, file_lessons_dir):
        lesson = {"topic_id": "alg1_t1", "hook": "Why do scales balance?",
                  "worked_example": [{"expression_latex": "$x=2$"}]}
        lesson_store.save_lesson("alg1_t1", lesson)
        assert lesson_store.get_lesson("alg1_t1") == lesson

    def test_missing_returns_none(self, file_lessons_dir):
        assert lesson_store.get_lesson("nonexistent_topic") is None

    def test_corrupt_file_returns_none(self, file_lessons_dir):
        (file_lessons_dir / "bad_topic.json").write_text("{not json", encoding="utf-8")
        assert lesson_store.get_lesson("bad_topic") is None

    def test_save_overwrites(self, file_lessons_dir):
        lesson_store.save_lesson("t", {"v": 1})
        lesson_store.save_lesson("t", {"v": 2})
        assert lesson_store.get_lesson("t") == {"v": 2}

    def test_lesson_count_file_mode(self, file_lessons_dir):
        lesson_store.save_lesson("a", {})
        lesson_store.save_lesson("b", {})
        db_count, file_count = lesson_store.lesson_count()
        assert db_count == 0
        assert file_count == 2


class TestDbModeFallback:
    def test_db_miss_falls_back_to_file(self, tmp_path, monkeypatch):
        """Partially migrated environments: DB enabled but lesson only on disk."""
        monkeypatch.setattr(lesson_store, "_LESSONS_DIR", tmp_path)
        monkeypatch.setattr(lesson_store, "_uses_database", lambda: True)
        monkeypatch.setattr(lesson_store, "_get_from_db", lambda topic_id: None)

        (tmp_path / "alg1_t1.json").write_text(json.dumps({"hook": "h"}), encoding="utf-8")
        assert lesson_store.get_lesson("alg1_t1") == {"hook": "h"}

    def test_db_error_degrades_to_file(self, tmp_path, monkeypatch):
        """A broken DB connection degrades to the file cache, never a 500."""
        import db_session

        monkeypatch.setattr(lesson_store, "_LESSONS_DIR", tmp_path)
        monkeypatch.setattr(lesson_store, "_uses_database", lambda: True)

        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(db_session, "get_session", boom)
        (tmp_path / "t.json").write_text(json.dumps({"src": "file"}), encoding="utf-8")

        # No exception, and the file fallback serves the lesson
        assert lesson_store.get_lesson("t") == {"src": "file"}

    def test_db_hit_wins_over_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lesson_store, "_LESSONS_DIR", tmp_path)
        monkeypatch.setattr(lesson_store, "_uses_database", lambda: True)
        monkeypatch.setattr(lesson_store, "_get_from_db", lambda topic_id: {"src": "db"})

        (tmp_path / "t.json").write_text(json.dumps({"src": "file"}), encoding="utf-8")
        assert lesson_store.get_lesson("t") == {"src": "db"}

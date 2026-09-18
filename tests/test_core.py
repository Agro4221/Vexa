from __future__ import annotations

import ast
import asyncio
import re
import sqlite3
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from Action_Manager import parse_actions
from Attention_Manager import AttentionManager
from Core_Brain import StreamerAI
from Data_Base import GlobalMemory
from Event_Bus import EventBus
from Twitch_Module import TwitchChatClient
from text_utils import prepare_text_for_tts


def test_parse_actions():
    result = parse_actions("Привет! [JOY] [BAN: bad_user]")
    assert result.text == "Привет!"
    assert result.emotion == "joy"
    assert result.moderation_target == "bad_user"


def test_model_is_not_hardcoded():
    combined = (
        (ROOT / "config.py").read_text(encoding="utf-8")
        + (ROOT / "Core_Brain.py").read_text(encoding="utf-8")
    )
    assert "red-angel" not in combined.lower()


def test_model_auto_selection_is_runtime_configured():
    brain = StreamerAI(model_name="")
    with patch("Core_Brain.requests.get") as mocked:
        mocked.return_value.status_code = 200
        mocked.return_value.json.return_value = {
            "models": [{"name": "arbitrary-local-model"}]
        }
        assert brain.model_name == "arbitrary-local-model"


def test_database_schema_and_user_id(tmp_path):
    db = GlobalMemory(tmp_path / "test.db")
    db.add_event("twitch", "Alice", "hello", "hi", 52, "", "u123")
    with sqlite3.connect(db.db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
        row = conn.execute(
            "SELECT platform,author,user_id,message FROM events"
        ).fetchone()
        profile = conn.execute(
            "SELECT user_id,display_name,interaction_count FROM viewer_profiles"
        ).fetchone()
    assert "user_id" in columns
    assert row == ("twitch", "Alice", "u123", "hello")
    assert profile == ("u123", "Alice", 1)


def test_old_tg_schema_is_migrated(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp TEXT, platform TEXT, author TEXT, message TEXT, "
            "ai_response TEXT, mood INTEGER, screenshot_path TEXT)"
        )
        conn.execute("CREATE TABLE tg_posts (post_hash TEXT PRIMARY KEY, date TEXT)")
    db = GlobalMemory(db_path)
    with sqlite3.connect(db.db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tg_posts)")}
    assert {"channel_id", "message_id", "status"} <= columns
    assert db.claim_tg_post("legacy")


def test_tg_claim_is_atomic(tmp_path):
    db = GlobalMemory(tmp_path / "test.db")
    assert db.claim_tg_post("abc")
    assert not db.claim_tg_post("abc")
    db.release_tg_claim("abc")
    assert db.claim_tg_post("abc")


def test_attention_and_queue_preserve_high_priority():
    async def scenario():
        manager = AttentionManager()
        bus = EventBus(max_size=2)
        low1 = manager.annotate({"author": "a", "message": "one", "service": "twitch"})
        low2 = manager.annotate({"author": "b", "message": "two", "service": "twitch"})
        urgent = manager.annotate(
            {"author": "c", "message": "донат", "service": "axelchat"}
        )
        assert bus.submit(low1)
        assert bus.submit(low2)
        assert bus.submit(urgent)
        first = await bus.get()
        assert first["message"] == "донат"

    asyncio.run(scenario())


def test_queue_accepts_submission_from_thread():
    async def scenario():
        bus = EventBus(max_size=4)
        payload = {
            "priority": 1,
            "timestamp": time.time(),
            "ttl": 10,
            "message": "thread event",
        }
        thread = threading.Thread(target=bus.submit, args=(payload,))
        thread.start()
        thread.join()
        event = await bus.get()
        assert event["message"] == "thread event"

    asyncio.run(scenario())


def test_attention_cooldown_blocks_duplicate_background_event():
    manager = AttentionManager()
    event = manager.annotate(
        {"author": "a", "message": "hello", "service": "twitch"}
    )
    assert manager.should_accept(event)
    assert not manager.should_accept(event)


def test_twitch_tags_parser():
    event = TwitchChatClient._parse_privmsg(
        "@badge-info=subscriber;display-name=Alice;user-id=42 "
        ":alice!x PRIVMSG #channel :привет"
    )
    assert event is not None
    assert event["author"] == "Alice"
    assert event["user_id"] == "42"


def test_twitch_privmsg_parser():
    event = TwitchChatClient._parse_privmsg(
        ":some_user!some_user@x PRIVMSG #channel :Привет, Векса!"
    )
    assert event is not None
    assert event["author"] == "some_user"
    assert event["service"] == "twitch"
    assert event["message"] == "Привет, Векса!"


def test_tts_text_cleanup():
    cleaned = prepare_text_for_tts(
        "Смотри 15: https://example.com @user!"
    )
    assert "https://" not in cleaned
    assert "@user" not in cleaned
    if "num2words" in sys.modules:
        assert "пятнадцать" in cleaned


def test_no_concrete_llm_name_in_runtime_code():
    forbidden = ("red-angel", "gemma", "llama3", "qwen", "miuu_4b")
    for path in (
        ROOT / "config.py",
        ROOT / "Core_Brain.py",
        ROOT / "README.md",
        ROOT / ".env.example",
    ):
        text = path.read_text(encoding="utf-8").lower()
        assert not any(name in text for name in forbidden), path


def test_no_real_secrets_in_repo_text():
    patterns = [
        re.compile(r"GOCSPX-[A-Za-z0-9_-]{10,}"),
        re.compile(r"\b\d{8,12}:AA[A-Za-z0-9_-]{20,}\b"),
        re.compile(
            r"\bMT[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{20,}\b"
        ),
    ]
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or ".git" in path.parts
            or "tests" in path.parts
            or path.suffix not in {".py", ".yml", ".md", ".txt", ".example"}
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not any(pattern.search(text) for pattern in patterns), path


def test_local_import_graph_points_to_existing_modules():
    local = {p.stem for p in ROOT.glob("*.py")}
    for path in ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            for name in names:
                if name in local:
                    assert (ROOT / f"{name}.py").exists()


def test_all_runtime_modules_import_without_service_credentials():
    modules = [p.stem for p in ROOT.glob("*.py") if p.stem != "main"]
    for name in modules:
        __import__(name)

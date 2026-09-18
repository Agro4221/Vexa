from pathlib import Path
import ast
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import config
from Action_Manager import parse_actions

def test_parse_actions():
    r=parse_actions("Привет! [JOY] [BAN: bad_user]")
    assert r.text=="Привет!"
    assert r.emotion=="joy"
    assert r.moderation_target=="bad_user"

def test_runtime_paths():
    assert config.DATA_DIR.exists() and config.LOG_DIR.exists() and config.VISION_DIR.exists()

def test_database_schema(tmp_path):
    from Data_Base import GlobalMemory
    db=GlobalMemory(tmp_path/"test.db")
    with sqlite3.connect(db.db_path) as conn:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events","tg_posts","viewer_profiles"} <= tables

def test_tg_claim_is_atomic(tmp_path):
    from Data_Base import GlobalMemory
    db=GlobalMemory(tmp_path/"test.db")
    assert db.claim_tg_post("abc")
    assert not db.claim_tg_post("abc")
    db.release_tg_claim("abc")
    assert db.claim_tg_post("abc")

def test_no_real_secrets_in_example():
    text=(ROOT/".env.example").read_text(encoding="utf-8")
    assert "oauth:" not in text
    assert "DISCORD_TOKEN=MT" not in text
    assert "TG_BOT_TOKEN=7" not in text

def test_local_python_import_graph():
    local={p.stem for p in ROOT.glob("*.py")}
    for path in ROOT.glob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                names=[a.name.split(".")[0] for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:
                names=[node.module.split(".")[0]]
            else: continue
            for name in names:
                if name in local:
                    assert (ROOT/f"{name}.py").exists()

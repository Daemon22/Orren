import json, sqlite3
class Store:
    def __init__(self, path="orren.sqlite"):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("CREATE TABLE IF NOT EXISTS snapshots(snapshot_id TEXT PRIMARY KEY,state_json TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS artifacts(node_id TEXT,realizer TEXT,path TEXT,status TEXT,hash TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);")
        self.db.commit()
    def snapshot(self, field):
        sid = field.snapshot_id
        self.db.execute("INSERT OR REPLACE INTO snapshots(snapshot_id,state_json) VALUES(?,?)",(sid,json.dumps(field.export(),sort_keys=True)))
        self.db.commit()
        return sid

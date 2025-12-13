import os
import random
import sqlite3

class MadlibManager:
    DB_PATH = "data/madlibs.db"

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(self.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._setup_database()
        self.global_words = {
            "adjective": self._load_static_words("static/adj.txt"),
            "noun": self._load_static_words("static/noun.txt"),
            "verb": self._load_static_words("static/verb.txt")}

    def _setup_database(self):
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS words (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, 
                                                 type TEXT NOT NULL, value TEXT NOT NULL, 
                                                 UNIQUE(guild_id, type, value))""")
        self.conn.commit()

    @staticmethod
    def _load_static_words(path: str):
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f]

    def add_word(self, word_type: str, word: str, guild_id: int):
        self.cursor.execute("INSERT INTO words (guild_id, type, value) VALUES (?, ?, ?)",
                            (guild_id, word_type, word))
        self.conn.commit()
        return True

    def remove_word(self, word_type: str, word: str, guild_id: int):
        self.cursor.execute("DELETE FROM words WHERE guild_id = ? AND type = ? AND value = ?",
                            (guild_id, word_type, word))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def _get_random_guild_word(self, word_type: str, guild_id: int):
        self.cursor.execute("""SELECT value FROM words WHERE guild_id = ? AND type = ? ORDER BY RANDOM() LIMIT 1""",
                            (guild_id, word_type))
        row = self.cursor.fetchone()
        return row["value"] if row is not None else None

    def _get_random_global_word(self, word_type: str):
        lst = self.global_words.get(word_type) or []
        if not lst:
            return None
        return random.choice(lst)

    def get_random_word(self, word_type: str, guild_id: int):
        pick_guild = random.random() < 0.10 # 10% chance to pick guild word
        if guild_id and pick_guild:
            tryword = self._get_random_guild_word(word_type, guild_id)
            word = tryword if tryword else self._get_random_global_word(word_type)
        else:
            word = self._get_random_global_word(word_type)
        return word

    def close(self):
        self.conn.close()
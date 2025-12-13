import os
import sqlite3

class ReminderManager:
    DB_PATH = "data/reminders.db"

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(self.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._setup_database()

    def _setup_database(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS reminders 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, author_id INTEGER NOT NULL, 
                                channel_id INTEGER NOT NULL, reminder_timestamp INTEGER NOT NULL, message 
                                TEXT NOT NULL)""")
        self.conn.commit()

    def add_reminder(self, author_id: int, channel_id: int, reminder_timestamp: int, message: str) -> int:
        self.cursor.execute("INSERT INTO reminders (author_id, channel_id, reminder_timestamp, message) "
                            "VALUES (?, ?, ?, ?)",
                            (author_id, channel_id, reminder_timestamp, message))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_reminder(self, reminder_id: int):
        self.cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        return self.cursor.fetchone()

    def get_due_reminders(self, current_timestamp: int) -> list:
        self.cursor.execute("SELECT * FROM reminders WHERE reminder_timestamp <= ?", (current_timestamp,))
        return self.cursor.fetchall()

    def remove_reminder(self, reminder_id: int):
        self.cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
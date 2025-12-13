import os
import sqlite3

class AllowlistManager:
    DB_PATH = "data/allowlist.db"

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(self.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._setup_database()

    def _setup_database(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS allowlist 
                               (domain TEXT PRIMARY KEY NOT NULL, params TEXT NOT NULL)""")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def get_params(self, domain: str) -> list[str] | None:
        domain_parts = domain.split('.')
        for i in range(len(domain_parts)):
            current_domain = ".".join(domain_parts[i:])
            self.cursor.execute("SELECT params FROM allowlist WHERE domain = ?", (current_domain,))
            result = self.cursor.fetchone()
            if result:
                return result['params'].split(',')
        return None

    def append_param(self, domain: str, param: str) -> tuple[bool, set]:
        self.cursor.execute("SELECT params FROM allowlist WHERE domain = ?", (domain,))
        result = self.cursor.fetchone()
        if result:
            params = set(result['params'].split(','))
            if param in params:
                return True, params
            params.add(param)
        else:
            params = {param}
        new_params_str = ",".join(sorted(list(params)))
        self.cursor.execute("INSERT OR REPLACE INTO allowlist (domain, params) VALUES (?, ?)", (domain, new_params_str))
        self.conn.commit()
        return False, params

    def remove_param(self, domain: str, param: str) -> tuple[str, set | None]:
        self.cursor.execute("SELECT params FROM allowlist WHERE domain = ?", (domain,))
        result = self.cursor.fetchone()
        if not result:
            return "domain_not_found", None
        params = set(result['params'].split(','))
        if param not in params:
            return "param_not_found", params
        params.remove(param)
        if not params:
            self.cursor.execute("DELETE FROM allowlist WHERE domain = ?", (domain,))
            status = "domain_removed"
        else:
            new_params_str = ",".join(sorted(list(params)))
            self.cursor.execute("UPDATE allowlist SET params = ? WHERE domain = ?", (new_params_str, domain))
            status = "param_removed"
        self.conn.commit()
        return status, params
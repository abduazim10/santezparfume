import aiosqlite


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            language TEXT NOT NULL DEFAULT 'ru'
        );

        CREATE TABLE IF NOT EXISTS genders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS perfumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            price_10ml INTEGER,
            price_50ml INTEGER,
            price_100ml INTEGER,
            availability_status TEXT NOT NULL DEFAULT 'unknown',
            gender_id INTEGER REFERENCES genders(id) ON DELETE SET NULL,
            brand_id INTEGER REFERENCES brands(id) ON DELETE SET NULL,
            description TEXT,
            image_file_id TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS perfume_categories (
            perfume_id INTEGER NOT NULL REFERENCES perfumes(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            PRIMARY KEY (perfume_id, category_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT,
            language TEXT NOT NULL,
            perfume_id INTEGER REFERENCES perfumes(id) ON DELETE SET NULL,
            perfume_name TEXT NOT NULL,
            volume TEXT NOT NULL,
            unit_price INTEGER,
            quantity INTEGER NOT NULL,
            total_price INTEGER,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            delivery TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        await self._migrate_legacy()
        await self._migrate_orders_workflow()
        await self.conn.commit()

    async def _columns(self, table):
        cur = await self.conn.execute(f"PRAGMA table_info({table})")
        return {r["name"] for r in await cur.fetchall()}

    async def _migrate_orders_workflow(self):
        """Статусы заявок (new / confirmed / cancelled) и привязка сообщений администраторов.

        Безопасно для уже работающей базы: существующие заявки получают статус 'new',
        данные не удаляются. Вызывается после _migrate_legacy, потому что та может
        пересоздавать таблицу orders.
        """
        cols = await self._columns("orders")
        for name, ddl in (
            ("status", "TEXT NOT NULL DEFAULT 'new'"),
            ("processed_by", "INTEGER"),
            ("processed_by_name", "TEXT"),
            ("processed_at", "TEXT"),
        ):
            if name not in cols:
                await self.conn.execute(f"ALTER TABLE orders ADD COLUMN {name} {ddl}")
        # Какие сообщения со статусом заявки лежат у каких администраторов:
        # нужны, чтобы после нажатия кнопки одним админом обновилось у всех.
        await self.conn.execute("""CREATE TABLE IF NOT EXISTS order_messages (
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            PRIMARY KEY (order_id, chat_id, message_id)
        )""")

    async def _migrate_legacy(self):
        # Migrate the previous MVP schema without deleting its catalogue or orders.
        tables_cur = await self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in await tables_cur.fetchall()}
        await self.conn.execute("INSERT OR IGNORE INTO genders(name,sort_order) VALUES('Мужской',1),('Женский',2)")

        if "aromas" in tables:
            cur = await self.conn.execute("SELECT * FROM aromas")
            old_aromas = await cur.fetchall()
            for old in old_aromas:
                name = old["name"]
                status = old["status"] if old["status"] in ("stock", "day", "unknown") else "unknown"
                await self.conn.execute(
                    "INSERT OR IGNORE INTO perfumes(name,availability_status) VALUES(?,?)", (name, status)
                )
                # Recover known gender/brand assignments from the old category keys.
                cat = old["category"]
                if cat in ("women", "men"):
                    gender_name = "Женский" if cat == "women" else "Мужской"
                    await self.conn.execute("UPDATE perfumes SET gender_id=(SELECT id FROM genders WHERE name=?) WHERE name=?", (gender_name, name))
                else:
                    brand_name = self._legacy_brand_name(cat)
                    if brand_name:
                        await self.conn.execute("INSERT OR IGNORE INTO brands(name) VALUES(?)", (brand_name,))
                        await self.conn.execute("UPDATE perfumes SET brand_id=(SELECT id FROM brands WHERE name=?) WHERE name=?", (brand_name, name))
            # Also migrate old many-to-many links as ordinary categories when possible.
            if "aroma_categories" in tables:
                cur = await self.conn.execute("SELECT a.name, ac.category FROM aroma_categories ac JOIN aromas a ON a.id=ac.aroma_id")
                for row in await cur.fetchall():
                    key = row["category"]
                    if key not in ("women", "men"):
                        brand_name = self._legacy_brand_name(key)
                        if brand_name:
                            await self.conn.execute("INSERT OR IGNORE INTO brands(name) VALUES(?)", (brand_name,))
                            await self.conn.execute("UPDATE perfumes SET brand_id=(SELECT id FROM brands WHERE name=?) WHERE name=?", (brand_name, row["name"]))

        if "orders" in tables:
            cols = await self._columns("orders")
            # Old orders table had aroma but not perfume_name/perfume_id/prices.
            if "aroma" in cols and "perfume_name" not in cols:
                # Rename and copy to the new structure, preserving every old request.
                await self.conn.execute("ALTER TABLE orders RENAME TO orders_legacy")
                await self.conn.execute("""CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, username TEXT,
                    language TEXT NOT NULL, perfume_id INTEGER REFERENCES perfumes(id) ON DELETE SET NULL,
                    perfume_name TEXT NOT NULL, volume TEXT NOT NULL, unit_price INTEGER, quantity INTEGER NOT NULL,
                    total_price INTEGER, customer_name TEXT NOT NULL, phone TEXT NOT NULL, delivery TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )""")
                await self.conn.execute("""INSERT INTO orders(id,telegram_id,username,language,perfume_name,volume,quantity,customer_name,phone,delivery,created_at)
                    SELECT id,telegram_id,username,language,aroma,volume,quantity,customer_name,phone,delivery,created_at FROM orders_legacy""")
                await self.conn.execute("DROP TABLE orders_legacy")

    @staticmethod
    def _legacy_brand_name(key):
        mapping = {
            "lv": "Louis Vuitton", "tom_ford": "Tom Ford", "pdm": "Parfums de Marly",
            "dior": "Dior", "amouage": "Amouage", "gucci": "Gucci", "armani": "Giorgio Armani",
            "ysl": "Yves Saint Laurent", "chanel": "Chanel", "hfc": "HFC",
            "creed": "Creed", "bvlgari": "Bvlgari", "roja": "Roja", "montblanc": "Montblanc",
            "jpg": "Jean Paul Gaultier", "kilian": "Kilian", "bleu": "Bleu", "other": "Другие ароматы",
        }
        return mapping.get(key)

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def get_language(self, user_id):
        cur = await self.conn.execute("SELECT language FROM users WHERE telegram_id=?", (user_id,))
        row = await cur.fetchone()
        return row["language"] if row else None

    async def set_language(self, user_id, lang):
        await self.conn.execute("INSERT INTO users(telegram_id,language) VALUES(?,?) ON CONFLICT(telegram_id) DO UPDATE SET language=excluded.language", (user_id, lang))
        await self.conn.commit()

    async def seed_directories(self, genders, brands):
        for name in genders:
            await self.conn.execute("INSERT OR IGNORE INTO genders(name) VALUES(?)", (name,))
        for name in brands:
            await self.conn.execute("INSERT OR IGNORE INTO brands(name) VALUES(?)", (name,))
        await self.conn.commit()

    async def list_genders(self, active_only=True):
        q = "SELECT * FROM genders" + (" WHERE is_active=1" if active_only else "") + " ORDER BY sort_order,name COLLATE NOCASE"
        cur = await self.conn.execute(q)
        return await cur.fetchall()

    async def list_brands(self, active_only=True):
        q = "SELECT * FROM brands" + (" WHERE is_active=1" if active_only else "") + " ORDER BY sort_order,name COLLATE NOCASE"
        cur = await self.conn.execute(q)
        return await cur.fetchall()

    async def list_categories(self, active_only=True):
        q = "SELECT * FROM categories" + (" WHERE is_active=1" if active_only else "") + " ORDER BY sort_order,name COLLATE NOCASE"
        cur = await self.conn.execute(q)
        return await cur.fetchall()

    async def add_directory_item(self, table, name):
        if table not in {"genders", "brands", "categories"}:
            raise ValueError("Unsupported directory")
        await self.conn.execute(f"INSERT INTO {table}(name) VALUES(?)", (name.strip(),))
        await self.conn.commit()

    async def add_perfume(self, name, gender_id, brand_id, p10=None, p50=None, p100=None, status="unknown", image_file_id=None):
        cur = await self.conn.execute("""INSERT INTO perfumes(name,gender_id,brand_id,price_10ml,price_50ml,price_100ml,availability_status,image_file_id)
            VALUES(?,?,?,?,?,?,?,?)""", (name.strip(), gender_id, brand_id, p10, p50, p100, status, image_file_id))
        await self.conn.commit()
        return cur.lastrowid

    async def set_image(self, perfume_id, image_file_id):
        """Сохраняет Telegram file_id фото парфюма. None убирает фото."""
        await self.conn.execute("UPDATE perfumes SET image_file_id=? WHERE id=?", (image_file_id, perfume_id))
        await self.conn.commit()

    async def get_perfume(self, perfume_id):
        cur = await self.conn.execute("""SELECT p.*,g.name AS gender_name,b.name AS brand_name
            FROM perfumes p LEFT JOIN genders g ON g.id=p.gender_id LEFT JOIN brands b ON b.id=p.brand_id WHERE p.id=?""", (perfume_id,))
        return await cur.fetchone()

    async def list_perfumes(self, kind=None, item_id=None, active_only=True):
        where = ["p.is_active=1"] if active_only else []
        params = []
        join = ""
        if kind == "gender":
            where.append("p.gender_id=?"); params.append(item_id)
        elif kind == "brand":
            where.append("p.brand_id=?"); params.append(item_id)
        elif kind == "category":
            join = " JOIN perfume_categories pc ON pc.perfume_id=p.id"
            where.append("pc.category_id=?"); params.append(item_id)
        sql = """SELECT DISTINCT p.*,g.name AS gender_name,b.name AS brand_name FROM perfumes p
            LEFT JOIN genders g ON g.id=p.gender_id LEFT JOIN brands b ON b.id=p.brand_id""" + join
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY p.name COLLATE NOCASE"
        cur = await self.conn.execute(sql, params)
        return await cur.fetchall()

    async def add_perfume_category(self, perfume_id, category_id):
        await self.conn.execute("INSERT OR IGNORE INTO perfume_categories(perfume_id,category_id) VALUES(?,?)", (perfume_id, category_id))
        await self.conn.commit()

    async def set_availability(self, perfume_id, status):
        await self.conn.execute("UPDATE perfumes SET availability_status=? WHERE id=?", (status, perfume_id))
        await self.conn.commit()

    async def set_prices(self, perfume_id, p10, p50, p100):
        await self.conn.execute("UPDATE perfumes SET price_10ml=?,price_50ml=?,price_100ml=? WHERE id=?", (p10,p50,p100,perfume_id))
        await self.conn.commit()

    async def create_order(self, **d):
        cur = await self.conn.execute("""INSERT INTO orders(telegram_id,username,language,perfume_id,perfume_name,volume,unit_price,total_price,quantity,customer_name,phone,delivery)
            VALUES(:telegram_id,:username,:language,:perfume_id,:perfume_name,:volume,:unit_price,:total_price,:quantity,:customer_name,:phone,:delivery)""", d)
        await self.conn.commit()
        return cur.lastrowid

    async def search_perfumes(self, query, limit=500):
        term=f"%{query.strip()}%"
        cur=await self.conn.execute("""SELECT DISTINCT p.*,g.name AS gender_name,b.name AS brand_name FROM perfumes p
            LEFT JOIN genders g ON g.id=p.gender_id LEFT JOIN brands b ON b.id=p.brand_id
            WHERE p.is_active=1 AND (p.name LIKE ? OR b.name LIKE ? OR g.name LIKE ?)
            ORDER BY p.name COLLATE NOCASE LIMIT ?""",(term,term,term,limit))
        return await cur.fetchall()

    async def get_recent_orders(self, limit=15):
        cur = await self.conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        return await cur.fetchall()

    # ---- обработка заявок администраторами
    ORDER_STATUSES = ("new", "confirmed", "cancelled")

    async def get_order(self, order_id):
        cur = await self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        return await cur.fetchone()

    async def list_orders(self, status=None, limit=15):
        """Заявки по статусу. Новые идут от старых к новым (очередь на обработку),
        остальные от новых к старым."""
        order = "ASC" if status == "new" else "DESC"
        if status:
            cur = await self.conn.execute(f"SELECT * FROM orders WHERE status=? ORDER BY id {order} LIMIT ?", (status, limit))
        else:
            cur = await self.conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        return await cur.fetchall()

    async def count_orders(self):
        cur = await self.conn.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status")
        counts = {s: 0 for s in self.ORDER_STATUSES}
        for r in await cur.fetchall():
            counts[r["status"]] = r["n"]
        return counts

    async def set_order_status(self, order_id, status, admin_id, admin_name, allowed_from):
        """Меняет статус заявки, только если сейчас он один из allowed_from.

        Защита от двойного нажатия: если один администратор уже обработал заявку,
        у второго обновление не пройдёт и вернётся False.
        Возврат в 'new' снимает отметку «кто и когда обработал».
        """
        if status not in self.ORDER_STATUSES:
            raise ValueError(status)
        marks = ",".join("?" for _ in allowed_from)
        if status == "new":
            cur = await self.conn.execute(
                f"UPDATE orders SET status='new', processed_by=NULL, processed_by_name=NULL, processed_at=NULL "
                f"WHERE id=? AND status IN ({marks})", (order_id, *allowed_from))
        else:
            cur = await self.conn.execute(
                f"UPDATE orders SET status=?, processed_by=?, processed_by_name=?, processed_at=datetime('now') "
                f"WHERE id=? AND status IN ({marks})", (status, admin_id, admin_name, order_id, *allowed_from))
        await self.conn.commit()
        return cur.rowcount == 1

    async def add_order_message(self, order_id, chat_id, message_id):
        await self.conn.execute("INSERT OR IGNORE INTO order_messages(order_id,chat_id,message_id) VALUES(?,?,?)",
                                (order_id, chat_id, message_id))
        await self.conn.commit()

    async def get_order_messages(self, order_id):
        cur = await self.conn.execute("SELECT chat_id, message_id FROM order_messages WHERE order_id=?", (order_id,))
        return await cur.fetchall()

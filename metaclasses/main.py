SCHEMA = {
    "users": {
        "pk": "id",
        "columns": {
            "id": {},
            "name": {"required": True},
            "email": {"required": True},
            "is_active": {"default": True},
        },
    },
    "orders": {
        "pk": "id",
        "columns": {
            "id": {},
            "user_id": {"required": True},
            "total": {"required": True},
            "status": {"default": "new"},
        },
    },
}

class InMemoryDB:
    def __init__(self, schema, initial_data=None):
        self.schema = schema
        self.data = {t: list((initial_data or {}).get(t, [])) for t in schema}
        self._seq = {t: max([r.get(schema[t]["pk"], 0) for r in self.data[t]], default=0) for t in schema}

    def next_pk(self, table):
        self._seq[table] += 1
        return self._seq[table]

    def insert(self, table, record):
        self.data[table].append(dict(record))
        return dict(record)

    def select(self, table, where=None):
        rows = self.data[table]
        if where:
            rows = [r for r in rows if all(r.get(k) == v for k, v in where.items())]
        return [dict(r) for r in rows]

    def get(self, table, pk):
        pk_name = self.schema[table]["pk"]
        for r in self.data[table]:
            if r.get(pk_name) == pk:
                return dict(r)
        return None

    def update(self, table, pk, updates):
        pk_name = self.schema[table]["pk"]
        for r in self.data[table]:
            if r.get(pk_name) == pk:
                r.update(updates)
                return dict(r)
        return None

    def delete(self, table, pk):
        pk_name = self.schema[table]["pk"]
        for i, r in enumerate(self.data[table]):
            if r.get(pk_name) == pk:
                self.data[table].pop(i)
                return True
        return False

    def count(self, table):
        return len(self.data[table])

class TableManagerMeta(type):
    """
    Usage:
      class UserManager(BaseManager, metaclass=TableManagerMeta):
          __table__ = "users"
    Auto-adds:
      - __table__, __pk__, __columns__
      - find_by_<column>() helpers
    """
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, dict(namespace))

        # Let BaseManager be created without a table
        if name == "BaseManager" and "__table__" not in namespace:
            return cls

        # Resolve table and schema (defaults to global SCHEMA)
        schema_all = namespace.get("__schema__", getattr(cls, "__schema__", SCHEMA))
        table = namespace.get("__table__", getattr(cls, "__table__", None))
        if not table:
            # Infer from ClassName ending with "Manager" -> snake_case base
            if name.endswith("Manager"):
                import re
                table = re.sub(r"(?<!^)(?=[A-Z])", "_", name[:-7]).lower()
            else:
                raise TypeError(f"{name}: please set __table__")

        if table not in schema_all:
            raise ValueError(f"{name}: table '{table}' not found in schema")

        tdef = schema_all[table]
        columns = list(tdef["columns"].keys())

        # Attach metadata
        cls.__schema__ = schema_all
        cls.__table__ = table
        cls.__pk__ = tdef["pk"]
        cls.__columns__ = columns
        cls.__coldefs__ = tdef["columns"]

        # Generate simple find_by_<field> methods
        for col in columns:
            def make_finder(field):
                def finder(self, value):
                    return self.filter(**{field: value})
                finder.__name__ = f"find_by_{field}"
                return finder
            setattr(cls, f"find_by_{col}", make_finder(col))

        return cls

class BaseManager(metaclass=TableManagerMeta):
    __schema__ = SCHEMA

    def __init__(self, db):
        self.db = db

    def _apply_defaults_and_check(self, data, partial=False):
        out = {}
        for col, cdef in self.__coldefs__.items():
            if col in data:
                out[col] = data[col]
            elif not partial:
                if "default" in cdef:
                    out[col] = cdef["default"]
                else:
                    out[col] = None

        if not partial:
            missing = [c for c, cdef in self.__coldefs__.items()
                       if cdef.get("required") and (out.get(c) is None)]
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Disallow unknown columns
        unknown = set(data.keys()) - set(self.__columns__)
        if unknown:
            raise KeyError(f"Unknown columns: {', '.join(sorted(unknown))}")

        return out

    def create(self, **data):
        row = self._apply_defaults_and_check(data, partial=False)
        pk = self.__pk__
        if row.get(pk) is None:
            row[pk] = self.db.next_pk(self.__table__)
        return self.db.insert(self.__table__, row)

    def get(self, pk):
        return self.db.get(self.__table__, pk)

    def filter(self, **conds):
        self._apply_defaults_and_check(conds, partial=True)  # validate keys only
        return self.db.select(self.__table__, conds or None)

    def update(self, pk, **updates):
        if not updates:
            return self.get(pk)
        clean = self._apply_defaults_and_check(updates, partial=True)
        return self.db.update(self.__table__, pk, clean)

    def delete(self, pk):
        return self.db.delete(self.__table__, pk)

    def count(self):
        return self.db.count(self.__table__)

class UserManager(BaseManager, metaclass=TableManagerMeta):
    __table__ = "users"

class OrderManager(BaseManager, metaclass=TableManagerMeta):
    __table__ = "orders"

if __name__ == "__main__":
    db = InMemoryDB(SCHEMA)
    users = UserManager(db)
    orders = OrderManager(db)

    u1 = users.create(name="Alice", email="alice@example.com")
    u2 = users.create(name="Bob", email="bob@example.com", is_active=False)

    print(users.find_by_is_active(True))
    print(users.filter(name="Bob"))

    o1 = orders.create(user_id=u1["id"], total=19.99)
    orders.update(o1["id"], status="paid")
    print(orders.get(o1["id"]))

    print(users.count(), orders.count())

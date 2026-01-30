from nbms_app.management.commands import db_doctor


def test_column_exists_checks_information_schema(monkeypatch):
    class FakeCursor:
        def __init__(self, results):
            self._results = results
            self._idx = 0

        def execute(self, _sql, _params):
            pass

        def fetchone(self):
            result = self._results[self._idx]
            self._idx += 1
            return result

    cursor = FakeCursor([("ok",), None])
    assert db_doctor._column_exists(cursor, "table_a", "col_a") is True
    assert db_doctor._column_exists(cursor, "table_b", "col_b") is False

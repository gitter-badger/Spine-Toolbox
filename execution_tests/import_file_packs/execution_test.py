import sys
from pathlib import Path
import shutil
import subprocess
import unittest
from spinedb_api import DatabaseMapping, from_database


class ModifyConnectionFilterByScript(unittest.TestCase):
    _root_path = Path(__file__).parent
    _mod_script_path = _root_path / "mod.py"
    _database_path = _root_path / ".spinetoolbox" / "items" / "data_store" / "db.sqlite"
    _tool_output_path = _root_path / ".spinetoolbox" / "items" / "create_file_pack" / "output"

    def setUp(self):
        if self._tool_output_path.exists():
            shutil.rmtree(self._tool_output_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        if self._database_path.exists():
            self._database_path.unlink()
        self._url = "sqlite:///" + str(self._database_path)
        db_map = DatabaseMapping(self._url, create=True)
        db_map.connection.close()

    def test_execution(self):
        completed = subprocess.run(
            (
                sys.executable,
                "-m",
                "spinetoolbox",
                "--execute-only",
                str(self._root_path),
            )
        )
        self.assertEqual(completed.returncode, 0)
        db_map = DatabaseMapping(self._url)
        values = {}
        for value_row in db_map.query(db_map.object_parameter_value_sq):
            self.assertEqual(value_row.object_class_name, "a")
            self.assertEqual(value_row.parameter_name, "info")
            self.assertEqual(value_row.alternative_name, "Base")
            values[value_row.object_name] = from_database(value_row.value, value_row.type)
        db_map.connection.close()
        self.assertEqual(len(values), 4)
        self.assertEqual(values["b"], 23.0)
        self.assertEqual(values["c"], 50.0)
        self.assertEqual(values["d"], -23.0)
        self.assertEqual(values["e"], -50.0)


if __name__ == '__main__':
    unittest.main()

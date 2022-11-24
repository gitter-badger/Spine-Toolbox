######################################################################################################################
# Copyright (C) 2017-2022 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
Unit tests for ``spine_db_fetcher`` module.

:authors: A. Soininen (VTT)
:date:    4.2.2021
"""
import unittest
from unittest.mock import MagicMock
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from spinetoolbox.fetch_parent import ItemTypeFetchParent
from spinedb_api import DatabaseMapping
from spinedb_api.import_functions import import_data
from tests.mock_helpers import TestSpineDBManager


class TestSpineDBFetcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            QApplication()

    def setUp(self):
        app_settings = MagicMock()
        self._logger = MagicMock()  # Collects error messages therefore handy for debugging.
        self._db_mngr = TestSpineDBManager(app_settings, None)
        self._db_map = self._db_mngr.get_db_map("sqlite://", self._logger, codename="test_db", create=True)

    def tearDown(self):
        self._db_mngr.close_all_sessions()
        self._db_mngr.clean_up()

    def test_fetch_empty_database(self):
        self._db_map.remove_items(alternative={1})
        self._db_map.commit_session("ddd")
        for item_type in DatabaseMapping.ITEM_TYPES:
            fetcher = ItemTypeFetchParent(item_type)
            fetcher.handle_items_added = MagicMock()
            if self._db_mngr.can_fetch_more(self._db_map, fetcher):
                self._db_mngr.fetch_more(self._db_map, fetcher)
            fetcher.handle_items_added.assert_not_called()

    def _import_data(self, **data):
        import_data(self._db_map, **data)
        self._db_map.commit_session("ddd")

    def test_fetch_alternatives(self):
        self._import_data(alternatives=("alt",))
        fetcher = ItemTypeFetchParent("alternative")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call(
            {
                self._db_map: [
                    {'id': 1, 'name': 'Base', 'description': 'Base alternative', 'commit_id': 1},
                    {'id': 2, 'name': 'alt', 'description': None, 'commit_id': 2},
                ]
            }
        )
        self.assertEqual(
            self._db_mngr.get_item(self._db_map, "alternative", 2),
            {'commit_id': 2, 'description': None, 'id': 2, 'name': 'alt'},
        )

    def test_fetch_scenarios(self):
        self._import_data(scenarios=("scenario",))
        item = {
            'id': 1,
            'name': 'scenario',
            'description': None,
            'active': False,
            'alternative_id_list': None,
            'alternative_name_list': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("scenario")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "scenario", 1), item)

    def test_fetch_scenario_alternatives(self):
        self._import_data(alternatives=("alt",), scenarios=("scenario",), scenario_alternatives=(("scenario", "alt"),))
        item = {
            'id': 1,
            'scenario_id': 1,
            'scenario_name': 'scenario',
            'alternative_id': 2,
            'alternative_name': 'alt',
            'rank': 1,
            'before_alternative_id': None,
            'before_rank': None,
            'before_alternative_name': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("scenario_alternative")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "scenario_alternative", 1), item)

    def test_fetch_object_classes(self):
        self._import_data(object_classes=("oc",))
        item = {
            'id': 1,
            'name': 'oc',
            'description': None,
            'display_order': 99,
            'display_icon': None,
            'hidden': 0,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("object_class")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertIsInstance(self._db_mngr.entity_class_icon(self._db_map, "object_class", 1), QIcon)
        self.assertEqual(self._db_mngr.get_item(self._db_map, "object_class", 1), item)

    def test_fetch_objects(self):
        self._import_data(object_classes=("oc",), objects=(("oc", "obj"),))
        item = {
            'id': 1,
            'class_id': 1,
            'class_name': 'oc',
            'name': 'obj',
            'description': None,
            'group_id': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("object")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "object", 1), item)

    def test_fetch_relationship_classes(self):
        self._import_data(object_classes=("oc",), relationship_classes=(("rc", ("oc",)),))
        item = {
            'id': 2,
            'name': 'rc',
            'description': None,
            'object_class_id_list': '1',
            'object_class_name_list': 'oc',
            'display_icon': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("relationship_class")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "relationship_class", 2), item)

    def test_fetch_relationships(self):
        self._import_data(
            object_classes=("oc",),
            objects=(("oc", "obj"),),
            relationship_classes=(("rc", ("oc",)),),
            relationships=(("rc", ("obj",)),),
        )
        item = {
            'id': 2,
            'name': 'rc_obj',
            'class_id': 2,
            'class_name': 'rc',
            'object_id_list': '1',
            'object_name_list': 'obj',
            'object_class_id_list': '1',
            'object_class_name_list': 'oc',
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("relationship")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "relationship", 2), item)

    def test_fetch_object_groups(self):
        self._import_data(
            object_classes=("oc",), objects=(("oc", "obj"), ("oc", "group")), object_groups=(("oc", "group", "obj"),)
        )
        item = {
            'id': 1,
            'class_id': 1,
            'group_id': 2,
            'member_id': 1,
            'class_name': 'oc',
            'group_name': 'group',
            'member_name': 'obj',
            'object_class_id': 1,
            'relationship_class_id': None,
        }
        fetcher = ItemTypeFetchParent("entity_group")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "entity_group", 1), item)

    def test_fetch_parameter_definitions(self):
        self._import_data(object_classes=("oc",), object_parameters=(("oc", "param"),))
        item = {
            'id': 1,
            'entity_class_id': 1,
            'object_class_id': 1,
            'relationship_class_id': None,
            'entity_class_name': 'oc',
            'object_class_name': 'oc',
            'relationship_class_name': None,
            'object_class_id_list': None,
            'object_class_name_list': None,
            'parameter_name': 'param',
            'value_list_id': None,
            'value_list_name': None,
            'default_value': None,
            'default_type': None,
            'list_value_id': None,
            'description': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("parameter_definition")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "parameter_definition", 1), item)

    def test_fetch_parameter_values(self):
        self._import_data(
            object_classes=("oc",),
            objects=(("oc", "obj"),),
            object_parameters=(("oc", "param"),),
            object_parameter_values=(("oc", "obj", "param", 2.3),),
        )
        item = {
            'id': 1,
            'entity_class_id': 1,
            'object_class_id': 1,
            'relationship_class_id': None,
            'entity_class_name': 'oc',
            'object_class_name': 'oc',
            'relationship_class_name': None,
            'object_class_id_list': None,
            'object_class_name_list': None,
            'entity_id': 1,
            'entity_name': 'obj',
            'object_id': 1,
            'relationship_id': None,
            'object_name': 'obj',
            'object_id_list': None,
            'object_name_list': None,
            'parameter_id': 1,
            'parameter_name': 'param',
            'alternative_id': 1,
            'alternative_name': 'Base',
            'value': b'2.3',
            'type': None,
            'list_value_id': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("parameter_value")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "parameter_value", 1), item)

    def test_fetch_parameter_value_lists(self):
        self._import_data(parameter_value_lists=(("value_list", (2.3,)),))
        item = {'id': 1, 'name': 'value_list', 'value_index_list': '0', 'value_id_list': '1', 'commit_id': 2}
        fetcher = ItemTypeFetchParent("parameter_value_list")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "parameter_value_list", 1), item)
        item = {'id': 1, 'parameter_value_list_id': 1, 'index': 0, 'value': b'[2.3]', 'type': None, 'commit_id': 2}
        fetcher = ItemTypeFetchParent("list_value")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "list_value", 1), item)

    def test_fetch_features(self):
        self._import_data(
            object_classes=("oc",),
            parameter_value_lists=(("value_list", 2.3),),
            object_parameters=(("oc", "param", 2.3, "value_list"),),
            features=(("oc", "param"),),
        )
        item = {
            'id': 1,
            'entity_class_id': 1,
            'entity_class_name': 'oc',
            'parameter_definition_id': 1,
            'parameter_definition_name': 'param',
            'parameter_value_list_id': 1,
            'parameter_value_list_name': 'value_list',
            'description': None,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("feature")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "feature", 1), item)

    def test_fetch_tools(self):
        self._import_data(tools=("tool",))
        item = {'id': 1, 'name': 'tool', 'description': None, 'commit_id': 2}
        fetcher = ItemTypeFetchParent("tool")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "tool", 1), item)

    def test_fetch_tool_features(self):
        self._import_data(
            object_classes=("oc",),
            parameter_value_lists=(("value_list", 2.3),),
            object_parameters=(("oc", "param", 2.3, "value_list"),),
            features=(("oc", "param"),),
            tools=("tool",),
            tool_features=(("tool", "oc", "param"),),
        )
        item = {
            'id': 1,
            'tool_id': 1,
            'tool_name': 'tool',
            'feature_id': 1,
            'entity_class_id': 1,
            'entity_class_name': 'oc',
            'parameter_definition_id': 1,
            'parameter_definition_name': 'param',
            'parameter_value_list_id': 1,
            'parameter_value_list_name': 'value_list',
            'required': False,
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("tool_feature")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "tool_feature", 1), item)

    def test_fetch_tool_feature_methods(self):
        self._import_data(
            object_classes=("oc",),
            parameter_value_lists=(("value_list", "m"),),
            object_parameters=(("oc", "param", "m", "value_list"),),
            features=(("oc", "param"),),
            tools=("tool",),
            tool_features=(("tool", "oc", "param"),),
            tool_feature_methods=(("tool", "oc", "param", "m"),),
        )
        item = {
            'id': 1,
            'tool_feature_id': 1,
            'tool_id': 1,
            'tool_name': 'tool',
            'feature_id': 1,
            'entity_class_id': 1,
            'entity_class_name': 'oc',
            'parameter_definition_id': 1,
            'parameter_definition_name': 'param',
            'parameter_value_list_id': 1,
            'parameter_value_list_name': 'value_list',
            'method_index': 0,
            'method': b'"m"',
            'commit_id': 2,
        }
        fetcher = ItemTypeFetchParent("tool_feature_method")
        fetcher.handle_items_added = MagicMock()
        if self._db_mngr.can_fetch_more(self._db_map, fetcher):
            self._db_mngr.fetch_more(self._db_map, fetcher)
        fetcher.handle_items_added.assert_any_call({self._db_map: [item]})
        self.assertEqual(self._db_mngr.get_item(self._db_map, "tool_feature_method", 1), item)


if __name__ == "__main__":
    unittest.main()

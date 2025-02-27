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
Unit tests for the TreeViewFormRemoveMixin.

:author: M. Marin (KTH)
:date:   6.12.2018
"""
from unittest import mock
from spinetoolbox.spine_db_editor.mvcmodels.compound_parameter_models import CompoundParameterModel


class TestSpineDBEditorRemoveMixin:
    def test_remove_object_classes_from_object_tree_model(self):
        """Test that object classes are removed from the object tree model."""
        self.spine_db_editor.init_models()
        self.put_mock_object_classes_in_db_mngr()
        self.fetch_object_tree_model()
        root_item = self.spine_db_editor.object_tree_model.root_item
        self.assertEqual(root_item.child_count(), 2)
        self.db_mngr.remove_items({self.mock_db_map: {"object_class": {self.fish_class["id"]}}})
        dog_item = root_item.child(0)
        self.assertEqual(root_item.child_count(), 1)
        self.assertEqual(dog_item.display_data, "dog")

    def test_remove_objects_from_object_tree_model(self):
        """Test that objects are removed from the object tree model."""
        self.spine_db_editor.init_models()
        self.put_mock_object_classes_in_db_mngr()
        self.put_mock_objects_in_db_mngr()
        self.fetch_object_tree_model()
        root_item = self.spine_db_editor.object_tree_model.root_item
        fish_item = root_item.child(1)
        self.assertEqual(fish_item.child_count(), 1)
        self.db_mngr.remove_items({self.mock_db_map: {"object": {self.nemo_object["id"]}}})
        self.assertEqual(fish_item.child_count(), 0)

    def test_remove_relationship_classes_from_object_tree_model(self):
        """Test that relationship classes removed from in the object tree model."""
        self.spine_db_editor.init_models()
        self.put_mock_object_classes_in_db_mngr()
        self.put_mock_objects_in_db_mngr()
        self.put_mock_relationship_classes_in_db_mngr()
        self.fetch_object_tree_model()
        root_item = self.spine_db_editor.object_tree_model.root_item
        dog_item = root_item.child(0)
        pluto_item = dog_item.child(0)
        self.assertEqual(pluto_item.child_count(), 2)
        self.db_mngr.remove_items({self.mock_db_map: {"relationship_class": {self.fish_dog_class["id"]}}})
        self.assertEqual(pluto_item.child_count(), 1)

    def test_remove_relationships_from_object_tree_model(self):
        """Test that relationships are removed from the object tree model."""
        self.spine_db_editor.init_models()
        self.put_mock_object_classes_in_db_mngr()
        self.put_mock_objects_in_db_mngr()
        self.put_mock_relationship_classes_in_db_mngr()
        self.put_mock_relationships_in_db_mngr()
        self.fetch_object_tree_model()
        root_item = self.spine_db_editor.object_tree_model.root_item
        fish_item = root_item.child(1)
        nemo_item = fish_item.child(0)
        nemo_fish_dog_item = nemo_item.child(1)
        relationships = [x.display_data for x in nemo_fish_dog_item.children]
        self.assertEqual(nemo_fish_dog_item.child_count(), 2)
        self.assertEqual(relationships[0], "pluto")
        self.assertEqual(relationships[1], "scooby")
        self.db_mngr.remove_items({self.mock_db_map: {"relationship": {self.nemo_pluto_rel["id"]}}})
        self.assertEqual(nemo_fish_dog_item.child_count(), 1)

    def test_remove_object_parameter_definitions_from_model(self):
        """Test that object parameter definitions are removed from the model."""
        model = self.spine_db_editor.object_parameter_definition_model
        model.init_model()
        if model.canFetchMore(None):
            model.fetchMore(None)
        self.put_mock_object_classes_in_db_mngr()
        self.put_mock_object_parameter_definitions_in_db_mngr()
        self.fetch_object_tree_model()
        self.db_mngr.remove_items({self.mock_db_map: {"parameter_definition": {self.water_parameter["id"]}}})
        h = model.header.index
        parameters = []
        for row in range(model.rowCount()):
            parameters.append(
                (model.index(row, h("object_class_name")).data(), model.index(row, h("parameter_name")).data())
            )
        self.assertTrue(("dog", "breed") in parameters)
        self.assertTrue(("fish", "water") not in parameters)

    def test_remove_relationship_parameter_definitions_from_model(self):
        """Test that object parameter definitions are removed from the model."""
        model = self.spine_db_editor.relationship_parameter_definition_model
        model.init_model()
        if model.canFetchMore(None):
            model.fetchMore(None)
        self.put_mock_object_classes_in_db_mngr()
        self.put_mock_relationship_classes_in_db_mngr()
        self.put_mock_object_parameter_definitions_in_db_mngr()
        self.put_mock_relationship_parameter_definitions_in_db_mngr()
        self.fetch_object_tree_model()
        self.db_mngr.remove_items({self.mock_db_map: {"parameter_definition": {self.relative_speed_parameter["id"]}}})
        h = model.header.index
        parameters = []
        for row in range(model.rowCount()):
            parameters.append(
                (model.index(row, h("relationship_class_name")).data(), model.index(row, h("parameter_name")).data())
            )
        self.assertTrue(("dog__fish", "combined_mojo") in parameters)
        self.assertTrue(("fish__dog", "relative_speed") not in parameters)

    def test_remove_object_parameter_values_from_model(self):
        """Test that object parameter values are removed from the model."""
        model = self.spine_db_editor.object_parameter_value_model
        model.init_model()
        self.put_mock_object_classes_in_db_mngr()
        self.put_mock_objects_in_db_mngr()
        self.put_mock_object_parameter_definitions_in_db_mngr()
        self.put_mock_object_parameter_values_in_db_mngr()
        self.fetch_object_tree_model()
        self.db_mngr.remove_items({self.mock_db_map: {"parameter_value": {self.nemo_water["id"]}}})
        h = model.header.index
        parameters = []
        for row in range(model.rowCount()):
            parameters.append(
                (
                    model.index(row, h("object_name")).data(),
                    model.index(row, h("parameter_name")).data(),
                    model.index(row, h("value")).data(),
                )
            )
        self.assertTrue(("nemo", "water", "salt") not in parameters)

    def test_remove_relationship_parameter_values_from_model(self):
        """Test that relationship parameter values are removed from the model."""
        model = self.spine_db_editor.relationship_parameter_value_model
        model.init_model()
        self.put_mock_dataset_in_db_mngr()
        self.db_mngr.remove_items({self.mock_db_map: {"parameter_value": {self.nemo_pluto_relative_speed["id"]}}})
        h = model.header.index
        parameters = []
        for row in range(model.rowCount()):
            parameters.append(
                (
                    model.index(row, h("object_name_list")).data(),
                    model.index(row, h("parameter_name")).data(),
                    model.index(row, h("value")).data(),
                )
            )
        self.assertTrue(("nemo,pluto", "relative_speed", None) not in parameters)

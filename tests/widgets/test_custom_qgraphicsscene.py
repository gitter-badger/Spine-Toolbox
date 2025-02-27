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
Unit tests for custom graphics scenes.

:author: A. Soininen (VTT)
:date:   8.7.2021
"""
from tempfile import TemporaryDirectory
import unittest
from PySide2.QtWidgets import QApplication, QGraphicsRectItem
from spine_items.data_connection.data_connection import DataConnection
from spinetoolbox.widgets.custom_qgraphicsscene import CustomGraphicsScene
from tests.mock_helpers import clean_up_toolbox, create_toolboxui_with_project


class TestCustomGraphicsScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            QApplication()

    def test_center_items(self):
        scene = CustomGraphicsScene()
        rect = scene.addRect(-120.0, 66.0, 1.0, 1.0)
        child_rect = QGraphicsRectItem(23.3, -5.5, 0.3, 0.3, rect)
        scene.center_items()
        self.assertEqual(scene.itemsBoundingRect(), scene.sceneRect())
        scene.deleteLater()


class TestDesignGraphicsScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            QApplication()

    def setUp(self):
        self._temp_dir = TemporaryDirectory()
        self._toolbox = create_toolboxui_with_project(self._temp_dir.name)

    def tearDown(self):
        clean_up_toolbox(self._toolbox)
        self._temp_dir.cleanup()

    def test_handle_selection_changed_synchronizes_with_project_tree(self):
        project = self._toolbox.project()
        dc = DataConnection("dc", "", 0.0, 0.0, self._toolbox, project)
        project.add_item(dc)
        scene = self._toolbox.ui.graphicsView.scene()
        self.assertEqual(scene.selectedItems(), [])
        dc.get_icon().setSelected(True)
        self.assertIs(scene.selectedItems()[0], dc.get_icon())
        indexes = self._toolbox.ui.treeView_project.selectionModel().selectedIndexes()
        self.assertEqual(len(indexes), 1)
        self.assertEqual(indexes[0].data(), "dc")
        current_index = self._toolbox.ui.treeView_project.selectionModel().currentIndex()
        self.assertTrue(current_index.isValid())
        self.assertEqual(current_index.data(), "dc")


if __name__ == "__main__":
    unittest.main()

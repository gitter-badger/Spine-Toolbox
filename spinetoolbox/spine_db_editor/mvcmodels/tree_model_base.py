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
Models to represent things in a tree.

:authors: M. Marin (KTH)
:date:    1.0.2020
"""
from PySide2.QtCore import Qt, QModelIndex
from spinetoolbox.mvcmodels.minimal_tree_model import MinimalTreeModel
from .tree_item_utility import StandardTreeItem


class TreeModelBase(MinimalTreeModel):
    """A base model to display items in a tree view."""

    def __init__(self, db_editor, db_mngr, *db_maps):
        """
        Args:
            db_editor (SpineDBEditor)
            db_mngr (SpineDBManager)
            *db_maps: DiffDatabaseMapping instances
        """
        super().__init__(db_editor)
        self.db_editor = db_editor
        self.db_mngr = db_mngr
        self.db_maps = db_maps

    def columnCount(self, parent=QModelIndex()):
        """Returns the number of columns under the given parent. Always 2.

        Returns:
            int: column count
        """
        return 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ("name", "description")[section]
        return None

    def build_tree(self):
        """Builds tree."""
        self.beginResetModel()
        self._invisible_root_item = StandardTreeItem(self)
        self.endResetModel()
        for db_map in self.db_maps:
            db_item = self._make_db_item(db_map)
            self._invisible_root_item.append_children([db_item])
            db_item.append_children(self._top_children())

    @staticmethod
    def _make_db_item(db_map):
        raise NotImplementedError()

    @staticmethod
    def _top_children():
        raise NotImplementedError()

    @staticmethod
    def db_item(item):
        while item.item_type != "db":
            item = item.parent_item
        return item

    def db_row(self, item):
        return self.db_item(item).child_number()

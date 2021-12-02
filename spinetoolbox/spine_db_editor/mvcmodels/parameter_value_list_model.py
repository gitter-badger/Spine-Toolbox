######################################################################################################################
# Copyright (C) 2017-2021 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
A tree model for parameter_value lists.

:authors: M. Marin (KTH)
:date:   28.6.2019
"""

from PySide2.QtCore import Qt, QModelIndex
from .tree_model_base import TreeModelBase
from .parameter_value_list_item import DBItem, ListItem, ValueItem


class ParameterValueListModel(TreeModelBase):
    """A model to display parameter_value_list data in a tree view."""

    def _get_db_item(self, db_map):
        return {db_item.db_map: db_item for db_item in self._invisible_root_item.children}[db_map]

    def _get_list_item(self, db_map, item):
        id_, commit_id = item["id"], item["commit_id"]
        db_item = self._get_db_item(db_map)
        list_item = {x.id: x for x in db_item.non_empty_children}.get(id_)
        if list_item is not None:
            return list_item
        list_item = ListItem(id_)
        if commit_id is not None:
            db_item.insert_children_sorted([list_item])
        else:
            db_item.insert_children(len(db_item.non_empty_children), [list_item])
        return list_item

    def add_parameter_value_lists(self, db_map_data):
        db_map_wide_data = {}
        for db_map, data in db_map_data.items():
            db_map_wide_data[db_map] = wide_data = {}
            for item in data:
                item = item.copy()
                id_ = int(item["id"].split(",")[0])
                wide_data.setdefault(id_, []).append(item)
        for db_map, wide_data in db_map_wide_data.items():
            for items in wide_data.values():
                list_item = self._get_list_item(db_map, next(iter(items)))
                children = [ValueItem(x["id"]) for x in items]
                list_item.insert_children_sorted(children)

    def update_parameter_value_lists(self, db_map_data):
        for root_item, items in self._items_per_db_item(db_map_data).items():
            self._update_leaf_items(root_item, {x["id"] for x in items})

    def remove_parameter_value_lists(self, db_map_data):
        for root_item, items in self._items_per_db_item(db_map_data).items():
            self._remove_leaf_items(root_item, {x["id"] for x in items})

    @staticmethod
    def _make_db_item(db_map):
        return DBItem(db_map)

    @staticmethod
    def _top_children():
        return []

    def columnCount(self, parent=QModelIndex()):
        """Returns the number of columns under the given parent. Always 1."""
        return 1

    def index_name(self, index):
        return self.data(index.parent(), role=Qt.DisplayRole)

    def get_set_data_delayed(self, index):
        """Returns a function that ParameterValueEditor can call to set data for the given index at any later time,
        even if the model changes.

        Args:
            index (QModelIndex)

        Returns:
            Callable
        """
        item = self.item_from_index(index)
        return lambda value, item=item: item.add_item_to_db(item.make_item_to_add(value[0]))

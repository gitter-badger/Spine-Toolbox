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
Contains :class:`ItemMetadataTableModel` and associated functionality.

:author: A. Soininen (VTT)
:date:   25.3.2022
"""
from enum import auto, Enum, IntEnum, unique

from PySide2.QtCore import QModelIndex

from spinetoolbox.helpers import rows_to_row_count_tuples
from spinetoolbox.fetch_parent import FlexibleFetchParent
from .metadata_table_model_base import Column, FLAGS_EDITABLE, FLAGS_FIXED, MetadataTableModelBase


@unique
class ExtraColumn(IntEnum):
    """Identifiers for hidden table columns."""

    ITEM_METADATA_ID = Column.max() + 1
    METADATA_ID = Column.max() + 2


@unique
class ItemType(Enum):
    """Allowed item types."""

    ENTITY = auto()
    VALUE = auto()


class ItemMetadataTableModel(MetadataTableModelBase):
    """Model for entity and parameter value metadata."""

    _ITEM_NAME_KEY = "metadata_name"
    _ITEM_VALUE_KEY = "metadata_value"

    def __init__(self, db_mngr, db_maps, db_editor):
        """
        Args:
            db_mngr (SpineDBManager): database manager
            db_maps (Iterable of DatabaseMappingBase): database maps
            db_editor (SpineDBEditor): DB editor
        """
        super().__init__(db_mngr, db_maps, db_editor)
        self._item_type = None
        self._item_ids = {}
        self._entity_metadata_fetch_parent = FlexibleFetchParent(
            "entity_metadata",
            handle_items_added=self.add_item_metadata,
            handle_items_removed=self.remove_item_metadata,
            handle_items_updated=self.update_item_metadata,
            accepts_item=self._accepts_entity_metadata_item,
            owner=self,
        )
        self._parameter_value_metadata_fetch_parent = FlexibleFetchParent(
            "parameter_value_metadata",
            handle_items_added=self.add_item_metadata,
            handle_items_removed=self.remove_item_metadata,
            handle_items_updated=self.update_item_metadata,
            accepts_item=self._accepts_parameter_value_metadata_item,
            owner=self,
        )

    def _fetch_parents(self):
        yield self._entity_metadata_fetch_parent
        yield self._parameter_value_metadata_fetch_parent

    def clear(self):
        """Clears the model."""
        self.beginResetModel()
        self._item_ids = {}
        self._data = []
        self._adder_row = self._make_adder_row(None)
        self.endResetModel()

    @staticmethod
    def _make_hidden_adder_columns():
        """See base class."""
        return [None, None]

    def _accepts_entity_metadata_item(self, item, db_map):
        if self._item_type != ItemType.ENTITY:
            return False
        return item["entity_id"] == self._item_ids.get(db_map)

    def _accepts_parameter_value_metadata_item(self, item, db_map):
        if self._item_type != ItemType.VALUE:
            return False
        return item["parameter_value_id"] == self._item_ids.get(db_map)

    def set_entity_ids(self, db_map_ids):
        """Sets the model to show metadata from given entity.

        Args:
            db_map_ids (dict): mapping from database mapping to entity's id in that database
        """
        self._reset_metadata(ItemType.ENTITY, db_map_ids)
        self._reset_fetch_parents()

    def set_parameter_value_ids(self, db_map_ids):
        """Sets the model to show metadata from given parameter value.

        Args:
            db_map_ids (dict): mapping from database mapping to value's id in that database
        """
        self._reset_metadata(ItemType.VALUE, db_map_ids)
        self._reset_fetch_parents()

    def _reset_metadata(self, item_type, db_map_ids):
        """Resets model.

        Args:
            item_type (ItemType): current item type
            db_map_ids (dict): mapping from database mapping to value's id in that database
        """
        self.beginResetModel()
        self._item_type = item_type
        self._item_ids = dict(db_map_ids)
        self._db_maps = set(db_map_ids.keys())
        default_db_map = next(iter(self._db_maps)) if self._db_maps else None
        self._adder_row = self._make_adder_row(default_db_map)
        self._data = []
        self.endResetModel()

    def _reset_fetch_parents(self):
        for parent in self._fetch_parents():
            parent.reset_fetching(None)
        if self.canFetchMore(None):
            self.fetchMore(None)

    def _add_data_to_db_mngr(self, name, value, db_map):
        """See base class."""
        item_id = self._item_ids[db_map]
        if self._item_type == ItemType.ENTITY:
            self._db_mngr.add_entity_metadata(
                {db_map: [{"entity_id": item_id, "metadata_name": name, "metadata_value": value}]}
            )
        else:
            self._db_mngr.add_parameter_value_metadata(
                {db_map: [{"parameter_value_id": item_id, "metadata_name": name, "metadata_value": value}]}
            )

    def _update_data_in_db_mngr(self, id_, name, value, db_map):
        """See base class"""
        if self._item_type == ItemType.ENTITY:
            self._db_mngr.update_entity_metadata(
                {db_map: [{"id": id_, "metadata_name": name, "metadata_value": value}]}
            )
        else:
            self._db_mngr.update_parameter_value_metadata(
                {db_map: [{"id": id_, "metadata_name": name, "metadata_value": value}]}
            )

    def rollback(self, _db_maps):
        """Rolls back changes in database.

        Args:
            db_maps (Iterable of DiffDatabaseMapping): database mappings that have been rolled back
        """
        self.beginResetModel()
        self._data = []
        self.endResetModel()
        self._reset_fetch_parents()

    def flags(self, index):
        row = index.row()
        column = index.column()
        if column == Column.DB_MAP and row < len(self._data):
            data_row = self._data[row]
            if data_row[ExtraColumn.ITEM_METADATA_ID] is not None and data_row[ExtraColumn.METADATA_ID] is not None:
                return FLAGS_FIXED
        return FLAGS_EDITABLE

    @staticmethod
    def _ids_from_added_item(item):
        """See base class."""
        return item["id"], item["metadata_id"]

    @staticmethod
    def _extra_cells_from_added_item(item):
        """See base class."""
        return [item["id"], item["metadata_id"]]

    def _set_extra_columns(self, row, ids):
        """See base class."""
        row[ExtraColumn.ITEM_METADATA_ID] = ids[0]
        row[ExtraColumn.METADATA_ID] = ids[1]

    def _database_table_name(self):
        """See base class"""
        return "entity_metadata" if self._item_type == ItemType.ENTITY else "parameter_value_metadata"

    def _row_id(self, row):
        """See base class."""
        return row[ExtraColumn.ITEM_METADATA_ID]

    def add_item_metadata(self, db_map_data):
        """Adds new item metadata from database manager to the model.

        Args:
            db_map_data (dict): added items keyed by database mapping
        """
        self._add_data(db_map_data)

    def update_item_metadata(self, db_map_data):
        """Updates item metadata in model after it has been updated in databases.

        Args:
            db_map_data (dict): updated metadata records
        """
        for db_map, items in db_map_data.items():
            for item in items:
                for row in self._data:
                    if db_map != row[Column.DB_MAP] or item["id"] != row[ExtraColumn.ITEM_METADATA_ID]:
                        continue
                    row[ExtraColumn.METADATA_ID] = item["metadata_id"]
                    break

    def remove_item_metadata(self, db_map_data):
        """Removes item metadata from model after it has been removed from databases.

        Args:
            db_map_data (dict): removed items keyed by database mapping
        """
        self._remove_data(db_map_data, ExtraColumn.ITEM_METADATA_ID)

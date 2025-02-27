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
Contains the ParameterViewMixin class.

:author: M. Marin (KTH)
:date:   26.11.2018
"""

from PySide2.QtCore import Qt, Slot, QModelIndex
from PySide2.QtWidgets import QHeaderView
from .object_name_list_editor import ObjectNameListEditor
from ..mvcmodels.compound_parameter_models import (
    CompoundObjectParameterDefinitionModel,
    CompoundObjectParameterValueModel,
    CompoundRelationshipParameterDefinitionModel,
    CompoundRelationshipParameterValueModel,
)
from ...helpers import preferred_row_height, DB_ITEM_SEPARATOR


class ParameterViewMixin:
    """
    Provides stacked parameter tables for the Spine db editor.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filter_class_ids = {}
        self._filter_entity_ids = {}
        self._filter_alternative_ids = {}
        self.object_parameter_value_model = CompoundObjectParameterValueModel(self, self.db_mngr)
        self.relationship_parameter_value_model = CompoundRelationshipParameterValueModel(self, self.db_mngr)
        self.object_parameter_definition_model = CompoundObjectParameterDefinitionModel(self, self.db_mngr)
        self.relationship_parameter_definition_model = CompoundRelationshipParameterDefinitionModel(self, self.db_mngr)
        self._parameter_models = (
            self.object_parameter_value_model,
            self.relationship_parameter_value_model,
            self.object_parameter_definition_model,
            self.relationship_parameter_definition_model,
        )
        self._parameter_value_models = (self.object_parameter_value_model, self.relationship_parameter_value_model)
        views = (
            self.ui.tableView_object_parameter_value,
            self.ui.tableView_relationship_parameter_value,
            self.ui.tableView_object_parameter_definition,
            self.ui.tableView_relationship_parameter_definition,
        )
        for view, model in zip(views, self._parameter_models):
            view.setModel(model)
            view.verticalHeader().setDefaultSectionSize(preferred_row_height(self))
            view.horizontalHeader().setResizeContentsPrecision(self.visible_rows)
            view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            view.horizontalHeader().setStretchLastSection(True)
            view.horizontalHeader().setSectionsMovable(True)
            view.connect_spine_db_editor(self)

    def connect_signals(self):
        """Connects signals to slots."""
        super().connect_signals()
        self.ui.treeView_alternative_scenario.alternative_selection_changed.connect(
            self._handle_alternative_selection_changed
        )
        self.ui.treeView_object.tree_selection_changed.connect(self._handle_object_tree_selection_changed)
        self.ui.treeView_relationship.tree_selection_changed.connect(self._handle_relationship_tree_selection_changed)
        self.ui.graphicsView.graph_selection_changed.connect(self._handle_graph_selection_changed)

    def init_models(self):
        """Initializes models."""
        super().init_models()
        self.object_parameter_value_model.db_maps = self.db_maps
        self.relationship_parameter_value_model.db_maps = self.db_maps
        self.object_parameter_definition_model.db_maps = self.db_maps
        self.relationship_parameter_definition_model.db_maps = self.db_maps
        self.object_parameter_value_model.init_model()
        self.object_parameter_definition_model.init_model()
        self.relationship_parameter_value_model.init_model()
        self.relationship_parameter_definition_model.init_model()
        self._set_default_parameter_data()

    @Slot(QModelIndex, int, object)
    def show_object_name_list_editor(self, index, rel_cls_id, db_map):
        """Shows the object names list editor.

        Args:
            index (QModelIndex)
            rel_cls_id (int)
            db_map (DiffDatabaseMapping)
        """
        relationship_class = self.db_mngr.get_item(db_map, "relationship_class", rel_cls_id, only_visible=False)
        object_class_id_list = relationship_class.get("object_class_id_list")
        object_class_names = []
        object_names_lists = []
        for id_ in object_class_id_list:
            object_class_name = self.db_mngr.get_item(db_map, "object_class", id_, only_visible=False).get("name")
            object_names_list = [
                x["name"]
                for x in self.db_mngr.get_items_by_field(db_map, "object", "class_id", id_, only_visible=False)
            ]
            object_class_names.append(object_class_name)
            object_names_lists.append(object_names_list)
        object_name_list = index.data(Qt.EditRole)
        try:
            current_object_names = object_name_list.split(DB_ITEM_SEPARATOR)
        except AttributeError:
            # Gibberish
            current_object_names = []
        editor = ObjectNameListEditor(self, index, object_class_names, object_names_lists, current_object_names)
        editor.show()

    def _set_default_parameter_data(self, index=None):
        """Sets default rows for parameter models according to given index.

        Args:
            index (QModelIndex): and index of the object or relationship tree
        """
        if index is None or not index.isValid():
            default_db_map = next(iter(self.db_maps))
            default_data = dict(database=default_db_map.codename)
        else:
            item = index.model().item_from_index(index)
            default_db_map = item.first_db_map
            default_data = item.default_parameter_data()
        self.set_default_parameter_data(default_data, default_db_map)

    def set_default_parameter_data(self, default_data, default_db_map):
        for model in self._parameter_models:
            model.empty_model.db_map = default_db_map
            model.empty_model.set_default_row(**default_data)
            model.empty_model.set_rows_to_default(model.empty_model.rowCount() - 1)

    def clear_all_filters(self):
        for model in self._parameter_models:
            model.clear_auto_filter()
        for model in self._parameter_value_models:
            model.clear_auto_filter()
        self._filter_class_ids = {}
        self._filter_entity_ids = {}
        self._filter_alternative_ids = {}
        self._reset_filters()

    def _reset_filters(self):
        """Resets filters."""
        for model in self._parameter_models:
            model.set_filter_class_ids(self._filter_class_ids)
        for model in self._parameter_value_models:
            model.set_filter_entity_ids(self._filter_entity_ids)
            model.set_filter_alternative_ids(self._filter_alternative_ids)

    @Slot(dict)
    def _handle_graph_selection_changed(self, selected_items):
        """Resets filter according to graph selection."""
        obj_items = selected_items["object"]
        rel_items = selected_items["relationship"]
        active_objs = {}
        for x in obj_items:
            for db_map in x.db_maps:
                active_objs.setdefault(db_map, []).append(x.db_representation(db_map))
        cascading_rels = self.db_mngr.find_cascading_relationships(self.db_mngr.db_map_ids(active_objs))
        active_rels = {}
        for x in rel_items:
            for db_map in x.db_maps:
                active_rels.setdefault(db_map, []).append(x.db_representation(db_map))
        for db_map, rels in cascading_rels.items():
            active_rels.setdefault(db_map, []).extend(rels)
        self._filter_class_ids = {}
        for db_map, items in active_objs.items():
            self._filter_class_ids.setdefault(db_map, set()).update({x["class_id"] for x in items})
        for db_map, items in active_rels.items():
            self._filter_class_ids.setdefault(db_map, set()).update({x["class_id"] for x in items})
        self._filter_entity_ids = self.db_mngr.db_map_class_ids(active_objs)
        self._filter_entity_ids.update(self.db_mngr.db_map_class_ids(active_rels))
        self._reset_filters()

    @Slot(dict)
    def _handle_object_tree_selection_changed(self, selected_indexes):
        """Resets filter according to object tree selection."""
        obj_cls_inds = set(selected_indexes.get("object_class", {}).keys())
        obj_inds = set(selected_indexes.get("object", {}).keys())
        rel_cls_inds = set(selected_indexes.get("relationship_class", {}).keys())
        active_rel_inds = set(selected_indexes.get("relationship", {}).keys())
        # Compute active indexes by merging in the parents from lower levels recursively
        active_rel_cls_inds = rel_cls_inds | {ind.parent() for ind in active_rel_inds}
        active_obj_inds = obj_inds | {ind.parent() for ind in active_rel_cls_inds}
        active_obj_cls_inds = obj_cls_inds | {ind.parent() for ind in active_obj_inds}
        self._filter_class_ids = self._db_map_ids(active_obj_cls_inds | active_rel_cls_inds)
        self._filter_entity_ids = self._db_map_class_ids(active_obj_inds | active_rel_inds)
        # Cascade (note that we carefully select where to cascade from, to avoid 'circularity')
        obj_cls_ids = self._db_map_ids(obj_cls_inds | {ind.parent() for ind in obj_inds})
        obj_ids = self._db_map_ids(obj_inds | {ind.parent() for ind in rel_cls_inds})
        cascading_rel_clss = self.db_mngr.find_cascading_relationship_classes(obj_cls_ids, only_visible=False)
        cascading_rels = self.db_mngr.find_cascading_relationships(obj_ids, only_visible=False)
        for db_map, ids in self.db_mngr.db_map_ids(cascading_rel_clss).items():
            self._filter_class_ids.setdefault(db_map, set()).update(ids)
        for (db_map, class_id), ids in self.db_mngr.db_map_class_ids(cascading_rels).items():
            self._filter_entity_ids.setdefault((db_map, class_id), set()).update(ids)
        self._reset_filters()
        self._set_default_parameter_data(self.ui.treeView_object.selectionModel().currentIndex())

    @Slot(dict)
    def _handle_relationship_tree_selection_changed(self, selected_indexes):
        """Resets filter according to relationship tree selection."""
        rel_cls_inds = set(selected_indexes.get("relationship_class", {}).keys())
        active_rel_inds = set(selected_indexes.get("relationship", {}).keys())
        active_rel_cls_inds = rel_cls_inds | {ind.parent() for ind in active_rel_inds}
        self._filter_class_ids = self._db_map_ids(active_rel_cls_inds)
        self._filter_entity_ids = self._db_map_class_ids(active_rel_inds)
        self._reset_filters()
        self._set_default_parameter_data(self.ui.treeView_relationship.selectionModel().currentIndex())

    @Slot(dict)
    def _handle_alternative_selection_changed(self, selected_db_map_alt_ids):
        """Resets filter according to selection in alternative tree view."""
        self._filter_alternative_ids = {db_map: alt_ids.copy() for db_map, alt_ids in selected_db_map_alt_ids.items()}
        self._reset_filters()

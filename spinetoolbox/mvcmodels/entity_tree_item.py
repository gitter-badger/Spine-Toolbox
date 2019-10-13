######################################################################################################################
# Copyright (C) 2017 - 2019 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
Classes to represent entities in a tree.

:authors: P. Vennström (VTT), M. Marin (KTH)
:date:   11.3.2019
"""
from PySide2.QtCore import Qt, Signal, QModelIndex
from sqlalchemy import or_
from PySide2.QtGui import QFont, QBrush, QIcon


class TreeItem:
    """A tree item that can fetch its children."""

    def __init__(self, parent=None):
        """Init class.

        Args:
            parent (TreeItem, NoneType): the parent item or None
        """
        self._children = []
        self._parent = None
        self._fetched = False
        self.parent = parent
        self.children = []

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, children):
        if not all(isinstance(child, TreeItem) for child in children):
            raise ValueError("all items in children must be instance of TreeItem")
        self._children = children

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        if not isinstance(parent, TreeItem) and parent is not None:
            raise ValueError("Parent must be instance of TreeItem or None")
        self._parent = parent

    def child(self, row):
        """Returns the child at given row or None if out of bounds."""
        try:
            return self._children[row]
        except IndexError:
            return None

    def last_child(self):
        return self.child(-1)

    def child_count(self):
        """Returns the number of children."""
        return len(self._children)

    def child_number(self):
        """Returns the row of this item as a children, or 0 if it doesn't have a parent."""
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0

    def find_children(self, cond=lambda child: True):
        """Returns children that meet condition expressed as a lambda function."""
        for child in self.children:
            if cond(child):
                yield child

    def find_child(self, cond=lambda child: True):
        """Returns first child that meet condition expressed as a lambda function or None."""
        return next(self.find_children(cond), None)

    def next_sibling(self):
        """Returns the next sibling or None if last or if doesn't have a parent."""
        if self.parent is None:
            return None
        return self.parent.child(self.child_number() + 1)

    def previous_sibling(self):
        """Returns the previous sibling or None if first or if doesn't have a parent."""
        if self.child_number() == 0:
            return None
        return self.parent.child(self.child_number() - 1)

    def clear_children(self):
        """Clear all children, used when resetting the model."""
        self.children.clear()

    def column_count(self):
        """Returns 0."""
        return 0

    def insert_children(self, position, new_children):
        """Insert new children at given position. Returns a boolean depending on how it went.

        Args:
            position (int): insert new items here
            new_children (list): insert items from this list
        """
        if not all(isinstance(item, TreeItem) for item in new_children):
            raise TypeError("All rows in new_rows must be of type 'TreeItem'")
        if position < 0 or position > self.child_count() + 1:
            return False
        self._children[position:position] = new_children
        return True

    def remove_children(self, position, count):
        """Removes count children starting from the given position."""
        if position > self.child_count() or position < 0:
            return False
        if position + count > self.child_count():
            count = self.child_count() - position
        del self._children[position : position + count]
        return True

    def flags(self, column):
        """Enables the item and makes it selectable."""
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def data(self, column, role=Qt.DisplayRole):
        """Returns data from this item."""
        return None

    def has_children(self):
        """Returns whether or not this item has or could have children."""
        if self.child_count() or self.can_fetch_more():
            return True
        return False

    def can_fetch_more(self):
        """Returns whether or not this item can fetch more."""
        return not self._fetched

    def fetch_more(self):
        """Fetches more children and returns them in a list.
        The base class implementation returns an empty list.
        """
        self._fetched = True
        return []


class MultiDBTreeItem(TreeItem):
    """A tree item that may belong in multiple databases."""

    def __init__(self, db_map_data, parent=None):
        """Init class.

        Args:
            db_map_data (dict): maps instances of DiffDatabaseMapping to the data of the item in that db

        """
        super().__init__(parent)
        self._db_map_data = db_map_data

    @property
    def unique_identifier(self):
        """"Returns the unique identifier for this item across all dbs.
        The base class implementation returns the name.
        """
        return self.db_map_data_field(self.first_db_map, "name")

    @property
    def display_name(self):
        """"Returns the name for display."""
        return self.unique_identifier

    @property
    def display_database(self):
        """"Returns the database for display."""
        return ", ".join([self.db_map_data_field(db_map, "database") for db_map in self.db_maps])

    @property
    def first_db_map(self):
        """Returns the first db_map where this item belongs."""
        db_map = next(iter(self._db_map_data.keys()))
        return db_map

    @property
    def db_maps(self):
        """Returns a list of all db_maps where this item belongs."""
        return list(self._db_map_data.keys())

    def add_db_map_data(self, db_map, new_data):
        """Adds new data from db_map for this item."""
        self._db_map_data[db_map] = new_data

    def remove_db_map(self, db_map):
        """Removes the given db_map."""
        self._db_map_data.pop(db_map, None)

    def db_map_data(self, db_map):
        """Returns the data of this item in given db_map or None if not found."""
        return self._db_map_data.get(db_map)

    def db_map_data_field(self, db_map, field, default=None):
        """Returns the data of this item for given filed in given db_map or None if not found."""
        return self._db_map_data.get(db_map, {}).get(field, default)

    def add_db_map_data_field(self, db_map, field, value):
        """Adds a new field to the data of this item in given db_map."""
        db_map_data = self.db_map_data(db_map)
        if db_map_data:
            db_map_data[field] = value

    def fetch_more(self):
        """Returns a list of new children to add to the model."""
        new_children = dict()
        for db_map, child_data in self._get_children_data():
            database = self.db_map_data_field(db_map, "database")
            child_data["database"] = database
            new_item = self._create_child_item({db_map: child_data})
            unique_identifier = new_item.unique_identifier
            existing_item = new_children.get(unique_identifier)
            if not existing_item:
                new_children[unique_identifier] = new_item
            else:
                existing_item.add_db_map_data(db_map, child_data)
                del new_item
        self._fetched = True
        return list(new_children.values())

    def _get_children_data(self):
        """Generates tuples of (db_map, child data) from all the dbs."""
        for db_map in self.db_maps:
            for child in self._children_query(db_map):
                yield (db_map, child._asdict())

    def _children_query(self, db_map):
        """Returns a query that selects all children from given db_map.
        Must be reimplemented in subclasses."""
        raise NotImplementedError()

    def _create_child_item(self, db_map_data):
        """Returns a child item from given db_map data.
        Must be reimplemented in subclasses."""
        raise NotImplementedError()

    def append_children_from_data(self, db_map, children_data):
        """

        Args:
            db_map (DiffDatabaseMapping)
            children_data (list): collection of dicts
        """
        existing_children = {child.unique_identifier: child for child in self.children}
        added_rows = []
        updated_inds = []
        database = self.db_map_data_field(db_map, "database")
        for child_data in children_data:
            child_data["database"] = database
            new_item = self._create_child_item({db_map: child_data})
            existing_item = existing_children.get(new_item.unique_identifier)
            if not existing_item:
                # No collision, add the new item
                added_rows.append(new_item)
            else:
                # Collision, update existing and get rid of new one
                existing_item.add_db_map_data(db_map, child_data)
                del new_item
        return added_rows

    def data(self, column, role):
        """Returns data from this item."""
        if role == Qt.DisplayRole:
            return (self.display_name, self.display_database)[column]
        if role == Qt.DecorationRole and column == 0:
            return self.display_icon()

    def display_icon(self):
        """Returns an icon to display next to the name.
        Reimplement in subclasses to return something nice."""
        return None

    def default_parameter_data(self):
        """Return data to put as default in a parameter table when this item is selected."""
        return {"database": self.db_map_data_field(self.first_db_map, "database")}


class TreeRootItem(MultiDBTreeItem):
    @property
    def unique_identifier(self):
        """"Returns a unique identifier for this item across all dbs."""
        return "root"


class ObjectTreeRootItem(TreeRootItem):
    """An object tree root item."""

    context_menu_actions = {"Add object classes": QIcon(":/icons/menu_icons/cube_plus.svg")}

    def _children_query(self, db_map):
        """Returns a query that selects all children from given db_map."""
        return db_map.query(db_map.object_class_sq)

    def _create_child_item(self, db_map_data):
        return ObjectClassItem(db_map_data, parent=self)


class RelationshipTreeRootItem(TreeRootItem):
    """A relationship tree root item."""

    context_menu_actions = {"Add relationship classes": QIcon(":/icons/menu_icons/cubes_plus.svg")}

    def _children_query(self, db_map):
        """Returns a query that selects all children from given db_map."""
        return db_map.query(db_map.wide_relationship_class_sq)

    def _create_child_item(self, db_map_data):
        return RelationshipClassItem(db_map_data, parent=self)


class EntityClassItem(MultiDBTreeItem):
    """An entity class item."""

    def data(self, column, role=Qt.DisplayRole):
        if role == Qt.ToolTipRole:
            return self.db_map_data_field(self.first_db_map, "description")
        if role == Qt.FontRole and column == 0:
            bold_font = QFont()
            bold_font.setBold(True)
            return bold_font
        if role == Qt.ForegroundRole and column == 0:
            if not self.has_children():
                return QBrush(Qt.gray)
        return super().data(column, role)


class ObjectClassItem(EntityClassItem):
    """An object class item."""

    type_name = "object class"
    context_menu_actions = {
        "Add relationship classes": QIcon(":/icons/menu_icons/cubes_plus.svg"),
        "Add objects": QIcon(":/icons/menu_icons/cube_plus.svg"),
        "": None,
        "Edit object classes": QIcon(":/icons/menu_icons/cube_pen.svg"),
        "": None,
        "Remove selection": QIcon(":/icons/menu_icons/cube_minus.svg"),
    }

    def _children_query(self, db_map):
        """Returns a query to the given db map that returns children of this item."""
        return db_map.query(db_map.object_sq).filter_by(class_id=self.db_map_data_field(db_map, 'id'))

    def _create_child_item(self, db_map_data):
        return ObjectItem(db_map_data, parent=self)

    def display_icon(self):
        """Returns the object class icon."""
        name = self.db_map_data_field(self.first_db_map, "name")
        # TODO return self._spinedb_manager.icon_manager.object_icon(name)

    def default_parameter_data(self):
        """Return data to put as default in a parameter table when this item is selected."""
        data = self.db_map_data(self.first_db_map)
        return dict(object_class_name=data['name'], database=data['database'])


class RelationshipClassItem(EntityClassItem):
    """A relationship class item."""

    type_name = "relationship class"
    context_menu_actions = {
        "Add relationships": QIcon(":/icons/menu_icons/cubes_plus.svg"),
        "": None,
        "Edit relationship classes": QIcon(":/icons/menu_icons/cubes_pen.svg"),
        "": None,
        "Remove selection": QIcon(":/icons/menu_icons/cubes_minus.svg"),
    }

    def __init__(self, *args, **kwargs):
        """Overriden method to parse some data for convenience later."""
        super().__init__(*args, **kwargs)
        for db_map in self.db_maps:
            object_class_id_list = self.db_map_data_field(db_map, "object_class_id_list")
            if object_class_id_list:
                parsed_object_class_id_list = [int(id_) for id_ in object_class_id_list.split(",")]
                self.add_db_map_data_field(db_map, "parsed_object_class_id_list", parsed_object_class_id_list)
            object_class_name_list = self.db_map_data_field(db_map, "object_class_name_list")
            if object_class_name_list:
                parsed_object_class_name_list = object_class_name_list.split(",")
                self.add_db_map_data_field(db_map, "parsed_object_class_name_list", parsed_object_class_name_list)

    @property
    def unique_identifier(self):
        """Returns a tuple of name, object class name list."""
        data = self.db_map_data(self.first_db_map)
        return (data["name"], data["object_class_name_list"])

    @property
    def display_name(self):
        """"Returns the name for display."""
        return self.db_map_data_field(self.first_db_map, "name")

    def display_icon(self):
        """Returns relationship class icon."""
        object_class_name_list = self.db_map_data_field(self.first_db_map, "object_class_name_list")
        # TODO return self._spinedb_manager.icon_manager.relationship_icon(object_class_name_list)

    def _children_query(self, db_map):
        """Returns a query to the given db map that returns children of this item."""
        sq = db_map.wide_relationship_sq
        qry = db_map.query(sq).filter_by(class_id=self.db_map_data_field(db_map, 'id'))
        if isinstance(self.parent, ObjectItem):
            object_id = self.parent.db_map_data_field(db_map, 'id')
            qry = qry.filter(
                or_(
                    sq.c.object_id_list.like(f"%,{object_id},%"),
                    sq.c.object_id_list.like(f"{object_id},%"),
                    sq.c.object_id_list.like(f"%,{object_id}"),
                    sq.c.object_id_list == object_id,
                )
            )
        return qry

    def _create_child_item(self, db_map_data):
        return RelationshipItem(db_map_data, parent=self)

    def default_parameter_data(self):
        """Return data to put as default in a parameter table when this item is selected."""
        data = self.db_map_data(self.first_db_map)
        return dict(relationship_class_name=data['name'], database=data['database'])


class EntityItem(MultiDBTreeItem):
    """An entity item."""

    def data(self, column, role=Qt.DisplayRole):
        if role == Qt.ToolTipRole:
            return self.db_map_data_field(self.first_db_map, "description")
        return super().data(column, role)


class ObjectItem(EntityItem):
    """An object item."""

    type_name = "object"
    context_menu_actions = {
        "Edit objects": QIcon(":/icons/menu_icons/cube_pen.svg"),
        "": None,
        "Remove selection": QIcon(":/icons/menu_icons/cube_minus.svg"),
    }

    def _children_query(self, db_map):
        """Returns a query to the given db map that returns children of this item."""
        object_class_id = self.db_map_data_field(db_map, 'class_id')
        sq = db_map.wide_relationship_class_sq
        return db_map.query(sq).filter(
            or_(
                sq.c.object_class_id_list.like(f"%,{object_class_id},%"),
                sq.c.object_class_id_list.like(f"{object_class_id},%"),
                sq.c.object_class_id_list.like(f"%,{object_class_id}"),
                sq.c.object_class_id_list == object_class_id,
            )
        )

    def _create_child_item(self, db_map_data):
        return RelationshipClassItem(db_map_data, parent=self)

    def display_icon(self):
        """Returns the object class icon."""
        name = self.parent.db_map_data_field(self.first_db_map, "name")
        # TODO return self._spinedb_manager.icon_manager.object_icon(name)

    def default_parameter_data(self):
        """Return data to put as default in a parameter table when this item is selected."""
        data = self.db_map_data(self.first_db_map)
        parent_data = self.parent.db_map_data(self.first_db_map)
        return dict(object_class_name=parent_data['name'], object_name=data['name'], database=data['database'])


class RelationshipItem(EntityItem):
    """An object item."""

    type_name = "relationship"
    context_menu_actions = {
        "Edit relationships": QIcon(":/icons/menu_icons/cubes_pen.svg"),
        "": None,
        "Find next": QIcon(":/icons/menu_icons/ellipsis-h.png"),
        "": None,
        "Remove selection": QIcon(":/icons/menu_icons/cubes_minus.svg"),
    }

    def __init__(self, *args, **kwargs):
        """Overriden method to parse some data for convenience later.
        Also make sure we never try and fetch this item."""
        super().__init__(*args, **kwargs)
        self._fetched = True
        for db_map in self.db_maps:
            object_id_list = self.db_map_data_field(db_map, "object_id_list")
            if object_id_list:
                parsed_object_id_list = [int(id_) for id_ in object_id_list.split(",")]
                self.add_db_map_data_field(db_map, "parsed_object_id_list", parsed_object_id_list)
            object_name_list = self.db_map_data_field(db_map, "object_name_list")
            if object_name_list:
                parsed_object_name_list = object_name_list.split(",")
                self.add_db_map_data_field(db_map, "parsed_object_name_list", parsed_object_name_list)

    @property
    def unique_identifier(self):
        """Returns a tuple of name, object name list."""
        data = self.db_map_data(self.first_db_map)
        return (data["name"], data["object_name_list"])

    @property
    def display_name(self):
        """"Returns the name for display."""
        return self.db_map_data_field(self.first_db_map, "object_name_list")

    def display_icon(self):
        """Returns relationship class icon."""
        object_class_name_list = self.parent.db_map_data_field(self.first_db_map, "object_class_name_list")
        # TODO return self._spinedb_manager.icon_manager.relationship_icon(object_class_name_list)

    def has_children(self):
        return False

    def append_children_from_data(self, db_map, children_data):
        pass

    def default_parameter_data(self):
        """Return data to put as default in a parameter table when this item is selected."""
        data = self.db_map_data(self.first_db_map)
        parent_data = self.parent.db_map_data(self.first_db_map)
        return dict(
            relationship_class_name=parent_data['name'],
            object_name_list=data['object_name_list'],
            database=data['database'],
        )

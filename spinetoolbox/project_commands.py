######################################################################################################################
# Copyright (C) 2017-2020 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
QUndoCommand subclasses for modifying the project.

:authors: M. Marin (KTH)
:date:   12.2.2020
"""

from PySide2.QtWidgets import QUndoCommand


class AddProjectItemsCommand(QUndoCommand):
    def __init__(self, project, category_name, *items, set_selected=False, verbosity=True):
        super().__init__()
        self.project = project
        self.category_ind, self.project_tree_items = project.make_project_tree_items(category_name, *items)
        self.set_selected = set_selected
        self.verbosity = verbosity
        self.setText(f"add {', '.join([item['name'] for item in items])}")

    def redo(self):
        self.project._add_project_tree_items(
            self.category_ind, *self.project_tree_items, set_selected=self.set_selected, verbosity=self.verbosity
        )

    def undo(self):
        for project_tree_item in self.project_tree_items:
            self.project._remove_item(self.category_ind, project_tree_item)


class RemoveProjectItemCommand(QUndoCommand):
    def __init__(self, project, name, delete_item=False, check_dialog=False):
        super().__init__()
        self.project = project
        self.name = name
        self.delete_item = delete_item
        self.check_dialog = check_dialog
        ind = project._project_item_model.find_item(name)
        self.project_tree_item = project._project_item_model.item(ind)
        self.category_ind = ind.parent()
        icon = self.project_tree_item.project_item.get_icon()
        self.links = set(link for conn in icon.connectors.values() for link in conn.links)
        self.setText(f"remove {name}")

    def redo(self):
        self.project._remove_item(
            self.category_ind, self.project_tree_item, delete_item=self.delete_item, check_dialog=self.check_dialog
        )
        self.check_dialog = False

    def undo(self):
        self.project._add_project_tree_items(self.category_ind, self.project_tree_item)
        for link in self.links:
            self.project._toolbox.ui.graphicsView._add_link(link)


class RenameProjectItemCommand(QUndoCommand):
    def __init__(self, project_item_model, tree_item, new_name):
        super().__init__()
        self.project_item_model = project_item_model
        self.tree_index = project_item_model.find_item(tree_item.name)
        self.old_name = tree_item.name
        self.new_name = new_name
        self.setText(f"rename {self.old_name} to {new_name}")

    def redo(self):
        if not self.project_item_model.setData(self.tree_index, self.new_name):
            self.setObsolete(True)

    def undo(self):
        self.project_item_model.setData(self.tree_index, self.old_name)


class AddLinkCommand(QUndoCommand):
    def __init__(self, graphics_view, src_connector, dst_connector):
        super().__init__()
        self.graphics_view = graphics_view
        self.link = graphics_view.make_link(src_connector, dst_connector)
        self.replaced_link = None
        self.link_name = f"{src_connector.parent_name()} to {dst_connector.parent_name()}"

    def redo(self):
        self.replaced_link = self.graphics_view._add_link(self.link)
        action = "add" if self.replaced_link is None else "replace"
        self.setText(f"{action} {self.link_name}")

    def undo(self):
        self.graphics_view.do_remove_link(self.link)
        if self.replaced_link is not None:
            self.graphics_view._add_link(self.replaced_link)


class RemoveLinkCommand(QUndoCommand):
    def __init__(self, graphics_view, link):
        super().__init__()
        self.graphics_view = graphics_view
        self.link = link
        self.setText(f"remove link from {link.src_connector.parent_name()} to {link.dst_connector.parent_name()}")

    def redo(self):
        self.graphics_view.do_remove_link(self.link)

    def undo(self):
        self.graphics_view._add_link(self.link)


class MoveIconCommand(QUndoCommand):
    def __init__(self, graphics_item):
        super().__init__()
        self.graphics_item = graphics_item
        self.previous_pos = {x: x._previous_pos for x in graphics_item.selected_icons}
        self.current_pos = {x: x._current_pos for x in graphics_item.selected_icons}
        self.setText(f"move {', '.join([x._project_item.name for x in graphics_item.selected_icons])}")

    def redo(self):
        for item, current_post in self.current_pos.items():
            item.setPos(current_post)
        self.graphics_item.update_links_geometry()
        self.graphics_item.shrink_scene_if_needed()

    def undo(self):
        for item, previous_pos in self.previous_pos.items():
            item.setPos(previous_pos)
        self.graphics_item.update_links_geometry()
        self.graphics_item.shrink_scene_if_needed()


class AddDCReferencesCommand(QUndoCommand):
    def __init__(self, dc, paths):
        super().__init__()
        self.dc = dc
        self.paths = paths
        self.setText(f"add references to {dc.name}")

    def redo(self):
        self.dc.do_add_files_to_references(self.paths)

    def undo(self):
        self.dc.do_remove_references(self.paths)


class RemoveDCReferencesCommand(QUndoCommand):
    def __init__(self, dc, paths):
        super().__init__()
        self.dc = dc
        self.paths = paths
        self.setText(f"remove references from {dc.name}")

    def redo(self):
        self.dc.do_remove_references(self.paths)

    def undo(self):
        self.dc.do_add_files_to_references(self.paths)

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
Contains the SpineDBEditor class.

:author: M. Marin (KTH)
:date:   26.11.2018
"""

import os
import json
from sqlalchemy.engine.url import URL
from PySide2.QtWidgets import (
    QAction,
    QMainWindow,
    QErrorMessage,
    QDockWidget,
    QMessageBox,
    QMenu,
    QAbstractScrollArea,
    QTabBar,
    QCheckBox,
    QDialog,
)
from PySide2.QtCore import QModelIndex, Qt, Signal, Slot, QTimer
from PySide2.QtGui import QFont, QFontMetrics, QGuiApplication, QKeySequence, QIcon
from spinedb_api import export_data, DatabaseMapping, SpineDBAPIError, SpineDBVersionError, Asterisk
from spinedb_api.spine_io.importers.excel_reader import get_mapped_data_from_xlsx
from .custom_menus import MainMenu
from .mass_select_items_dialogs import MassRemoveItemsDialog, MassExportItemsDialog
from .parameter_view_mixin import ParameterViewMixin
from .tree_view_mixin import TreeViewMixin
from .graph_view_mixin import GraphViewMixin
from .tabular_view_mixin import TabularViewMixin
from .db_session_history_dialog import DBSessionHistoryDialog
from .url_toolbar import UrlToolBar
from ...widgets.notification import ChangeNotifier
from ...widgets.notification import NotificationStack
from ...widgets.parameter_value_editor import ParameterValueEditor
from ...widgets.custom_qwidgets import ToolBarWidgetAction
from ...widgets.commit_dialog import CommitDialog
from ...helpers import (
    get_save_file_name_in_last_dir,
    get_open_file_name_in_last_dir,
    format_string_list,
    call_on_focused_widget,
    busy_effect,
    CharIconEngine,
)
from ...spine_db_parcel import SpineDBParcel
from ...config import APPLICATION_PATH


class SpineDBEditorBase(QMainWindow):
    """Base class for SpineDBEditor (i.e. Spine database editor)."""

    msg = Signal(str)
    link_msg = Signal(str, object)
    msg_error = Signal(str)
    file_exported = Signal(str)
    sqlite_file_exported = Signal(str)

    def __init__(self, db_mngr):
        """Initializes form.

        Args:
            db_mngr (SpineDBManager): The manager to use
        """
        super().__init__()
        from ..ui.spine_db_editor_window import Ui_MainWindow  # pylint: disable=import-outside-toplevel

        self.db_mngr = db_mngr
        self.db_maps = []
        self.db_urls = []
        self._change_notifiers = []
        self._changelog = []
        self.db_url = None
        # Setup UI from Qt Designer file
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.takeCentralWidget()
        self.url_toolbar = UrlToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.url_toolbar)
        toolbox = self.db_mngr.parent()
        if toolbox is not None:
            self.url_toolbar.show_toolbox_action.triggered.connect(toolbox.restore_and_activate)
        else:
            self.url_toolbar.show_toolbox_action.deleteLater()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("")
        self.qsettings = self.db_mngr.qsettings
        self.err_msg = QErrorMessage(self)
        self.err_msg.setWindowTitle("Error")
        self.err_msg.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.notification_stack = NotificationStack(self)
        self.silenced = False
        fm = QFontMetrics(QFont("", 0))
        self.default_row_height = 1.2 * fm.lineSpacing()
        max_screen_height = max([s.availableSize().height() for s in QGuiApplication.screens()])
        self.visible_rows = int(max_screen_height / self.default_row_height)
        self.settings_group = "spineDBEditor"
        self.undo_action = None
        self.redo_action = None
        self.ui.actionUndo.setShortcuts(QKeySequence.Undo)
        self.ui.actionRedo.setShortcuts(QKeySequence.Redo)
        self.update_commit_enabled()
        self.setContextMenuPolicy(Qt.NoContextMenu)

    @property
    def toolbox(self):
        return self.db_mngr.parent()

    @property
    def settings_subgroup(self):
        return ";".join(self.db_urls)

    @property
    def db_names(self):
        return ", ".join([f"{db_map.codename}" for db_map in self.db_maps])

    @property
    def first_db_map(self):
        return self.db_maps[0]

    @property
    def db_url_codenames(self):
        return {db_map.db_url: db_map.codename for db_map in self.db_maps}

    def load_db_urls(self, db_url_codenames, create=False, update_history=True):
        self.ui.actionImport.setEnabled(False)
        self.ui.actionExport.setEnabled(False)
        self.ui.actionMass_remove_items.setEnabled(False)
        self.url_toolbar.reload_action.setEnabled(False)
        if not db_url_codenames:
            return
        if not self.tear_down():
            return
        self.db_maps = []
        self._changelog.clear()
        while self._change_notifiers:
            self._change_notifiers.pop(0).deleteLater()
        for url, codename in db_url_codenames.items():
            db_map = self.db_mngr.get_db_map(url, self, codename=codename, create=create)
            if db_map is not None:
                self.db_maps.append(db_map)
        if not self.db_maps:
            return
        self.ui.actionImport.setEnabled(True)
        self.ui.actionExport.setEnabled(True)
        self.ui.actionMass_remove_items.setEnabled(True)
        self.url_toolbar.reload_action.setEnabled(True)
        self._change_notifiers = [
            ChangeNotifier(self, self.db_mngr.undo_stack[db_map], self.qsettings, "appSettings/dbEditorShowUndo")
            for db_map in self.db_maps
        ]
        self.db_urls = [db_map.db_url for db_map in self.db_maps]
        self.url_toolbar.set_current_urls(self.db_urls)
        self.db_url = self.db_urls[0]
        self.db_mngr.register_listener(self, *self.db_maps)
        self.init_models()
        self.init_add_undo_redo_actions()
        self.setWindowTitle(f"{self.db_names}")  # This sets the tab name, just in case
        self.restore_ui()
        if update_history:
            self.url_toolbar.add_urls_to_history(self.db_urls)

    def init_add_undo_redo_actions(self):
        new_undo_action = self.db_mngr.undo_action[self.first_db_map]
        new_redo_action = self.db_mngr.redo_action[self.first_db_map]
        self._replace_undo_redo_actions(new_undo_action, new_redo_action)

    @Slot(bool)
    def load_previous_urls(self, _=False):
        urls = self.url_toolbar.get_previous_urls()
        self.load_db_urls({url: None for url in urls}, update_history=False)

    @Slot(bool)
    def load_next_urls(self, _=False):
        urls = self.url_toolbar.get_next_urls()
        self.load_db_urls({url: None for url in urls}, update_history=False)

    @Slot(bool)
    def open_db_file(self, _=False):
        self.qsettings.beginGroup(self.settings_group)
        file_path, _ = get_open_file_name_in_last_dir(
            self.qsettings, "openSQLiteUrl", self, "Open SQLite file", self._get_base_dir(), "SQLite (*.sqlite)"
        )
        self.qsettings.endGroup()
        if not file_path:
            return
        url = "sqlite:///" + file_path
        self.load_db_urls({url: None})

    @Slot(bool)
    def add_db_file(self, _=False):
        self.qsettings.beginGroup(self.settings_group)
        file_path, _ = get_open_file_name_in_last_dir(
            self.qsettings, "addSQLiteUrl", self, "Add SQLite file", self._get_base_dir(), "SQLite (*.sqlite)"
        )
        self.qsettings.endGroup()
        if not file_path:
            return
        url = "sqlite:///" + file_path
        db_url_codenames = self.db_url_codenames
        db_url_codenames[url] = None
        self.load_db_urls(db_url_codenames)

    @Slot(bool)
    def create_db_file(self, _=False):
        self.qsettings.beginGroup(self.settings_group)
        file_path, _ = get_save_file_name_in_last_dir(
            self.qsettings, "createSQLiteUrl", self, "Create SQLite file", self._get_base_dir(), "SQLite (*.sqlite)"
        )
        self.qsettings.endGroup()
        if not file_path:
            return
        try:
            os.remove(file_path)
        except OSError:
            pass
        url = "sqlite:///" + file_path
        self.load_db_urls({url: None}, create=True)

    def _make_docks_menu(self):
        """Returns a menu with all dock toggle/view actions. Called by ``self.add_main_menu()``.

        Returns:
            QMenu
        """
        menu = QMenu(self)
        menu.addAction(self.ui.dockWidget_object_tree.toggleViewAction())
        menu.addAction(self.ui.dockWidget_relationship_tree.toggleViewAction())
        menu.addSeparator()
        menu.addAction(self.ui.dockWidget_object_parameter_value.toggleViewAction())
        menu.addAction(self.ui.dockWidget_object_parameter_definition.toggleViewAction())
        menu.addAction(self.ui.dockWidget_relationship_parameter_value.toggleViewAction())
        menu.addAction(self.ui.dockWidget_relationship_parameter_definition.toggleViewAction())
        menu.addSeparator()
        menu.addAction(self.ui.dockWidget_pivot_table.toggleViewAction())
        menu.addAction(self.ui.dockWidget_frozen_table.toggleViewAction())
        menu.addSeparator()
        menu.addAction(self.ui.dockWidget_entity_graph.toggleViewAction())
        menu.addSeparator()
        menu.addAction(self.ui.dockWidget_tool_feature_tree.toggleViewAction())
        menu.addAction(self.ui.dockWidget_parameter_value_list.toggleViewAction())
        menu.addAction(self.ui.dockWidget_alternative_scenario_tree.toggleViewAction())
        menu.addSeparator()
        menu.addAction(self.ui.dockWidget_exports.toggleViewAction())
        return menu

    def add_main_menu(self):
        """Adds a menu with main actions to toolbar."""
        menu = MainMenu(self)
        file_action = ToolBarWidgetAction("File", menu)
        file_action.tool_bar.addActions(
            [self.ui.actionNew_db_file, self.ui.actionOpen_db_file, self.ui.actionAdd_db_file]
        )
        file_action.tool_bar.addSeparator()
        file_action.tool_bar.addActions([self.ui.actionImport, self.ui.actionExport, self.ui.actionExport_session])
        edit_action = ToolBarWidgetAction("Edit", menu)
        edit_action.tool_bar.addActions([self.ui.actionUndo, self.ui.actionRedo])
        edit_action.tool_bar.addSeparator()
        edit_action.tool_bar.addActions([self.ui.actionCopy, self.ui.actionPaste])
        edit_action.tool_bar.addSeparator()
        edit_action.tool_bar.addAction(self.ui.actionMass_remove_items)
        view_action = ToolBarWidgetAction("View", menu)
        view_action.tool_bar.addActions([self.ui.actionStacked_style, self.ui.actionGraph_style])
        pivot_actions = self.pivot_action_group.actions()
        view_action.tool_bar.addActions(pivot_actions)
        view_action.tool_bar.add_frame(pivot_actions[0], pivot_actions[-1], "Pivot table")
        view_action.tool_bar.addSeparator()
        docks_menu_action = view_action.tool_bar.addAction(QIcon(CharIconEngine("\uf2d0")), "Doc&ks...")
        docks_menu = self._make_docks_menu()
        docks_menu_action.setMenu(docks_menu)
        docks_menu_button = view_action.tool_bar.widgetForAction(docks_menu_action)
        docks_menu_button.setPopupMode(docks_menu_button.InstantPopup)
        session_action = ToolBarWidgetAction("Session", menu)
        session_action.tool_bar.addActions([self.ui.actionCommit, self.ui.actionRollback])
        session_action.tool_bar.addSeparator()
        session_action.tool_bar.addAction(self.ui.actionView_history)
        menu.addAction(file_action)
        menu.addSeparator()
        menu.addAction(edit_action)
        menu.addSeparator()
        menu.addAction(view_action)
        menu.addSeparator()
        menu.addAction(session_action)
        menu.addSeparator()
        menu.addAction(self.ui.actionUser_guide)
        menu.addAction(self.ui.actionSettings)
        menu.aboutToShow.connect(self.refresh_copy_paste_actions)
        menu_action = self.url_toolbar.add_main_menu(menu)
        actions = [
            self.ui.actionNew_db_file,
            self.ui.actionOpen_db_file,
            self.ui.actionAdd_db_file,
            self.ui.actionImport,
            self.ui.actionExport,
            self.ui.actionExport_session,
            self.ui.actionUndo,
            self.ui.actionRedo,
            self.ui.actionCopy,
            self.ui.actionPaste,
            self.ui.actionStacked_style,
            self.ui.actionGraph_style,
            *docks_menu.actions(),
            *self.pivot_action_group.actions(),
            self.ui.actionCommit,
            self.ui.actionRollback,
            self.ui.actionView_history,
        ]
        for action in actions:
            action.triggered.connect(menu.hide)
        # Add actions to activate shortcuts
        self.addActions([menu_action, *actions])

    def connect_signals(self):
        """Connects signals to slots."""
        # Message signals
        self.msg.connect(self.add_message)
        self.link_msg.connect(self.add_link_msg)
        self.msg_error.connect(self.err_msg.showMessage)
        # Menu actions
        self.ui.actionCommit.triggered.connect(self.commit_session)
        self.ui.actionRollback.triggered.connect(self.rollback_session)
        self.ui.actionView_history.triggered.connect(self.show_history_dialog)
        self.ui.actionClose.triggered.connect(self.close)
        self.ui.actionNew_db_file.triggered.connect(self.create_db_file)
        self.ui.actionOpen_db_file.triggered.connect(self.open_db_file)
        self.ui.actionAdd_db_file.triggered.connect(self.add_db_file)
        self.ui.actionImport.triggered.connect(self.import_file)
        self.ui.actionExport.triggered.connect(self.show_mass_export_items_dialog)
        self.ui.actionExport_session.triggered.connect(self.export_session)
        self.ui.actionCopy.triggered.connect(self.copy)
        self.ui.actionPaste.triggered.connect(self.paste)
        self.ui.actionMass_remove_items.triggered.connect(self.show_mass_remove_items_form)

    @Slot(int)
    def update_undo_redo_actions(self, index):
        undo_db_map = max(self.db_maps, key=lambda db_map: self.db_mngr.undo_stack[db_map].undo_age)
        redo_db_map = max(self.db_maps, key=lambda db_map: self.db_mngr.undo_stack[db_map].redo_age)
        new_undo_action = self.db_mngr.undo_action[undo_db_map]
        new_redo_action = self.db_mngr.redo_action[redo_db_map]
        self._replace_undo_redo_actions(new_undo_action, new_redo_action)

    def _replace_undo_redo_actions(self, new_undo_action, new_redo_action):
        if new_undo_action != self.undo_action:
            if self.undo_action:
                self.ui.actionUndo.triggered.disconnect(self.undo_action.triggered)
            self.ui.actionUndo.triggered.connect(new_undo_action.triggered)
            self.undo_action = new_undo_action
        if new_redo_action != self.redo_action:
            if self.redo_action:
                self.ui.actionRedo.triggered.disconnect(self.redo_action.triggered)
            self.ui.actionRedo.triggered.connect(new_redo_action.triggered)
            self.redo_action = new_redo_action
        QTimer.singleShot(0, self._refresh_undo_redo_actions)

    @Slot()
    def _refresh_undo_redo_actions(self):
        self.ui.actionUndo.setEnabled(self.undo_action.isEnabled())
        self.ui.actionUndo.setToolTip(f"<p>{self.undo_action.text()}")
        self.ui.actionRedo.setEnabled(self.redo_action.isEnabled())
        self.ui.actionRedo.setToolTip(f"<p>{self.redo_action.text()}")

    @Slot(bool)
    def update_commit_enabled(self, _clean=False):
        dirty = not all(self.db_mngr.undo_stack[db_map].isClean() for db_map in self.db_maps)
        self.ui.actionExport_session.setEnabled(dirty)
        self.ui.actionCommit.setEnabled(dirty)
        self.ui.actionRollback.setEnabled(dirty)
        self.ui.actionView_history.setEnabled(dirty)
        self.setWindowModified(dirty)
        self.windowTitleChanged.emit(self.windowTitle())

    @Slot(bool)
    def show_history_dialog(self, checked=False):
        dialog = DBSessionHistoryDialog(self, self.db_mngr, *self.db_maps)
        dialog.show()

    def init_models(self):
        """Initializes models."""

    @Slot(str)
    def add_message(self, msg):
        """Pushes message to notification stack.

        Args:
            msg (str): String to show in the notification
        """
        if self.silenced:
            return
        self.notification_stack.push(msg)

    @Slot(str, object)
    def add_link_msg(self, msg, open_link=None):
        """Pushes link message to notification stack.

        Args:
            msg (str): String to show in notification
            open_link (Callable, optional): callback to invoke when notification's link is opened
        """
        if self.silenced:
            return
        self.notification_stack.push_link(msg, open_link=open_link)

    @Slot()
    def refresh_copy_paste_actions(self):
        """Runs when menus are about to show.
        Enables or disables actions according to selection status."""
        self.ui.actionCopy.setEnabled(bool(call_on_focused_widget(self, "can_copy")))
        self.ui.actionPaste.setEnabled(bool(call_on_focused_widget(self, "can_paste")))

    @Slot(bool)
    def copy(self, checked=False):
        """Copies data to clipboard."""
        call_on_focused_widget(self, "copy")

    @Slot(bool)
    def paste(self, checked=False):
        """Pastes data from clipboard."""
        call_on_focused_widget(self, "paste")

    @Slot(dict)
    def import_data(self, data):
        self.db_mngr.import_data({db_map: data for db_map in self.db_maps})

    @Slot(bool)
    def import_file(self, checked=False):
        """Import file. It supports SQLite, JSON, and Excel."""
        self.qsettings.beginGroup(self.settings_group)
        file_path, selected_filter = get_open_file_name_in_last_dir(
            self.qsettings,
            "importFileIntoDB",
            self,
            "Import file",
            self._get_base_dir(),
            "SQLite (*.sqlite);; JSON file (*.json);; Excel file (*.xlsx)",
        )
        self.qsettings.endGroup()
        if not file_path:  # File selection cancelled
            return
        if selected_filter.startswith("JSON"):
            self.import_from_json(file_path)
        elif selected_filter.startswith("SQLite"):
            self.import_from_sqlite(file_path)
        elif selected_filter.startswith("Excel"):
            self.import_from_excel(file_path)
        else:
            raise ValueError()

    def import_from_json(self, file_path):
        with open(file_path) as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as err:
                self.msg_error.emit(f"File {file_path} is not a valid json: {err}")
                return
        self.import_data(data)
        filename = os.path.split(file_path)[1]
        self.msg.emit(f"File {filename} successfully imported.")

    def import_from_sqlite(self, file_path):
        url = URL("sqlite", database=file_path)
        filename = os.path.split(file_path)[1]
        try:
            db_map = DatabaseMapping(url)
        except (SpineDBAPIError, SpineDBVersionError) as err:
            self.msg.emit(f"Couldn't import file {filename}: {str(err)}")
            return
        data = export_data(db_map)
        self.import_data(data)
        self.msg.emit(f"File {filename} successfully imported.")

    def import_from_excel(self, file_path):
        filename = os.path.split(file_path)[1]
        try:
            mapped_data, errors = get_mapped_data_from_xlsx(file_path)
        except Exception as err:  # pylint: disable=broad-except
            self.msg.emit(f"Couldn't import file {filename}: {str(err)}")
            raise err  # NOTE: This is so the programmer gets to see the traceback
        if errors:
            msg = f"The following errors where found parsing {filename}:" + format_string_list(errors)
            self.msg_error.emit(msg)
        self.import_data(mapped_data)
        self.msg.emit(f"File {filename} successfully imported.")

    @Slot(bool)
    def show_mass_export_items_dialog(self, checked=False):
        """Shows dialog for user to select dbs and items for export."""
        dialog = MassExportItemsDialog(self, self.db_mngr, *self.db_maps)
        dialog.data_submitted.connect(self.mass_export_items)
        dialog.show()

    @Slot(bool)
    def export_session(self, checked=False):
        """Exports changes made in the current session as reported by DiffDatabaseMapping.
        """
        db_map_diff_ids = {db_map: db_map.diff_ids() for db_map in self.db_maps}
        db_map_obj_cls_ids = {db_map: diff_ids["object_class"] for db_map, diff_ids in db_map_diff_ids.items()}
        db_map_rel_cls_ids = {db_map: diff_ids["relationship_class"] for db_map, diff_ids in db_map_diff_ids.items()}
        db_map_obj_ids = {db_map: diff_ids["object"] for db_map, diff_ids in db_map_diff_ids.items()}
        db_map_rel_ids = {db_map: diff_ids["relationship"] for db_map, diff_ids in db_map_diff_ids.items()}
        db_map_par_val_lst_ids = {
            db_map: diff_ids["parameter_value_list"] for db_map, diff_ids in db_map_diff_ids.items()
        }
        db_map_par_def_ids = {db_map: diff_ids["parameter_definition"] for db_map, diff_ids in db_map_diff_ids.items()}
        db_map_par_val_ids = {db_map: diff_ids["parameter_value"] for db_map, diff_ids in db_map_diff_ids.items()}
        db_map_ent_group_ids = {db_map: diff_ids["entity_group"] for db_map, diff_ids in db_map_diff_ids.items()}
        parcel = SpineDBParcel(self.db_mngr)
        parcel.push_object_class_ids(db_map_obj_cls_ids)
        parcel.push_object_ids(db_map_obj_ids)
        parcel.push_relationship_class_ids(db_map_rel_cls_ids)
        parcel.push_relationship_ids(db_map_rel_ids)
        parcel.push_parameter_definition_ids(db_map_par_def_ids, "object")
        parcel.push_parameter_definition_ids(db_map_par_def_ids, "relationship")
        parcel.push_parameter_value_ids(db_map_par_val_ids, "object")
        parcel.push_parameter_value_ids(db_map_par_val_ids, "relationship")
        parcel.push_parameter_value_list_ids(db_map_par_val_lst_ids)
        parcel.push_object_group_ids(db_map_ent_group_ids)
        self.export_data(parcel.data)

    def mass_export_items(self, db_map_item_types):
        def _ids(t, types):
            return Asterisk if t in types else ()

        db_map_obj_cls_ids = {db_map: _ids("object_class", types) for db_map, types in db_map_item_types.items()}
        db_map_rel_cls_ids = {db_map: _ids("relationship_class", types) for db_map, types in db_map_item_types.items()}
        db_map_obj_ids = {db_map: _ids("object", types) for db_map, types in db_map_item_types.items()}
        db_map_rel_ids = {db_map: _ids("relationship", types) for db_map, types in db_map_item_types.items()}
        db_map_par_val_lst_ids = {
            db_map: _ids("parameter_value_list", types) for db_map, types in db_map_item_types.items()
        }
        db_map_par_def_ids = {
            db_map: _ids("parameter_definition", types) for db_map, types in db_map_item_types.items()
        }
        db_map_par_val_ids = {db_map: _ids("parameter_value", types) for db_map, types in db_map_item_types.items()}
        db_map_ent_group_ids = {db_map: _ids("entity_group", types) for db_map, types in db_map_item_types.items()}
        db_map_alt_ids = {db_map: _ids("alternative", types) for db_map, types in db_map_item_types.items()}
        db_map_scen_ids = {db_map: _ids("scenario", types) for db_map, types in db_map_item_types.items()}
        db_map_scen_alt_ids = {
            db_map: _ids("scenario_alternative", types) for db_map, types in db_map_item_types.items()
        }
        db_map_feat_ids = {db_map: _ids("feature", types) for db_map, types in db_map_item_types.items()}
        db_map_tool_ids = {db_map: _ids("tool", types) for db_map, types in db_map_item_types.items()}
        db_map_tool_feat_ids = {db_map: _ids("tool_feature", types) for db_map, types in db_map_item_types.items()}
        db_map_tool_feat_meth_ids = {
            db_map: _ids("tool_feature_method", types) for db_map, types in db_map_item_types.items()
        }
        parcel = SpineDBParcel(self.db_mngr)
        parcel.push_object_class_ids(db_map_obj_cls_ids)
        parcel.push_object_ids(db_map_obj_ids)
        parcel.push_relationship_class_ids(db_map_rel_cls_ids)
        parcel.push_relationship_ids(db_map_rel_ids)
        parcel.push_parameter_definition_ids(db_map_par_def_ids, "object")
        parcel.push_parameter_definition_ids(db_map_par_def_ids, "relationship")
        parcel.push_parameter_value_ids(db_map_par_val_ids, "object")
        parcel.push_parameter_value_ids(db_map_par_val_ids, "relationship")
        parcel.push_parameter_value_list_ids(db_map_par_val_lst_ids)
        parcel.push_object_group_ids(db_map_ent_group_ids)
        parcel.push_alternative_ids(db_map_alt_ids)
        parcel.push_scenario_ids(db_map_scen_ids)
        parcel.push_scenario_alternative_ids(db_map_scen_alt_ids)
        parcel.push_feature_ids(db_map_feat_ids)
        parcel.push_tool_ids(db_map_tool_ids)
        parcel.push_tool_feature_ids(db_map_tool_feat_ids)
        parcel.push_tool_feature_method_ids(db_map_tool_feat_meth_ids)
        self.export_data(parcel.data)

    @Slot(object)
    def export_data(self, db_map_ids_for_export):
        """Exports data from given dictionary into a file.

        Args:
            db_map_ids_for_export: Dictionary mapping db maps to keyword arguments for spinedb_api.export_data
        """
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        self.qsettings.beginGroup(self.settings_group)
        file_path, file_filter = get_save_file_name_in_last_dir(
            self.qsettings,
            "exportDB",
            self,
            "Export file",
            self._get_base_dir(),
            "SQLite (*.sqlite);; JSON file (*.json);; Excel file (*.xlsx)",
        )
        self.qsettings.endGroup()
        if not file_path:  # File selection cancelled
            return
        self.db_mngr.export_data(self, db_map_ids_for_export, file_path, file_filter)

    @staticmethod
    def _parse_db_map_metadata(db_map_metadata):
        s = "<ul>"
        for db_map_name, element_metadata in db_map_metadata.items():
            s += f"<li>{db_map_name}<ul>"
            for element_name, metadata in element_metadata.items():
                s += f"<li>{element_name}<ul>"
                for name, value in metadata.items():
                    s += f"<li>{name}: {value}</li>"
                s += "</ul>"
            s += "</ul>"
        s += "</ul>"
        return s

    def show_db_map_entity_metadata(self, db_map_ids):
        metadata = {
            db_map.codename: self.db_mngr.get_metadata_per_entity(db_map, entity_ids)
            for db_map, entity_ids in db_map_ids.items()
        }
        QMessageBox.information(self, "Entity metadata", self._parse_db_map_metadata(metadata))

    def show_db_map_parameter_value_metadata(self, db_map_ids):
        metadata = {
            db_map.codename: self.db_mngr.get_metadata_per_parameter_value(db_map, param_val_ids)
            for db_map, param_val_ids in db_map_ids.items()
        }
        QMessageBox.information(self, "Parameter value metadata", self._parse_db_map_metadata(metadata))

    @Slot(bool)
    def refresh_session(self, checked=False):
        self.db_mngr.refresh_session(*self.db_maps)

    @Slot(bool)
    def commit_session(self, checked=False):
        """Commits dirty database maps."""
        dirty_db_maps = self.db_mngr.dirty(*self.db_maps)
        if not dirty_db_maps:
            return
        db_names = ", ".join([db_map.codename for db_map in dirty_db_maps])
        commit_msg = self._get_commit_msg(db_names)
        if not commit_msg:
            return
        self.db_mngr.commit_session(commit_msg, *dirty_db_maps, cookie=self)

    @Slot(bool)
    def rollback_session(self, checked=False):
        """Rolls back dirty datbase maps."""
        dirty_db_maps = self.db_mngr.dirty(*self.db_maps)
        if not dirty_db_maps:
            return
        db_names = ", ".join([db_map.codename for db_map in dirty_db_maps])
        if not self._get_rollback_confirmation(db_names):
            return
        self.db_mngr.rollback_session(*dirty_db_maps)

    def receive_session_committed(self, db_maps, cookie):
        db_maps = set(self.db_maps) & set(db_maps)
        if not db_maps:
            return
        db_names = ", ".join([x.codename for x in db_maps])
        if cookie is self:
            msg = f"All changes in {db_names} committed successfully."
            self.msg.emit(msg)
            return
        # Commit done by an 'outside force'.
        self.init_models()
        self.msg.emit(f"Databases {db_names} reloaded from an external action.")

    def receive_session_rolled_back(self, db_maps):
        db_maps = set(self.db_maps) & set(db_maps)
        if not db_maps:
            return
        self.init_models()
        db_names = ", ".join([x.codename for x in db_maps])
        msg = f"All changes in {db_names} rolled back successfully."
        self.msg.emit(msg)

    def receive_session_refreshed(self, db_maps):
        db_maps = set(self.db_maps) & set(db_maps)
        if not db_maps:
            return
        self.init_models()
        self.msg.emit("Session refreshed.")

    @Slot(bool)
    def show_mass_remove_items_form(self, checked=False):
        dialog = MassRemoveItemsDialog(self, self.db_mngr, *self.db_maps)
        dialog.show()

    @busy_effect
    @Slot(QModelIndex)
    def show_parameter_value_editor(self, index, plain=False):
        """Shows the parameter_value editor for the given index of given table view.
        """
        editor = ParameterValueEditor(index, parent=self, plain=plain)
        editor.show()

    def receive_error_msg(self, db_map_error_log):
        msgs = []
        for db_map, error_log in db_map_error_log.items():
            if isinstance(error_log, str):
                error_log = [error_log]
            msg = "From " + db_map.codename + ":" + format_string_list(error_log)
            msgs.append(msg)
        self.msg_error.emit(format_string_list(msgs))

    def log_changes(self, action, item_type, db_map_data):
        """Enables or disables actions and informs the user about what just happened."""
        count = sum(len(data) for data in db_map_data.values())
        msg = f"Successfully {action} {count} {item_type} item(s)"
        self._changelog.append(msg)

    def receive_scenarios_added(self, db_map_data):
        self.log_changes("added", "scenario", db_map_data)

    def receive_alternatives_added(self, db_map_data):
        self.log_changes("added", "alternative", db_map_data)

    def receive_object_classes_added(self, db_map_data):
        self.log_changes("added", "object_class", db_map_data)

    def receive_objects_added(self, db_map_data):
        self.log_changes("added", "object", db_map_data)

    def receive_relationship_classes_added(self, db_map_data):
        self.log_changes("added", "relationship_class", db_map_data)

    def receive_relationships_added(self, db_map_data):
        self.log_changes("added", "relationship", db_map_data)

    def receive_entity_groups_added(self, db_map_data):
        self.log_changes("added", "entity_group", db_map_data)

    def receive_parameter_definitions_added(self, db_map_data):
        self.log_changes("added", "parameter_definition", db_map_data)

    def receive_parameter_values_added(self, db_map_data):
        self.log_changes("added", "parameter_value", db_map_data)

    def receive_parameter_value_lists_added(self, db_map_data):
        self.log_changes("added", "parameter_value_list", db_map_data)

    def receive_features_added(self, db_map_data):
        self.log_changes("added", "feature", db_map_data)

    def receive_tools_added(self, db_map_data):
        self.log_changes("added", "tool", db_map_data)

    def receive_tool_features_added(self, db_map_data):
        self.log_changes("added", "tool_feature", db_map_data)

    def receive_tool_feature_methods_added(self, db_map_data):
        self.log_changes("added", "tool_feature_method", db_map_data)

    def receive_scenarios_updated(self, db_map_data):
        self.log_changes("updated", "scenario", db_map_data)

    def receive_alternatives_updated(self, db_map_data):
        self.log_changes("updated", "alternative", db_map_data)

    def receive_object_classes_updated(self, db_map_data):
        self.log_changes("updated", "object_class", db_map_data)

    def receive_objects_updated(self, db_map_data):
        self.log_changes("updated", "object", db_map_data)

    def receive_relationship_classes_updated(self, db_map_data):
        self.log_changes("updated", "relationship_class", db_map_data)

    def receive_relationships_updated(self, db_map_data):
        self.log_changes("updated", "relationship", db_map_data)

    def receive_parameter_definitions_updated(self, db_map_data):
        self.log_changes("updated", "parameter_definition", db_map_data)

    def receive_parameter_values_updated(self, db_map_data):
        self.log_changes("updated", "parameter_value", db_map_data)

    def receive_parameter_value_lists_updated(self, db_map_data):
        self.log_changes("updated", "parameter_value_list", db_map_data)

    def receive_features_updated(self, db_map_data):
        self.log_changes("updated", "feature", db_map_data)

    def receive_tools_updated(self, db_map_data):
        self.log_changes("updated", "tool", db_map_data)

    def receive_tool_features_updated(self, db_map_data):
        self.log_changes("updated", "tool_feature", db_map_data)

    def receive_tool_feature_methods_updated(self, db_map_data):
        self.log_changes("updated", "tool_feature_method", db_map_data)

    def receive_scenarios_removed(self, db_map_data):
        self.log_changes("removed", "scenarios", db_map_data)

    def receive_alternatives_removed(self, db_map_data):
        self.log_changes("removed", "alternatives", db_map_data)

    def receive_object_classes_removed(self, db_map_data):
        self.log_changes("removed", "object_class", db_map_data)

    def receive_objects_removed(self, db_map_data):
        self.log_changes("removed", "object", db_map_data)

    def receive_relationship_classes_removed(self, db_map_data):
        self.log_changes("removed", "relationship_class", db_map_data)

    def receive_relationships_removed(self, db_map_data):
        self.log_changes("removed", "relationship", db_map_data)

    def receive_entity_groups_removed(self, db_map_data):
        self.log_changes("removed", "entity_group", db_map_data)

    def receive_parameter_definitions_removed(self, db_map_data):
        self.log_changes("removed", "parameter_definition", db_map_data)

    def receive_parameter_values_removed(self, db_map_data):
        self.log_changes("removed", "parameter_value", db_map_data)

    def receive_parameter_value_lists_removed(self, db_map_data):
        self.log_changes("removed", "parameter_value_list", db_map_data)

    def receive_features_removed(self, db_map_data):
        self.log_changes("removed", "feature", db_map_data)

    def receive_tools_removed(self, db_map_data):
        self.log_changes("removed", "tool", db_map_data)

    def receive_tool_features_removed(self, db_map_data):
        self.log_changes("removed", "tool_feature", db_map_data)

    def receive_tool_feature_methods_removed(self, db_map_data):
        self.log_changes("removed", "tool_feature_method", db_map_data)

    def restore_ui(self):
        """Restore UI state from previous session."""
        self.qsettings.beginGroup(self.settings_group)
        self.qsettings.beginGroup(self.settings_subgroup)
        window_state = self.qsettings.value("windowState")
        self.qsettings.endGroup()
        self.qsettings.endGroup()
        if window_state:
            self.restoreState(window_state, version=1)  # Toolbar and dockWidget positions

    def save_window_state(self):
        """Save window state parameters (size, position, state) via QSettings."""
        self.qsettings.beginGroup(self.settings_group)
        self.qsettings.beginGroup(self.settings_subgroup)
        self.qsettings.setValue("windowState", self.saveState(version=1))
        self.qsettings.endGroup()
        self.qsettings.endGroup()

    def tear_down(self):
        """Performs clean up duties.

        Returns:
            bool: True if editor is ready to close, False otherwise
        """
        dirty_or_orphan = self.db_mngr.dirty_or_orphan(self, *self.db_maps)
        commit_dirty = False
        commit_msg = ""
        if dirty_or_orphan:
            answer = self._prompt_to_commit_changes()
            if answer == QMessageBox.Cancel:
                return False
            db_names = ", ".join([db_map.codename for db_map in dirty_or_orphan])
            if answer == QMessageBox.Save:
                commit_dirty = True
                commit_msg = self._get_commit_msg(db_names)
                if not commit_msg:
                    return False
        self.db_mngr.unregister_listener(self, commit_dirty, commit_msg, *self.db_maps)
        self.save_window_state()
        return True

    def _prompt_to_commit_changes(self):
        """Prompts the user to commit or rollback changes to 'dirty' db maps.

        Returns:
            int: QMessageBox status code
        """
        commit_at_exit = int(self.qsettings.value("appSettings/commitAtExit", defaultValue="1"))
        if commit_at_exit == 0:
            # Don't commit session and don't show message box
            return QMessageBox.Discard
        if commit_at_exit == 1:  # Default
            # Show message box
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle(self.windowTitle())
            msg.setText("The current session has uncommitted changes. Do you want to commit them now?")
            msg.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            msg.button(QMessageBox.Save).setText("Commit and close ")
            msg.button(QMessageBox.Discard).setText("Discard changes and close")
            chkbox = QCheckBox()
            chkbox.setText("Do not ask me again")
            msg.setCheckBox(chkbox)
            answer = msg.exec_()
            if answer != QMessageBox.Cancel and chkbox.checkState() == 2:
                # Save preference
                preference = "2" if answer == QMessageBox.Save else "0"
                self.qsettings.setValue("appSettings/commitAtExit", preference)
            return answer
        if commit_at_exit == 2:
            # Commit session and don't show message box
            return QMessageBox.Save

    def _get_commit_msg(self, db_names):
        """Prompts user for commit message.

        Args:
            db_names (Iterable of str): database names

        Returns:
            str: commit message
        """
        dialog = CommitDialog(self, db_names)
        answer = dialog.exec_()
        if answer == QDialog.Accepted:
            return dialog.commit_msg

    def _get_rollback_confirmation(self, db_names):
        """Prompts user for confirmation before rolling back the session.

        Args:
            db_names (Iterable of str): database names

        Returns:
            bool: True if user confirmed, False otherwise
        """
        message_box = QMessageBox(
            QMessageBox.Question,
            f"Rollback changes in {db_names}",
            "Are you sure? "
            "All your changes since the last commit will be reverted and removed from the undo/redo stack.",
            QMessageBox.Ok | QMessageBox.Cancel,
            parent=self,
        )
        message_box.button(QMessageBox.Ok).setText("Rollback")
        answer = message_box.exec_()
        return answer == QMessageBox.Ok

    def closeEvent(self, event):
        """Handle close window.

        Args:
            event (QCloseEvent): Closing event
        """
        if not self.tear_down():
            event.ignore()
            return
        super().closeEvent(event)

    def scenario_items(self, db_map):
        """Gathers scenario items from alternative scenario tree for given database.

        Args:
            db_map (DiffDatabaseMapping): database map

        Returns:
            list of CachedItem: scenario items
        """
        model = self.ui.treeView_alternative_scenario.model()
        db_index = None
        for row in range(model.rowCount()):
            db_index = model.index(row, 0)
            item = model.item_from_index(db_index)
            if item.db_map is db_map:
                break
        if db_index is None:
            raise RuntimeError("Database item not found in alternative/scenario model.")
        scenario_root_index = model.index(1, 0, db_index)
        return [
            model.item_from_index(model.index(row, 0, scenario_root_index))
            for row in range(model.rowCount(scenario_root_index))
        ]


class SpineDBEditor(TabularViewMixin, GraphViewMixin, ParameterViewMixin, TreeViewMixin, SpineDBEditorBase):
    """A widget to visualize Spine dbs."""

    def __init__(self, db_mngr, db_url_codenames=None):
        """Initializes everything.

        Args:
            db_mngr (SpineDBManager): The manager to use
        """
        super().__init__(db_mngr)
        self._original_size = None
        self._dock_views = {d: d.findChild(QAbstractScrollArea) for d in self.findChildren(QDockWidget)}
        self._timer_refresh_tab_order = QTimer(self)  # Used to limit refresh
        self._timer_refresh_tab_order.setSingleShot(True)
        self.add_main_menu()
        self.connect_signals()
        self.apply_stacked_style()
        if db_url_codenames is not None:
            self.load_db_urls(db_url_codenames)

    def connect_signals(self):
        super().connect_signals()
        self.ui.actionStacked_style.triggered.connect(self.apply_stacked_style)
        self.ui.actionGraph_style.triggered.connect(self.apply_graph_style)
        self.pivot_action_group.triggered.connect(self.apply_pivot_style)
        for dock in self._dock_views:
            dock.visibilityChanged.connect(self._restart_timer_refresh_tab_order)

    @Slot(bool)
    def _restart_timer_refresh_tab_order(self, _visible=False):
        self._timer_refresh_tab_order.timeout.connect(self._refresh_tab_order, Qt.UniqueConnection)
        self._timer_refresh_tab_order.start(100)

    @Slot()
    def _refresh_tab_order(self):
        self._timer_refresh_tab_order.timeout.disconnect(self._refresh_tab_order)
        visible_docks = []
        for dock, view in self._dock_views.items():
            if view is None:
                continue
            if dock.pos().x() >= 0 and not dock.isFloating():
                visible_docks.append(dock)
                view.setFocusPolicy(Qt.StrongFocus)
            else:
                view.setFocusPolicy(Qt.ClickFocus)
        if not visible_docks:
            return
        sorted_docks = sorted(visible_docks, key=lambda d: (d.pos().x(), d.pos().y()))
        tab_bars = {}
        for tab_bar in self.findChildren(QTabBar):
            i = tab_bar.currentIndex()
            if i != -1:
                tab_bars[tab_bar.tabText(i)] = tab_bar
        sorted_widgets = []
        for dock in sorted_docks:
            sorted_widgets.append(self._dock_views[dock])
            tab_bar = tab_bars.get(dock.windowTitle())
            if tab_bar is not None:
                sorted_widgets.append(tab_bar)
        self.setTabOrder(self.url_toolbar.line_edit, sorted_widgets[0])
        for first, second in zip(sorted_widgets[:-1], sorted_widgets[1:]):
            self.setTabOrder(first, second)

    def tabify_and_raise(self, docks):
        """
        Tabifies docks in given list, then raises the first.

        Args:
            docks (list)
        """
        for first, second in zip(docks[:-1], docks[1:]):
            self.tabifyDockWidget(first, second)
        docks[0].raise_()

    def restore_dock_widgets(self):
        """Docks all floating and or hidden QDockWidgets back to the window."""
        for dock in self._dock_views:
            dock.setFloating(False)
            dock.setVisible(True)
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def begin_style_change(self):
        """Begins a style change operation."""
        self._original_size = self.size()
        self.restore_dock_widgets()

    def end_style_change(self):
        """Ends a style change operation."""
        qApp.processEvents()  # pylint: disable=undefined-variable
        self.ui.dockWidget_exports.hide()
        self.resize(self._original_size)

    @Slot(bool)
    def apply_stacked_style(self, checked=False):
        """Applies the stacked style, inspired in the former tree view."""
        self.begin_style_change()
        self.splitDockWidget(self.ui.dockWidget_object_tree, self.ui.dockWidget_object_parameter_value, Qt.Horizontal)
        self.splitDockWidget(
            self.ui.dockWidget_object_parameter_value, self.ui.dockWidget_tool_feature_tree, Qt.Horizontal
        )
        self.splitDockWidget(self.ui.dockWidget_object_tree, self.ui.dockWidget_relationship_tree, Qt.Vertical)
        self.splitDockWidget(self.ui.dockWidget_tool_feature_tree, self.ui.dockWidget_parameter_value_list, Qt.Vertical)
        self.splitDockWidget(
            self.ui.dockWidget_parameter_value_list, self.ui.dockWidget_alternative_scenario_tree, Qt.Vertical
        )
        self.splitDockWidget(
            self.ui.dockWidget_object_parameter_value, self.ui.dockWidget_relationship_parameter_value, Qt.Vertical
        )
        self.tabify_and_raise(
            [self.ui.dockWidget_object_parameter_value, self.ui.dockWidget_object_parameter_definition]
        )
        self.tabify_and_raise(
            [self.ui.dockWidget_relationship_parameter_value, self.ui.dockWidget_relationship_parameter_definition]
        )
        self.ui.dockWidget_entity_graph.hide()
        self.ui.dockWidget_pivot_table.hide()
        self.ui.dockWidget_frozen_table.hide()
        docks = [
            self.ui.dockWidget_object_tree,
            self.ui.dockWidget_object_parameter_value,
            self.ui.dockWidget_parameter_value_list,
        ]
        width = sum(d.size().width() for d in docks)
        self.resizeDocks(docks, [0.2 * width, 0.6 * width, 0.2 * width], Qt.Horizontal)
        docks = [
            self.ui.dockWidget_tool_feature_tree,
            self.ui.dockWidget_parameter_value_list,
            self.ui.dockWidget_alternative_scenario_tree,
        ]
        height = sum(d.size().height() for d in docks)
        self.resizeDocks(docks, [0.3 * height, 0.3 * height, 0.4 * height], Qt.Vertical)
        self.end_style_change()

    @Slot(QAction)
    def apply_pivot_style(self, _action):
        """Applies the pivot style, inspired in the former tabular view."""
        self.begin_style_change()
        self.splitDockWidget(self.ui.dockWidget_object_tree, self.ui.dockWidget_pivot_table, Qt.Horizontal)
        self.splitDockWidget(self.ui.dockWidget_pivot_table, self.ui.dockWidget_frozen_table, Qt.Horizontal)
        self.splitDockWidget(self.ui.dockWidget_object_tree, self.ui.dockWidget_relationship_tree, Qt.Vertical)
        self.splitDockWidget(self.ui.dockWidget_frozen_table, self.ui.dockWidget_tool_feature_tree, Qt.Vertical)
        self.splitDockWidget(
            self.ui.dockWidget_tool_feature_tree, self.ui.dockWidget_alternative_scenario_tree, Qt.Vertical
        )
        self.ui.dockWidget_entity_graph.hide()
        self.ui.dockWidget_object_parameter_value.hide()
        self.ui.dockWidget_object_parameter_definition.hide()
        self.ui.dockWidget_relationship_parameter_value.hide()
        self.ui.dockWidget_relationship_parameter_definition.hide()
        self.ui.dockWidget_parameter_value_list.hide()
        docks = [self.ui.dockWidget_object_tree, self.ui.dockWidget_pivot_table, self.ui.dockWidget_frozen_table]
        width = sum(d.size().width() for d in docks)
        self.resizeDocks(docks, [0.2 * width, 0.6 * width, 0.2 * width], Qt.Horizontal)
        self.end_style_change()

    @Slot(bool)
    def apply_graph_style(self, checked=False):
        """Applies the graph style, inspired in the former graph view."""
        self.begin_style_change()
        self.ui.dockWidget_pivot_table.hide()
        self.ui.dockWidget_frozen_table.hide()
        self.splitDockWidget(self.ui.dockWidget_object_tree, self.ui.dockWidget_entity_graph, Qt.Horizontal)
        self.splitDockWidget(
            self.ui.dockWidget_entity_graph, self.ui.dockWidget_alternative_scenario_tree, Qt.Horizontal
        )
        self.splitDockWidget(self.ui.dockWidget_object_tree, self.ui.dockWidget_relationship_tree, Qt.Vertical)
        self.splitDockWidget(self.ui.dockWidget_entity_graph, self.ui.dockWidget_object_parameter_value, Qt.Vertical)
        self.splitDockWidget(
            self.ui.dockWidget_alternative_scenario_tree, self.ui.dockWidget_tool_feature_tree, Qt.Vertical
        )
        self.splitDockWidget(self.ui.dockWidget_tool_feature_tree, self.ui.dockWidget_parameter_value_list, Qt.Vertical)
        self.tabify_and_raise(
            [
                self.ui.dockWidget_object_parameter_value,
                self.ui.dockWidget_object_parameter_definition,
                self.ui.dockWidget_relationship_parameter_value,
                self.ui.dockWidget_relationship_parameter_definition,
            ]
        )
        docks = [
            self.ui.dockWidget_object_tree,
            self.ui.dockWidget_entity_graph,
            self.ui.dockWidget_parameter_value_list,
        ]
        width = sum(d.size().width() for d in docks)
        self.resizeDocks(docks, [0.2 * width, 0.6 * width, 0.2 * width], Qt.Horizontal)
        docks = [self.ui.dockWidget_entity_graph, self.ui.dockWidget_object_parameter_value]
        height = sum(d.size().height() for d in docks)
        self.resizeDocks(docks, [0.7 * height, 0.3 * height], Qt.Vertical)
        docks = [self.ui.dockWidget_alternative_scenario_tree, self.ui.dockWidget_parameter_value_list]
        height = sum(d.size().height() for d in docks)
        self.resizeDocks(docks, [0.5 * height, 0.5 * height], Qt.Vertical)
        self.end_style_change()
        self.ui.graphicsView.reset_zoom()

    @staticmethod
    def _get_base_dir():
        return APPLICATION_PATH

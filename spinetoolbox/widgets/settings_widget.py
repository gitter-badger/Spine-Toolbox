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
Widget for controlling user settings.

:author: P. Savolainen (VTT)
:date:   17.1.2018
"""

import os
from PySide2.QtWidgets import QWidget, QFileDialog, QColorDialog
from PySide2.QtCore import Slot, Qt, QSize, QSettings
from PySide2.QtGui import QPixmap, QIntValidator
from spine_engine.utils.helpers import (
    resolve_python_interpreter,
    resolve_julia_executable,
    resolve_gams_executable,
    resolve_conda_executable,
    get_julia_env,
)
from .notification import Notification
from .install_julia_wizard import InstallJuliaWizard
from .add_up_spine_opt_wizard import AddUpSpineOptWizard
from ..config import DEFAULT_WORK_DIR, SETTINGS_SS
from ..link import Link, JumpLink
from ..project_item_icon import ProjectItemIcon
from ..widgets.kernel_editor import (
    KernelEditor,
    MiniPythonKernelEditor,
    MiniJuliaKernelEditor,
    find_python_kernels,
    find_julia_kernels,
)
from ..helpers import (
    select_gams_executable,
    select_python_interpreter,
    select_julia_executable,
    select_julia_project,
    select_conda_executable,
    select_certificate_directory,
    file_is_valid,
    dir_is_valid,
    home_dir,
)


class SettingsWidgetBase(QWidget):
    def __init__(self, qsettings):
        """
        Args:
            qsettings (QSettings): Toolbox settings
        """
        # FIXME: setting the parent to toolbox causes the checkboxes in the
        # groupBox_general to not layout correctly, this might be caused elsewhere?
        from ..ui.settings import Ui_SettingsForm  # pylint: disable=import-outside-toplevel

        super().__init__(parent=None)  # Do not set parent. Uses own stylesheet.
        # Set up the ui from Qt Designer files
        self._qsettings = qsettings
        self.ui = Ui_SettingsForm()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint)
        self.setStyleSheet(SETTINGS_SS)
        self._mouse_press_pos = None
        self._mouse_release_pos = None
        self._mouse_move_pos = None

    @property
    def qsettings(self):
        return self._qsettings

    def connect_signals(self):
        """Connect signals."""
        self.ui.buttonBox.accepted.connect(self.save_and_close)
        self.ui.buttonBox.rejected.connect(self.update_ui_and_close)

    def keyPressEvent(self, e):
        """Close settings form when escape key is pressed.

        Args:
            e (QKeyEvent): Received key press event.
        """
        if e.key() == Qt.Key_Escape:
            self.update_ui_and_close()

    def mousePressEvent(self, e):
        """Save mouse position at the start of dragging.

        Args:
            e (QMouseEvent): Mouse event
        """
        self._mouse_press_pos = e.globalPos()
        self._mouse_move_pos = e.globalPos()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        """Save mouse position at the end of dragging.

        Args:
            e (QMouseEvent): Mouse event
        """
        if self._mouse_press_pos is not None:
            self._mouse_release_pos = e.globalPos()
            moved = self._mouse_release_pos - self._mouse_press_pos
            if moved.manhattanLength() > 3:
                e.ignore()
                return

    def mouseMoveEvent(self, e):
        """Moves the window when mouse button is pressed and mouse cursor is moved.

        Args:
            e (QMouseEvent): Mouse event
        """
        currentpos = self.pos()
        globalpos = e.globalPos()
        if not self._mouse_move_pos:
            e.ignore()
            return
        diff = globalpos - self._mouse_move_pos
        newpos = currentpos + diff
        self.move(newpos)
        self._mouse_move_pos = globalpos

    def update_ui(self):
        """Updates UI to reflect current settings. Called when the user choses to cancel their changes.
        Undoes all temporary UI changes that resulted from the user playing with certain settings."""

    # pylint: disable=no-self-use
    def save_settings(self):
        """Gets selections and saves them to persistent memory."""
        return True

    @Slot(bool)
    def update_ui_and_close(self, checked=False):
        """Updates UI to reflect current settings and close."""
        self.update_ui()
        self.close()

    @Slot(bool)
    def save_and_close(self, checked=False):
        """Saves settings and close."""
        if self.save_settings():
            self.close()


class SpineDBEditorSettingsMixin:
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.ui.checkBox_auto_expand_objects.clicked.connect(self.set_auto_expand_objects)
        self.ui.checkBox_merge_dbs.clicked.connect(self.set_merge_dbs)

    def read_settings(self):
        """Read saved settings from app QSettings instance and update UI to display them."""
        commit_at_exit = int(self._qsettings.value("appSettings/commitAtExit", defaultValue="1"))  # tri-state
        sticky_selection = self._qsettings.value("appSettings/stickySelection", defaultValue="false")
        smooth_zoom = self._qsettings.value("appSettings/smoothEntityGraphZoom", defaultValue="false")
        smooth_rotation = self._qsettings.value("appSettings/smoothEntityGraphRotation", defaultValue="false")
        relationship_items_follow = self._qsettings.value("appSettings/relationshipItemsFollow", defaultValue="true")
        auto_expand_objects = self._qsettings.value("appSettings/autoExpandObjects", defaultValue="true")
        merge_dbs = self._qsettings.value("appSettings/mergeDBs", defaultValue="true")
        db_editor_show_undo = int(self._qsettings.value("appSettings/dbEditorShowUndo", defaultValue="2"))
        if commit_at_exit == 0:  # Not needed but makes the code more readable.
            self.ui.checkBox_commit_at_exit.setCheckState(Qt.Unchecked)
        elif commit_at_exit == 1:
            self.ui.checkBox_commit_at_exit.setCheckState(Qt.PartiallyChecked)
        else:  # commit_at_exit == "2":
            self.ui.checkBox_commit_at_exit.setCheckState(Qt.Checked)
        self.ui.checkBox_object_tree_sticky_selection.setChecked(sticky_selection == "true")
        self.ui.checkBox_smooth_entity_graph_zoom.setChecked(smooth_zoom == "true")
        self.ui.checkBox_smooth_entity_graph_rotation.setChecked(smooth_rotation == "true")
        self.ui.checkBox_relationship_items_follow.setChecked(relationship_items_follow == "true")
        self.ui.checkBox_auto_expand_objects.setChecked(auto_expand_objects == "true")
        self.ui.checkBox_merge_dbs.setChecked(merge_dbs == "true")
        if db_editor_show_undo == 2:
            self.ui.checkBox_db_editor_show_undo.setChecked(True)

    def save_settings(self):
        """Get selections and save them to persistent memory."""
        if not super().save_settings():
            return False
        commit_at_exit = str(int(self.ui.checkBox_commit_at_exit.checkState()))
        self._qsettings.setValue("appSettings/commitAtExit", commit_at_exit)
        sticky_selection = "true" if int(self.ui.checkBox_object_tree_sticky_selection.checkState()) else "false"
        self._qsettings.setValue("appSettings/stickySelection", sticky_selection)
        smooth_zoom = "true" if int(self.ui.checkBox_smooth_entity_graph_zoom.checkState()) else "false"
        self._qsettings.setValue("appSettings/smoothEntityGraphZoom", smooth_zoom)
        smooth_rotation = "true" if int(self.ui.checkBox_smooth_entity_graph_rotation.checkState()) else "false"
        self._qsettings.setValue("appSettings/smoothEntityGraphRotation", smooth_rotation)
        relationship_items_follow = "true" if int(self.ui.checkBox_relationship_items_follow.checkState()) else "false"
        self._qsettings.setValue("appSettings/relationshipItemsFollow", relationship_items_follow)
        auto_expand_objects = "true" if int(self.ui.checkBox_auto_expand_objects.checkState()) else "false"
        self._qsettings.setValue("appSettings/autoExpandObjects", auto_expand_objects)
        merge_dbs = "true" if int(self.ui.checkBox_merge_dbs.checkState()) else "false"
        self._qsettings.setValue("appSettings/mergeDBs", merge_dbs)
        db_editor_show_undo = str(int(self.ui.checkBox_db_editor_show_undo.checkState()))
        self._qsettings.setValue("appSettings/dbEditorShowUndo", db_editor_show_undo)
        return True

    def update_ui(self):
        super().update_ui()
        auto_expand_objects = self._qsettings.value("appSettings/autoExpandObjects", defaultValue="true") == "true"
        merge_dbs = self._qsettings.value("appSettings/mergeDBs", defaultValue="true") == "true"
        self.set_auto_expand_objects(auto_expand_objects)
        self.set_merge_dbs(merge_dbs)

    @Slot(bool)
    def set_auto_expand_objects(self, checked=False):
        for db_editor in self.db_mngr.get_all_spine_db_editors():
            db_editor.ui.graphicsView.set_auto_expand_objects(checked)

    @Slot(bool)
    def set_merge_dbs(self, checked=False):
        for db_editor in self.db_mngr.get_all_spine_db_editors():
            db_editor.ui.graphicsView.set_merge_dbs(checked)


class SpineDBEditorSettingsWidget(SpineDBEditorSettingsMixin, SettingsWidgetBase):
    """A widget to change user's preferred settings, but only for the Spine db editor."""

    def __init__(self, multi_db_editor):
        """Initialize class."""
        super().__init__(multi_db_editor.qsettings)
        self._multi_db_editor = multi_db_editor
        self.ui.stackedWidget.setCurrentWidget(self.ui.SpineDBEditor)
        self.ui.listWidget.hide()
        self.connect_signals()

    def show(self):
        super().show()
        self.read_settings()

    @property
    def db_mngr(self):
        return self._multi_db_editor.db_mngr


class SettingsWidget(SpineDBEditorSettingsMixin, SettingsWidgetBase):
    """A widget to change user's preferred settings."""

    def __init__(self, toolbox):
        """
        Args:
            toolbox (ToolboxUI): Parent widget.
        """
        super().__init__(toolbox.qsettings())
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.listWidget.setFocus()
        self.ui.listWidget.setCurrentRow(0)
        self._toolbox = toolbox  # QWidget parent
        self._project = self._toolbox.project()
        self.orig_work_dir = ""  # Work dir when this widget was opened
        self._kernel_editor = None
        self._remote_host = ""
        # Initial scene bg color. Is overridden immediately in read_settings() if it exists in qSettings
        self.bg_color = self._toolbox.ui.graphicsView.scene().bg_color
        for item in self.ui.listWidget.findItems("*", Qt.MatchWildcard):
            item.setSizeHint(QSize(128, 44))
        # Ensure this window gets garbage-collected when closed
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.connect_signals()
        self.read_settings()
        self._update_python_widgets_enabled(self.ui.radioButton_use_python_jupyter_console.isChecked())
        self._update_julia_widgets_enabled(self.ui.radioButton_use_julia_jupyter_console.isChecked())
        self._update_remote_execution_page_widget_status(self.ui.checkBox_enable_remote_exec.isChecked())

    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.ui.toolButton_browse_gams.clicked.connect(self.browse_gams_button_clicked)
        self.ui.toolButton_browse_julia.clicked.connect(self.browse_julia_button_clicked)
        self.ui.toolButton_browse_julia_project.clicked.connect(self.browse_julia_project_button_clicked)
        self.ui.toolButton_browse_python.clicked.connect(self.browse_python_button_clicked)
        self.ui.toolButton_browse_conda.clicked.connect(self.browse_conda_button_clicked)
        self.ui.toolButton_pick_secfolder.clicked.connect(self.browse_certificate_directory_clicked)
        self.ui.pushButton_open_kernel_editor_python.clicked.connect(self.show_python_kernel_editor)
        self.ui.pushButton_open_kernel_editor_julia.clicked.connect(self.show_julia_kernel_editor)
        self.ui.toolButton_browse_work.clicked.connect(self.browse_work_path)
        self.ui.toolButton_bg_color.clicked.connect(self.show_color_dialog)
        self.ui.radioButton_bg_grid.clicked.connect(self.update_scene_bg)
        self.ui.radioButton_bg_tree.clicked.connect(self.update_scene_bg)
        self.ui.radioButton_bg_solid.clicked.connect(self.update_scene_bg)
        self.ui.checkBox_color_toolbar_icons.clicked.connect(self.set_toolbar_colored_icons)
        self.ui.checkBox_use_curved_links.clicked.connect(self.update_links_geometry)
        self.ui.checkBox_use_rounded_items.clicked.connect(self.update_items_path)
        self.ui.pushButton_install_julia.clicked.connect(self._show_install_julia_wizard)
        self.ui.pushButton_add_up_spine_opt.clicked.connect(self._show_add_up_spine_opt_wizard)
        self.ui.radioButton_use_python_jupyter_console.toggled.connect(self._update_python_widgets_enabled)
        self.ui.radioButton_use_julia_jupyter_console.toggled.connect(self._update_julia_widgets_enabled)
        self.ui.checkBox_enable_remote_exec.clicked.connect(self._update_remote_execution_page_widget_status)
        self.ui.lineEdit_host.textEdited.connect(self._edit_remote_host)
        self.ui.user_defined_engine_process_limit_radio_button.toggled.connect(
            self.ui.engine_process_limit_spin_box.setEnabled
        )
        self.ui.user_defined_persistent_process_limit_radio_button.toggled.connect(
            self.ui.persistent_process_limit_spin_box.setEnabled
        )

    @Slot(bool)
    def _update_python_widgets_enabled(self, state):
        # use_python_kernel = self.ui.radioButton_use_python_jupyter_console.isChecked()
        self.ui.comboBox_python_kernel.setEnabled(state)
        self.ui.pushButton_open_kernel_editor_python.setEnabled(state)
        self.ui.lineEdit_python_path.setEnabled(not state)
        self.ui.toolButton_browse_python.setEnabled(not state)

    @Slot(bool)
    def _update_julia_widgets_enabled(self, state):
        # use_julia_kernel = self.ui.radioButton_use_julia_jupyter_console.isChecked()
        self.ui.comboBox_julia_kernel.setEnabled(state)
        self.ui.pushButton_open_kernel_editor_julia.setEnabled(state)
        self.ui.lineEdit_julia_path.setEnabled(not state)
        self.ui.lineEdit_julia_project_path.setEnabled(not state)
        self.ui.toolButton_browse_julia.setEnabled(not state)
        self.ui.toolButton_browse_julia_project.setEnabled(not state)

    @Slot(bool)
    def _update_remote_execution_page_widget_status(self, state):
        """Enables or disables widgets on Remote Execution page,
        based on the state of remote execution enabled check box."""
        self.ui.lineEdit_host.setEnabled(state)
        self.ui.spinBox_port.setEnabled(state)
        self.ui.comboBox_security.setEnabled(state)
        self.ui.lineEdit_secfolder.setEnabled(state)
        self.ui.toolButton_pick_secfolder.setEnabled(state)

    def _show_install_julia_wizard(self):
        wizard = InstallJuliaWizard(self)
        wizard.julia_exe_selected.connect(self.ui.lineEdit_julia_path.setText)
        wizard.show()

    def _show_add_up_spine_opt_wizard(self):
        use_julia_jupyter_console, julia_path, julia_project_path, julia_kernel = self._get_julia_settings()
        settings = QSettings("SpineProject", "AddUpSpineOptWizard")
        settings.setValue("appSettings/useJuliaKernel", use_julia_jupyter_console)
        settings.setValue("appSettings/juliaPath", julia_path)
        settings.setValue("appSettings/juliaProjectPath", julia_project_path)
        settings.setValue("appSettings/juliaKernel", julia_kernel)
        julia_env = get_julia_env(settings)
        settings.deleteLater()
        if julia_env is None:
            julia_exe = julia_project = ""
        else:
            julia_exe, julia_project = julia_env
        wizard = AddUpSpineOptWizard(self, julia_exe, julia_project)
        wizard.show()

    @property
    def db_mngr(self):
        return self._toolbox.db_mngr

    @Slot(bool)
    def browse_gams_button_clicked(self, checked=False):
        """Calls static method that shows a file browser for selecting a Gams executable."""
        select_gams_executable(self, self.ui.lineEdit_gams_path)

    @Slot(bool)
    def browse_julia_button_clicked(self, checked=False):
        """Calls static method that shows a file browser for selecting a Julia path."""
        select_julia_executable(self, self.ui.lineEdit_julia_path)

    @Slot(bool)
    def browse_julia_project_button_clicked(self, checked=False):
        """Calls static method that shows a folder browser for selecting a Julia project."""
        select_julia_project(self, self.ui.lineEdit_julia_project_path)

    @Slot(bool)
    def browse_python_button_clicked(self, checked=False):
        """Calls static method that shows a file browser for selecting a Python interpreter."""
        select_python_interpreter(self, self.ui.lineEdit_python_path)

    @Slot(bool)
    def browse_conda_button_clicked(self, checked=False):
        """Calls static method that shows a file browser for selecting a Conda executable."""
        select_conda_executable(self, self.ui.lineEdit_conda_path)

    @Slot(bool)
    def browse_certificate_directory_clicked(self, _):
        """Calls static method that shows a file browser for selecting the security folder for Engine Server."""
        select_certificate_directory(self, self.ui.lineEdit_secfolder)

    @Slot(bool)
    def show_python_kernel_editor(self, checked=False):
        """Opens kernel editor, where user can make a kernel for the Python Console."""
        p = self.ui.lineEdit_python_path.text()  # This may be an empty string
        j = self.ui.lineEdit_julia_path.text()
        current_kernel = self.ui.comboBox_python_kernel.currentText()
        self._kernel_editor = KernelEditor(self, p, j, "python", current_kernel)
        self._kernel_editor.finished.connect(self.python_kernel_editor_closed)
        self._kernel_editor.open()

    @Slot(int)
    def python_kernel_editor_closed(self, ret_code):
        """Catches the selected Python kernel name when the editor is closed."""
        previous_python_kernel = self.ui.comboBox_python_kernel.currentText()
        self.ui.comboBox_python_kernel.clear()
        python_kernel_cb_items = ["Select Python kernel spec..."] + list(find_python_kernels())
        self.ui.comboBox_python_kernel.addItems(python_kernel_cb_items)
        if ret_code != 1:  # Editor closed with something else than clicking Ok.
            # Set previous kernel selected in Python kernel combobox if it still exists
            python_kernel_index = self.ui.comboBox_python_kernel.findText(previous_python_kernel)
            if python_kernel_index == -1:
                self.ui.comboBox_python_kernel.setCurrentIndex(0)  # Previous not found
            else:
                self.ui.comboBox_python_kernel.setCurrentIndex(python_kernel_index)
            return
        new_kernel = self._kernel_editor.selected_kernel
        index = self.ui.comboBox_python_kernel.findText(new_kernel)
        if index == -1:  # New kernel not found, should be quite exceptional
            notification = Notification(self, f"Python kernel spec {new_kernel} not found")
            notification.show()
            self.ui.comboBox_python_kernel.setCurrentIndex(0)
        else:
            self.ui.comboBox_python_kernel.setCurrentIndex(index)

    @Slot(bool)
    def show_julia_kernel_editor(self, checked=False):
        """Opens kernel editor, where user can make a kernel the Julia Console."""
        p = self.ui.lineEdit_python_path.text()  # This may be an empty string
        j = self.ui.lineEdit_julia_path.text()
        current_kernel = self.ui.comboBox_julia_kernel.currentText()
        self._kernel_editor = KernelEditor(self, p, j, "julia", current_kernel)
        self._kernel_editor.finished.connect(self.julia_kernel_editor_closed)
        self._kernel_editor.open()

    @Slot(int)
    def julia_kernel_editor_closed(self, ret_code):
        """Catches the selected Julia kernel name when the editor is closed."""
        previous_julia_kernel = self.ui.comboBox_julia_kernel.currentText()
        self.ui.comboBox_julia_kernel.clear()
        julia_kernel_cb_items = ["Select Julia kernel spec..."] + list(find_julia_kernels())
        self.ui.comboBox_julia_kernel.addItems(julia_kernel_cb_items)
        if ret_code != 1:  # Editor closed with something else than clicking Ok.
            # Set previous kernel selected in combobox if it still exists
            previous_kernel_index = self.ui.comboBox_julia_kernel.findText(previous_julia_kernel)
            if previous_kernel_index == -1:
                self.ui.comboBox_julia_kernel.setCurrentIndex(0)
            else:
                self.ui.comboBox_julia_kernel.setCurrentIndex(previous_kernel_index)
            return
        new_kernel = self._kernel_editor.selected_kernel
        index = self.ui.comboBox_julia_kernel.findText(new_kernel)
        if index == -1:
            notification = Notification(self, f"Julia kernel spec {new_kernel} not found")
            notification.show()
            self.ui.comboBox_julia_kernel.setCurrentIndex(0)
        else:
            self.ui.comboBox_julia_kernel.setCurrentIndex(index)

    @Slot(bool)
    def browse_work_path(self, checked=False):
        """Open file browser where user can select the path to wanted work directory."""
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QFileDialog.getExistingDirectory(self, "Select Work Directory", home_dir())
        if answer == '':  # Cancel button clicked
            return
        selected_path = os.path.abspath(answer)
        self.ui.lineEdit_work_dir.setText(selected_path)

    @Slot(bool)
    def show_color_dialog(self, checked=False):
        """Let user pick the bg color.

        Args:
            checked (boolean): Value emitted with clicked signal
        """
        # noinspection PyArgumentList
        color = QColorDialog.getColor(initial=self.bg_color)
        if not color.isValid():
            return  # Canceled
        self.bg_color = color
        self.update_bg_color()

    def update_bg_color(self):
        """Set tool button icon as the selected color and update
        Design View scene background color."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(self.bg_color)
        self.ui.toolButton_bg_color.setIcon(pixmap)
        self._toolbox.ui.graphicsView.scene().set_bg_color(self.bg_color)
        self._toolbox.ui.graphicsView.scene().update()

    @Slot(bool)
    def update_scene_bg(self, checked=False):
        """Draw background on scene depending on radiobutton states.

        Args:
            checked (boolean): Toggle state
        """
        if self.ui.radioButton_bg_grid.isChecked():
            self._toolbox.ui.graphicsView.scene().set_bg_choice("grid")
        elif self.ui.radioButton_bg_tree.isChecked():
            self._toolbox.ui.graphicsView.scene().set_bg_choice("tree")
        elif self.ui.radioButton_bg_solid.isChecked():
            self._toolbox.ui.graphicsView.scene().set_bg_choice("solid")
        self._toolbox.ui.graphicsView.scene().update()

    @Slot(bool)
    def update_links_geometry(self, checked=False):
        for item in self._toolbox.ui.graphicsView.items():
            if isinstance(item, (Link, JumpLink)):
                item.update_geometry(curved_links=checked)

    @Slot(bool)
    def update_items_path(self, checked=False):
        for item in self._toolbox.ui.graphicsView.items():
            if isinstance(item, ProjectItemIcon):
                item.update_path(checked)

    @Slot(bool)
    def set_toolbar_colored_icons(self, checked=False):
        self._toolbox.main_toolbar.set_colored_icons(checked)

    @Slot(bool)
    def _update_properties_widget(self, _checked=False):
        self._toolbox.ui.tabWidget_item_properties.update()

    def read_settings(self):
        """Read saved settings from app QSettings instance and update UI to display them."""
        # checkBox check state 0: unchecked, 1: partially checked, 2: checked
        # QSettings value() method returns a str even if a boolean was stored
        super().read_settings()
        open_previous_project = int(self._qsettings.value("appSettings/openPreviousProject", defaultValue="0"))
        show_exit_prompt = int(self._qsettings.value("appSettings/showExitPrompt", defaultValue="2"))
        save_at_exit = int(self._qsettings.value("appSettings/saveAtExit", defaultValue="1"))  # tri-state
        datetime = int(self._qsettings.value("appSettings/dateTime", defaultValue="2"))
        delete_data = int(self._qsettings.value("appSettings/deleteData", defaultValue="0"))
        custom_open_project_dialog = self._qsettings.value("appSettings/customOpenProjectDialog", defaultValue="true")
        smooth_zoom = self._qsettings.value("appSettings/smoothZoom", defaultValue="false")
        color_toolbar_icons = self._qsettings.value("appSettings/colorToolbarIcons", defaultValue="false")
        color_properties_widgets = self._qsettings.value("appSettings/colorPropertiesWidgets", defaultValue="false")
        curved_links = self._qsettings.value("appSettings/curvedLinks", defaultValue="false")
        drag_to_draw_links = self._qsettings.value("appSettings/dragToDrawLinks", defaultValue="false")
        rounded_items = self._qsettings.value("appSettings/roundedItems", defaultValue="false")
        prevent_overlapping = self._qsettings.value("appSettings/preventOverlapping", defaultValue="false")
        data_flow_anim_dur = int(self._qsettings.value("appSettings/dataFlowAnimationDuration", defaultValue="100"))
        bg_choice = self._qsettings.value("appSettings/bgChoice", defaultValue="solid")
        bg_color = self._qsettings.value("appSettings/bgColor", defaultValue="false")
        gams_path = self._qsettings.value("appSettings/gamsPath", defaultValue="")
        use_julia_jupyter_console = int(self._qsettings.value("appSettings/useJuliaKernel", defaultValue="0"))
        julia_path = self._qsettings.value("appSettings/juliaPath", defaultValue="")
        julia_project_path = self._qsettings.value("appSettings/juliaProjectPath", defaultValue="")
        julia_kernel = self._qsettings.value("appSettings/juliaKernel", defaultValue="")
        use_python_jupyter_console = int(self._qsettings.value("appSettings/usePythonKernel", defaultValue="0"))
        python_path = self._qsettings.value("appSettings/pythonPath", defaultValue="")
        python_kernel = self._qsettings.value("appSettings/pythonKernel", defaultValue="")
        conda_path = self._qsettings.value("appSettings/condaPath", defaultValue="")
        work_dir = self._qsettings.value("appSettings/workDir", defaultValue="")
        save_spec = int(self._qsettings.value("appSettings/saveSpecBeforeClosing", defaultValue="1"))  # tri-state
        spec_show_undo = int(self._qsettings.value("appSettings/specShowUndo", defaultValue="2"))
        if open_previous_project == 2:
            self.ui.checkBox_open_previous_project.setCheckState(Qt.Checked)
        if show_exit_prompt == 2:
            self.ui.checkBox_exit_prompt.setCheckState(Qt.Checked)
        if save_at_exit == 0:  # Not needed but makes the code more readable.
            self.ui.checkBox_save_project_before_closing.setCheckState(Qt.Unchecked)
        elif save_at_exit == 1:
            self.ui.checkBox_save_project_before_closing.setCheckState(Qt.PartiallyChecked)
        else:  # save_at_exit == 2:
            self.ui.checkBox_save_project_before_closing.setCheckState(Qt.Checked)
        if datetime == 2:
            self.ui.checkBox_datetime.setCheckState(Qt.Checked)
        if delete_data == 2:
            self.ui.checkBox_delete_data.setCheckState(Qt.Checked)
        if custom_open_project_dialog == "true":
            self.ui.checkBox_custom_open_project_dialog.setCheckState(Qt.Checked)
        if smooth_zoom == "true":
            self.ui.checkBox_use_smooth_zoom.setCheckState(Qt.Checked)
        if color_toolbar_icons == "true":
            self.ui.checkBox_color_toolbar_icons.setCheckState(Qt.Checked)
        if color_properties_widgets == "true":
            self.ui.checkBox_color_properties_widgets.setCheckState(Qt.Checked)
        if curved_links == "true":
            self.ui.checkBox_use_curved_links.setCheckState(Qt.Checked)
        if drag_to_draw_links == "true":
            self.ui.checkBox_drag_to_draw_links.setCheckState(Qt.Checked)
        if rounded_items == "true":
            self.ui.checkBox_use_rounded_items.setCheckState(Qt.Checked)
        self.ui.horizontalSlider_data_flow_animation_duration.setValue(data_flow_anim_dur)
        if prevent_overlapping == "true":
            self.ui.checkBox_prevent_overlapping.setCheckState(Qt.Checked)
        self.ui.horizontalSlider_data_flow_animation_duration.setValue(data_flow_anim_dur)
        if bg_choice == "grid":
            self.ui.radioButton_bg_grid.setChecked(True)
        elif bg_choice == "tree":
            self.ui.radioButton_bg_tree.setChecked(True)
        else:
            self.ui.radioButton_bg_solid.setChecked(True)
        if bg_color == "false":
            pass
        else:
            self.bg_color = bg_color
        self.update_bg_color()
        self.ui.lineEdit_gams_path.setPlaceholderText(resolve_gams_executable(""))
        self.ui.lineEdit_gams_path.setText(gams_path)
        # Add Python and Julia kernels to comboBoxes
        julia_k_cb_items = ["Select Julia kernel spec..."] + list(find_julia_kernels())  # Unpack to list literal
        self.ui.comboBox_julia_kernel.addItems(julia_k_cb_items)
        python_k_cb_items = ["Select Python kernel spec..."] + list(find_python_kernels())
        self.ui.comboBox_python_kernel.addItems(python_k_cb_items)
        if use_julia_jupyter_console == 2:
            self.ui.radioButton_use_julia_jupyter_console.setChecked(True)
        else:
            self.ui.radioButton_use_julia_basic_console.setChecked(True)
        self.ui.lineEdit_julia_path.setPlaceholderText(resolve_julia_executable(""))
        self.ui.lineEdit_julia_path.setText(julia_path)
        self.ui.lineEdit_julia_project_path.setText(julia_project_path)
        ind = self.ui.comboBox_julia_kernel.findText(julia_kernel)
        if ind == -1:
            self.ui.comboBox_julia_kernel.setCurrentIndex(0)
        else:
            self.ui.comboBox_julia_kernel.setCurrentIndex(ind)
        if use_python_jupyter_console == 2:
            self.ui.radioButton_use_python_jupyter_console.setChecked(True)
        else:
            self.ui.radioButton_use_python_basic_console.setChecked(True)
        self.ui.lineEdit_python_path.setPlaceholderText(resolve_python_interpreter(""))
        self.ui.lineEdit_python_path.setText(python_path)
        ind = self.ui.comboBox_python_kernel.findText(python_kernel)
        if ind == -1:
            self.ui.comboBox_python_kernel.setCurrentIndex(0)
        else:
            self.ui.comboBox_python_kernel.setCurrentIndex(ind)
        conda_placeholder_txt = resolve_conda_executable("")
        if conda_placeholder_txt:
            self.ui.lineEdit_conda_path.setPlaceholderText(conda_placeholder_txt)
        self.ui.lineEdit_conda_path.setText(conda_path)
        self.ui.lineEdit_work_dir.setText(work_dir)
        self.orig_work_dir = work_dir
        if save_spec == 0:
            self.ui.checkBox_save_spec_before_closing.setCheckState(Qt.Unchecked)
        elif save_spec == 1:
            self.ui.checkBox_save_spec_before_closing.setCheckState(Qt.PartiallyChecked)
        else:  # save_spec == 2:
            self.ui.checkBox_save_spec_before_closing.setCheckState(Qt.Checked)
        if spec_show_undo == 2:
            self.ui.checkBox_spec_show_undo.setChecked(True)
        self._read_engine_settings()

    def _read_engine_settings(self):
        """Reads Engine settings and sets the corresponding UI elements."""
        # Remote execution settings
        enable_remote_exec = self._qsettings.value("engineSettings/remoteExecutionEnabled", defaultValue="false")
        if enable_remote_exec == "true":
            self.ui.checkBox_enable_remote_exec.setCheckState(Qt.Checked)
        remote_host = self._qsettings.value("engineSettings/remoteHost", defaultValue="")
        self._edit_remote_host(remote_host)
        remote_port = int(self._qsettings.value("engineSettings/remotePort", defaultValue="49152"))
        self.ui.spinBox_port.setValue(remote_port)
        security = self._qsettings.value("engineSettings/remoteSecurityModel", defaultValue="")
        if not security:
            self.ui.comboBox_security.setCurrentIndex(0)
        else:
            self.ui.comboBox_security.setCurrentIndex(1)
        sec_folder = self._qsettings.value("engineSettings/remoteSecurityFolder", defaultValue="")
        self.ui.lineEdit_secfolder.setText(sec_folder)
        # Parallel process limits
        process_limiter = self._qsettings.value("engineSettings/processLimiter", defaultValue="unlimited")
        if process_limiter == "unlimited":
            self.ui.unlimited_engine_process_radio_button.setChecked(True)
        elif process_limiter == "auto":
            self.ui.automatic_engine_process_limit_radio_button.setChecked(True)
        else:
            self.ui.user_defined_engine_process_limit_radio_button.setChecked(True)
        process_limit = int(self._qsettings.value("engineSettings/maxProcesses", defaultValue=os.cpu_count()))
        self.ui.engine_process_limit_spin_box.setValue(process_limit)
        persistent_limiter = self._qsettings.value("engineSettings/persistentLimiter", defaultValue="unlimited")
        if persistent_limiter == "unlimited":
            self.ui.unlimited_persistent_process_radio_button.setChecked(True)
        elif persistent_limiter == "auto":
            self.ui.automatic_persistent_process_limit_radio_button.setChecked(True)
        else:
            self.ui.user_defined_persistent_process_limit_radio_button.setChecked(True)
        persistent_process_limit = int(
            self._qsettings.value("engineSettings/maxPersistentProcesses", defaultValue=os.cpu_count())
        )
        self.ui.persistent_process_limit_spin_box.setValue(persistent_process_limit)

    @Slot()
    def save_settings(self):
        """Get selections and save them to persistent memory.
        Note: On Linux, True and False are saved as boolean values into QSettings.
        On Windows, booleans and integers are saved as strings. To make it consistent,
        we should use strings.
        """
        # checkBox check state 0: unchecked, 1: partially checked, 2: checked
        # checkBox check states are cast from integers to string for consistency
        if not super().save_settings():
            return False
        open_prev_proj = str(int(self.ui.checkBox_open_previous_project.checkState()))
        self._qsettings.setValue("appSettings/openPreviousProject", open_prev_proj)
        exit_prompt = str(int(self.ui.checkBox_exit_prompt.checkState()))
        self._qsettings.setValue("appSettings/showExitPrompt", exit_prompt)
        save_at_exit = str(int(self.ui.checkBox_save_project_before_closing.checkState()))
        self._qsettings.setValue("appSettings/saveAtExit", save_at_exit)
        datetime = str(int(self.ui.checkBox_datetime.checkState()))
        self._qsettings.setValue("appSettings/dateTime", datetime)
        delete_data = str(int(self.ui.checkBox_delete_data.checkState()))
        self._qsettings.setValue("appSettings/deleteData", delete_data)
        custom_open_project_dial = "true" if int(self.ui.checkBox_custom_open_project_dialog.checkState()) else "false"
        self._qsettings.setValue("appSettings/customOpenProjectDialog", custom_open_project_dial)
        smooth_zoom = "true" if int(self.ui.checkBox_use_smooth_zoom.checkState()) else "false"
        self._qsettings.setValue("appSettings/smoothZoom", smooth_zoom)
        color_toolbar_icons = "true" if int(self.ui.checkBox_color_toolbar_icons.checkState()) else "false"
        self._qsettings.setValue("appSettings/colorToolbarIcons", color_toolbar_icons)
        color_properties_widgets = "true" if int(self.ui.checkBox_color_properties_widgets.checkState()) else "false"
        self._qsettings.setValue("appSettings/colorPropertiesWidgets", color_properties_widgets)
        curved_links = "true" if int(self.ui.checkBox_use_curved_links.checkState()) else "false"
        self._qsettings.setValue("appSettings/curvedLinks", curved_links)
        drag_to_draw_links = "true" if int(self.ui.checkBox_drag_to_draw_links.checkState()) else "false"
        self._qsettings.setValue("appSettings/dragToDrawLinks", drag_to_draw_links)
        rounded_items = "true" if int(self.ui.checkBox_use_rounded_items.checkState()) else "false"
        self._qsettings.setValue("appSettings/roundedItems", rounded_items)
        prevent_overlapping = "true" if int(self.ui.checkBox_prevent_overlapping.checkState()) else "false"
        self._qsettings.setValue("appSettings/preventOverlapping", prevent_overlapping)
        data_flow_anim_dur = str(self.ui.horizontalSlider_data_flow_animation_duration.value())
        self._qsettings.setValue("appSettings/dataFlowAnimationDuration", data_flow_anim_dur)
        if self.ui.radioButton_bg_grid.isChecked():
            bg_choice = "grid"
        elif self.ui.radioButton_bg_tree.isChecked():
            bg_choice = "tree"
        else:
            bg_choice = "solid"
        self._qsettings.setValue("appSettings/bgChoice", bg_choice)
        self._qsettings.setValue("appSettings/bgColor", self.bg_color)
        save_spec = str(int(self.ui.checkBox_save_spec_before_closing.checkState()))
        self._qsettings.setValue("appSettings/saveSpecBeforeClosing", save_spec)
        spec_show_undo = str(int(self.ui.checkBox_spec_show_undo.checkState()))
        self._qsettings.setValue("appSettings/specShowUndo", spec_show_undo)
        # GAMS
        gams_path = self.ui.lineEdit_gams_path.text().strip()
        # Check gams_path is a file, it exists, and file name starts with 'gams'
        if not file_is_valid(self, gams_path, "Invalid GAMS Program", extra_check="gams"):
            return False
        self._qsettings.setValue("appSettings/gamsPath", gams_path)
        # Julia
        use_julia_jupyter_console, julia_exe, julia_project, julia_kernel = self._get_julia_settings()
        if use_julia_jupyter_console == "2" and not julia_kernel:
            julia_kernel = _get_julia_kernel_name_by_env(julia_exe, julia_project)
            if not julia_kernel:
                MiniJuliaKernelEditor(self, julia_exe, julia_project).make_kernel()
                julia_kernel = _get_julia_kernel_name_by_env(julia_exe, julia_project)
        self._qsettings.setValue("appSettings/useJuliaKernel", use_julia_jupyter_console)
        # Check julia_path is a file, it exists, and file name starts with 'julia'
        if not file_is_valid(self, julia_exe, "Invalid Julia Executable", extra_check="julia"):
            return False
        self._qsettings.setValue("appSettings/juliaPath", julia_exe)
        # Check julia project is a directory and it exists
        if julia_project != "@." and not dir_is_valid(self, julia_project, "Invalid Julia Project"):
            return False
        self._qsettings.setValue("appSettings/juliaProjectPath", julia_project)
        self._qsettings.setValue("appSettings/juliaKernel", julia_kernel)
        # Python
        use_python_jupyter_console = "2" if self.ui.radioButton_use_python_jupyter_console.isChecked() else "0"
        python_exe = self.ui.lineEdit_python_path.text().strip()
        if self.ui.comboBox_python_kernel.currentIndex() == 0:
            python_kernel = ""
        else:
            python_kernel = self.ui.comboBox_python_kernel.currentText()
        if use_python_jupyter_console == "2" and not python_kernel:
            python_kernel = _get_python_kernel_name_by_exe(python_exe)
            if not python_kernel:
                MiniPythonKernelEditor(self, python_exe).make_kernel()
                python_kernel = _get_python_kernel_name_by_exe(python_exe)
        self._qsettings.setValue("appSettings/usePythonKernel", use_python_jupyter_console)
        # Check python_path is a file, it exists, and file name starts with 'python'
        if not file_is_valid(self, python_exe, "Invalid Python Interpreter", extra_check="python"):
            return False
        self._qsettings.setValue("appSettings/pythonPath", python_exe)
        self._qsettings.setValue("appSettings/pythonKernel", python_kernel)
        # Conda
        conda_exe = self.ui.lineEdit_conda_path.text().strip()
        self._qsettings.setValue("appSettings/condaPath", conda_exe)
        # Work directory
        work_dir = self.ui.lineEdit_work_dir.text().strip()
        self.set_work_directory(work_dir)
        # Check if something in the app needs to be updated
        self._toolbox.show_datetime = self._toolbox.update_datetime()
        if not self._save_engine_settings():
            return False
        return True

    def _save_engine_settings(self):
        """Stores Engine settings to application settings.

        Returns:
            bool: True if settings were stored successfully, False otherwise
        """
        # Remote execution settings
        remote_exec = "true" if int(self.ui.checkBox_enable_remote_exec.checkState()) else "false"
        self._qsettings.setValue("engineSettings/remoteExecutionEnabled", remote_exec)
        self._qsettings.setValue("engineSettings/remoteHost", self._remote_host)
        self._qsettings.setValue("engineSettings/remotePort", self.ui.spinBox_port.value())
        if self.ui.comboBox_security.currentIndex() == 0:
            sec_str = ""
        else:
            sec_str = self.ui.comboBox_security.currentText()
        self._qsettings.setValue("engineSettings/remoteSecurityModel", sec_str)
        self._qsettings.setValue("engineSettings/remoteSecurityFolder", self.ui.lineEdit_secfolder.text())
        # Parallel process limits
        if self.ui.unlimited_engine_process_radio_button.isChecked():
            limiter = "unlimited"
        elif self.ui.automatic_engine_process_limit_radio_button.isChecked():
            limiter = "auto"
        else:
            limiter = "user"
        self._qsettings.setValue("engineSettings/processLimiter", limiter)
        self._qsettings.setValue("engineSettings/maxProcesses", str(self.ui.engine_process_limit_spin_box.value()))
        if self.ui.unlimited_persistent_process_radio_button.isChecked():
            limiter = "unlimited"
        elif self.ui.automatic_persistent_process_limit_radio_button.isChecked():
            limiter = "auto"
        else:
            limiter = "user"
        self._qsettings.setValue("engineSettings/persistentLimiter", limiter)
        self._qsettings.setValue(
            "engineSettings/maxPersistentProcesses", str(self.ui.persistent_process_limit_spin_box.value())
        )
        return True

    def _get_julia_settings(self):
        use_julia_jupyter_console = "2" if self.ui.radioButton_use_julia_jupyter_console.isChecked() else "0"
        julia_exe = self.ui.lineEdit_julia_path.text().strip()
        julia_project = self.ui.lineEdit_julia_project_path.text().strip()
        if self.ui.comboBox_julia_kernel.currentIndex() == 0:
            julia_kernel = ""
        else:
            julia_kernel = self.ui.comboBox_julia_kernel.currentText()
        return use_julia_jupyter_console, julia_exe, julia_project, julia_kernel

    def set_work_directory(self, new_work_dir):
        """Sets new work directory.

        Args:
            new_work_dir (str): Possibly a new work directory
        """
        if not new_work_dir:  # Happens when clearing the work dir line edit
            new_work_dir = DEFAULT_WORK_DIR
        if self.orig_work_dir != new_work_dir:
            self._toolbox.set_work_directory(new_work_dir)

    def update_ui(self):
        super().update_ui()
        curved_links = self._qsettings.value("appSettings/curvedLinks", defaultValue="false")
        rounded_items = self._qsettings.value("appSettings/roundedItems", defaultValue="false")
        bg_choice = self._qsettings.value("appSettings/bgChoice", defaultValue="solid")
        bg_color = self._qsettings.value("appSettings/bgColor", defaultValue="false")
        color_toolbar_icons = self._qsettings.value("appSettings/colorToolbarIcons", defaultValue="false")
        self.set_toolbar_colored_icons(color_toolbar_icons == "true")
        self.update_links_geometry(curved_links == "true")
        self.update_items_path(rounded_items == "true")
        if bg_choice == "grid":
            self.ui.radioButton_bg_grid.setChecked(True)
        elif bg_choice == "tree":
            self.ui.radioButton_bg_tree.setChecked(True)
        else:
            self.ui.radioButton_bg_solid.setChecked(True)
        self.update_scene_bg()
        if not bg_color == "false":
            self.bg_color = bg_color
        self.update_bg_color()

    @Slot(str)
    def _edit_remote_host(self, new_text):
        """Prepends host line edit with the protocol for user convenience.

        Args:
            new_text (str): Text in the line edit after user has entered a character
        """
        prep_str = "tcp://"
        if new_text.startswith(prep_str):  # prep str already present
            new = new_text[len(prep_str) :]
        else:  # First letter has been entered
            new = new_text
        # Clear when only prep str present or when clear (x) button is clicked
        if new_text == prep_str or not new_text:
            self.ui.lineEdit_host.clear()
        else:
            self.ui.lineEdit_host.setText(prep_str + new)  # Add prep str + user input
        self._remote_host = new

    def closeEvent(self, ev):
        super().closeEvent(ev)
        self._toolbox.update_properties_ui()


def _get_python_kernel_name_by_exe(python_exe):
    """Returns a kernel name corresponding to given python exe, or an empty string if none available.

    Args:
        python_exe (str)

    Returns:
        str
    """
    python_exe = resolve_python_interpreter(python_exe)
    for name, location in find_python_kernels().items():
        deats = KernelEditor.get_kernel_deats(location)
        if _samefile(deats["exe"], python_exe):
            return name
    return ""


def _get_julia_kernel_name_by_env(julia_exe, julia_project):
    """Returns a kernel name corresponding to given julia exe and project, or an empty string if none available.

    Args:
        julia_exe (str)
        julia_project (str)

    Returns:
        str
    """
    julia_exe = resolve_julia_executable(julia_exe)
    for name, location in find_julia_kernels().items():
        deats = KernelEditor.get_kernel_deats(location)
        if _samefile(deats["exe"], julia_exe) and _samefile(deats["project"], julia_project):
            return name
    return ""


def _samefile(a, b):
    try:
        return os.path.samefile(os.path.realpath(a), os.path.realpath(b))
    except FileNotFoundError:
        return False

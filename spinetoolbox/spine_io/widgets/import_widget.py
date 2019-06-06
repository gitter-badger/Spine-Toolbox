# -*- coding: utf-8 -*-

from PySide2.QtWidgets import (
    QWidget,
    QApplication,
    QListWidget,
    QVBoxLayout,
    QDialogButtonBox,
    QMainWindow,
    QDialog,
    QPushButton,
    QLabel,
)
from PySide2.QtCore import Qt
import spinedb_api

from helpers import busy_effect
from spine_io.importers.csv_reader import CSVConnector
from spine_io.importers.excel_reader import ExcelConnector
from spine_io.importers.sqlalchemy_connector import SqlAlchemyConnector
from spine_io.widgets.import_preview_widget import ImportPreviewWidget
from spine_io.widgets.import_errors_widget import ImportErrorWidget
from spine_io.connection_manager import ConnectionManager


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # DB mapping
        if parent is not None:
            self._db_map = parent.db_map

        # state
        self._mapped_data = None
        self._mapping_errors = []
        self.connector_list = [CSVConnector, ExcelConnector, SqlAlchemyConnector]
        self.connector_list = {c.DISPLAY_NAME: c for c in self.connector_list}
        self._selected_connector = None
        self.active_connector = None

        # create widgets
        self._import_preview = None
        self._ui_list = QListWidget()
        self._error_widget = ImportErrorWidget()
        self._error_widget.hide()
        self._dialog_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # layout
        self.select_widget = QWidget()
        self.select_widget.setLayout(QVBoxLayout())
        self.select_widget.layout().addWidget(self._ui_list)
        self.select_widget.layout().addWidget(self._dialog_buttons)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.select_widget)
        self.layout().addWidget(self._error_widget)

        # set list items
        self._ui_list.blockSignals(True)
        self._ui_list.addItems([c for c in self.connector_list.keys()])
        self._ui_list.clearSelection()
        self._ui_list.blockSignals(False)

        # connect signals
        self._ui_list.currentItemChanged.connect(self.connector_selected)
        self._ui_list.activated.connect(self.launch_import_preview)
        self._dialog_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.launch_import_preview)
        self._dialog_buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)

        self._error_widget.rejected.connect(self.reject_import)
        self._error_widget.rejected.connect(self.reject)
        self._error_widget.importWithErrors.connect(self.accept)
        self._error_widget.goBack.connect(self.reject_import)
        self._error_widget.goBack.connect(self.set_preview_as_main_widget)

        # init ok button
        self.set_ok_button_availability()

    @property
    def mapped_data(self):
        return self._mapped_data

    @property
    def mapping_errors(self):
        return self._mapping_errors

    def connector_selected(self, selection):
        connector = None
        if selection:
            connector = self.connector_list.get(selection.text(), None)
        self._selected_connector = connector
        self.set_ok_button_availability()

    def set_ok_button_availability(self):
        if self._selected_connector:
            self._dialog_buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self._dialog_buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    @busy_effect
    def import_data(self, data, errors):
        del errors  # Unused parameter
        try:
            import_num, import_errors = spinedb_api.import_data(self._db_map, **data)
        except spinedb_api.SpineIntegrityError as err:
            self.reject_import()
            self._error_widget.set_import_state(0, [err.msg])
            self.set_error_widget_as_main_widget()
        except spinedb_api.SpineDBAPIError as err:
            self.reject_import()
            self._error_widget.set_import_state(0, ["Unable to import Data: %s", err.msg])
            self.set_error_widget_as_main_widget()
        else:
            if import_errors:
                self._error_widget.set_import_state(import_num, [f"{e.db_type}: {e.msg}" for e in import_errors])
                self.set_error_widget_as_main_widget()
                return False
            else:
                return True

    def data_ready(self, data, errors):
        if self.import_data(data, errors):
            self.accept()
        else:
            pass

    def launch_import_preview(self):
        if self._selected_connector:
            # create instance of connector
            self.active_connector = ConnectionManager(self._selected_connector)
            valid_source = self.active_connector.connection_ui()
            if valid_source:
                # Create instance of ImportPreviewWidget and configure

                self._import_preview = ImportPreviewWidget(self.active_connector, self)
                self._import_preview.set_loading_status(True)
                self._import_preview.rejected.connect(self.reject)
                # Connect data_ready method to the widget
                self._import_preview.mappedDataReady.connect(self.data_ready)
                self.layout().addWidget(self._import_preview)

                self.active_connector.connectionFailed.connect(self._handle_failed_connection)
                self.active_connector.init_connection()
                # show preview widget
                self.set_preview_as_main_widget()
            else:
                # remove connector object.
                self.active_connector.deleteLater()
                self.active_connector = None

    def _handle_failed_connection(self, msg):
        """Handle failed connection, show error message and select widget
        
        Arguments:
            msg {str} -- str with message of reason for failed connection.
        """
        self.select_widget.hide()
        self._error_widget.hide()
        self._import_preview.hide()

        if self.active_connector:
            self.active_connector.close_connection()
            self.active_connector.deleteLater()
            self.active_connector = None
        if self._import_preview:
            self._import_preview.deleteLater()
            self._import_preview = None

        ok_button = QPushButton()
        ok_button.setText("Ok")

        temp_widget = QWidget()
        temp_widget.setLayout(QVBoxLayout())
        temp_widget.layout().addWidget(QLabel(msg))
        temp_widget.layout().addWidget(ok_button)

        ok_button.clicked.connect(self.select_widget.show)
        ok_button.clicked.connect(temp_widget.deleteLater)
        self.layout().addWidget(temp_widget)

    def set_preview_as_main_widget(self):
        self.select_widget.hide()
        self._error_widget.hide()
        self._import_preview.show()

    def reject_import(self):
        self._db_map.rollback_session()

    def set_error_widget_as_main_widget(self):
        self.select_widget.hide()
        self._error_widget.show()
        self._import_preview.hide()


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    m = QMainWindow()
    m.setAttribute(Qt.WA_DeleteOnClose, True)
    w = ImportDialog()
    m.show()
    w.exec()
    # m.setCentralWidget(w)
    # m.setLayout(QVBoxLayout())

    sys.exit(app.exec_())

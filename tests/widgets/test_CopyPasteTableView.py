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
Unit tests for CopyPasteTableView class.

:author: A. Soininen (VTT)
:date:   12.8.2019
"""

import locale
import unittest
from unittest.mock import patch
from PySide2.QtCore import QAbstractTableModel, QModelIndex, QItemSelectionModel, Qt
from PySide2.QtWidgets import QApplication
from spinetoolbox.widgets.custom_qtableview import CopyPasteTableView


class _MockModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._data = [['a', 'b', '1.1'], ['c', 'd', '2.2'], ['e', 'f', '3.3']]

    def batch_set_data(self, indexes, data):
        for index, value in zip(indexes, data):
            self._data[index.row()][index.column()] = value
        return True

    def columnCount(self, parent=QModelIndex()):
        return len(self._data[0])

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        return self._data[index.row()][index.column()]

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        if orientation == Qt.Horizontal:
            return 'Column {}'.format(section)
        return 'Row {}'.format(section)

    def insertColumns(self, column, count, parent=QModelIndex()):
        self.beginInsertColumns(parent, column, column + count)
        if column < self.columnCount():
            for row in self._data:
                row.insert(column, count * [None])
        else:
            for row in self._data:
                row.append(count * [None])
        self.endInsertColumns()

    def insertRows(self, row, count, parent=QModelIndex()):
        self.beginInsertRows(parent, row, row + count)
        empty = count * [self.columnCount() * [None]]
        if row < self.rowCount():
            self._data.insert(row, empty)
        else:
            self._data.append(empty)
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)


def delocalize_comma_decimal_separator(x):
    return x.replace(',', '.')


def str_with_comma_decimal_separator(x):
    string = str(x)
    return string.replace('.', ',')


class TestCopyPasteTableView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            QApplication()

    @patch('spinetoolbox.widgets.custom_qtableview.locale.str', str_with_comma_decimal_separator)
    def test_copy_single_number(self):
        view = CopyPasteTableView()
        model = _MockModel()
        view.setModel(model)
        selection_model = view.selectionModel()
        selection_model.select(model.index(0, 2), QItemSelectionModel.Select)
        self.assertTrue(view.copy())
        clipboard = QApplication.clipboard()
        copied = clipboard.text()
        self.assertEqual(copied, "1,1\r\n")

    @patch('spinetoolbox.widgets.custom_qtableview.locale.str', str_with_comma_decimal_separator)
    def test_copy_row_with_hidden_column(self):
        view = CopyPasteTableView()
        model = _MockModel()
        view.setModel(model)
        view.setColumnHidden(1, True)
        selection_model = view.selectionModel()
        selection_model.select(model.index(0, 0), QItemSelectionModel.Rows | QItemSelectionModel.Select)
        self.assertTrue(view.copy())
        clipboard = QApplication.clipboard()
        copied = clipboard.text()
        self.assertEqual(copied, "a\t1,1\r\n")

    @patch('locale.str', str_with_comma_decimal_separator)
    @patch('spinetoolbox.widgets.custom_qtableview.locale.str', str_with_comma_decimal_separator)
    @patch('spinetoolbox.widgets.custom_qtableview.locale.delocalize', delocalize_comma_decimal_separator)
    def test_paste_single_localized_number(self):
        view = CopyPasteTableView()
        model = _MockModel()
        view.setModel(model)
        view.setCurrentIndex(model.index(0, 2))
        QApplication.clipboard().setText(locale.str(-1.1))
        self.assertTrue(view.paste())
        self.assertEqual(model.index(0, 2).data(), "-1.1")

    @patch('locale.str', str_with_comma_decimal_separator)
    @patch('spinetoolbox.widgets.custom_qtableview.locale.str', str_with_comma_decimal_separator)
    @patch('spinetoolbox.widgets.custom_qtableview.locale.delocalize', delocalize_comma_decimal_separator)
    def test_paste_single_localized_row(self):
        view = CopyPasteTableView()
        model = _MockModel()
        view.setModel(model)
        selection_model = view.selectionModel()
        selection_model.select(model.index(0, 0), QItemSelectionModel.Rows | QItemSelectionModel.Select)
        QApplication.clipboard().setText("A\tB\t{}".format(locale.str(-1.1)))
        self.assertTrue(view.paste())
        self.assertEqual(model.index(0, 0).data(), "A")
        self.assertEqual(model.index(0, 1).data(), "B")
        self.assertEqual(model.index(0, 2).data(), "-1.1")

    @patch('locale.str', str_with_comma_decimal_separator)
    @patch('spinetoolbox.widgets.custom_qtableview.locale.str', str_with_comma_decimal_separator)
    @patch('spinetoolbox.widgets.custom_qtableview.locale.delocalize', delocalize_comma_decimal_separator)
    def test_paste_single_comma_separated_string(self):
        view = CopyPasteTableView()
        model = _MockModel()
        view.setModel(model)
        view.setCurrentIndex(model.index(0, 2))
        QApplication.clipboard().setText("unit,node")
        self.assertTrue(view.paste())
        self.assertEqual(model.index(0, 2).data(), "unit,node")


if __name__ == '__main__':
    unittest.main()

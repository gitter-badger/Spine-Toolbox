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

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '../spinetoolbox/ui/fixed_step_time_series_editor.ui',
# licensing of '../spinetoolbox/ui/fixed_step_time_series_editor.ui' applies.
#
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_FixedStepTimeSeriesEditor(object):
    def setupUi(self, FixedStepTimeSeriesEditor):
        FixedStepTimeSeriesEditor.setObjectName("FixedStepTimeSeriesEditor")
        FixedStepTimeSeriesEditor.setWindowModality(QtCore.Qt.WindowModal)
        FixedStepTimeSeriesEditor.resize(563, 418)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(FixedStepTimeSeriesEditor)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.splitter = QtWidgets.QSplitter(FixedStepTimeSeriesEditor)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.start_time_label = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.start_time_label.setObjectName("start_time_label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.start_time_label)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.start_time_edit = QtWidgets.QLineEdit(self.verticalLayoutWidget)
        self.start_time_edit.setObjectName("start_time_edit")
        self.verticalLayout_2.addWidget(self.start_time_edit)
        self.label = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.verticalLayout_2)
        self.length_label = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.length_label.setObjectName("length_label")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.length_label)
        self.length_edit = QtWidgets.QSpinBox(self.verticalLayoutWidget)
        self.length_edit.setMinimum(2)
        self.length_edit.setMaximum(999999999)
        self.length_edit.setObjectName("length_edit")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.length_edit)
        self.resolution_label = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.resolution_label.setObjectName("resolution_label")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.resolution_label)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.resolution_edit = QtWidgets.QLineEdit(self.verticalLayoutWidget)
        self.resolution_edit.setObjectName("resolution_edit")
        self.verticalLayout_3.addWidget(self.resolution_edit)
        self.label_2 = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_3.addWidget(self.label_2)
        self.formLayout.setLayout(2, QtWidgets.QFormLayout.FieldRole, self.verticalLayout_3)
        self.verticalLayout.addLayout(self.formLayout)
        self.time_series_table = QtWidgets.QTableView(self.verticalLayoutWidget)
        self.time_series_table.setObjectName("time_series_table")
        self.verticalLayout.addWidget(self.time_series_table)
        self.verticalLayout_4.addWidget(self.splitter)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.close_button = QtWidgets.QPushButton(FixedStepTimeSeriesEditor)
        self.close_button.setObjectName("close_button")
        self.horizontalLayout.addWidget(self.close_button)
        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.retranslateUi(FixedStepTimeSeriesEditor)
        QtCore.QMetaObject.connectSlotsByName(FixedStepTimeSeriesEditor)

    def retranslateUi(self, FixedStepTimeSeriesEditor):
        FixedStepTimeSeriesEditor.setWindowTitle(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Edit time series", None, -1))
        self.start_time_label.setText(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Start time", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Format: YYYY-MM-DDThh:mm:ss", None, -1))
        self.length_label.setText(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Length", None, -1))
        self.resolution_label.setText(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Resolution", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Available units: S, M, H, d, m, y", None, -1))
        self.close_button.setText(QtWidgets.QApplication.translate("FixedStepTimeSeriesEditor", "Close", None, -1))


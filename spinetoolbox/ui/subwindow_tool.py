#############################################################################\
# Copyright (C) 2017 - 2018 VTT Technical Research Centre of Finland\
#\
# This file is part of Spine Toolbox.\
#\
# Spine Toolbox is free software: you can redistribute it and\/or modify\
# it under the terms of the GNU Lesser General Public License as published by\
# the Free Software Foundation, either version 3 of the License, or\
# (at your option) any later version.\
#\
# This program is distributed in the hope that it will be useful,\
# but WITHOUT ANY WARRANTY; without even the implied warranty of\
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\
# GNU Lesser General Public License for more details.\
#\
# You should have received a copy of the GNU Lesser General Public License\
# along with this program.  If not, see <http:\/\/www.gnu.org\/licenses\/>.\
#############################################################################\

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '../spinetoolbox/ui/subwindow_tool.ui'
#
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.setEnabled(True)
        Form.resize(200, 275)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QtCore.QSize(200, 275))
        Form.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_name = QtWidgets.QLabel(Form)
        self.label_name.setEnabled(True)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setWeight(75)
        font.setBold(True)
        self.label_name.setFont(font)
        self.label_name.setStyleSheet("background-color: rgb(255, 0, 0);\n"
"color: rgb(255, 255, 255);")
        self.label_name.setAlignment(QtCore.Qt.AlignCenter)
        self.label_name.setWordWrap(True)
        self.label_name.setObjectName("label_name")
        self.verticalLayout_2.addWidget(self.label_name)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setContentsMargins(4, 4, 4, 4)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(4)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_tool = QtWidgets.QLabel(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_tool.sizePolicy().hasHeightForWidth())
        self.label_tool.setSizePolicy(sizePolicy)
        self.label_tool.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_tool.setFont(font)
        self.label_tool.setObjectName("label_tool")
        self.horizontalLayout_2.addWidget(self.label_tool)
        self.comboBox_tool = QtWidgets.QComboBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_tool.sizePolicy().hasHeightForWidth())
        self.comboBox_tool.setSizePolicy(sizePolicy)
        self.comboBox_tool.setObjectName("comboBox_tool")
        self.horizontalLayout_2.addWidget(self.comboBox_tool)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(2)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_args = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_args.setFont(font)
        self.label_args.setObjectName("label_args")
        self.horizontalLayout_3.addWidget(self.label_args)
        self.lineEdit_tool_args = QtWidgets.QLineEdit(Form)
        self.lineEdit_tool_args.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.lineEdit_tool_args.setFont(font)
        self.lineEdit_tool_args.setCursor(QtCore.Qt.ArrowCursor)
        self.lineEdit_tool_args.setFocusPolicy(QtCore.Qt.NoFocus)
        self.lineEdit_tool_args.setReadOnly(True)
        self.lineEdit_tool_args.setObjectName("lineEdit_tool_args")
        self.horizontalLayout_3.addWidget(self.lineEdit_tool_args)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.treeView_input_files = QtWidgets.QTreeView(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeView_input_files.sizePolicy().hasHeightForWidth())
        self.treeView_input_files.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.treeView_input_files.setFont(font)
        self.treeView_input_files.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.treeView_input_files.setIndentation(5)
        self.treeView_input_files.setUniformRowHeights(True)
        self.treeView_input_files.setObjectName("treeView_input_files")
        self.verticalLayout.addWidget(self.treeView_input_files)
        self.treeView_output_files = QtWidgets.QTreeView(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeView_output_files.sizePolicy().hasHeightForWidth())
        self.treeView_output_files.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.treeView_output_files.setFont(font)
        self.treeView_output_files.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.treeView_output_files.setIndentation(5)
        self.treeView_output_files.setUniformRowHeights(True)
        self.treeView_output_files.setObjectName("treeView_output_files")
        self.verticalLayout.addWidget(self.treeView_output_files)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_details = QtWidgets.QPushButton(Form)
        self.pushButton_details.setEnabled(True)
        self.pushButton_details.setMaximumSize(QtCore.QSize(75, 23))
        self.pushButton_details.setAutoFillBackground(False)
        self.pushButton_details.setObjectName("pushButton_details")
        self.horizontalLayout.addWidget(self.pushButton_details)
        self.pushButton_connections = QtWidgets.QPushButton(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_connections.sizePolicy().hasHeightForWidth())
        self.pushButton_connections.setSizePolicy(sizePolicy)
        self.pushButton_connections.setMaximumSize(QtCore.QSize(75, 23))
        self.pushButton_connections.setObjectName("pushButton_connections")
        self.horizontalLayout.addWidget(self.pushButton_connections)
        self.pushButton_execute = QtWidgets.QPushButton(Form)
        self.pushButton_execute.setMaximumSize(QtCore.QSize(75, 23))
        self.pushButton_execute.setObjectName("pushButton_execute")
        self.horizontalLayout.addWidget(self.pushButton_execute)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        Form.setTabOrder(self.treeView_input_files, self.treeView_output_files)
        Form.setTabOrder(self.treeView_output_files, self.pushButton_details)
        Form.setTabOrder(self.pushButton_details, self.pushButton_connections)
        Form.setTabOrder(self.pushButton_connections, self.pushButton_execute)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Tool", None, -1))
        self.label_name.setText(QtWidgets.QApplication.translate("Form", "Name", None, -1))
        self.label_tool.setText(QtWidgets.QApplication.translate("Form", "Tool", None, -1))
        self.label_args.setText(QtWidgets.QApplication.translate("Form", "Args", None, -1))
        self.lineEdit_tool_args.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>Tool command line arguments. Edit tool definition file to change these.</p></body></html>", None, -1))
        self.pushButton_details.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>Show selected Tool details</p></body></html>", None, -1))
        self.pushButton_details.setText(QtWidgets.QApplication.translate("Form", "Info", None, -1))
        self.pushButton_connections.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>Show connections</p></body></html>", None, -1))
        self.pushButton_connections.setText(QtWidgets.QApplication.translate("Form", "Conn.", None, -1))
        self.pushButton_execute.setText(QtWidgets.QApplication.translate("Form", "Exec.", None, -1))


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
Contains PropertiesWidgetBase.

:author: M. Marin (ER)
:date: 20.01.2022
"""

from PySide2.QtWidgets import QWidget, QAbstractItemView, QLineEdit, QHeaderView
from PySide2.QtCore import Qt, QRect, QPoint, QEvent
from PySide2.QtGui import QPainter, QPixmap, QColor
from ..helpers import fix_lightness_color


class PropertiesWidgetBase(QWidget):
    """Properties widget base class."""

    def __init__(self, toolbox, base_color=None):
        super().__init__()
        self._toolbox = toolbox
        self._pixmap = None
        self._bg_color = None
        self._fg_color = None
        self._transparent_classes = {QAbstractItemView, QLineEdit}
        self._non_transparent_classes = {QHeaderView}
        self._transparent_widgets = set()
        if base_color is not None:
            self.set_color_and_icon(base_color)

    @property
    def fg_color(self):
        return self._fg_color

    def set_color_and_icon(self, base_color, icon=None):
        self._bg_color = fix_lightness_color(base_color, 248)
        self._fg_color = fix_lightness_color(base_color, 240)
        if icon is None:
            return
        bnw_pixmap = QPixmap(icon)
        self._pixmap = QPixmap(bnw_pixmap.size())
        self._pixmap.fill(self._fg_color)
        self._pixmap.setMask(bnw_pixmap.createMaskFromColor(Qt.transparent))

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Paint:
            painter = QPainter(obj)
            painter.fillRect(obj.rect(), QColor(255, 255, 255, 180))
        return super().eventFilter(obj, ev)

    def paintEvent(self, ev):
        """Paints background"""
        settings = self._toolbox.qsettings()
        if settings.value("appSettings/colorPropertiesWidgets", defaultValue="false") == "false":
            super().paintEvent(ev)
            return
        new_transparent_widgets = {
            widget
            for transparent in self._transparent_classes
            for widget in self.findChildren(transparent)
            if not any(isinstance(widget, non_transparent) for non_transparent in self._non_transparent_classes)
        }
        new_transparent_widgets -= self._transparent_widgets
        self._transparent_widgets |= new_transparent_widgets
        for widget in new_transparent_widgets:
            widget.setAttribute(Qt.WA_NoSystemBackground)
            widget.installEventFilter(self)
            try:
                widget.viewport().setAttribute(Qt.WA_TranslucentBackground)
            except AttributeError:
                pass
        rect = self.rect()
        painter = QPainter(self)
        painter.fillRect(rect, self._bg_color)
        if self._pixmap is not None:
            margin = 20
            offset = QPoint(margin, margin)
            painter.drawPixmap(QRect(rect.topLeft() + offset, rect.bottomRight() - offset), self._pixmap)

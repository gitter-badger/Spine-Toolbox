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
Provides SpineDBIconManager.

:authors: M. Marin (KTH)
:date:   3.2.2021
"""

from PySide2.QtCore import Qt, QPointF, QRectF, QBuffer
from PySide2.QtWidgets import QGraphicsScene
from PySide2.QtGui import QIcon, QFont, QTextOption, QPainter
from PySide2.QtSvg import QSvgGenerator, QSvgRenderer
from .helpers import TransparentIconEngine, interpret_icon_id


def _align_text_in_item(item):
    document = item.document()
    document.setDocumentMargin(0)
    option = QTextOption(Qt.AlignCenter)
    document.setDefaultTextOption(option)
    item.adjustSize()
    rect = item.boundingRect()
    size = 0.875 * round(min(rect.width(), rect.height()))
    font = item.font()
    font.setPixelSize(max(1, size))
    item.setFont(font)


def _center_scene(scene):
    rect = scene.itemsBoundingRect()
    center = rect.center()
    extent = 0.5 * max(rect.width(), rect.height())
    top_left = center - QPointF(extent, extent)
    bottom_right = center + QPointF(extent, extent)
    square = QRectF(top_left, bottom_right)
    scene.setSceneRect(square)
    rect_item = scene.addRect(square)
    rect_item.setPen(Qt.NoPen)


class _SceneSvgRenderer(QSvgRenderer):
    scene = None

    @classmethod
    def from_scene(cls, scene):
        buffer = QBuffer()
        generator = QSvgGenerator()
        generator.setOutputDevice(buffer)
        scene_rect = scene.sceneRect()
        generator.setViewBox(scene_rect)
        painter = QPainter(generator)
        scene.render(painter, scene_rect, scene_rect)
        painter.end()
        buffer.open(QBuffer.ReadOnly)
        renderer = cls(buffer.readAll())
        buffer.close()
        renderer.scene = scene
        return renderer


class SpineDBIconManager:
    """A class to manage object_class icons for spine db editors."""

    def __init__(self):
        self.display_icons = {}  # A mapping from object_class name to display icon code
        self._rel_cls_renderers = {}  # A mapping from object_class name list to associated renderer
        self._group_renderers = {}  # A mapping from class name to associated group renderer
        self._class_renderers = {}  # A mapping from class name to associated renderer
        self.icon_renderers = {}

    def update_icon_caches(self, classes):
        """Called after adding or updating entity classes.
        Stores display_icons and clears obsolete entries
        from the relationship class and entity group renderer caches."""
        for class_ in classes:
            self.display_icons[class_["name"]] = class_["display_icon"]
        class_names = [x["name"] for x in classes]
        dirty_keys = [k for k in self._rel_cls_renderers if any(x in class_names for x in k)]
        for k in dirty_keys:
            del self._rel_cls_renderers[k]
        for name in class_names:
            self._group_renderers.pop(name, None)
            self._class_renderers.pop(name, None)

    def _create_icon_renderer(self, icon_code, color_code):
        scene = QGraphicsScene()
        font = QFont('Font Awesome 5 Free Solid')
        text_item = scene.addText(icon_code, font)
        text_item.setDefaultTextColor(color_code)
        _align_text_in_item(text_item)
        self.icon_renderers[icon_code, color_code] = _SceneSvgRenderer.from_scene(scene)

    def icon_renderer(self, icon_code, color_code):
        if (icon_code, color_code) not in self.icon_renderers:
            self._create_icon_renderer(icon_code, color_code)
        return self.icon_renderers[icon_code, color_code]

    def _create_class_renderer(self, class_name):
        display_icon = self.display_icons.get(class_name, -1)
        icon_code, color_code = interpret_icon_id(display_icon)
        self._class_renderers[class_name] = self.icon_renderer(chr(icon_code), color_code)

    def class_renderer(self, class_name):
        if class_name not in self._class_renderers:
            self._create_class_renderer(class_name)
        return self._class_renderers[class_name]

    def _create_rel_cls_renderer(self, object_class_names):
        if not any(object_class_names):
            self._rel_cls_renderers[object_class_names] = self.icon_renderer("\uf1b3", 0)
            return
        font = QFont('Font Awesome 5 Free Solid')
        scene = QGraphicsScene()
        x = 0
        for j, obj_cls_name in enumerate(object_class_names):
            display_icon = self.display_icons.get(obj_cls_name, -1)
            icon_code, color_code = interpret_icon_id(display_icon)
            text_item = scene.addText(chr(icon_code), font)
            text_item.setDefaultTextColor(color_code)
            _align_text_in_item(text_item)
            if j % 2 == 0:
                y = 0
            else:
                y = -0.875 * 0.75 * text_item.boundingRect().height()
                text_item.setZValue(-1)
            text_item.setPos(x, y)
            x += 0.875 * 0.5 * text_item.boundingRect().width()
        _center_scene(scene)
        self._rel_cls_renderers[object_class_names] = _SceneSvgRenderer.from_scene(scene)

    def relationship_class_renderer(self, rel_cls_name, object_class_name_list):
        display_icon = self.display_icons.get(rel_cls_name)
        if display_icon is not None:
            return self.class_renderer(rel_cls_name)
        if object_class_name_list not in self._rel_cls_renderers:
            self._create_rel_cls_renderer(object_class_name_list)
        return self._rel_cls_renderers[object_class_name_list]

    def _create_group_renderer(self, class_name):
        display_icon = self.display_icons.get(class_name, -1)
        icon_code, color_code = interpret_icon_id(display_icon)
        font = QFont('Font Awesome 5 Free Solid')
        scene = QGraphicsScene()
        x = 0
        for _ in range(2):
            y = 0
            for _ in range(2):
                text_item = scene.addText(chr(icon_code), font)
                text_item.setDefaultTextColor(color_code)
                text_item.setPos(x, y)
                y += 0.875 * text_item.boundingRect().height()
            x += 0.875 * text_item.boundingRect().width()
        scene.addRect(scene.itemsBoundingRect())
        self._group_renderers[class_name] = _SceneSvgRenderer.from_scene(scene)

    def group_renderer(self, class_name):
        if class_name not in self._group_renderers:
            self._create_group_renderer(class_name)
        return self._group_renderers[class_name]

    @staticmethod
    def icon_from_renderer(renderer):
        return QIcon(SceneIconEngine(renderer.scene))


class SceneIconEngine(TransparentIconEngine):
    """Specialization of QIconEngine used to draw scene-based icons."""

    def __init__(self, scene):
        super().__init__()
        self.scene = scene

    def paint(self, painter, rect, mode=None, state=None):
        painter.save()
        self.scene.render(painter, rect, self.scene.sceneRect())
        painter.restore()

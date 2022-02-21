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

import os
from enum import Enum, auto, unique
from pygments.styles import get_style_by_name
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound
from pygments.token import Token
from PySide2.QtCore import Qt, QRunnable, QThreadPool, Slot, QTimer, QPoint, QMutex
from PySide2.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QWidget,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QMenu,
)
from PySide2.QtGui import (
    QFontDatabase,
    QColor,
    QFont,
    QTextDocument,
    QTextCursor,
    QTextCharFormat,
)
from spinetoolbox.helpers import CustomSyntaxHighlighter, keeping_at_bottom
from spinetoolbox.spine_engine_manager import make_engine_manager

_PROMPT_ROLE = Qt.UserRole + 1
_SELECTION_ROLE = Qt.UserRole + 2

_STYLE = get_style_by_name("monokai")
_BG_COLOR = _STYLE.background_color
_HL_COLOR = _STYLE.highlight_color
_FG_COLOR = _STYLE.styles[Token.Text]


@unique
class PromptType(Enum):
    NORMAL = auto()
    CONTINUATION = auto()


class PromptLineEdit(QPlainTextEdit):
    def __init__(self, console):
        super().__init__()
        self._console = console
        self.setUndoRedoEnabled(False)
        self.setCursorWidth(0)
        char_width = self.fontMetrics().horizontalAdvance("x")
        self.setTabStopDistance(4 * char_width)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _get_current_text(self):
        """Returns current text.

        Returns:
            str: the complete text
            str: the text before the cursor (for autocompletion)
        """
        cursor = self.textCursor()
        text = self.toPlainText()
        partial_text = text[: cursor.position()]
        return text, partial_text

    def keyPressEvent(self, ev):
        text, partial_text = self._get_current_text()
        if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._console.issue_command(text)
            return
        if ev.key() == Qt.Key_Up:
            self._console.move_history(text, 1)
            return
        if ev.key() == Qt.Key_Down:
            self._console.move_history(text, -1)
            return
        if ev.key() == Qt.Key_Tab and partial_text.strip():
            self._console.autocomplete(text, partial_text)
            return
        super().keyPressEvent(ev)


class PromptDelegate(QStyledItemDelegate):
    def __init__(self, language, console):
        super().__init__(parent=console)
        self._console = console
        self._prompt_type = None
        self._prompt, self._prompt_format = _make_prompt(language)
        self._cont_prompt = _make_cont_prompt(language)
        self._font = _font()
        self._text_format = QTextCharFormat()
        self._text_format.setForeground(QColor(_FG_COLOR))
        self.label = QLabel()
        self.label.setFont(self._font)
        self.line_edit = PromptLineEdit(console)
        self._highlighter = _make_highlighter(language)
        self.update_prompt_type(PromptType.NORMAL)

    @property
    def prompt(self):
        return self._prompt

    def createEditor(self, parent, option, index):
        editor = QWidget(parent)
        layout = QHBoxLayout(editor)
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        editor.setStyleSheet("background-color: transparent; color:transparent; border: 0px")
        editor.setAttribute(Qt.WA_TransparentForMouseEvents)
        return editor

    def update_prompt_type(self, prompt_type):
        self._prompt_type = prompt_type
        text = {PromptType.NORMAL: self._prompt, PromptType.CONTINUATION: self._cont_prompt}.get(self._prompt_type, "")
        self.label.setText(text)

    def make_doc(self, index):
        if index.row() == index.model().rowCount() - 1:
            text = self.line_edit.toPlainText() + "\u2588"
            prompt_type = self._prompt_type
        else:
            text = index.data(Qt.DisplayRole)
            prompt_type = index.data(_PROMPT_ROLE)
        if text is None:
            text = ""
        doc = _make_doc(self._font)
        cursor = QTextCursor(doc)
        if prompt_type is not None:
            prompt = self._prompt if prompt_type == PromptType.NORMAL else self._cont_prompt
            cursor.insertText(prompt, self._prompt_format)
            self._insert_formatted_text(cursor, text)
        else:
            cursor.insertText(text, self._text_format)
        return doc

    def sizeHint(self, option, index):
        doc = self.make_doc(index)
        doc.setTextWidth(self._console.viewport().width())
        return doc.size().toSize()

    def paint(self, painter, option, index):
        doc = self.make_doc(index)
        text_edit = QTextEdit()
        text_edit.setStyleSheet("background-color: transparent; border: 0px")
        text_edit.setDocument(doc)
        text_edit.setFixedSize(option.rect.size())
        _select(text_edit, index)
        painter.save()
        painter.translate(option.rect.topLeft())
        text_edit.render(painter, QPoint(0, 0))
        painter.restore()

    def _insert_formatted_text(self, cursor, text):
        """Inserts formatted text.

        Args:
            cursor (QTextCursor)
            text (str)
        """
        for start, count, text_format in self._highlighter.yield_formats(text):
            chunk = text[start : start + count]
            chunk = chunk.replace("\n", "\n" + self._cont_prompt).replace("\t", 4 * " ")
            cursor.insertText(chunk, text_format)


class PersistentConsoleWidget(QListWidget):
    """A widget to interact with a persistent process."""

    _MAX_ROWS = 2000

    def __init__(self, toolbox, key, language, owner=None):
        """
        Args:
            toolbox (ToolboxUI)
            key (tuple): persistent process identifier
            language (str): for syntax highlighting and prompting, etc.
            owner (ProjectItemBase, optional): console owner
        """
        super().__init__(parent=toolbox)
        self.setCursor(Qt.IBeamCursor)
        self.setSpacing(1)
        self.setStyleSheet(f"QListWidget{{background-color: {_BG_COLOR}; border: 0px}}")
        self._toolbox = toolbox
        self._thread_pool = QThreadPool()
        self._key = key
        self._language = language
        self.owners = {owner}
        self._history_index = 0
        self._history_item_zero = ""
        self._pending_command_count = 0
        self._is_last_command_complete = True
        self._delegate = PromptDelegate(language, self)
        self.setItemDelegate(self._delegate)
        self._add_prompt()
        self._text_buffer = []
        self._mutex = QMutex()
        self._timer = QTimer()
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._drain_text_buffer)
        self._timer.start()
        self._press_row_column = None
        self._move_row_column = None
        self._current_row = None
        self._can_copy = False

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if ev.button() != Qt.LeftButton:
            return
        for row in range(self.model().rowCount()):
            self.item(row).setData(_SELECTION_ROLE, None)
        if not self.indexAt(ev.pos()).isValid():
            self._press_row_column = None
            return
        self._press_row_column = self._move_row_column = self._current_row, _ = self._row_and_column_at(ev.pos())
        self._recompute_selection()

    def mouseMoveEvent(self, ev):
        super().mouseMoveEvent(ev)
        if not self.indexAt(ev.pos()).isValid():
            return
        self._move_row_column = self._row_and_column_at(ev.pos())
        if self._press_row_column is None:
            self._press_row_column = self._current_row, _ = self._move_row_column
        self._recompute_selection()

    def _row_and_column_at(self, pos):
        index = self.indexAt(pos)
        doc = self._delegate.make_doc(index)
        doc.setTextWidth(self.viewport().width())
        pos -= self.visualRect(index).topLeft()
        return index.row(), doc.documentLayout().hitTest(pos, Qt.FuzzyHit)

    def _recompute_selection(self):
        press_row, press_column = self._press_row_column
        move_row, move_column = self._move_row_column
        # Move current row, selecting or deselecting as needed
        step = 1 if move_row > self._current_row else -1
        while self._current_row != move_row:
            next_row = self._current_row + step
            # If we are moving to a row that is not selected, it means we are extending the selection.
            # Otherwise we are shrinking it
            extending_selection = self.item(next_row).data(_SELECTION_ROLE) is None
            # If we are extending, then the current row (the one we are leaving) should become fully selected.
            # Otherwise it should become fully deselected
            self.item(self._current_row).setData(_SELECTION_ROLE, (None, None) if extending_selection else None)
            self._current_row = next_row
        # Set partial selections in first and last rows
        _set_data = lambda item, role, value: item.setData(role, value) if item is not None else None
        if press_row < move_row:
            _set_data(self.item(press_row), _SELECTION_ROLE, (press_column, None))
            _set_data(self.item(move_row), _SELECTION_ROLE, (None, move_column))
        elif move_row < press_row:
            _set_data(self.item(move_row), _SELECTION_ROLE, (move_column, None))
            _set_data(self.item(press_row), _SELECTION_ROLE, (None, press_column))
        else:
            left, right = min(press_column, move_column), max(press_column, move_column)
            _set_data(self.item(press_row), _SELECTION_ROLE, (left, right))
        self._can_copy = press_row != move_row or press_column != move_column
        self.scheduleDelayedItemsLayout()

    def copy(self):
        lines = []
        append_line = lines.append
        for row in range(self.model().rowCount() - 1):
            text = self.item(row).data(Qt.DisplayRole)
            if self.item(row).data(_PROMPT_ROLE) is not None:
                text = self._delegate.prompt + text
            if not text:
                continue
            selection = self.item(row).data(_SELECTION_ROLE)
            if selection is None:
                continue
            start, end = selection
            start = 0 if start is None else start
            if end is None:
                append_line(text[start:])
            else:
                append_line(text[start:end])
        qApp.clipboard().setText("\n".join(lines))  # pylint: disable=undefined-variable

    def name(self):
        """Returns console name for display purposes."""
        return f"{self._language.capitalize()} Console - {self.owner_names}"

    @property
    def owner_names(self):
        return " & ".join(x.name for x in self.owners if x is not None)

    def focusInEvent(self, ev):
        self._delegate.line_edit.setFocus()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.scheduleDelayedItemsLayout()

    def move_history(self, text, step):
        """Moves history.

        Args:
            text (str)
            step (int)
        """
        if self._history_index == 0:
            self._history_item_zero = text
        engine_server_address = self._toolbox.qsettings().value("appSettings/engineServerAddress", defaultValue="")
        engine_mngr = make_engine_manager(engine_server_address)
        self._history_index += step
        if self._history_index < 1:
            self._history_index = 0
            history_item = self._history_item_zero
        else:
            history_item = engine_mngr.get_persistent_history_item(self._key, self._history_index)
        self._delegate.line_edit.setPlainText(history_item)
        cursor = self._delegate.line_edit.textCursor()
        cursor.movePosition(cursor.End)
        self._delegate.line_edit.setTextCursor(cursor)

    def autocomplete(self, text, partial_text):
        """Autocompletes current text in the prompt (or print options if multiple matches).

        Args:
            text (str)
            partial_text (str)
        """
        engine_server_address = self._toolbox.qsettings().value("appSettings/engineServerAddress", defaultValue="")
        engine_mngr = make_engine_manager(engine_server_address)
        completions = engine_mngr.get_persistent_completions(self._key, partial_text)
        prefix = os.path.commonprefix(completions)
        if partial_text.endswith(prefix):
            # Can't complete: 'commit' stdin and print options to stdout
            self.add_stdin(text)
            self.add_stdout("\t\t".join(completions))
        else:
            # Complete in current line
            cursor = self._delegate.line_edit.textCursor()
            last_word = partial_text.split(" ")[-1]
            cursor.insertText(prefix[len(last_word) :])

    def _add_prompt(self):
        """Adds a prompt at the end of the document."""
        item = QListWidgetItem(None)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
        self.addItem(item)
        self.openPersistentEditor(self.indexFromItem(item))
        self._delegate.label.show()

    def issue_command(self, text):
        """Issues command.

        Args:
            text (str)
        """
        engine_server_address = self._toolbox.qsettings().value("appSettings/engineServerAddress", defaultValue="")
        issuer = CommandIssuer(engine_server_address, self._key, text)
        issuer.stdout_msg.connect(self.add_stdout)
        issuer.stderr_msg.connect(self.add_stderr)
        issuer.finished.connect(self._handle_command_finished)
        if self._pending_command_count:
            issuer.stdin_msg.connect(self.add_stdin)
        self._print_command(text, with_prompt=not self._pending_command_count)
        self._delegate.line_edit.clear()
        self._delegate.label.hide()
        self._history_index = 0
        self._pending_command_count += 1
        self._thread_pool.start(issuer)

    def _get_prompt_type(self, with_prompt):
        if not with_prompt:
            return None
        if self._is_last_command_complete:
            return PromptType.NORMAL
        return PromptType.CONTINUATION

    def _print_command(self, text, with_prompt):
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        prompt_type = self._get_prompt_type(with_prompt)
        item.setData(_PROMPT_ROLE, prompt_type)
        with keeping_at_bottom(self):
            self.insertItem(self.model().rowCount() - 1, item)

    def _handle_command_finished(self, is_complete):
        self._pending_command_count -= 1
        self._is_last_command_complete = is_complete
        self._delegate.label.show()
        self._delegate.update_prompt_type(PromptType.NORMAL if is_complete else PromptType.CONTINUATION)

    def add_stdin(self, data):
        """Adds new prompt with data. Used when adding stdin from external execution.

        Args:
            data (str)
        """
        self._insert_text_before_prompt(data, with_prompt=True)

    def add_stdout(self, data):
        """Adds new line to stdout. Used when adding stdout from external execution.

        Args:
            data (str)
        """
        self._insert_text_before_prompt(data)

    def add_stderr(self, data):
        """Adds new line to stderr. Used when adding stderr from external execution.

        Args:
            data (str)
        """
        text_format = QTextCharFormat()
        text_format.setForeground(Qt.red)
        self._insert_text_before_prompt(data, text_format=text_format)

    def _insert_text_before_prompt(self, text, with_prompt=False, text_format=QTextCharFormat()):
        """Inserts given text before the prompt. Used when adding input and output from external execution.

        Args:
            text (str)
        """
        prompt_type = self._get_prompt_type(with_prompt)
        self._text_buffer.append((text, prompt_type))

    @Slot()
    def _drain_text_buffer(self):
        """Inserts all text from buffer."""
        if not self._text_buffer:
            return
        row = self.model().rowCount() - 1
        texts, prompt_types = zip(*self._text_buffer)
        self._text_buffer = []
        with keeping_at_bottom(self):
            self.insertItems(row, texts)
        for i, prompt_type in enumerate(prompt_types):
            item = self.item(row + i)
            item.setFlags(Qt.ItemIsEnabled)
            item.setData(_PROMPT_ROLE, prompt_type)
        rows_to_remove = self.model().rowCount() - self._MAX_ROWS
        if rows_to_remove > 0:
            self.model().removeRows(0, rows_to_remove)

    def _restart_persistent(self, _=False):
        """Restarts underlying persistent process."""
        self.model().removeRows(0, self.model().rowCount() - 1)
        engine_server_address = self._toolbox.qsettings().value("appSettings/engineServerAddress", defaultValue="")
        restarter = Restarter(engine_server_address, self._key)
        self._thread_pool.start(restarter)

    def _interrupt_persistent(self, _=False):
        """Interrupts underlying persistent process."""
        engine_server_address = self._toolbox.qsettings().value("appSettings/engineServerAddress", defaultValue="")
        interrupter = Interrupter(engine_server_address, self._key)
        self._thread_pool.start(interrupter)

    def _extend_menu(self, menu):
        """Adds two more actions: Restart, and Interrupt."""
        menu.addSeparator()
        menu.addAction("Copy", self.copy).setEnabled(self._can_copy)
        menu.addSeparator()
        menu.addAction("Restart", self._restart_persistent)
        menu.addAction("Interrupt", self._interrupt_persistent)

    def contextMenuEvent(self, event):
        """Reimplemented to extend menu with custom actions."""
        menu = QMenu()
        self._extend_menu(menu)
        menu.exec_(event.globalPos())


class _Signal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args, **kwargs):
        for slot in self._slots:
            slot(*args, **kwargs)


class PersistentRunnableBase(QRunnable):
    """Base class for runnables that talk to the persistent process in another QThread."""

    def __init__(self, engine_server_address, persistent_key):
        """
        Args:
            engine_server_address (str): address of the remote engine, currently should always be an empty string
            persistent_key (tuple): persistent process identifier
        """
        super().__init__()
        self._persistent_key = persistent_key
        self._engine_mngr = make_engine_manager(engine_server_address)
        self.finished = _Signal()


class Restarter(PersistentRunnableBase):
    """A runnable that restarts a persistent process."""

    def run(self):
        self._engine_mngr.restart_persistent(self._persistent_key)
        self.finished.emit()


class Interrupter(PersistentRunnableBase):
    """A runnable that interrupts a persistent process."""

    def run(self):
        self._engine_mngr.interrupt_persistent(self._persistent_key)
        self.finished.emit()


class CommandIssuer(PersistentRunnableBase):
    """A runnable that issues a command."""

    def __init__(self, engine_server_address, persistent_key, command):
        """
        Args:
            engine_server_address (str): address of the remote engine, currently should always be an empty string
            persistent_key (tuple): persistent process identifier
            command (str): command to execute
        """
        super().__init__(engine_server_address, persistent_key)
        self._command = command
        self.stdin_msg = _Signal()
        self.stdout_msg = _Signal()
        self.stderr_msg = _Signal()

    def run(self):
        for msg in self._engine_mngr.issue_persistent_command(self._persistent_key, self._command):
            msg_type = msg["type"]
            if msg_type == "stdin":
                self.stdin_msg.emit(msg["data"])
            elif msg_type == "stdout":
                self.stdout_msg.emit(msg["data"])
            elif msg_type == "stderr":
                self.stderr_msg.emit(msg["data"])
            elif msg_type == "command_finished":
                self.finished.emit(msg["is_complete"])
                break


def _font():
    return QFontDatabase.systemFont(QFontDatabase.FixedFont)


def _make_prompt(language):
    text_format = QTextCharFormat()
    if language == "julia":
        prompt = "julia> "
        text_format.setForeground(Qt.darkGreen)
        text_format.setFontWeight(QFont.Bold)
    elif language == "python":
        prompt = ">>> "
    else:
        prompt = "$ "
    return prompt, text_format


def _make_cont_prompt(language):
    if language == "julia":
        prompt = len("julia> ") * " "
    elif language == "python":
        prompt = "... "
    else:
        prompt = "  "
    return prompt


def _make_doc(font):
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setDefaultFont(font)
    return doc


def _make_formatted_text(font, text, format_):
    doc = _make_doc(font)
    cursor = QTextCursor(doc)
    cursor.insertText(text, format_)
    return doc.toHtml()


def _make_highlighter(language):
    highlighter = CustomSyntaxHighlighter(None)
    highlighter.set_style(_STYLE)
    try:
        highlighter.lexer = get_lexer_by_name(language)
    except ClassNotFound:
        pass
    return highlighter


def _select(text_edit, index):
    selection = index.data(_SELECTION_ROLE)
    if selection is None:
        return
    cursor = text_edit.textCursor()
    start, end = selection
    if start is not None:
        cursor.setPosition(start)
    else:
        cursor.movePosition(QTextCursor.Start)
    if end is not None:
        cursor.setPosition(end, QTextCursor.KeepAnchor)
    else:
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
    text_edit.setTextCursor(cursor)

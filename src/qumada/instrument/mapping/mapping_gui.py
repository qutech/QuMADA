# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Jonas Mertens

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, Union

from PyQt5.QtCore import QItemSelectionModel, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QDropEvent,
    QFocusEvent,
    QKeyEvent,
    QMouseEvent,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDesktopWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from qcodes.instrument.channel import InstrumentModule
from qcodes.instrument.instrument import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.utils.metadata import Metadatable

from qumada.instrument.mapping.base import (
    add_mapping_to_instrument,
    filter_flatten_parameters,
)
from qumada.metadata import Metadata

TerminalParameters = Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]

RED = QColor(255, 0, 0)
WHITE = QColor(255, 255, 255)
GREEN = QColor(0, 255, 0)
YELLOW = QColor(255, 255, 0)
PINK = QColor(255, 192, 203)
BLUE = QColor(0, 0, 255)


# TODO: terminal_parameter attributes
class TerminalTreeView(QTreeView):
    """
    QTreeView, that displays QuMADA `TerminalParameters` (`Mapping[Any, Mapping[Any, Parameter] | Parameter]`) datastructure.
    Items are draggable to map them to instruments.
    """

    def __init__(self, monitoring=False):
        super().__init__()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Terminal", "Mapped Instrument", "Monitoring"])
        self.setModel(model)
        self.terminal_parameters = None

        self.selected_terminal_tree_elem = None

        # Parameter Monitoring Functionality
        self.monitoring_enable = monitoring
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self.update_monitoring)

        self.setDragEnabled(True)

    # forward keypressevents "hack". keyPressEvent of QMainWindow doesnt fire for letter keys
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_A or event.key() == Qt.Key_R or event.key() == Qt.Key_E or event.key() == Qt.Key_U:
            self.parentWidget().keyPressEvent(event)
        else:
            return super().keyPressEvent(event)

    # overwrite default double click event behaviour
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pass

    def update_monitoring(self):
        """
        This is called periodically, gets the mapped parameter values and updates the labels
        """
        # TODO: maybe format cells based on settable
        # if(param.settable):
        #     pass # maybe do coloring based on settable

        root = self.model().invisibleRootItem()
        for terminal in get_children(root):
            for terminal_param in get_children(terminal):
                param = self.terminal_parameters[terminal_param.source[0]][terminal_param.source[1]]
                if not param is None:
                    if self.monitoring_get_type == "get" and param.gettable:
                        # Use get command
                        try:
                            val = param.get()
                        except:
                            val = param.cache.get(get_if_invalid=False)
                    else:
                        # Use cached value (also applicable to non-gettable parameters (last set value))
                        val = param.cache.get(get_if_invalid=False)

                    if not val is None and (type(val) is int or type(val) is float):
                        if not param.unit is None:
                            self.model().setData(terminal_param.index().siblingAtColumn(2), f"{val:.2f} {param.unit}")
                        else:
                            self.model().setData(terminal_param.index().siblingAtColumn(2), f"{val:.2f}")
                else:
                    self.model().setData(terminal_param.index().siblingAtColumn(2), "")

        self.resizeColumnToContents(2)

    def update_tree(self):
        """
        Function that sets all visual elements (labels, colors) based on state of mapping.
        This is a clean solution (not super efficient) because changing the mapping for one
        parameter can have an influence on any other visual elements (duplicate markings etc.)
        """
        # Set mapped instrument labels and colors, set colors for duplicates
        tree = self.model()
        parameter_duplicates = {}
        for terminal in get_children(tree.invisibleRootItem()):
            tree.setData(terminal.index(), QBrush(WHITE), Qt.BackgroundRole)
            tree.setData(terminal.index().siblingAtColumn(1), QBrush(RED), Qt.BackgroundRole)
            tree.setData(terminal.index().siblingAtColumn(1), "")
            all_mapped = True
            any_mapped = False
            channel_names = set()
            for terminal_param in get_children(terminal):
                tree.setData(terminal_param.index(), QBrush(WHITE), Qt.BackgroundRole)
                tree.setData(terminal_param.index().siblingAtColumn(1), QBrush(RED), Qt.BackgroundRole)
                tree.setData(terminal_param.index().siblingAtColumn(1), "")
                param = self.terminal_parameters[terminal_param.source[0]][terminal_param.source[1]]
                if not param is None:
                    if isinstance(param, Parameter):
                        param_hash = hash(param)
                        if param_hash in parameter_duplicates:
                            parameter_duplicates[param_hash].append(terminal_param)
                        else:
                            parameter_duplicates[param_hash] = [terminal_param]

                        channel_names.add(param.instrument.full_name)
                        tree.setData(terminal_param.index().siblingAtColumn(1), param.full_name)
                        tree.setData(terminal_param.index().siblingAtColumn(1), QBrush(GREEN), Qt.BackgroundRole)
                        any_mapped = True
                    else:
                        raise TypeError("Gate parameters have to be either None or of type Parameter.")
                else:
                    all_mapped = False

            # color and label terminals
            if all_mapped:
                tree.setData(terminal.index().siblingAtColumn(1), QBrush(GREEN), Qt.BackgroundRole)
                if len(channel_names) == 1:
                    tree.setData(terminal.index().siblingAtColumn(1), channel_names.pop())
                else:
                    tree.setData(terminal.index().siblingAtColumn(1), "")
            elif any_mapped:
                tree.setData(terminal.index().siblingAtColumn(1), QBrush(YELLOW), Qt.BackgroundRole)

        # color duplicates
        for items_with_param in parameter_duplicates.values():
            if len(items_with_param) != 1:
                for duplicate in items_with_param:
                    duplicate.setData(QBrush(PINK), Qt.BackgroundRole)
                    duplicate.parent().setData(QBrush(PINK), Qt.BackgroundRole)
                    # tree.setData(duplicate.index(), QBrush(PINK), Qt.BackgroundRole)
                    # tree.setData(duplicate.parent().index(), QBrush(PINK), Qt.BackgroundRole)

        # any item selected?
        if not self.selected_terminal_tree_elem is None:
            self.selected_terminal_tree_elem.setData(QBrush(BLUE), Qt.BackgroundRole)
            # tree.setData(self.selected_terminal_tree_elem, QBrush(BLUE), Qt.BackgroundRole)

        self.resizeColumnToContents(1)
        self.update_monitoring()

    def import_data(self, terminal_parameters: TerminalParameters) -> None:
        """Build up tree with provided terminal parameters."""
        root = self.model().invisibleRootItem()
        self.terminal_parameters = terminal_parameters
        for terminal_name, terminal_params in terminal_parameters.items():
            item = QStandardItem(terminal_name)
            # item.setData((terminal_name, tuple(terminal_params.keys())))
            # print(item.data(),item.text())
            item.source = (terminal_name, tuple(terminal_params.keys()))
            root.appendRow(item)

            # if isinstance(terminal_params, Mapping):
            for terminal_param_name in terminal_params.keys():
                subitem = QStandardItem(terminal_param_name)
                # subitem.setData((terminal_name, terminal_param_name))
                # print(subitem.data(),subitem.text())
                subitem.source = (terminal_name, terminal_param_name)
                item.appendRow(subitem)

            qidx = item.index()
            self.model().setData(qidx.siblingAtColumn(1), QBrush(RED), Qt.BackgroundRole)
            self.model().insertColumn(1, qidx)
            self.model().insertColumn(2, qidx)
            for i in range(len(terminal_params.keys())):
                self.model().setData(qidx.child(i, 1), "")
                self.model().setData(qidx.child(i, 1), QBrush(RED), Qt.BackgroundRole)
                self.model().setData(qidx.child(i, 2), "")

            self.setColumnHidden(2, not self.monitoring_enable)


class InstrumentTreeView(QTreeView):
    """QTreeView, that displays qcodes instruments."""

    drag_terminal_drop_instr = pyqtSignal(QStandardItem, QStandardItem)

    def __init__(self):
        super().__init__()

        model = QStandardItemModel()
        # model.setHorizontalHeaderLabels(["Name", "Terminal"])
        model.setHorizontalHeaderLabels(["Instrument Name"])
        self.setModel(model)

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pass

    def focusOutEvent(self, a0: QFocusEvent) -> None:
        mainwindow = self.parentWidget()
        for child in mainwindow.children():
            if isinstance(child, TerminalTreeView):
                terminal_tree = child
                break

        if not terminal_tree.selected_terminal_tree_elem is None:
            terminal_tree.selected_terminal_tree_elem = None
            terminal_tree.update_tree()

        return super().focusOutEvent(a0)

    # forward keypressevents "hack". keyPressEvent of QMainWindow doesnt fire for letter keys
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_A or event.key() == Qt.Key_R or event.key() == Qt.Key_E or event.key() == Qt.Key_U:
            self.parentWidget().keyPressEvent(event)
        else:
            return super().keyPressEvent(event)

    def get_perfect_mappings(self, terminal_params: list[str], parent_elem=None) -> list[QStandardItem]:
        """
        Given a list of terminal_parameters (names) return a list of QStandardItems in InstrumentTree (perfect mapping candidate)
        that could be mapped perfectly i.e. every terminal_parameter can be mapped uniquely to the list of all children parameters of
        the perfect mapping candidate.
        """
        if parent_elem == None:
            parent_elem = self.model().invisibleRootItem()

        perfect_elems = []
        for instrument_elem in get_children(parent_elem):
            if instrument_elem.hasChildren():
                all_mappings = self.get_all_possible_mapping_names(instrument_elem)
                perfect_mapping = True
                for terminal_param in terminal_params:
                    if all_mappings.count(terminal_param) != 1:
                        perfect_mapping = False
                        break

                if perfect_mapping:
                    perfect_elems.append(instrument_elem)
                if instrument_elem.hasChildren():
                    perfect_elems = perfect_elems + self.get_perfect_mappings(terminal_params, instrument_elem)

        return perfect_elems

    def get_all_possible_mapping_names(self: InstrumentTreeView, instrument_elem: QStandardItem) -> list[str] | None:
        """
        Get all possible mapping names for all children of instrument_elem. None if
        """
        mapping_names = []
        if not hasattr(instrument_elem, "source"):
            return None

        if instrument_elem.hasChildren():
            for child in get_children(instrument_elem):
                mapping_names = mapping_names + self.get_all_possible_mapping_names(child)
        else:
            if isinstance(instrument_elem.source, Parameter):
                if hasattr(instrument_elem.source, "_mapping"):
                    return [instrument_elem.source._mapping]

        return mapping_names

    def map_given_terminal_instrument_elem_selection(
        self,
        tree: TerminalTreeView,
        terminal_tree_traversal: tuple[str, tuple[str]] | tuple[str, str],
        instr_elem: Metadatable | Parameter,
    ) -> bool:
        """
        For a selected item in terminal_tree (given via terminal_tree_traversal) and selected item in instrument_tree (instr_elem)
        do the mapping process. Behaviour based on combinations like: direct mapping between parameters, automap to all children etc.
        """
        mapped = False
        if isinstance(terminal_tree_traversal[1], str) and isinstance(instr_elem, Parameter):
            # map directly - should mapping be forbidden if _mapping attribute of Parameter does not fit?
            tree.map_parameter(instr_elem, terminal_tree_traversal)
            mapped = True
            # self.add_terminal_to_view(parent, row, f"{terminal[0]}.{terminal[1]}")  # maybe later - if used this should be done somewhere else (map_parameter)
        elif isinstance(terminal_tree_traversal[1], tuple) and isinstance(instr_elem, (InstrumentModule, Instrument)):
            # map automatically as much as possible
            all_params = filter_flatten_parameters(instr_elem)
            child_params_all = {
                param_name: param
                for param_name, param in all_params.items()
                if instr_elem in param.instrument.ancestors
            }

            # try to map chosen terminal_parameters with child parameters of instr_elem if uniquely possible
            possible_mappings = get_possible_mapping_candidates(terminal_tree_traversal[1], child_params_all)
            for terminal_param_name, parameter_candidates in possible_mappings.items():
                if len(parameter_candidates) == 1:
                    # unique mapping - iterate over terminal_parameters of terminal

                    terminal = get_child(tree.model().invisibleRootItem(), terminal_tree_traversal[0])
                    terminal_param = get_child(terminal, terminal_param_name)
                    tree.map_parameter(parameter_candidates[0], terminal_param.source)
                    mapped = True

        elif isinstance(terminal_tree_traversal[1], str) and isinstance(instr_elem, (InstrumentModule, Instrument)):
            # map automatically to one parameter
            all_params = filter_flatten_parameters(instr_elem)
            child_params_all = {
                param_name: param
                for param_name, param in all_params.items()
                if instr_elem in param.instrument.ancestors
            }
            possible_mappings = get_possible_mapping_candidates((terminal_tree_traversal[1],), child_params_all)

            # dict is always of size 1 (only one terminal_parameter)
            terminal_param_name = terminal_tree_traversal[1]
            possible_instrument_parameters = possible_mappings[terminal_param_name]
            if len(possible_instrument_parameters) == 1:
                if terminal_param_name == terminal_tree_traversal[1]:
                    tree.map_parameter(possible_instrument_parameters[0], terminal_tree_traversal)
                    mapped = True
        elif isinstance(terminal_tree_traversal[1], tuple) and isinstance(instr_elem, Parameter):
            # map parameter of chosen terminal to chosen instrument parameter
            parameter = instr_elem
            terminal_parameters = terminal_tree_traversal[1]
            if hasattr(parameter, "_mapping"):
                if parameter._mapping in terminal_parameters:
                    tree.map_parameter(parameter, (terminal_tree_traversal[0], parameter._mapping))
                    mapped = True

        return mapped

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Start mapping based on selected element in terminal tree (dragged from) and selected element in instrument tree (dropped to)
        Different mapping behaviour depending on the combination of "types" of elements (see map_given_terminal_instrument_elem_selection)
        """
        dest_index = self.indexAt(event.pos())
        if not dest_index.isValid():
            return

        if dest_index.column() != 0:
            instr_elem = self.model().itemFromIndex(dest_index.siblingAtColumn(0))
        else:
            instr_elem = self.model().itemFromIndex(dest_index)

        tree = event.source()
        assert isinstance(tree, TerminalTreeView)
        terminal_tree_idx = tree.currentIndex().siblingAtColumn(0)
        terminal_elem = tree.model().itemFromIndex(terminal_tree_idx)

        # communicate selected instrument/terminal to main window. drag_terminal_drop_instr_slot catches this signal and does mapping
        self.drag_terminal_drop_instr.emit(instr_elem, terminal_elem)

    def add_terminal_to_view(self, parent, row, terminal_name):
        model = self.model()
        # Create cell, if its not there yet
        if not model.hasIndex(row, 1, parent):
            model.insertColumn(1, parent)
        # Add terminal name to instrument row
        model.setData(parent.child(row, 1), terminal_name)

    def import_data(self, components: Mapping[Any, Metadatable]) -> None:
        """Build up tree with provided instruments."""
        parent = self.model().invisibleRootItem()
        seen: set[int] = set()

        def recurse(node, parent) -> None:
            """Recursive part of the function. Fills instrument_parameters dict."""
            # TODO: Change this try-except-phrase to match-case, when switched to Python3.10
            try:
                values = list(node.values()) if isinstance(node, dict) else list(node)
            except KeyError:
                values = [node]
            except IndexError:
                values = []

            for value in values:
                if isinstance(value, Parameter):
                    item = QStandardItem(value.name)
                    item.source = value
                    parent.appendRow(item)
                else:
                    if isinstance(value, Iterable) and not isinstance(value, str):
                        recurse(value, parent)
                    elif isinstance(value, Metadatable):
                        # Object of some Metadatable type, try to get __dict__ and _filter_flatten_parameters
                        try:
                            value_hash = hash(value)
                            if not parent is self.model().invisibleRootItem():
                                try:
                                    if value in parent.source.ancestors:
                                        continue

                                    if len(value.ancestors) >= 2:
                                        if not value.ancestors[1] == parent.source:
                                            # print(f"{value.full_name} is not a direct decendant of {parent.source.full_name}")
                                            continue
                                except AttributeError:
                                    continue

                            if value_hash not in seen:
                                seen.add(value_hash)
                                item = QStandardItem(value.name)
                                item.source = (
                                    value  # TODO: does it make sense to save value as .data()? or is .source ok?
                                )
                                parent.appendRow(item)
                                recurse(vars(value), item)
                                # if item has no parameters (item has no children after recurse) delete (last) row
                                if not item.hasChildren():
                                    num_rows = parent.rowCount()
                                    parent.removeRow(num_rows - 1)
                        except TypeError:
                            # End of tree
                            pass

        recurse(components, parent)


class MainWindow(QMainWindow):
    """
    Main window containing the two trees and buttons
    """

    def __init__(
        self,
        components,
        terminal_parameters,
        monitoring: bool = False,
    ):
        super().__init__()
        self.components = components
        self.setWindowTitle("Mapping GUI")

        container = QWidget()
        layout = QVBoxLayout()

        # Tree views
        self.instrument_tree = InstrumentTreeView()
        self.instrument_tree.import_data(components)
        self.instrument_tree.setSelectionMode(self.instrument_tree.SelectionMode(1))
        self.instrument_tree.drag_terminal_drop_instr.connect(self.drag_terminal_drop_instr_slot)
        self.instrument_tree.setSizePolicy(QSizePolicy.Policy(3), QSizePolicy.Policy(3))

        self.terminal_tree = TerminalTreeView(monitoring)
        self.terminal_tree.import_data(terminal_parameters)
        self.terminal_tree.instrument_model = self.instrument_tree.model()
        self.terminal_tree.setSelectionMode(self.terminal_tree.SelectionMode(1))
        self.terminal_tree.selected_terminal_tree_elem = None
        self.terminal_tree.expandAll()
        self.terminal_tree.resizeColumnToContents(0)
        self.terminal_tree.collapseAll()
        self.terminal_tree.resizeColumnToContents(1)
        self.terminal_tree.setSizePolicy(QSizePolicy.Policy(3), QSizePolicy.Policy(3))

        upper_widget = QSplitter(Qt.Horizontal)
        upper_widget.addWidget(self.terminal_tree)
        upper_widget.addWidget(self.instrument_tree)
        upper_widget.setChildrenCollapsible(False)

        # Buttons
        button_container = QWidget()
        button_layout = QHBoxLayout()

        self.button_map_auto = QPushButton("Map automatically (a)")
        self.button_map_auto.clicked.connect(self.map_automatically)

        self.button_reset_mapping = QPushButton("Reset mapping (r)")
        self.button_reset_mapping.clicked.connect(self.reset_mapping)

        self.button_unfold_terminals = QPushButton("Unfold (u)")
        self.button_unfold_terminals.clicked.connect(self.unfold_terminals)

        self.button_exit = QPushButton("Exit (e)")
        self.button_exit.clicked.connect(self.close)

        # Button layout
        button_layout.addWidget(self.button_map_auto)
        button_layout.addWidget(self.button_reset_mapping)
        button_layout.addWidget(self.button_unfold_terminals)
        button_layout.addStretch()
        button_layout.addWidget(self.button_exit)
        button_container.setLayout(button_layout)
        button_container.setSizePolicy(QSizePolicy.Policy(3), QSizePolicy.Policy(0))

        # Menu
        menu = self.menuBar()

        # Monitoring
        Monitoring_menu = menu.addMenu("Monitoring")
        self.monitoring_enable = monitoring
        self.terminal_tree.monitoring_get_type = "get"
        if monitoring:
            self.terminal_tree.monitoring_timer.start(1000)

        # Monitoring - Refresh delay
        self.monitoring_refresh_delay = QAction("Refresh Delay", self)
        self.monitoring_refresh_delay.triggered.connect(self.set_refresh_rate)
        Monitoring_menu.addAction(self.monitoring_refresh_delay)

        # Monitoring - Enable/Disable
        if monitoring:
            self.toggle_monitoring_action = QAction("Disable", self)
        else:
            self.toggle_monitoring_action = QAction("Enable", self)

        self.toggle_monitoring_action.triggered.connect(self.toggle_monitoring)
        Monitoring_menu.addAction(self.toggle_monitoring_action)

        # Monitoring - Get type (from cache or by get() command)
        get_type_menu = Monitoring_menu.addMenu("Get type")
        self.use_cache_action = QAction("Only Cached values", self)
        self.use_get_action = QAction("Get command", self)
        self.use_cache_action.setCheckable(True)
        self.use_get_action.setCheckable(True)
        self.use_get_action.setChecked(True)
        get_type_menu.addAction(self.use_cache_action)
        get_type_menu.addAction(self.use_get_action)
        self.use_get_action.triggered.connect(self.monitoring_set_get_type)
        self.use_cache_action.triggered.connect(self.monitoring_set_cache_type)

        # Help button
        help_action = menu.addAction("Help")
        help_action.triggered.connect(self.show_help)

        # Main layout
        layout.addWidget(upper_widget)
        layout.addWidget(button_container)

        container.setLayout(layout)
        self.setCentralWidget(container)
        self.terminal_tree.setFocus()
        idx = self.terminal_tree.model().invisibleRootItem().child(0, 0).index()
        self.terminal_tree.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self.terminal_tree.setCurrentIndex(idx)
        self.resize(QDesktopWidget().availableGeometry(self).size() * 0.45)

        self.terminal_parameters = terminal_parameters

        self.terminal_tree.update_tree()

    def closeEvent(self, ev) -> None:
        """
        Before closing check if some things about the mapping (fully mapped, no duplicates). Then close the application
        """
        all_mapped = True
        parameter_duplicates = {}
        for terminal_params in self.terminal_parameters.values():
            for param in terminal_params.values():
                if param is None:
                    all_mapped = False
                elif isinstance(param, Parameter):
                    param_hash = hash(param)
                    if param_hash in parameter_duplicates:
                        parameter_duplicates[param_hash].append(param)
                    else:
                        parameter_duplicates[param_hash] = [param]
                else:
                    raise TypeError("Gate parameters have to be either None or of type Parameter.")

        # Not every terminal parameter is mapped
        if not all_mapped:
            dialog = MessageBox_notallmapped(self)
            answer = dialog.exec()
            if not answer == QMessageBox.Yes:
                ev.ignore()
                return

        # Give warning if there are duplicates
        for items_with_param in parameter_duplicates.values():
            if len(items_with_param) != 1:
                dialog = MessageBox_duplicates(self)
                answer = dialog.exec()
                # answer = dialog.question(self, "", "Do you really want to stop the mapping process? Multiple terminal parameters are mapped to the same parameter!",  QMessageBox.Yes | QMessageBox.No)
                if not answer == QMessageBox.Yes:
                    ev.ignore()
                    return

        # properly close application
        self.terminal_tree.monitoring_timer.stop()
        QApplication.exit()
        return super().closeEvent(ev)

    def show_help(self):
        gui_help_txt_path = __file__.replace("mapping_gui.py", "GUI_help.txt")
        with open(gui_help_txt_path) as f:
            help_txt = f.read()

        self.help_window = ScrollLabel(help_txt)

        self.help_window.show()

    def monitoring_set_get_type(self):
        self.use_get_action.setChecked(True)
        self.use_cache_action.setChecked(False)
        self.terminal_tree.monitoring_get_type = "get"

    def monitoring_set_cache_type(self):
        self.use_cache_action.setChecked(True)
        self.use_get_action.setChecked(False)
        self.terminal_tree.monitoring_get_type = "cache"

    @pyqtSlot(QStandardItem, QStandardItem)
    def drag_terminal_drop_instr_slot(self, instr_elem, terminal_elem):
        """
        This receives signal from InstrumentTree if two elements were paired via drag and drop.
        Mapping is carried out from here (mainwindow)
        """
        self.map_given_terminal_instrument_elem_selection(terminal_elem.source, instr_elem.source)
        self.terminal_tree.update_tree()

    def toggle_monitoring(self):
        if self.monitoring_enable:
            self.terminal_tree.monitoring_timer.stop()
            self.monitoring_enable = False
            self.toggle_monitoring_action.setText("Enable")
        else:
            self.terminal_tree.monitoring_timer.start(1000)
            self.monitoring_enable = True
            self.toggle_monitoring_action.setText("Disable")

        self.terminal_tree.setColumnHidden(2, not self.monitoring_enable)

    def set_refresh_rate(self):
        """
        Set refresh rate of monitoring via input dialog.
        """
        val, ok = QInputDialog.getDouble(
            self, "Refresh delay [s]", "Refresh delay [s]", 1, 0.01, 100, 2, Qt.WindowFlags(), 0.1
        )
        if ok:
            self.terminal_tree.monitoring_timer.stop()
            self.terminal_tree.showColumn(2)
            self.toggle_monitoring_action.setText("Disable")
            self.terminal_tree.monitoring_timer.start(int(val * 1000))
            self.monitoring_enable = True

    def map_parameter(self, parameter: Parameter, traverse: tuple[str, str]):
        """
        Maps a instrument parameter to a specific terminal parameter accessed by the given traversal info.
        Doesn't do much anymore, but I kept this around for slightly better readability (and easier refactoring if necessary)
        """
        self.terminal_parameters[traverse[0]][traverse[1]] = parameter

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handles keyboard shortcuts and mapping using enter key. Selecting an instrument in the terminal_tree and pressing enter will switch focus to the
        instrument_tree and select a suitable mapping candidate. The user can change the selection and press enter again to do the mapping. The focus switches
        back to the terminal_tree and a new terminal is selected.
        """
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            sel_idx = []
            for idx in self.terminal_tree.selectedIndexes():
                if idx.column() == 0:
                    sel_idx.append(idx)

            if self.terminal_tree.hasFocus() and len(sel_idx) == 1:
                # Element in terminal tree has been selected.

                # select element and switch focus to instruments
                self.terminal_tree.selected_terminal_tree_elem = sel_idx[0]
                selected_item = self.terminal_tree.model().itemFromIndex(self.terminal_tree.selected_terminal_tree_elem)
                self.instrument_tree.setFocus()

                # select instrument element based on predicted mapping
                if selected_item.hasChildren():
                    _terminal_params = get_children(selected_item)
                    terminal_params = []
                    for terminal_param in _terminal_params:
                        terminal_params.append(terminal_param.source[1])
                else:
                    terminal_params = [selected_item.source[1]]

                perfect_mappings = self.instrument_tree.get_perfect_mappings(terminal_params)

                # set idx to first perfect_mapping that has not yet been fully mapped to a terminal
                idx = self.instrument_tree.model().invisibleRootItem().child(0, 0).index()  # default
                for perfect_mapping in perfect_mappings:
                    instr_mapped = False
                    for terminal in get_children(self.terminal_tree.model().invisibleRootItem()):
                        if (
                            self.terminal_tree.model().data(terminal.index().siblingAtColumn(1))
                            == perfect_mapping.source.full_name
                        ):
                            instr_mapped = True
                            break

                    if not instr_mapped:
                        idx = perfect_mapping.index()
                        break

                self.instrument_tree.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
                self.instrument_tree.setCurrentIndex(idx)
            elif (
                self.instrument_tree.hasFocus()
                and not self.terminal_tree.selected_terminal_tree_elem is None
                and len(self.instrument_tree.selectedIndexes()) == 1
            ):
                # Element in instrument tree selected. Start mapping
                terminal_elem = self.terminal_tree.model().itemFromIndex(self.terminal_tree.selected_terminal_tree_elem)

                idx_instr = self.instrument_tree.selectedIndexes()[0]
                instr_elem = self.instrument_tree.model().itemFromIndex(idx_instr)

                # Check if it is already mapped to display dialog
                any_mapped = False
                if type(terminal_elem.source[1]) is str:
                    terminal_params = (terminal_elem.source[1],)
                else:
                    terminal_params = terminal_elem.source[1]

                for terminal_param in terminal_params:
                    if not self.terminal_parameters[terminal_elem.source[0]][terminal_param] is None:
                        any_mapped = True
                        break

                    if any_mapped:
                        break

                if any_mapped:
                    dialog = MessageBox_overwrite(self)
                    answer = dialog.exec()
                    if answer == QMessageBox.Yes:
                        do_mapping = True
                    else:
                        do_mapping = False
                else:
                    do_mapping = True

                if do_mapping:
                    mapped = self.map_given_terminal_instrument_elem_selection(terminal_elem.source, instr_elem.source)
                    if mapped:
                        self.terminal_tree.selected_terminal_tree_elem = None

                        # select next not fully mapped terminal (quick navigation)
                        self.terminal_tree.setFocus()
                        for terminal_name, terminal in self.terminal_tree.terminal_parameters.items():
                            all_mapped = True
                            for terminal_param_name, terminal_param in terminal.items():
                                if terminal_param is None:
                                    all_mapped = False
                                    break

                            if not all_mapped:
                                terminal_elem = get_child(self.terminal_tree.model().invisibleRootItem(), terminal_name)

                                self.terminal_tree.selectionModel().select(
                                    terminal_elem.index(), QItemSelectionModel.SelectionFlag.ClearAndSelect
                                )
                                self.terminal_tree.setCurrentIndex(terminal_elem.index())
                                break
            # self.terminal_tree.update_tree()
        elif event.key() == Qt.Key_A:
            self.map_automatically()
        elif event.key() == Qt.Key_R:
            self.reset_mapping()
        elif event.key() == Qt.Key_E:
            self.close()
        elif event.key() == Qt.Key_U:
            self.unfold_terminals()

        self.terminal_tree.update_tree()

        return super().keyPressEvent(event)

    def map_given_terminal_instrument_elem_selection(
        self,
        terminal_tree_traversal: tuple[str, tuple[str]] | tuple[str, str],
        instr_elem: Metadatable | Parameter,
    ) -> bool:
        """
        For a selected item in terminal_tree (given via terminal_tree_traversal) and selected item in instrument_tree (instr_elem)
        do the mapping process. Behaviour based on combinations like: direct mapping between parameters, automap to all children etc.
        """
        tree = self.terminal_tree
        mapped = False
        if isinstance(terminal_tree_traversal[1], str) and isinstance(instr_elem, Parameter):
            # map directly
            self.map_parameter(instr_elem, terminal_tree_traversal)
            mapped = True
        elif isinstance(terminal_tree_traversal[1], tuple) and isinstance(instr_elem, (InstrumentModule, Instrument)):
            # map automatically as much as possible
            all_params = filter_flatten_parameters(instr_elem)
            child_params_all = {
                param_name: param
                for param_name, param in all_params.items()
                if instr_elem in param.instrument.ancestors
            }

            # try to map chosen terminal_parameters with child parameters of instr_elem if uniquely possible
            possible_mappings = get_possible_mapping_candidates(terminal_tree_traversal[1], child_params_all)
            for terminal_param_name, parameter_candidates in possible_mappings.items():
                if len(parameter_candidates) == 1:
                    # unique mapping - iterate over terminal_parameters of terminal

                    terminal = get_child(tree.model().invisibleRootItem(), terminal_tree_traversal[0])
                    terminal_param = get_child(terminal, terminal_param_name)
                    self.map_parameter(parameter_candidates[0], terminal_param.source)
                    mapped = True

        elif isinstance(terminal_tree_traversal[1], str) and isinstance(instr_elem, (InstrumentModule, Instrument)):
            # map automatically to one parameter
            all_params = filter_flatten_parameters(instr_elem)
            child_params_all = {
                param_name: param
                for param_name, param in all_params.items()
                if instr_elem in param.instrument.ancestors
            }
            possible_mappings = get_possible_mapping_candidates((terminal_tree_traversal[1],), child_params_all)

            # dict is always of size 1 (only one terminal_parameter)
            terminal_param_name = terminal_tree_traversal[1]
            possible_instrument_parameters = possible_mappings[terminal_param_name]
            if len(possible_instrument_parameters) == 1:
                if terminal_param_name == terminal_tree_traversal[1]:
                    self.map_parameter(possible_instrument_parameters[0], terminal_tree_traversal)
                    mapped = True
        elif isinstance(terminal_tree_traversal[1], tuple) and isinstance(instr_elem, Parameter):
            # map parameter of chosen terminal to chosen instrument parameter
            parameter = instr_elem
            terminal_parameters = terminal_tree_traversal[1]
            if hasattr(parameter, "_mapping"):
                if parameter._mapping in terminal_parameters:
                    self.map_parameter(parameter, (terminal_tree_traversal[0], parameter._mapping))
                    mapped = True

        return mapped

    def unfold_terminals(self):
        """
        Unfolds all terminals in the terminal_tree (quickly make everything visible). Collapse all if already unfolded
        """
        all_expanded = True
        for terminal in get_children(self.terminal_tree.model().invisibleRootItem()):
            if not self.terminal_tree.isExpanded(terminal.index()):
                all_expanded = False
                break

        if all_expanded:
            self.terminal_tree.collapseAll()
        else:
            self.terminal_tree.expandAll()

        self.terminal_tree.update_tree()

    def map_automatically(self):
        """
        Map all terminals automatically. The algorithm used is (almost) equivalent to selecting the first terminal and repeatedly
        pressing the enter key until the last terminal (in the tree) is mapped. This works best if the terminals are in
        the same order as the instruments that they should be mapped to. Additionally the terminals mapping to channels of
        an instrument should be ordered the same as the channels (up to the driver but usually something like 0,1,2,...)
        """
        self.reset_mapping()
        for terminal_name, terminal in self.terminal_parameters.items():
            _perfect_mappings = self.instrument_tree.get_perfect_mappings(terminal.keys())

            # filtering out parent channels (instrument) that would also lead to unique mapping
            # This is an edge case for instruments that have a single channel of some type (then both the channel and the instrument are uniquely mappable)
            perfect_mappings = []
            for _perfect_mapping1 in _perfect_mappings:
                # check if there is a mapping which has _perfect_mapping1 as parent
                child_in_perfect_mappings = False
                for _perfect_mapping2 in _perfect_mappings:
                    if _perfect_mapping1.source is _perfect_mapping2.source.parent:
                        child_in_perfect_mappings = True
                        break

                if not child_in_perfect_mappings:
                    perfect_mappings.append(_perfect_mapping1)

            # map to first perfect_mapping that has not yet been fully mapped to a terminal
            for perfect_mapping in perfect_mappings:
                perfect_mapping_channel_name = perfect_mapping.source.full_name
                instr_mapped = False
                # find out if perfect mapping candidate has been already perfectly mapped to another terminal
                for _terminal_name, _terminal in self.terminal_parameters.items():
                    all_mapped_to_same_channel = True
                    for terminal_param_name, param in _terminal.items():
                        if not param is None:
                            if param.instrument.full_name != perfect_mapping_channel_name:
                                all_mapped_to_same_channel = False
                                break
                        else:
                            all_mapped_to_same_channel = False
                            break

                    if all_mapped_to_same_channel:
                        instr_mapped = True
                        break

                if not instr_mapped:
                    # map to channel
                    terminal_element = (terminal_name, tuple(terminal.keys()))
                    mapped = self.map_given_terminal_instrument_elem_selection(terminal_element, perfect_mapping.source)
                    break

        self.terminal_tree.update_tree()

    # Not used anymore. Unique, but algorithm to weak to be useful in practise
    def map_automatically_unique(self):
        """
        Automatically map all unique terminal_parameter instrument_parameter pairs. If there are multiple terminal_parameters
        with the same name their unique mapping is impossible.
        """
        # call get_possible_mapping_candidates for each terminal
        terminal_mapping_candidates = {}
        terminal_parameters_occurances = {}
        all_params = filter_flatten_parameters(self.components)
        for terminal_name, terminal_params in self.terminal_tree.terminal_parameters.items():
            terminal_mapping_candidates[terminal_name] = get_possible_mapping_candidates(
                terminal_params.keys(), all_params
            )
            for terminal_param in terminal_params.keys():
                if terminal_param in terminal_parameters_occurances.keys():
                    terminal_parameters_occurances[terminal_param] += 1
                else:
                    terminal_parameters_occurances[terminal_param] = 1

        # a terminal parameter can be mapped uniquely if its mapped parameter only appears once in the candidate dictionaries of all terminals
        # For a unique mapping between terminal parameter and instrument parameter:
        #   1. a terminal parameter (name) must only occur a single time for all terminals
        #   2. unique mapping from terminal parameter to instrument_parameter (true if list of candidates has length 1)
        for terminal, terminal_params in self.terminal_tree.terminal_parameters.items():
            all_mapped = True
            for terminal_param in terminal_params.keys():
                if not terminal_parameters_occurances[terminal_param] == 1:
                    all_mapped = False
                    continue
                if not len(terminal_mapping_candidates[terminal][terminal_param]) == 1:
                    all_mapped = False
                    continue

                self.map_parameter(terminal_mapping_candidates[terminal][terminal_param][0], (terminal, terminal_param))

            if all_mapped:
                self.terminal_tree.collapse(get_child(self.terminal_tree.model().invisibleRootItem(), terminal).index())
            else:
                self.terminal_tree.expand(get_child(self.terminal_tree.model().invisibleRootItem(), terminal).index())

        self.terminal_tree.update_tree()

    def reset_mapping(self):
        """
        Reset all mappings. Reset dictionary which actually holds the mapping. Reset Tree representation.
        """
        for terminal_name, terminal_params in self.terminal_parameters.items():
            self.terminal_parameters[terminal_name] = {
                terminal_param_name: None for terminal_param_name in terminal_params.keys()
            }

        self.terminal_tree.selected_terminal_tree_elem = None
        self.terminal_tree.update_tree()
        self.terminal_tree.setFocus()


def get_possible_mapping_candidates(
    terminal_params: tuple[str], instrument_parameters: Mapping[Any, Parameter]
) -> Mapping[Any, list[Parameter]]:
    """
    For input terminal and collection of instrument_parameters: get dictionary with key: terminal parameter name, value: list(parameters that can be mapped to that terminal parameter)
    Similar to base.py _map_gate_to_instrument
    """
    mapped_parameters = {
        key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")
    }
    mapping = {}
    for terminal_param in terminal_params:
        candidates = [parameter for parameter in mapped_parameters.values() if parameter._mapping == terminal_param]
        mapping[terminal_param] = candidates

    return mapping


def get_children(parent: QStandardItem) -> list[QStandardItem]:
    """Return list of children (QStandardItem) of parent"""
    children = []
    num_rows = parent.rowCount()
    if num_rows == 0:
        return []

    _row = 0
    while True:
        children.append(parent.child(_row, 0))
        if _row == num_rows - 1:
            break

        _row = _row + 1

    return children


def get_child(parent: QStandardItem, text: str) -> QStandardItem | None:
    for child in get_children(parent):
        if child.text() == text:
            return child

    return None


def traverse_tree(root: QStandardItem, traversal_names: list(str)) -> QStandardItem:
    def traverse(parent, names):
        if names == []:
            return parent

        child = get_child(parent, names.pop(0))
        if child == None:
            print("problem")
        else:
            return traverse(child, names)

    return traverse(root, traversal_names)


class ScrollLabel(QScrollArea):
    """
    Scrollable Label for displaying help window
    """

    def __init__(self, text: str):
        QScrollArea.__init__(self)

        self.setWidgetResizable(True)

        self.label = QLabel(self)
        self.setWidget(self.label)
        self.label.setIndent(10)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setWordWrap(True)

        self.label.setText(text)

    def setText(self, text):
        self.label.setText(text)


class MessageBox_notallmapped(QMessageBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Warning! Not all parameters mapped!")
        self.setIcon(QMessageBox.Warning)
        self.setText("Do you really want to stop the mapping process? Not all parameters are mapped!")
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


class MessageBox_duplicates(QMessageBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Warning! Duplicate mapping!")
        self.setIcon(QMessageBox.Warning)
        self.setText(
            "Do you really want to stop the mapping process? Multiple terminal parameters are mapped to the same parameter!"
        )
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


class MessageBox_overwrite(QMessageBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Warning! Duplicate mapping!")
        self.setIcon(QMessageBox.Warning)
        self.setText("Do you really want to change/overwrite the existing mapping?")
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


def map_terminals_gui(
    components: Mapping[Any, Metadatable],
    terminal_parameters: TerminalParameters,
    existing_terminal_parameters: TerminalParameters | None = None,
    metadata: Metadata | None = None,
    monitoring: bool = True,
    skip_gui_if_mapped: bool = True,
) -> None:
    """
    Maps the terminals, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        terminal_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Terminals, as defined in the measurement script
        existing_terminal_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]] | None): Already existing mapping
                that is used to automatically create the mapping for already known terminals without user input.
        metadata (Metadata | None): If provided, add mapping to the metadata object.
        monitoring: if True the mapped parameters are periodically read out (either by get command (default) or cached value)
        skip_gui_if_mapped: if True and existing_terminal_parameters completely covers all terminal_parameters, dont open gui and continue
    """
    if existing_terminal_parameters is None:
        # reset in case there is already some mapping
        for terminal_name, parameter_mapping in terminal_parameters.items():
            for terminal_parameter, instr_parameter in parameter_mapping.items():
                terminal_parameters[terminal_name][terminal_parameter] = None

        run_gui = True
    else:
        # try to get the mapping from an existing mapping (if the respective terminal name exists)
        for terminal_name, terminal_params in terminal_parameters.items():
            if terminal_name in existing_terminal_parameters:
                for terminal_param_name, mapped_param in terminal_params.items():
                    if terminal_param_name in existing_terminal_parameters[terminal_name]:
                        terminal_parameters[terminal_name][terminal_param_name] = existing_terminal_parameters[
                            terminal_name
                        ][terminal_param_name]

        all_mapped = True
        for terminal_params in terminal_parameters.values():
            for param in terminal_params.values():
                if param is None:
                    all_mapped = False
                    break

            if not all_mapped:
                break

        run_gui = not all_mapped

    if run_gui or not skip_gui_if_mapped:
        if QApplication.instance() is None:
            app = QApplication([])
        else:
            app = QApplication.instance()

        w = MainWindow(
            components,
            terminal_parameters,
            monitoring=monitoring,
        )

        w.show()
        app.exec_()

    # if metadata is provided, add mapping to metadata object
    if metadata is not None:
        j = json.dumps(terminal_parameters, default=lambda o: str(o))
        metadata.add_terminal_mapping(j, "custom-mapping")

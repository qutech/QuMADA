from __future__ import annotations

from collections.abc import Iterable, Mapping
from threading import Event, Thread
from typing import Any

from PyQt5.QtCore import (
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QFocusEvent,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import (
    QApplication,
    QDesktopWidget,
    QGridLayout,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QTreeView,
    QWidget,
)
from qcodes.instrument.channel import InstrumentModule
from qcodes.instrument.instrument import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.station import Station
from qcodes.tests.instrument_mocks import DummyChannelInstrument
from qcodes.utils.metadata import Metadatable
from qtools_metadata.metadata import Metadata

from qtools.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qtools.instrument.mapping import DUMMY_CHANNEL_MAPPING, DUMMY_DMM_MAPPING
from qtools.instrument.mapping.base import (
    add_mapping_to_instrument,
    filter_flatten_parameters,
)
from qtools.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qtools.measurement.scripts.generic_measurement import Generic_1D_Sweep

TerminalParameters = Mapping[Any, Mapping[Any, Parameter] | Parameter]


class TerminalTreeView(QTreeView):
    """
    QTreeView, that displays qtools `TerminalParameters` (`Mapping[Any, Mapping[Any, Parameter] | Parameter]`) datastructure.
    Items are draggable to map them to instruments.
    """

    # TODO: necessary?
    # class DragStandardItem(QStandardItem):
    #     """Draggable QStandardItem from TerminalTreeView."""

    #     def mouseMoveEvent(self, event: QMouseEvent) -> None:
    #         """Initiate drag and set preview pixmap."""
    #         if event.buttons() == Qt.LeftButton:
    #             drag = QDrag(self)
    #             mime = QMimeData()
    #             drag.setMimeData(mime)
    #             pixmap = QPixmap(self.size())
    #             self.render(pixmap)
    #             drag.setPixmap(pixmap)

    #             drag.exec_(Qt.MoveAction)

    def __init__(self):
        super().__init__()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Terminal", "Mapped Instrument"])
        self.setModel(model)

        self.terminal_parameters = None

        self.selected_terminal_tree_elem = None

        # self.setAcceptDrops(True)
        self.setDragEnabled(True)

    # forward keypressevents "hack". keyPressEvent of QMainWindow doesnt fire for letter keys
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_A or event.key() == Qt.Key_R or event.key() == Qt.Key_E or event.key() == Qt.Key_U:
            self.nextInFocusChain().keyPressEvent(event)
        else:
            return super().keyPressEvent(event)

    # overwrite default double click event behaviour
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pass

    def update_tree(self):
        """
        Set labels and coloring based on state (terminal_parameters)
        """
        # Set mapped instrument labels and colors, set colors for duplicates
        tree = self.model()
        parameter_duplicates = {}
        for terminal in get_children(tree.invisibleRootItem()):
            tree.setData(terminal.index(), QBrush(QColor(255, 255, 255)), Qt.BackgroundRole)
            tree.setData(terminal.index().siblingAtColumn(1), QBrush(QColor(255, 0, 0)), Qt.BackgroundRole)
            tree.setData(terminal.index().siblingAtColumn(1), "")
            all_mapped = True
            any_mapped = False
            channels = set()
            for terminal_param in get_children(terminal):
                tree.setData(terminal_param.index(), QBrush(QColor(255, 255, 255)), Qt.BackgroundRole)
                tree.setData(terminal_param.index().siblingAtColumn(1), QBrush(QColor(255, 0, 0)), Qt.BackgroundRole)
                tree.setData(terminal_param.index().siblingAtColumn(1), "")
                param = self.terminal_parameters[terminal_param.source[0]][terminal_param.source[1]]
                if not param is None:
                    if isinstance(param, Parameter):
                        param_hash = hash(param)
                        if param_hash in parameter_duplicates:
                            parameter_duplicates[param_hash].append(terminal_param)
                        else:
                            parameter_duplicates[param_hash] = [terminal_param]

                        param_bound_instr_full_name = param.instrument.full_name
                        channels.add(param_bound_instr_full_name)
                        tree.setData(terminal_param.index().siblingAtColumn(1), param_bound_instr_full_name)
                        tree.setData(
                            terminal_param.index().siblingAtColumn(1), QBrush(QColor(0, 255, 0)), Qt.BackgroundRole
                        )
                        any_mapped = True
                    else:
                        raise TypeError("Gate parameters has to be either None or of type Parameter.")
                else:
                    all_mapped = False

            # color and label terminals
            if all_mapped:
                tree.setData(terminal.index().siblingAtColumn(1), QBrush(QColor(0, 255, 0)), Qt.BackgroundRole)
                if len(channels) == 1:
                    tree.setData(terminal.index().siblingAtColumn(1), channels.pop())
                else:
                    tree.setData(terminal.index().siblingAtColumn(1), "")
            elif any_mapped:
                tree.setData(terminal.index().siblingAtColumn(1), QBrush(QColor(255, 255, 0)), Qt.BackgroundRole)

        # color duplicates
        for items_with_param in parameter_duplicates.values():
            if len(items_with_param) != 1:
                for duplicate in items_with_param:
                    tree.setData(duplicate.index(), QBrush(QColor(255, 192, 203)), Qt.BackgroundRole)
                    tree.setData(duplicate.parent().index(), QBrush(QColor(255, 192, 203)), Qt.BackgroundRole)

        # any item selected?
        if not self.selected_terminal_tree_elem is None:
            tree.setData(self.selected_terminal_tree_elem, QBrush(QColor(0, 0, 255)), Qt.BackgroundRole)

        self.resizeColumnToContents(1)

    def import_data(self, terminal_parameters: TerminalParameters) -> None:
        """Build up tree with provided terminal parameters."""
        root = self.model().invisibleRootItem()
        self.terminal_parameters = terminal_parameters
        for terminal_name, terminal_params in terminal_parameters.items():
            # item = TerminalTreeView.DragStandardItem(terminal_name)  # TODO: check if QStandardItem or DragStandardItem necessary?
            item = QStandardItem(terminal_name)
            item.source = (terminal_name, tuple(terminal_params.keys()))
            root.appendRow(item)

            # if isinstance(terminal_params, Mapping):
            for terminal_param_name in terminal_params.keys():
                # subitem = TerminalTreeView.DragStandardItem(terminal_param_name)
                subitem = QStandardItem(terminal_param_name)
                subitem.source = (terminal_name, terminal_param_name)
                item.appendRow(subitem)

            qidx = item.index()
            self.model().setData(qidx.siblingAtColumn(1), QBrush(QColor(255, 0, 0)), Qt.BackgroundRole)
            self.model().insertColumn(1, qidx)
            for i in range(len(terminal_params.keys())):
                self.model().setData(qidx.child(i, 1), "")
                self.model().setData(qidx.child(i, 1), QBrush(QColor(255, 0, 0)), Qt.BackgroundRole)


def get_possible_mapping_candidates(
    terminal_params: tuple[str], instrument_parameters: Mapping[Any, Parameter]
) -> Mapping[Any, list[Parameter]]:
    """
    For input terminal, collection of instrument_parameters: get dictionary with key: terminal parameter name, value: list(parameters that can be mapped to that terminal parameter)
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
            ret_val = super().keyPressEvent(event)
            self.previousInFocusChain().keyPressEvent(event)
            return ret_val
        else:
            return super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Check for correct mime type to accept the dragging event."""
        # TODO: Check mime type for correct type
        event.accept()
        # event.acceptProposedAction()  # TODO: what is the difference to accept? Why does accept make problems during dragging sometimes..

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
        elif isinstance(terminal_tree_traversal[1], tuple) and isinstance(instr_elem, InstrumentModule | Instrument):
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

        elif isinstance(terminal_tree_traversal[1], str) and isinstance(instr_elem, InstrumentModule | Instrument):
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
        terminal_tree_idx = tree.currentIndex().siblingAtColumn(0)
        assert isinstance(tree, TerminalTreeView)
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

    # TODO: testing with real instruments (decadac!)
    def import_data(self, components: Mapping[Any, Metadatable]) -> None:
        """Build up tree with provided instruments."""
        parent = self.model().invisibleRootItem()
        seen: set[int] = set()

        # this recurse method creates a tree. It could happen that an instrument has a class hierarchy that is not a tree.
        # e.g. decadac: contains all slots and all channels which are Metadatable each (Graph looks like)
        # Decadac
        #   Slot1
        #     Ch1
        #     Ch2
        #   Slot2
        #     Ch3
        #     Ch4
        #   ...
        #   Ch1
        #   Ch2
        #   ...
        #
        # BUT: The recurse algorithm would only create a tree with either Decadac/Slot1/Ch1 or Decadac/Ch1 (depending which object is processed first)
        # is that a serious problem?

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
                    type_ = QStandardItem(str(value.__class__))
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
                                except:
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


class AppInstanceException(Exception):
    """
    Throw this when the user tries to open multiple instances of app
    """

    pass


class MainWindow(QMainWindow):
    def __init__(
        self,
        components,
        terminal_parameters,
        existing_terminal_parameters: TerminalParameters | None = None,
        unlock_main_thread: Event | None = None,
        auto_run: bool = False,
    ):
        super().__init__()
        self.components = components
        self.terminal_parameters = terminal_parameters
        self.auto_run = auto_run
        if not unlock_main_thread is None:
            self.unlock_main_thread = unlock_main_thread

        container = QWidget()
        layout = QGridLayout()

        # Tree views
        self.instrument_tree = InstrumentTreeView()
        self.instrument_tree.import_data(components)
        self.instrument_tree.setSelectionMode(self.instrument_tree.SelectionMode(1))
        self.instrument_tree.drag_terminal_drop_instr.connect(self.drag_terminal_drop_instr_slot)

        self.terminal_tree = TerminalTreeView()
        self.terminal_tree.import_data(terminal_parameters)
        self.terminal_tree.instrument_model = self.instrument_tree.model()
        self.terminal_tree.setSelectionMode(self.terminal_tree.SelectionMode(1))
        self.terminal_tree.selected_terminal_tree_elem = None
        self.terminal_tree.expandAll()
        self.terminal_tree.resizeColumnToContents(0)
        self.terminal_tree.collapseAll()
        self.terminal_tree.resizeColumnToContents(1)

        # Buttons
        button_container = QWidget()
        button_layout = QHBoxLayout()

        button_map_auto = QPushButton("Map automatically (a)")
        button_map_auto.clicked.connect(self.map_automatically)

        button_reset_mapping = QPushButton("Reset mapping (r)")
        button_reset_mapping.clicked.connect(self.reset_mapping)

        button_unfold_terminals = QPushButton("Unfold (u)")
        button_unfold_terminals.clicked.connect(self.unfold_terminals)

        button_exit = QPushButton("Exit (e)")
        button_exit.clicked.connect(self.close)

        # Button layout
        button_layout.addWidget(button_map_auto)
        button_layout.addWidget(button_reset_mapping)
        button_layout.addWidget(button_unfold_terminals)
        button_layout.addStretch()
        button_layout.addWidget(button_exit)
        button_container.setLayout(button_layout)

        # Main layout
        layout.addWidget(self.terminal_tree, 0, 0)
        layout.addWidget(self.instrument_tree, 0, 1)
        layout.addWidget(button_container, 1, 0, 1, 2)

        container.setLayout(layout)
        self.setCentralWidget(container)
        self.terminal_tree.setFocus()
        idx = self.terminal_tree.model().invisibleRootItem().child(0, 0).index()
        self.terminal_tree.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self.terminal_tree.setCurrentIndex(idx)
        self.resize(QDesktopWidget().availableGeometry(self).size() * 0.6)

        if not existing_terminal_parameters is None:
            for terminal_name, parameter_mapping in existing_terminal_parameters.items():
                for terminal_parameter, instr_parameter in parameter_mapping.items():
                    if not instr_parameter is None:
                        self.map_parameter(instr_parameter, (terminal_name, terminal_parameter))

            self.terminal_tree.update_tree()

    @pyqtSlot(QStandardItem, QStandardItem)
    def drag_terminal_drop_instr_slot(self, instr_elem, terminal_elem):
        """
        This receives signal from InstrumentTree if two elements were paired via drag and drop.
        Mapping is carried out from here (mainwindow)
        """
        self.map_given_terminal_instrument_elem_selection(terminal_elem.source, instr_elem.source)
        self.terminal_tree.update_tree()

    def map_parameter(self, parameter: Parameter, traverse: tuple[str, str]):
        """
        Maps a instrument parameter to a specific terminal parameter accessed by the given traversal info.
        Updates the instrument field next to the mapped terminal parameter
        """
        self.terminal_parameters[traverse[0]][traverse[1]] = parameter
        # self.terminal_tree.update_tree()

        if hasattr(self, "unlock_main_thread") and self.auto_run:
            all_mapped = True
            for terminal in self.terminal_parameters.values():
                for terminal_param in terminal.values():
                    if terminal_param is None:
                        all_mapped = False
                        break

            if all_mapped:
                self.unlock_main_thread.set()
                self.terminal_tree.setDragEnabled(False)  # Read only

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            # read-only mode after thread was released
            if hasattr(self, "unlock_main_thread"):
                if self.unlock_main_thread.is_set():
                    return

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

                # set idx to first perfect_mapping that not has not yet been fully mapped to a terminal
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
            # map directly - should mapping be forbidden if _mapping attribute of Parameter does not fit?
            self.map_parameter(instr_elem, terminal_tree_traversal)
            mapped = True
        elif isinstance(terminal_tree_traversal[1], tuple) and isinstance(instr_elem, InstrumentModule | Instrument):
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

        elif isinstance(terminal_tree_traversal[1], str) and isinstance(instr_elem, InstrumentModule | Instrument):
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
        all_expanded = True
        for terminal in get_children(self.terminal_tree.model().invisibleRootItem()):
            if not self.terminal_tree.isExpanded(terminal.index()):
                all_expanded = False
                break

        if all_expanded:
            self.terminal_tree.collapseAll()
        else:
            self.terminal_tree.expandAll()

    def map_automatically(self):
        """
        Automatically map all unique terminal_parameter instrument_parameter pairs. If there are multiple terminal_parameters
        with the same name their unique mapping is impossible.
        """
        # read-only mode after thread was released
        if hasattr(self, "unlock_main_thread"):
            if self.unlock_main_thread.is_set():
                return

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
        # read-only mode after thread was released
        if hasattr(self, "unlock_main_thread"):
            if self.unlock_main_thread.is_set():
                return

        for terminal_name, terminal_params in self.terminal_parameters.items():
            self.terminal_parameters[terminal_name] = {
                terminal_param_name: None for terminal_param_name in terminal_params.keys()
            }

        self.terminal_tree.selected_terminal_tree_elem = None
        self.terminal_tree.update_tree()
        self.terminal_tree.setFocus()


def map_terminals_gui(
    components: Mapping[Any, Metadatable],
    terminal_parameters: TerminalParameters,
    existing_terminal_parameters: TerminalParameters | None = None,
    *,
    metadata: Metadata | None = None,
    keep_open: bool = False,
    auto_run: bool = False,
) -> None:
    """
    Maps the terminals, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        terminal_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Terminals, as defined in the measurement script
        existing_terminal_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]] | None): Already existing mapping
                that is used to automatically create the mapping for already known terminals without user input.
        metadata (Metadata | None): If provided, add mapping to the metadata object.
        keep_open: application is run in different thread. The main thread is halted and can be released from the gui.
                   when released everything is read-only
        auto_run: if all terminals are fully mapped (and keep_open = True) the main thread is released
    """

    if not QApplication.instance() is None:
        raise AppInstanceException("There can be only a single instance of the application.")

    def fun(ev):
        app = QApplication([])
        w = MainWindow(
            components, terminal_parameters, existing_terminal_parameters, unlock_main_thread=ev, auto_run=auto_run
        )
        w.show()
        # w1 = MainWindow(components, terminal_parameters, existing_terminal_parameters, unlock_main_thread=ev, auto_run=auto_run)
        # w1.show()
        app.exec_()

        ev.set()

    if keep_open:
        ev = Event()
        gui_thread = Thread(target=fun, args=(ev,))
        gui_thread.start()
        ev.wait()
    else:
        ev = None
        auto_run = False
        app = QApplication([])
        w = MainWindow(components, terminal_parameters, existing_terminal_parameters)
        w.show()
        app.exec_()


if __name__ == "__main__":
    # Setup qcodes station
    station = Station()

    # The dummy instruments have a trigger_event attribute as replacement for
    # the trigger inputs of real instruments.

    dmm = DummyDmm("dmm")
    add_mapping_to_instrument(dmm, path=DUMMY_DMM_MAPPING)
    print(f"dmm.voltage._mapping: {dmm.voltage._mapping}")
    station.add_component(dmm)

    dac = DummyDac("dac")
    add_mapping_to_instrument(dac, mapping=DummyDacMapping())
    print(f"dac.voltage._mapping: {dac.voltage._mapping}")
    station.add_component(dac)

    # dci = DummyChannelInstrument("dci",channel_names=("ChanA",))
    dci = DummyChannelInstrument("dci")
    add_mapping_to_instrument(dci, path=DUMMY_CHANNEL_MAPPING)
    station.add_component(dci)

    parameters: TerminalParameters = {
        "dmm": {"voltage": {"type": "gettable"}, "current": {"type": "gettable"}},
        "dac": {
            "voltage": {
                "type": "dynamic",
                "setpoints": [0, 5],
            }
        },
        "T1": {"temperature": {"type": "gettable"}},
        "T2": {"temperature": {"type": "gettable"}},
    }
    # parameters: TerminalParameters = {
    #     "dmm": {"voltage": {"type": "gettable"}, "current": {"type": "gettable"}},
    # }
    script = Generic_1D_Sweep()
    script.setup(
        parameters,
        None,
        add_script_to_metadata=False,
        add_parameters_to_metadata=False,
    )

    map_terminals_gui(station.components, script.gate_parameters, keep_open=False, auto_run=False)
    print("finished")

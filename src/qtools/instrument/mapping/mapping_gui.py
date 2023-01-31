from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QTreeView, QWidget
from qcodes.instrument.parameter import Parameter
from qcodes.station import Station
from qcodes.tests.instrument_mocks import DummyChannelInstrument
from qcodes.utils.metadata import Metadatable
from qtools_metadata.metadata import Metadata

from qtools.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qtools.instrument.mapping import DUMMY_DMM_MAPPING
from qtools.instrument.mapping.base import add_mapping_to_instrument
from qtools.instrument.mapping.Dummies.DummyDac import DummyDacMapping

TerminalParameters = Mapping[Any, Mapping[Any, Parameter] | Parameter]


class TerminalTreeView(QTreeView):
    """
    QTreeView, that displays qtools `TerminalParameters` (`Mapping[Any, Mapping[Any, Parameter] | Parameter]`) datastructure.
    Items are draggable to map them to instruments.
    """

    class DragStandardItem(QStandardItem):
        """Draggable QStandardItem from TerminalTreeView."""

        def mouseMoveEvent(self, event: QMouseEvent) -> None:
            if event.buttons() == Qt.LeftButton:
                drag = QDrag(self)
                mime = QMimeData()
                drag.setMimeData(mime)

                pixmap = QPixmap(self.size())
                self.render(pixmap)
                drag.setPixmap(pixmap)

                drag.exec_(Qt.MoveAction)

    def __init__(self):
        super().__init__()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Terminal"])
        self.setModel(model)

        self.terminal_parameters = None

        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def import_data(self, terminal_parameters: TerminalParameters) -> None:
        """Build up tree with provided terminal parameters."""
        parent = self.model().invisibleRootItem()
        self.terminal_parameters = terminal_parameters
        for name, value in terminal_parameters.items():
            item = TerminalTreeView.DragStandardItem(name)
            item.source = (name, value)
            parent.appendRow(item)

            if isinstance(value, Mapping):
                for name2, value2 in value.items():
                    subitem = TerminalTreeView.DragStandardItem(name2)
                    subitem.source = (f"{name}.{name2}", value2)
                    item.appendRow(subitem)


class InstrumentTreeView(QTreeView):
    """QTreeView, that displays qcodes instruments."""

    def __init__(self):
        super().__init__()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Type", "Terminal"])
        self.setModel(model)

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Check for correct mime type to accept the dragging event."""
        # TODO: Check mime type for correct type
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Map terminal (parameters) with the dropped on instrument (parameter).
        If a terminal parameter is dropped on an instrument parameter, they are mapped.
        If a terminal is dropped on an instrument, they are automatically mapped as much as possible.
        If a terminal parameter is dropped on an instrument, it is automatically mapped to one of the instrument's parameters.
        If a terminal is dropped on an instrument parameter, it is automatically mapped to the whole instrument as much as possible.
        """
        tree = event.source()
        assert isinstance(tree, TerminalTreeView)
        terminal = tree.model().itemFromIndex(tree.currentIndex()).source

        dest_index = self.indexAt(event.pos())

        model = self.model()
        row = dest_index.row()
        parent = dest_index.parent()

        # Create cell, if its not there yet
        if not model.hasIndex(row, 2, parent):
            model.insertColumn(2, parent)
        # Add terminal name to instrument row
        model.setData(parent.child(row, 2), terminal[0])

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
                    type_ = QStandardItem(str(value.__class__))
                    parent.appendRow([item, type_])
                else:
                    if isinstance(value, Iterable) and not isinstance(value, str):
                        # parent.appendRow(item)
                        recurse(value, parent)
                    elif isinstance(value, Metadatable):
                        # Object of some Metadatable type, try to get __dict__ and _filter_flatten_parameters
                        try:
                            value_hash = hash(value)
                            if value_hash not in seen:
                                seen.add(value_hash)
                                item = QStandardItem(value.name)
                                item.source = value
                                parent.appendRow(item)
                                recurse(vars(value), item)
                        except TypeError:
                            # End of tree
                            pass

        recurse(components, parent)


def map_terminals_gui(
    components: Mapping[Any, Metadatable],
    terminal_parameters: TerminalParameters,
    existing_terminal_parameters: TerminalParameters | None = None,
    *,
    metadata: Metadata | None = None,
) -> None:
    """
    Maps the terminals, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        terminal_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Terminals, as defined in the measurement script
        existing_terminal_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]] | None): Already existing mapping
                that is used to automatically create the mapping for already known terminals without user input.
        metadata (Metadata | None): If provided, add mapping to the metadata object.
    """
    app = QApplication([])
    w = QMainWindow()
    container = QWidget()
    layout = QHBoxLayout()

    instrument_tree = InstrumentTreeView()
    instrument_tree.import_data(components)

    terminal_tree = TerminalTreeView()
    terminal_tree.import_data(terminal_parameters)

    layout.addWidget(instrument_tree)
    layout.addWidget(terminal_tree)
    layout.addStretch(1)
    container.setLayout(layout)

    w.setCentralWidget(container)
    w.show()
    app.exec_()


if __name__ == "__main__":
    # Setup qcodes station
    station = Station()

    # The dummy instruments have a trigger_event attribute as replacement for
    # the trigger inputs of real instruments.

    dmm = DummyDmm("dmm")
    add_mapping_to_instrument(dmm, path=DUMMY_DMM_MAPPING)
    station.add_component(dmm)

    dac = DummyDac("dac")
    add_mapping_to_instrument(dac, mapping=DummyDacMapping())
    station.add_component(dac)

    dci = DummyChannelInstrument("dci")
    station.add_component(dci)

    parameters: TerminalParameters = {
        "dmm": {"voltage": {"type": "gettable"}},
        "dac": {
            "voltage": {
                "type": "dynamic",
                "setpoints": [0, 5],
            }
        },
    }

    map_terminals_gui(station.components, parameters)

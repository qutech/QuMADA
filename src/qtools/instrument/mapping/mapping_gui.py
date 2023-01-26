from collections.abc import Iterable, Mapping
from typing import Any

from PyQt5.QtCore import QMimeData, QModelIndex, Qt
from PyQt5.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
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


# class ComponentModel(QAbstractItemModel):

#     def __init__(self, components: Mapping[Any, Metadatable]) -> None:
#         super().__init__()
#         self.root = components

#     def columnCount(self):
#         return 2

#     def rowCount(self, )


# class DragItem(QLabel):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.setContentsMargins(25, 5, 25, 5)
#         self.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.setStyleSheet("border: 1px solid black;")
#         self.data = self.text()

#     def mouseMoveEvent(self, event: QMouseEvent) -> None:
#         if event.buttons() == Qt.LeftButton:
#             drag = QDrag(self)
#             mime = QMimeData()
#             drag.setMimeData(mime)

#             pixmap = QPixmap(self.size())
#             self.render(pixmap)
#             drag.setPixmap(pixmap)

#             drag.exec_(Qt.MoveAction)


class TreeView(QWidget):
    def __init__(self):
        super().__init__()

        self.tree = QTreeView()
        self.model = QStandardItemModel()
        self.parent_item = self.model.invisibleRootItem()
        self.tree.header().setDefaultSectionSize(180)
        self.tree.setModel(self.model)


class TerminalTreeView(TreeView):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.model.setHorizontalHeaderLabels(["Terminal"])

    def import_data(self, terminal_parameters: TerminalParameters) -> None:
        for name, value in terminal_parameters.items():
            item = QStandardItem(name)
            item.source = value
            self.parent_item.appendRow(item)

            if isinstance(value, Mapping):
                for name2, value2 in value.items():
                    subitem = QStandardItem(name2)
                    subitem.source = value2
                    item.appendRow(subitem)

    # def dragEnterEvent(self, event: QDragEnterEvent) -> None:
    #     event.accept()

    # def dropEvent(self, event: QDropEvent) -> None:
    #     pos = event.pos()
    #     widget = event.source()

    #     for i in range(self.layout().count()):
    #         w = self.layout().itemAt(i).widget()
    #         if pos.x() < w.x() + w.size().width() // 2:
    #             self.layout().insertWidget(i - 1, widget)
    #             break
    #     event.accept()


class InstrumentTreeView(TreeView):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.model.setHorizontalHeaderLabels(["Name", "Type", "Terminal"])

    def import_data(self, components: Mapping[Any, Metadatable]) -> None:
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

        seen: set[int] = set()
        recurse(components, self.parent_item)


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
        gate_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Gates, as defined in the measurement script
        existing_gate_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]] | None): Already existing mapping
                that is used to automatically create the mapping for already known gates without user input.
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

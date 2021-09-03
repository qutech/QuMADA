#!/usr/bin/env python3
"""
Main Window UI
"""
import sys
from typing import Dict

from PyQt5 import QtWidgets, uic
from qtconsole.console_widget import ConsoleWidget
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager


class Ui(QtWidgets.QMainWindow):
    """Main Window of the UI."""
    def __init__(self):
        super().__init__()
        uic.loadUi("qtools/ui/main_window.ui", self)
        self.add_gate_widgets()
        self.connect_signal_slots()

    def add_gate_widgets(self):
        """Adds 6 dummy GateWidgets."""
        self.gates = [GateWidget(self) for x in range(6)]
        for gate in self.gates:
            self.gateOverview.addWidget(gate)

    def connect_signal_slots(self):
        """Not yet implemented."""


class MyConsoleWidget(RichJupyterWidget, ConsoleWidget):
    """
    qConsole Jupyter Widget to be embedded as QWidget.
    """
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel(show_banner=False)
        self.kernel_manager.gui = "qt"
        self.kernel_client = self._kernel_manager.client()
        self.kernel_client.start_channels()

        def stop():
            self.kernel_client.stop_channels()
            self.kernel_manager.shutdown_kernel()
            self.guisupport.get_app_qt().exit()

        self.exit_requested.connect(stop)

    def push_vars(self, variable_dict: dict):
        """
        Given a dictionary containing name/value pairs,
        push those variables to the Jupyter console widget
        """
        self.kernel_manager.kernel.shell.push(variable_dict)

    def clear(self):
        """
        Clears the terminal
        """
        self._control.clear()

        # self.kernel_manager

    def print_text(self, text: str):
        """
        Prints some plain text to the console
        """
        self._append_plain_text(text)

    def execute_command(self, command: str):
        """
        Execute a command in the frame of the console widget
        """
        self._execute(command, False)


class GateWidget(QtWidgets.QWidget):
    """Gate widget, that incorporates a measurement view"""
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        uic.loadUi("qtools/ui/gate_widget.ui", self)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.show()
    app.exec_()

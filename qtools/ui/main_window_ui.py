#!/usr/bin/env python3
"""
Main Window UI
"""

from typing import Dict
from PyQt5 import QtWidgets, uic, QtGui
from qtconsole.console_widget import ConsoleWidget
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

import sys

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi("qtools/ui/main_window.ui", self)
        self.setup_ipython_console()
        self.connect_signal_slots()

    def setup_ipython_console(self):
        pass

    def connect_signal_slots(self):
        pass

class MyConsoleWidget(RichJupyterWidget,ConsoleWidget):
    def __init__(self, *args, **kwargs):

        super(MyConsoleWidget, self).__init__(*args, **kwargs)

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

    def push_vars(self, variable_dict: Dict):
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


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.show()
    app.exec_()
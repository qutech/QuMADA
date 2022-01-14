#!/usr/bin/env python3

from qtools.ui.cmd2.app import QToolsApp


def start_console_app():
    app = QToolsApp()
    ret_code = app.cmdloop()
    raise SystemExit(ret_code)


def start_gui_app():
    raise NotImplementedError()


if __name__ == "__main__":
    start_console_app()

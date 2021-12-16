#!/usr/bin/env python3


from qtools.ui.cmd2.app import QToolsApp

if __name__ == "__main__":
    app = QToolsApp()
    ret_code = app.cmdloop()
    raise SystemExit(ret_code)

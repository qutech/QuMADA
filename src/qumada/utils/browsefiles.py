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
# - Till Huckeman
# - Daniel Grothe


# Python program to create
# a file explorer in Tkinter

# import filedialog module
import tkinter
from tkinter import filedialog
from os import curdir


# Function for opening the file explorer window
def browsefiles(**kwargs):
    """
    Opens gui for selecting files, returns filepath+name.
    kwargs:
        initialdir ([str], def: "/"): directory to start at
        filetypes ([tuple([str:label],[str: suffix])], def: txt and all files):
            Selectable filetypes
    """
    print("A popup window opened, it is possibly hidden behind other windows...")
    initialdir = kwargs.get("initialdir", curdir)
    filetypes = kwargs.get("filetypes", (("Text files", "*.txt*"), ("all files", "*.*")))
    # Make a top-level instance and hide since it is ugly and big.
    root = tkinter.Tk()
    root.withdraw()
    # Make it almost invisible - no decorations, 0 size, top left corner.
    root.overrideredirect(True)
    root.geometry("0x0+0+0")

    # Show window again and lift it to top so it can get focus,
    # otherwise dialogs will end up behind the terminal.
    root.deiconify()
    root.tkraise()
    root.focus_force()
    filename = filedialog.askopenfilename(
        parent=root, initialdir=initialdir, title="Select a File", filetypes=filetypes
    )
    root.destroy()
    return filename


def browsesavefile(**kwargs):
    """
    Opens gui for creating new file for saving stuff. Returns opened file
    Keep in mind to close it after writing.
    kwargs:
        initialdir ([str], def: "/"): directory to start at
        filetypes ([tuple([str:label],[str: suffix])], def: txt and all files):
            Selectable filetypes

    """
    initialdir = kwargs.get("initialdir", curdir)
    filetypes = kwargs.get("filetypes", (("Text files", "*.txt*"), ("all files", "*.*")))
    # Make a top-level instance and hide since it is ugly and big.
    root = tkinter.Tk()
    root.withdraw()
    # Make it almost invisible - no decorations, 0 size, top left corner.
    root.overrideredirect(True)
    root.geometry("0x0+0+0")

    # Show window again and lift it to top so it can get focus,
    # otherwise dialogs will end up behind the terminal.
    root.deiconify()
    root.tkraise()
    root.focus_force()
    file = tkinter.filedialog.asksaveasfile(parent=root, initialdir=initialdir, filetypes=filetypes)
    root.destroy()
    return file

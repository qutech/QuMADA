"""
Created on Tue Feb 23 16:04:17 2021

@author: Till
"""

# Python program to create
# a file explorer in Tkinter

# import filedialog module
import tkinter
from tkinter import filedialog
from os import curdir


# Function for opening the file explorer window
def browsefiles(**kwargs):
    '''
    Opens gui for selecting files, returns filepath+name.
    kwargs:
        initialdir ([str], def: "/"): directory to start at
        filetypes ([tuple([str:label],[str: suffix])], def: txt and all files):
            Selectable filetypes
    '''
    print("A popup window opened, it is possibly hidden behind other windows...")
    initialdir = kwargs.get("initialdir", curdir)
    filetypes = kwargs.get("filetypes", (("Text files", "*.txt*"),
                                         ("all files", "*.*")))
    # Make a top-level instance and hide since it is ugly and big.
    root = tkinter.Tk()
    root.withdraw()
    # Make it almost invisible - no decorations, 0 size, top left corner.
    root.overrideredirect(True)
    root.geometry('0x0+0+0')

    # Show window again and lift it to top so it can get focus,
    # otherwise dialogs will end up behind the terminal.
    root.deiconify()
    root.tkraise()
    root.focus_force()
    filename = filedialog.askopenfilename(parent=root,
                                          initialdir=initialdir,
                                          title="Select a File",
                                          filetypes=filetypes)
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
    filetypes = kwargs.get("filetypes", (("Text files", "*.txt*"),
                                         ("all files", "*.*")))
    # Make a top-level instance and hide since it is ugly and big.
    root = tkinter.Tk()
    root.withdraw()
    # Make it almost invisible - no decorations, 0 size, top left corner.
    root.overrideredirect(True)
    root.geometry('0x0+0+0')

    # Show window again and lift it to top so it can get focus,
    # otherwise dialogs will end up behind the terminal.
    root.deiconify()
    root.tkraise()
    root.focus_force()
    file = tkinter.filedialog.asksaveasfile(parent=root,
                                            initialdir=initialdir,
                                            filetypes=filetypes)
    root.destroy()
    return file

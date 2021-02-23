# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 16:04:17 2021

@author: till3
"""

# Python program to create 
# a file explorer in Tkinter

# import filedialog module
from tkinter import filedialog
  
# Function for opening the 
# file explorer window
def browsefiles(**kwargs):
    '''
    Opens gui for selecting files, returns filepath+name. 
    kwargs: 
        initialdir ([str], def: "/"): directory to start at 
        filetypes ([tuple([str:label],[str: suffix])], def: txt and all files):
            Selectable filetypes
    '''
    initialdir = kwargs.get("initialdir", "/")
    filetypes = kwargs.get("filetypes", (("Text files", "*.txt*"),
                                         ("all files", "*.*")))
    filename = filedialog.askopenfilename(initialdir = initialdir,
                                          title = "Select a File",
                                          filetypes = filetypes)
    return filename


#! /usr/bin/env python3
"""
Tapeimgr, automated reading of tape
Graphical user interface

Author: Johan van der Knijff
Research department,  KB / National Library of the Netherlands
"""

import sys
import os
import imp
import time
import threading
import _thread as thread
import logging
import queue
import glob
import tkinter as tk
from tkinter import filedialog as tkFileDialog
from tkinter import scrolledtext as ScrolledText
from tkinter import messagebox as tkMessageBox
from tkinter import ttk
from .tapeimgr import Tape
from . import config


__version__ = '0.1.0'


class tapeimgrGUI(tk.Frame):

    """This class defines the graphical user interface + associated functions
    for associated actions
    """

    def __init__(self, parent, *args, **kwargs):
        """Initiate class"""
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.finishedTape = False
        self.dirOut = os.path.expanduser("~")
        self.logFileName = config.logFileName
        self.tapeDevice = config.tapeDevice
        self.initBlockSize = config.initBlockSize
        self.sessions = ''
        self.logFile = ''
        self.prefix = config.prefix
        self.extension = config.extension
        self.fillBlocks = bool(config.fillBlocks)
        self.build_gui()

    def on_quit(self):
        """Quit tapeimgr"""
        os._exit(0)

    def on_submit(self):
        """fetch and validate entered input, and start processing"""
     
        # This flag is true if all input validates
        inputValidateFlag = True
    
        # Fetch entered values (strip any leading / trailing whitespace characters)
        self.tapeDevice = self.tapeDevice_entry.get().strip()
        self.initBlockSize = self.initBlockSize_entry.get().strip()
        self.sessions = self.sessions_entry.get().strip()
        self.prefix = self.prefix_entry.get().strip()
        self.extension = self.extension_entry.get().strip()
        self.fillBlocks = self.fBlocks.get()
        self.logFile = os.path.join(self.dirOut, self.logFileName)
    
        # Create tape instance
        self.tape = Tape(self.dirOut,
                         self.tapeDevice,
                         self.initBlockSize,
                         self.sessions,
                         self.prefix,
                         self.extension,
                         self.fillBlocks)
        # Validate input
        self.tape.validateInput()

        # Show error message for any parameters that didn't pass validation
        if not self.tape.dirOutIsDirectory:
            inputValidateFlag = False
            msg = ("Output directory doesn't exist:\n" + self.dirOut)
            tkMessageBox.showerror("ERROR", msg)

        if not self.tape.dirOutIsWritable:
            inputValidateFlag = False
            msg = ('Cannot write to directory ' + self.dirOut)
            tkMessageBox.showerror("ERROR", msg)
    
        if not self.tape.blockSizeIsValid:
            inputValidateFlag = False
            msg = ('Block size not valid')
            tkMessageBox.showerror("ERROR", msg)

        if not self.tape.sessionsIsValid:
            inputValidateFlag = False
            msg = ('Sessions value not valid\n'
                   '(must be comma-delimited string of integer numbers, or empty)')
            tkMessageBox.showerror("ERROR", msg)

        # Ask confirmation if output files exist already
        outDirConfirmFlag = True
        if self.tape.outputExistsFlag:
            msg = ('writing to ' + self.dirOut + ' will overwrite existing files!\n'
                   'press OK to continue, otherwise press Cancel ')
            outDirConfirmFlag = tkMessageBox.askokcancel("Overwrite files?", msg)

        if (inputValidateFlag and outDirConfirmFlag):

            # Start logger
            successLogger = True
            try:
                self.setupLogger()
                # Start polling log messages from the queue
                self.after(100, self.poll_log_queue)
            except OSError:
                # Something went wrong while trying to write to lof file
                msg = ('error trying to write log file to ' + self.logFile)
                tkMessageBox.showerror("ERROR", msg)
                successLogger = False
            
            if successLogger:
                # Disable start and exit buttons
                self.start_button.config(state='disabled')
                self.quit_button.config(state='disabled')

                # Launch tape processing function as subprocess
                t1 = threading.Thread(target=self.tape.processTape)
                t1.start()


    def selectOutputDirectory(self):
        """Select output directory"""
        dirInit = self.dirOut
        self.dirOut = tkFileDialog.askdirectory(initialdir=dirInit)
        self.outDirLabel['text'] = self.dirOut

    def decreaseBlocksize(self):
        """Decrease value of initBlockSize"""
        try:
            blockSizeOld = int(self.initBlockSize_entry.get().strip())
        except ValueError:
            # Reset if user manually entered something weird
            blockSizeOld = int(config.initBlockSize)
        blockSizeNew = max(blockSizeOld - 512, 512)
        self.initBlockSize_entry.delete(0, tk.END)
        self.initBlockSize_entry.insert(tk.END, str(blockSizeNew))

    def increaseBlocksize(self):
        """Increase value of initBlockSize"""
        try:
            blockSizeOld = int(self.initBlockSize_entry.get().strip())
        except ValueError:
            # Reset if user manually entered something weird
            blockSizeOld = int(config.initBlockSize)
        blockSizeNew = blockSizeOld + 512
        self.initBlockSize_entry.delete(0, tk.END)
        self.initBlockSize_entry.insert(tk.END, str(blockSizeNew))

    def build_gui(self):
        """Build the GUI"""

        self.root.title('tapeimgr')
        self.root.option_add('*tearOff', 'FALSE')
        self.grid(column=0, row=0, sticky='w')
        self.grid_columnconfigure(0, weight=0, pad=0)
        self.grid_columnconfigure(1, weight=0, pad=0)
        self.grid_columnconfigure(2, weight=0, pad=0)
        self.grid_columnconfigure(3, weight=0, pad=0)

        # Entry elements
        ttk.Separator(self, orient='horizontal').grid(column=0, row=0, columnspan=4, sticky='ew')
        # Output Directory
        self.outDirButton_entry = tk.Button(self,
                                            text='Select Output Directory',
                                            command=self.selectOutputDirectory,
                                            width=20)
        self.outDirButton_entry.grid(column=0, row=3, sticky='w')
        self.outDirLabel = tk.Label(self, text=self.dirOut)
        self.outDirLabel.update()
        self.outDirLabel.grid(column=1, row=3, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=5, columnspan=4, sticky='ew')

        # Tape Device
        tk.Label(self, text='Tape Device').grid(column=0, row=6, sticky='w')
        self.tapeDevice_entry = tk.Entry(self, width=20)
        self.tapeDevice_entry['background'] = 'white'
        self.tapeDevice_entry.insert(tk.END, self.tapeDevice)
        self.tapeDevice_entry.grid(column=1, row=6, sticky='w')

        # Initial Block Size
        tk.Label(self, text='Initial Block Size').grid(column=0, row=7, sticky='w')
        self.initBlockSize_entry = tk.Entry(self, width=20)
        self.initBlockSize_entry['background'] = 'white'
        self.initBlockSize_entry.insert(tk.END, self.initBlockSize)
        self.initBlockSize_entry.grid(column=1, row=7, sticky='w')
        self.decreaseBSButton = tk.Button(self, text='-', command=self.decreaseBlocksize, width=1)
        self.decreaseBSButton.grid(column=2, row=7, sticky='e')
        self.increaseBSButton = tk.Button(self, text='+', command=self.increaseBlocksize, width=1)
        self.increaseBSButton.grid(column=3, row=7, sticky='w')

        # Sessions
        tk.Label(self, text='Sessions (comma-separated list)').grid(column=0, row=8, sticky='w')
        self.sessions_entry = tk.Entry(self, width=20)
        self.sessions_entry['background'] = 'white'
        self.sessions_entry.grid(column=1, row=8, sticky='w')

        # Prefix
        tk.Label(self, text='Prefix').grid(column=0, row=9, sticky='w')
        self.prefix_entry = tk.Entry(self, width=20)
        self.prefix_entry['background'] = 'white'
        self.prefix_entry.insert(tk.END, self.prefix)
        self.prefix_entry.grid(column=1, row=9, sticky='w')

        # Extension
        tk.Label(self, text='Extension').grid(column=0, row=10, sticky='w')
        self.extension_entry = tk.Entry(self, width=20)
        self.extension_entry['background'] = 'white'
        self.extension_entry.insert(tk.END, self.extension)
        self.extension_entry.grid(column=1, row=10, sticky='w')

        # Fill failed blocks
        tk.Label(self, text='Fill failed blocks').grid(column=0, row=11, sticky='w')
        self.fBlocks = tk.IntVar()
        self.fillblocks_entry = tk.Checkbutton(self, variable=self.fBlocks)
        self.fillblocks_entry.grid(column=1, row=11, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=12, columnspan=4, sticky='ew')

        self.start_button = tk.Button(self,
                                      text='Start',
                                      width=10,
                                      underline=0,
                                      command=self.on_submit)
        self.start_button.grid(column=1, row=13, sticky='e')

        self.quit_button = tk.Button(self,
                                     text='Exit',
                                     width=10,
                                     underline=0,
                                     command=self.on_quit)
        self.quit_button.grid(column=2, row=13, sticky='w', columnspan=2)

        ttk.Separator(self, orient='horizontal').grid(column=0, row=14, columnspan=4, sticky='ew')

        # Add ScrolledText widget to display logging info
        self.st = ScrolledText.ScrolledText(self, state='disabled', height=15)
        self.st.configure(font='TkFixedFont')
        self.st['background'] = 'white'
        self.st.grid(column=0, row=15, sticky='ew', columnspan=4)

        # Define bindings for keyboard shortcuts: buttons
        self.root.bind_all('<Control-Key-s>', self.on_submit)
        self.root.bind_all('<Control-Key-e>', self.on_quit)

        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def setupLogger(self):
        """Set up logger configuration"""

        # Basic configuration
        logging.basicConfig(filename=self.logFile,
                            level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        # Add the handler to logger
        self.logger = logging.getLogger()

        # Create a logging handler using a queue
        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)
        # This sets the console output format (slightly different from basicConfig!)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        self.logger.addHandler(self.queue_handler)

    def display(self, record):
        """Display log record in scrolledText widget"""
        msg = self.queue_handler.format(record)
        self.st.configure(state='normal')
        self.st.insert(tk.END, msg + '\n', record.levelname)
        self.st.configure(state='disabled')
        # Autoscroll to the bottom
        self.st.yview(tk.END)

    def poll_log_queue(self):
        """Check every 100ms if there is a new message in the queue to display"""
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.after(100, self.poll_log_queue)


class QueueHandler(logging.Handler):
    """Class to send logging records to a queue

    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    Taken from https://github.com/beenje/tkinter-logging-text-widget/blob/master/main.py
    """

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


def checkDirExists(dirIn):
    """Check if directory exists and exit if not"""
    if not os.path.isdir(dirIn):
        msg = ('directory ' + dirIn + ' does not exist!')
        tkMessageBox.showerror("Error", msg)
        sys.exit(1)


def errorExit(error):
    """Show error message in messagebox and then exit after user presses OK"""
    tkMessageBox.showerror("Error", error)
    os._exit(1)


def main_is_frozen():
    """Return True if application is frozen (Py2Exe), and False otherwise"""
    return (hasattr(sys, "frozen") or  # new py2exe
            hasattr(sys, "importers") or  # old py2exe
            imp.is_frozen("__main__"))  # tools/freeze


def get_main_dir():
    """Return application (installation) directory"""
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])


def main():
    """Main function"""

    root = tk.Tk()
    myGUI = tapeimgrGUI(root)

    while True:
        try:
            root.update_idletasks()
            root.update()
            time.sleep(0.1)
        except KeyboardInterrupt:
            if myGUI.tape.tapeDeviceIOError:
                # Tape device not accessible
                msg = ('Cannot access tape device ' + myGUI.tape.tapeDevice +
                       '. Check that device exits, and that tapeimgr is run as root')
                errorExit(msg)
            elif myGUI.tape.successFlag:
                # Tape extraction completed with no errors
                msg = ('Tape processed successfully without errors')
                tkMessageBox.showinfo("Success", msg)
            else:
                # Tape extraction resulted in errors
                msg = ('One or more errors occurred while processing tape, '
                       'check log file for details')
                tkMessageBox.showwarning("Errors occurred", msg)

            # Restart the program
            python = sys.executable
            os.execl(python, python, * sys.argv)
  
if __name__ == "__main__":
    main()

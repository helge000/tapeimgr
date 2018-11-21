#! /usr/bin/env python3
"""This module contains iromlab's cdWorker code, i.e. the code that monitors
the list of jobs (submitted from the GUI) and does the actual imaging and ripping
"""

import os
import time
import glob
import hashlib
import logging
import _thread as thread
from . import shared
from . import config

def generate_file_sha512(fileIn):
    """Generate sha512 hash of file"""

    # fileIn is read in chunks to ensure it will work with (very) large files as well
    # Adapted from: http://stackoverflow.com/a/1131255/1209004

    blocksize = 2**20
    m = hashlib.sha512()
    with open(fileIn, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def checksumDirectory(directory):
    """Calculate checksums for all files in directory"""

    # All files in directory
    allFiles = glob.glob(directory + "/*." + extension)

    # Dictionary for storing results
    checksums = {}

    for fName in allFiles:
        hashString = generate_file_sha512(fName)
        checksums[fName] = hashString

    # Write checksum file
    try:
        fChecksum = open(os.path.join(directory, "checksums.sha512"), "w", encoding="utf-8")
        for fName in checksums:
            lineOut = checksums[fName] + " " + os.path.basename(fName) + '\n'
            fChecksum.write(lineOut)
        fChecksum.close()
        wroteChecksums = True
    except IOError:
        wroteChecksums = False

    return wroteChecksums

def processTape(dirOut, tapeDevice, initBlocksize, sessions, prefix, extension, fillBlocks):
    """Process a tape"""
    # TODO: add actual calls to mt

    print("entering processTape")

    # Write some general info to log file
    logging.info('*** Tape extraction log ***')
    #dateStart="$(date)"
    #logging.info('# Start date/time ' + dateStart)
    logging.info('# User input')
    logging.info('dirOut = ' + dirOut)
    logging.info('tapeDevice = ' + tapeDevice)
    logging.info('initial blockSize = ' + initBlocksize)
    logging.info('sessions = ' + sessions)
    logging.info('prefix = ' + prefix)
    logging.info('extension = ' + extension)
    logging.info('fill blocks = ' + str(fillBlocks))

    if fillBlocks == 1:
        # dd's conv=sync flag results in padding bytes for each block if block
        # size is too large, so override user-defined value with default
        # if -f flag was used
        initBlocksize = 512
        logging.info('Reset initial block size to 512 because -f flag is used')

    # Flag that indicates end of tape was reached
    endOfTape = False
    # Session index
    session = 1

    # Get tape status, output to log file
    logging.info('# Tape status')
    # TODO insert mt call
    # mt -f "$tapeDevice" status | tee -a "$logFile"

    # Split sessions string to list
    try:
        sessions = [int(i) for i in sessions.split(',')]
    except ValueError:
        # sessions is empty string or invalid input
        sessions = []

    # Iterate over all sessions on tape until end is detected
    # TODO remove session < 10 limit
    while not endOfTape and session < 10:
        print("session = " + str(session))
        # Only extract sessions defined by sessions parameter
        # (if session parameter is empty all sessions are extracted)
        if session in sessions or sessions == []:
            extractSession = True
        else:
            extractSession = False

        print("xtractSession = " + str(extractSession))

        # Call session processing function
        resultSession = processSession(session, extractSession)
        print("Processing session")

        # Increase session number
        session += 1

    # Create checksum file
    logging.info('# Creating checksum file')
    checksumStatus = checksumDirectory(os.path.normpath(dirOut))

    # Rewind and eject the tape
    logging.info('# Rewinding tape')
    #mt -f "$tapeDevice" rewind 2>&1 | tee -a "$logFile"
    logging.info('# Ejecting tape')
    #mt -f "$tapeDevice" eject 2>&1 | tee -a "$logFile"

    # Write end date/time to log
    #dateEnd="$(date)"
    #logging.info('# End date/time ' + dateEnd)

    finishedTape = True

    # Wait 2 seconds to avoid race condition
    time.sleep(2)
    # This triggers a KeyboardInterrupt in the main thread
    thread.interrupt_main()

    return True


def processSession(sessionNumber, extractSessionFlag):
    """Process a session"""
    # TODO: add actual calls to mt and dd

    if extractSessionFlag:
        # Determine block size for this session
        blockSize = findBlocksize(initBlocksize)
        logging.info('Block size = ' + str(blockSize))

        # Name of output file for this session
        ofName = prefix + str(sessionNumber).zfill(6) + '.' + extension
        ofName = os.path.join(dirOut, ofName)
        #ofName = "$dirOut"/""$prefix""`printf "%06g" "$session"`."$extension"

        logging.info('# Extracting session # ' + str(sessionNumber) + ' to file ' + ofName)

        if fillBlocks == 1:
            # Invoke dd with conv=noerror,sync options
            pass
            #dd if="$tapeDevice" of="$ofName" bs="$bSize" conv=noerror,sync >> "$logFile" 2>&1
        else:
            pass
            #dd if="$tapeDevice" of="$ofName" bs="$bSize" >> "$logFile" 2>&1

        #ddStatus="$?"
        #echo "# dd exit code = " "$ddStatus" | tee -a "$logFile"
    else:
        # Fast-forward tape to next session
        pass
        logging.info('# Skipping session # ' + str(sessionNumber) + ', fast-forward to next session')
        #mt -f "$tapeDevice" fsf 1 >> "$logFile" 2>&1

    # Try to position tape 1 record forward; if this fails this means
    # the end of the tape was reached
    #mt -f "$tapeDevice" fsr 1 >> "$logFile" 2>&1
    mtStatus = 0 # TODO, change to actual status!
    logging.info('mt exit code = ' + str(mtStatus))

    if mtStatus == 0:
        # Another session exists. Position tape one record backward
        #mt -f "$tapeDevice" bsr 1 >> "$logFile" 2>&1
        pass
    else:
        # No further sessions, end of tape reached
        logging.info('# Reached end of tape')
        endOfTape = True

    return True

def findBlocksize(blockSizeInit):
    """Find block size, starting from blockSizeInit"""
    blockSize = 9999
    return blockSize
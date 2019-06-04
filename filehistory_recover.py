import os
import sys
import time
import re
import custom_shutil as shutil
import errno
import Queue
import threading
import os
import time
import multiprocessing

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Brandon Roberts <brandonnickroberts@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
filehistory_recover - removes redudant file-history entries from a directory.
Program was created because old filehistory backups can become incompatible with certain hardware.
===============================================================
Version: 0.2
Copyright (C) 2019 Brandon Roberts <brandonnickroberts@gmail.com>
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


def newConfig():
    return {
        'export_dir': "./",
        'modes': ["list"]
    }

fileQueue = Queue.Queue()

class Main(object):
    totalFiles = 0
    copyCount = 0
    lock = threading.Lock()

    def __init__(self):
        self.export_dir = "./"
        self.config = newConfig()
        self.directories = []
        self.files = []
        self.latestFiles = {}
        self.redundants = []
        self.args = []
        self.currentSize = 0
        self.totalSize = 0
        pass

    def worker(self):
        while not fileQueue.empty():
            src, dest = fileQueue.get()
            try:
                shutil.copy(src, dest)
            except IOError as e:
                if e.errno != errno.ENOENT and e.errno != errno.EEXIST and e.errno != errno.EACCES:
                    pass
                try:
                    os.makedirs(os.path.dirname(dest))
                    shutil.copy(src, dest)
                except:
                    pass
            fileQueue.task_done()
            try:
                size = os.path.getsize(dest)
            except:
                size = 0
            with self.lock:
                self.copyCount += 1
                self.currentSize += size
                sys.stdout.write("%i/%i Files copied. (%iMB/%iMB)\r" % (self.copyCount,
                                                                        self.totalFiles, self.currentSize/1024/1024, self.totalSize/1024/1024))
                sys.stdout.flush()

    def copier(self):
        for i in range(multiprocessing.cpu_count() * 2):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
        fileQueue.join()

    def run(self):
        self.args = sys.argv[2:]

        if len(self.args) == 0:
            self.args.append('copy')

        print "** Undo_FileHistory **"
        if "copy" in self.args:
            print "You have entered copy mode."
            print "Your files will remian in their original location, and useable copies will be stored in a new location."
            print "Only the latest versions of files will be copied. \n"

        elif "move" in self.args:
            print "You have entered move mode."
            print "Your files will be deleted from their original location, and useable copies will be stored in a new location."
            print "Only the latest copies will be moved. Redundant files will be deleted. \n"

        elif "delete" in self.args:
            print "You have entered delete mode."
            print "Redundant files will be deleted. \n"

        print "Beware, the use of this program can lead to data loss."
        print "You may need to run this script with administrative privileges."
        print "Would you like to continue? (Y/N)"
        if raw_input() != "Y":
            return

        self.config['input_directory'] = raw_input(
            "Please enter the directory to search: ")
        print "You have selected to the input directory %s" % (
            self.config['input_directory'])
        print "The program will first list the details of directory. No data will modified at this point."
        print "Please wait."
        self.directories.append(self.config["input_directory"])
        self.analyseDirectory()
        self.printAnalysis()

        if "copy" in self.args:
            print "-- COPY MODE --"
            print "Would you like to copy the files to the output folder? This will keep the original files. (Y/N)"
            if raw_input() != "Y":
                return
            myPath = os.path.abspath("./output/")
            self.totalFiles = len(self.latestFiles)
            self.totalSize = reduce(lambda x, y: x + os.path.getsize(y),
                                    map(lambda x: x['filename'], self.latestFiles.values()), 0)
            for f in self.latestFiles.keys():
                newPath = myPath + f[len(self.config['input_directory']):]
                src = self.latestFiles[f]['filename']
                dest = newPath
                fileQueue.put((src, dest))
            self.copier()
            print "Task completed."

        if "move" in self.args:
            print "-- MOVE MODE -- UNIMPLEMENTED"
            print "Would you like to move the files to a new location? This will delete the original files. (Y/N)"
            if raw_input() != "Y":
                return

        if "delete" in self.args:
            print "-- DELETE MODE -- UNIMPLEMENTED"
            print "Redundant files will be deleted. \n"
            if raw_input() != "Y":
                return

    def analyseDirectory(self):
        while len(self.directories):
            directory = self.directories.pop()
            newFiles = listdir_fullpath(directory)
            for f in newFiles:
                if not os.path.isabs(f):
                    print "Error, not absolute."

                elif os.path.isfile(f):
                    self.files.append(f)
                    strippedName = strip_fileHistory(f)
                    update = False
                    if strippedName in self.latestFiles:
                        if os.path.getmtime(f) > os.path.getmtime(self.latestFiles[strippedName]['filename']):
                            update = True
                            self.redundants.append(
                                self.latestFiles[strippedName]['filename'])
                        else:
                            self.redundants.append(f)

                    else:
                        update = True

                    if update:
                        self.latestFiles[strippedName] = {
                            'filename': f,
                            'utime': os.path.getmtime(f)
                        }

                elif os.path.isdir(f):
                    self.directories.append(f)

                else:
                    print "Unknown file error."

            sys.stdout.write("%i Files detected. %i Redundant files detected. \r" % (
                len(self.files), len(self.redundants)))
            sys.stdout.flush()

        pass

    def printAnalysis(self):
        usefulFileSize = reduce(lambda x, y: x + os.path.getsize(y),
                                map(lambda x: x['filename'], self.latestFiles.values()), 0)
        redundantFileSize = reduce(
            lambda x, y: x + os.path.getsize(y), self.redundants, 0)
        sys.stdout.write("%i Files detected. %i Redundant files detected. \n" % (
            len(self.files), len(self.redundants)))
        sys.stdout.write("%i megabytes of useful files. \n" %
                         (usefulFileSize/1024/1024))
        sys.stdout.write("%i megabytes of redundant files. \n" %
                         (redundantFileSize/1024/1024))
        pass


def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]


def strip_fileHistory(filename):
    if re.search(".* \(...._.._.. .._.._.. .{3}\)", filename):
        start, end = re.search(
            " \(...._.._.. .._.._.. .{3}\)", filename).span()

        return filename[:start] + filename[end:]
    return filename


if __name__ == '__main__':
    try:
        Main().run()
    except KeyboardInterrupt:
        stop = True
        print '\nKeyboardInterrupt'

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from PySide6 import QtCore
from app import constants
from app.domain.models import ToolboxEntry

class SizeCalculationWorker(QtCore.QThread):
    progress = QtCore.Signal(str)
    finished_calculation = QtCore.Signal(int)
    
    def __init__(self, entries: list[ToolboxEntry], parent=None):
        super().__init__(parent)
        self._entries = entries
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        total_size = 0
        for entry in self._entries:
            if self._is_cancelled:
                return
            if entry.kind not in (constants.ENTRY_KIND_TOOL, constants.ENTRY_KIND_FILE, constants.ENTRY_KIND_FOLDER):
                continue
            path = Path(entry.path)
            if not path.exists():
                continue
                
            try:
                if path.is_file():
                    total_size += path.stat().st_size
                elif path.is_dir():
                    # Walk the directory
                    for root, dirs, files in os.walk(path):
                        if self._is_cancelled:
                            return
                        for f in files:
                            if self._is_cancelled:
                                return
                            try:
                                fpath = Path(root) / f
                                if fpath.is_symlink():
                                    continue # ignore symlinks to avoid infinite loops or counting external sizes
                                total_size += fpath.stat().st_size
                            except Exception:
                                pass
            except Exception:
                pass
                
        if not self._is_cancelled:
            self.finished_calculation.emit(total_size)

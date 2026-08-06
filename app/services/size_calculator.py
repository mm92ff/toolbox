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
        
        def _get_dir_size_bfs(start_path: str) -> int:
            sz = 0
            dirs_to_visit = [start_path]
            while dirs_to_visit:
                if self._is_cancelled:
                    return 0
                current_dir = dirs_to_visit.pop()
                try:
                    for it in os.scandir(current_dir):
                        if self._is_cancelled:
                            return 0
                        if it.is_symlink():
                            continue
                        if it.is_file():
                            sz += it.stat(follow_symlinks=False).st_size
                        elif it.is_dir():
                            dirs_to_visit.append(it.path)
                except Exception:
                    pass
            return sz

        for entry in self._entries:
            if self._is_cancelled:
                return
            if entry.kind not in (constants.ENTRY_KIND_TOOL, constants.ENTRY_KIND_FILE, constants.ENTRY_KIND_FOLDER):
                continue
                
            try:
                st = os.stat(entry.path)
                import stat
                if stat.S_ISREG(st.st_mode):
                    total_size += st.st_size
                elif stat.S_ISDIR(st.st_mode):
                    total_size += _get_dir_size_bfs(entry.path)
            except Exception:
                pass
                
        if not self._is_cancelled:
            self.finished_calculation.emit(total_size)

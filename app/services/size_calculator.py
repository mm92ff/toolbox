#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import time
from PySide6 import QtCore
from app import constants
from app.domain.models import ToolboxEntry


class SizeCalculationWorker(QtCore.QThread):
    finished_calculation = QtCore.Signal(str)

    def __init__(self, entries: list[ToolboxEntry], parent=None):
        super().__init__(parent)
        self._entries = entries
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total_size = 0
        is_approximate = False
        start_time = time.monotonic()

        def _get_dir_size(start_path: str) -> int:
            nonlocal is_approximate
            sz = 0
            dirs_to_visit = [start_path]
            while dirs_to_visit:
                if self._is_cancelled:
                    return 0
                if time.monotonic() - start_time > 1.5:
                    is_approximate = True
                    return sz
                current_dir = dirs_to_visit.pop()
                try:
                    with os.scandir(current_dir) as it:
                        for entry in it:
                            if self._is_cancelled:
                                return 0
                            try:
                                if entry.is_symlink():
                                    continue
                                if entry.is_file(follow_symlinks=False):
                                    sz += entry.stat(follow_symlinks=False).st_size
                                elif entry.is_dir(follow_symlinks=False):
                                    dirs_to_visit.append(entry.path)
                            except OSError:
                                pass
                except OSError:
                    pass
            return sz

        # Only process tool-kind entries (sections have no path)
        tool_entries = [e for e in self._entries if e.kind == constants.ENTRY_KIND_TOOL and e.path]

        for entry in tool_entries:
            if self._is_cancelled:
                return
            if time.monotonic() - start_time > 1.5:
                is_approximate = True
                break

            try:
                st = os.stat(entry.path, follow_symlinks=False)
                mode = st.st_mode
                if stat.S_ISREG(mode):
                    total_size += st.st_size
                elif stat.S_ISDIR(mode):
                    total_size += _get_dir_size(entry.path)
                # Ignore other types (sockets, devices, symlinks, etc.)
            except OSError:
                pass

        if not self._is_cancelled:
            if total_size < 1024:
                size_str = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            elif total_size < 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"

            if is_approximate:
                size_str = f"≥ {size_str} (geschätzt)"

            self.finished_calculation.emit(size_str)

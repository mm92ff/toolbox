#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_HOME="${XDG_STATE_HOME:-${HOME}/.local/state}"
LOG_DIR="${STATE_HOME}/toolbox"
LOG_FILE="${LOG_DIR}/code_backup.log"
BACKUP_PREFIX="toolbox_code"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
ARCHIVE_PATH="${PROJECT_DIR}/${BACKUP_PREFIX}_${TIMESTAMP}.7z"
SELF_TEST=false
TEMP_DIR=""
TEMP_ARCHIVE=""
RESTORE_DIR=""
HAS_GIT_REPOSITORY=false
SOURCE_GIT_HEAD_PRESENT=false
SOURCE_GIT_HEAD_FILE=""
SOURCE_GIT_REFS_FILE=""
RESTORED_GIT_HEAD_FILE=""
RESTORED_GIT_REFS_FILE=""

REQUIRED_BACKUP_FILES=(
  ".gitignore"
  "CHANGELOG.md"
  "LICENSE"
  "NOTICE"
  "README.md"
  "THIRD_PARTY_NOTICES.md"
  "Toolbox-Code-Backup.desktop"
  "create-project-backup.bat"
  "main.py"
  "pyproject.toml"
  "requirements.txt"
  "requirements-dev.txt"
  "requirements-build-linux.txt"
  "requirements-build-windows.txt"
  "toolbox_lightweight.spec"
  "toolbox_linux.spec"
  "packaging/linux/AppRun"
  "packaging/linux/toolbox.desktop"
  "packaging/linux/io.github.toolbox.Toolbox.appdata.xml"
  "packaging/linux/FFMPEG-SOURCE.md"
  "packaging/linux/ffmpeg-source-7.0.2.sha256"
  "packaging/linux/ffmpeg-runtime-7.0.2.sha256"
  "packaging/linux/ffmpeg-x86_64.sha256"
  "packaging/linux/licenses/XCB-LICENSE.txt"
  "packaging/linux/licenses/XKBCOMMON-LICENSE.txt"
  "scripts/build-appimage.sh"
  "scripts/build-bundled-ffmpeg.sh"
  "scripts/build-deb.sh"
  "scripts/build-windows-release.ps1"
  "scripts/test-windows-release.ps1"
  "scripts/create_code_backup.sh"
  "scripts/test-deb.sh"
  "scripts/verify-linux-release.sh"
  "app/constants.py"
  "app/application_controller.py"
  "app/main_window.py"
  "app/services/folder_count.py"
  "app/services/desktop_entries.py"
  "app/services/desktop_entry_launch.py"
  "tests/test_appimage_packaging.py"
  "tests/test_deb_packaging.py"
  "tests/test_desktop_entries.py"
  "tests/test_release_licensing.py"
  "tests/test_windows_packaging.py"
  ".github/workflows/build-windows-release.yml"
)

OPTIONAL_BACKUP_FILES=(
  "_pyinstaller_venv_spec_v3.3_debug_fixed.bat"
  "start-toolbox.bat"
)

mkdir -p "${LOG_DIR}"

case "${1:-}" in
  "")
    ;;
  --self-test)
    SELF_TEST=true
    ;;
  *)
    printf 'Verwendung: %s [--self-test]\n' "$0" >&2
    exit 2
    ;;
esac

notify_error() {
  local message="$1"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="Toolbox Code-Backup" --text="${message}" >/dev/null 2>&1 || true
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send -u critical "Toolbox Code-Backup" "${message}" >/dev/null 2>&1 || true
  fi
  printf 'FEHLER: %s\n' "${message}" >&2
}

notify_success() {
  local message="$1"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Toolbox Code-Backup erstellt" "${message}" >/dev/null 2>&1 || true
  elif command -v zenity >/dev/null 2>&1; then
    zenity --info --title="Toolbox Code-Backup" --text="${message}" >/dev/null 2>&1 || true
  fi
  printf '%s\n' "${message}"
}

cleanup() {
  if [[
    -n "${TEMP_DIR}"
    && -d "${TEMP_DIR}"
    && "${TEMP_DIR}" == "${PROJECT_DIR}/.toolbox-backup-tmp-"*
  ]]; then
    rm -rf -- "${TEMP_DIR}"
  fi
}
trap cleanup EXIT

capture_source_git_state() {
  if [[ -e "${PROJECT_DIR}/.git/shallow" ]]; then
    printf '%s\n' \
      "Das Repository ist shallow und enthaelt nicht die vollstaendige Historie." \
      "Fuehre vor dem Backup git fetch --unshallow aus."
    return 1
  fi
  if [[ -e "${PROJECT_DIR}/.git/objects/info/alternates" ]]; then
    printf '%s\n' \
      "Das Repository verwendet einen externen Git-Objektspeicher." \
      "Eine eigenstaendige Sicherung der Git-Historie ist damit nicht garantiert."
    return 1
  fi
  if git -C "${PROJECT_DIR}" config --local --get extensions.partialClone \
    >/dev/null 2>&1; then
    printf '%s\n' \
      "Das Repository ist ein Partial Clone und kann fehlende Git-Objekte enthalten." \
      "Lade vor dem Backup alle Git-Objekte vollstaendig herunter."
    return 1
  fi
  if ! git -C "${PROJECT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%s\n' "Der Projektordner ist kein gueltiges Git-Arbeitsverzeichnis."
    return 1
  fi
  if ! git -C "${PROJECT_DIR}" fsck --strict --full --no-dangling; then
    printf '%s\n' "Die lokale Git-Historie ist beschaedigt oder unvollstaendig."
    return 1
  fi

  if git -C "${PROJECT_DIR}" rev-parse --verify HEAD \
    >"${SOURCE_GIT_HEAD_FILE}" 2>/dev/null; then
    SOURCE_GIT_HEAD_PRESENT=true
  else
    SOURCE_GIT_HEAD_PRESENT=false
    : >"${SOURCE_GIT_HEAD_FILE}"
  fi
  if ! git -C "${PROJECT_DIR}" for-each-ref \
    --sort=refname \
    --format="%(refname) %(objectname)" \
    >"${SOURCE_GIT_REFS_FILE}"; then
    printf '%s\n' "Git-Branches und Tags konnten nicht erfasst werden."
    return 1
  fi
}

verify_restored_git_state() {
  for required_path in .git/HEAD .git/config .git/objects; do
    if [[ ! -e "${RESTORE_DIR}/${required_path}" ]]; then
      printf 'Git-Historie fehlt im Probe-Restore: %s\n' "${required_path}"
      return 1
    fi
  done
  if ! git -C "${RESTORE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%s\n' "Der Probe-Restore ist kein gueltiges Git-Arbeitsverzeichnis."
    return 1
  fi
  if ! git -C "${RESTORE_DIR}" fsck --strict --full --no-dangling; then
    printf '%s\n' "Die Git-Historie im Probe-Restore ist beschaedigt oder unvollstaendig."
    return 1
  fi
  if ! git -C "${RESTORE_DIR}" for-each-ref \
    --sort=refname \
    --format="%(refname) %(objectname)" \
    >"${RESTORED_GIT_REFS_FILE}"; then
    printf '%s\n' "Git-Branches und Tags konnten im Probe-Restore nicht gelesen werden."
    return 1
  fi
  if ! cmp -s "${SOURCE_GIT_REFS_FILE}" "${RESTORED_GIT_REFS_FILE}"; then
    printf '%s\n' "Git-Branches oder Tags stimmen nach dem Probe-Restore nicht ueberein."
    return 1
  fi

  if [[ "${SOURCE_GIT_HEAD_PRESENT}" == false ]]; then
    if git -C "${RESTORE_DIR}" rev-parse --verify HEAD >/dev/null 2>&1; then
      printf '%s\n' "Der Probe-Restore besitzt unerwartet einen anderen Git-HEAD."
      return 1
    fi
    return 0
  fi
  if ! git -C "${RESTORE_DIR}" rev-parse --verify HEAD \
    >"${RESTORED_GIT_HEAD_FILE}" 2>/dev/null; then
    printf '%s\n' "Git-HEAD konnte im Probe-Restore nicht gelesen werden."
    return 1
  fi
  if ! cmp -s "${SOURCE_GIT_HEAD_FILE}" "${RESTORED_GIT_HEAD_FILE}"; then
    printf '%s\n' "Git-HEAD stimmt nach dem Probe-Restore nicht mit dem Original ueberein."
    return 1
  fi
}

if ! command -v 7z >/dev/null 2>&1; then
  notify_error "7z wurde nicht gefunden. Installiere es mit: sudo apt install p7zip-full"
  exit 1
fi

if [[ -e "${PROJECT_DIR}/.git" ]]; then
  if [[ ! -d "${PROJECT_DIR}/.git" ]]; then
    notify_error \
      "Verknuepfte Git-Worktrees koennen nicht als eigenstaendige Historie gesichert werden."
    exit 1
  fi
  if ! command -v git >/dev/null 2>&1; then
    notify_error \
      "Git wurde nicht gefunden. Installiere es mit: sudo apt install git"
    exit 1
  fi
  HAS_GIT_REPOSITORY=true
fi

if [[ -e "${ARCHIVE_PATH}" ]]; then
  suffix=1
  while [[ -e "${PROJECT_DIR}/${BACKUP_PREFIX}_${TIMESTAMP}_${suffix}.7z" ]]; do
    suffix=$((suffix + 1))
  done
  ARCHIVE_PATH="${PROJECT_DIR}/${BACKUP_PREFIX}_${TIMESTAMP}_${suffix}.7z"
fi

TEMP_DIR="$(mktemp -d "${PROJECT_DIR}/.toolbox-backup-tmp-XXXXXXXX")"
TEMP_ARCHIVE="${TEMP_DIR}/$(basename "${ARCHIVE_PATH}")"
RESTORE_DIR="${TEMP_DIR}/restore-check"
SOURCE_GIT_HEAD_FILE="${TEMP_DIR}/source-git-head.txt"
SOURCE_GIT_REFS_FILE="${TEMP_DIR}/source-git-refs.txt"
RESTORED_GIT_HEAD_FILE="${TEMP_DIR}/restored-git-head.txt"
RESTORED_GIT_REFS_FILE="${TEMP_DIR}/restored-git-refs.txt"

{
  printf '\n[%s] Erstelle Code-Backup: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${ARCHIVE_PATH}"
  cd "${PROJECT_DIR}"
  if [[ "${HAS_GIT_REPOSITORY}" == true ]]; then
    capture_source_git_state
  fi
  7z a -t7z -mx=9 -mmt=on \
    '-xr!.venv' \
    '-xr!.venv-appimage' \
    '-xr!venv' \
    '-xr!env' \
    '-xr!__pycache__' \
    '-xr!.pytest_cache' \
    '-xr!.ruff_cache' \
    '-xr!.mypy_cache' \
    '-xr!.pyright' \
    '-xr!.tox' \
    '-xr!.nox' \
    '-xr!.coverage' \
    '-xr!htmlcov' \
    '-xr!coverage.xml' \
    '-xr!build' \
    '-xr!dist' \
    '-xr!dist-appimage' \
    '-xr!dist-deb' \
    '-xr!dist-source' \
    '-xr!dist-windows' \
    '-xr!Toolbox.AppDir' \
    '-xr!thirdparty' \
    '-xr!.bin' \
    '-xr!*.egg-info' \
    '-xr!node_modules' \
    '-xr!.toolbox-backup-tmp-*' \
    '-xr!.env' \
    '-xr!.env.*' \
    '-xr!*.pyc' \
    '-xr!*.pyo' \
    '-xr!*.log' \
    '-xr!*.AppImage' \
    '-xr!*.AppImage.sha256' \
    '-xr!*.deb' \
    '-xr!*.deb.sha256' \
    '-xr!*.exe' \
    '-xr!*.7z' \
    '-xr!*.zip' \
    '-xr!*.rar' \
    "${TEMP_ARCHIVE}" .
  7z t "${TEMP_ARCHIVE}"

  mkdir -p "${RESTORE_DIR}"
  7z x -y "-o${RESTORE_DIR}" "${TEMP_ARCHIVE}"
  for required_file in "${REQUIRED_BACKUP_FILES[@]}"; do
    if [[ ! -f "${RESTORE_DIR}/${required_file}" ]]; then
      printf 'Pflichtdatei fehlt im Probe-Restore: %s\n' "${required_file}"
      exit 1
    fi
  done
  for optional_file in "${OPTIONAL_BACKUP_FILES[@]}"; do
    if [[
      -f "${PROJECT_DIR}/${optional_file}"
      && ! -f "${RESTORE_DIR}/${optional_file}"
    ]]; then
      printf 'Vorhandene Zusatzdatei fehlt im Probe-Restore: %s\n' "${optional_file}"
      exit 1
    fi
  done

  if [[ "${HAS_GIT_REPOSITORY}" == true ]]; then
    verify_restored_git_state
  fi

  if find "${RESTORE_DIR}" -type f \
    \( -name '.env' -o -name '.env.*' \) -print -quit | grep -q .; then
    printf 'Probe-Restore enthaelt eine ausgeschlossene .env-Datei.\n'
    exit 1
  fi
  if find "${RESTORE_DIR}" -type d \
    \( \
      -name '.venv' -o \
      -name '__pycache__' -o \
      -name '.pytest_cache' -o \
      -name 'build' -o \
      -name 'dist' -o \
      -name 'dist-appimage' -o \
      -name 'dist-deb' -o \
      -name 'dist-source' -o \
      -name 'dist-windows' -o \
      -name 'Toolbox.AppDir' \
      -o -name 'thirdparty' \
      -o -name '.bin' \
    \) -print -quit | grep -q .; then
    printf 'Probe-Restore enthaelt einen ausgeschlossenen Build- oder Cacheordner.\n'
    exit 1
  fi
} >>"${LOG_FILE}" 2>&1 || {
  notify_error "Das Backup konnte nicht erstellt oder geprueft werden. Details: ${LOG_FILE}"
  exit 1
}

if [[ "${SELF_TEST}" == true ]]; then
  printf 'Backup-Selbsttest erfolgreich. Details: %s\n' "${LOG_FILE}"
  exit 0
fi

mv -- "${TEMP_ARCHIVE}" "${ARCHIVE_PATH}"
TEMP_ARCHIVE=""
archive_size="$(du -h "${ARCHIVE_PATH}" | awk '{print $1}')"
notify_success "$(basename "${ARCHIVE_PATH}") (${archive_size}) wurde im Projektordner gespeichert."

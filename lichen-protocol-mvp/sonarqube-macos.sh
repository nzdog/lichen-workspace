#!/usr/bin/env bash
set -euo pipefail

# SonarQube macOS One-Command Installer
# - Installs Java 17 (Temurin) via Homebrew if needed
# - Downloads latest SonarQube Community it can find
# - Starts it and waits until healthy
# - Optional: installs sonar-scanner
#
# Usage:
#   ./sonarqube-macos.sh                 # install & start (default)
#   ./sonarqube-macos.sh stop            # stop the service
#   ./sonarqube-macos.sh uninstall       # stop and remove install dir
#   ./sonarqube-macos.sh status          # print health status
#
# Install location:
#   $HOME/.local/sonarqube
#
# Notes:
#   - Requires network access and (ideally) Homebrew.
#   - For local/evaluation use. For production, use PostgreSQL + a service.

ACTION="${1:-install}"

# -------- Config --------
INSTALL_DIR="${HOME}/.local/sonarqube"
DOWNLOAD_DIR="${INSTALL_DIR}/downloads"
RUN_DIR="${INSTALL_DIR}/current"
PORT="9000"
HOST="http://localhost:${PORT}"
BIN_SUBPATH="bin/macosx-universal-64/sonar.sh"
BINARY_INDEX="https://binaries.sonarsource.com/Distribution/sonarqube/"
# Fallback version if scraping fails (update if ever needed):
FALLBACK_VERSION="10.6.0.92116"

mkdir -p "${DOWNLOAD_DIR}"

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
note() { printf "➜ %s\n" "$*"; }
warn() { printf "\033[33m⚠ %s\033[0m\n" "$*"; }
die()  { printf "\033[31m✖ %s\033[0m\n" "$*"; exit 1; }

require_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || die "This script is for macOS only."
}

ensure_homebrew() {
  if ! command -v brew >/dev/null 2>&1; then
    warn "Homebrew not found. Installing Homebrew (interactive, official installer)…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Update current shell to use brew (Apple Silicon)
    local BREW_PREFIX
    BREW_PREFIX="$(/usr/bin/which brew || true)"
    if [[ -z "${BREW_PREFIX}" ]]; then
      if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
      elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
      else
        die "Homebrew installation did not place 'brew' on PATH. Open a new terminal and try again."
      fi
    fi
  fi
}

ensure_java17() {
  if ! /usr/libexec/java_home -v 17 >/dev/null 2>&1; then
    note "Installing Java 17 (Temurin) via Homebrew…"
    brew install --cask temurin@17
  fi
  export JAVA_HOME="$("/usr/libexec/java_home" -v 17)"
  export PATH="${JAVA_HOME}/bin:${PATH}"
  note "JAVA_HOME=${JAVA_HOME}"
}

latest_sonarqube_url() {
  # Try to scrape the binaries index to find the newest sonarqube-*.zip
  local list
  if list="$(curl -fsSL "${BINARY_INDEX}")"; then
    # extract all sonarqube-XX.zip, sort by version, pick latest
    local latest_zip
    latest_zip="$(printf "%s" "${list}" \
      | grep -Eo 'sonarqube-[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?\.zip' \
      | sort -V | tail -1 || true)"
    if [[ -n "${latest_zip}" ]]; then
      printf "%s%s" "${BINARY_INDEX}" "${latest_zip}"
      return 0
    fi
  fi
  # Fallback to a known version if scraping fails
  printf "%ssonarqube-%s.zip" "${BINARY_INDEX}" "${FALLBACK_VERSION}"
}

download_and_unpack() {
  local url dest zip_name extracted_dir
  url="$(latest_sonarqube_url)"
  zip_name="${url##*/}"
  dest="${DOWNLOAD_DIR}/${zip_name}"
  bold "Downloading SonarQube: ${url}"
  if [[ ! -f "${dest}" ]]; then
    curl -fSL -o "${dest}" "${url}" || die "Download failed."
  else
    note "Using cached: ${dest}"
  fi

  bold "Unpacking…"
  (cd "${INSTALL_DIR}" && unzip -q -o "${dest}")
  # Find directory name (e.g., sonarqube-10.6.0.92116)
  extracted_dir="$(basename "${zip_name}" .zip)"
  [[ -d "${INSTALL_DIR}/${extracted_dir}" ]] || die "Unpack failed; '${extracted_dir}' not found."

  # Point RUN_DIR -> extracted_dir (symlink for easy upgrades)
  rm -f "${RUN_DIR}"
  ln -s "${INSTALL_DIR}/${extracted_dir}" "${RUN_DIR}"
  note "Installed at: ${RUN_DIR}"
}

start_sonarqube() {
  bold "Starting SonarQube…"
  local script="${RUN_DIR}/${BIN_SUBPATH}"
  [[ -x "${script}" ]] || die "Start script not found: ${script}"

  # Ensure clean logs dir
  mkdir -p "${RUN_DIR}/logs"

  # Start in background (daemon)
  "${script}" start

  # Wait for port and health
  wait_for_ready
}

wait_for_ready() {
  bold "Waiting for SonarQube to become healthy on ${HOST}…"
  local -i tries=0 max_tries=60
  until curl -fsS "${HOST}/api/system/health" >/dev/null 2>&1; do
    tries+=1
    if (( tries > max_tries )); then
      warn "SonarQube did not respond in time. Check logs at: ${RUN_DIR}/logs"
      "${RUN_DIR}/${BIN_SUBPATH}" status || true
      exit 1
    fi
    sleep 2
  done

  # Optionally check health field
  local health
  health="$(curl -fsS "${HOST}/api/system/health" | sed -E 's/.*"health":"?([A-Z]+)"?.*/\1/')"
  note "Health: ${health:-UNKNOWN}"
  bold "✅ SonarQube is up: ${HOST}"
  printf "\nLogin with:\n  Username: admin\n  Password: admin\n(You'll be prompted to change it.)\n\n"
}

install_scanner() {
  if command -v sonar-scanner >/dev/null 2>&1; then
    note "sonar-scanner already installed."
  else
    note "Installing sonar-scanner via Homebrew…"
    brew install sonar-scanner
  fi
}

cmd_status() {
  bold "SonarQube status"
  if curl -fsS "${HOST}/api/system/health" >/dev/null 2>&1; then
    curl -fsS "${HOST}/api/system/health"; echo
  else
    warn "Not responding on ${HOST}."
  fi
  if [[ -L "${RUN_DIR}" || -d "${RUN_DIR}" ]]; then
    "${RUN_DIR}/${BIN_SUBPATH}" status || true
  fi
}

cmd_stop() {
  if [[ -L "${RUN_DIR}" || -d "${RUN_DIR}" ]]; then
    bold "Stopping SonarQube…"
    "${RUN_DIR}/${BIN_SUBPATH}" stop || true
    note "Stopped (if it was running)."
  else
    warn "No current install found at ${RUN_DIR}"
  fi
}

cmd_uninstall() {
  cmd_stop
  bold "Removing install directory: ${INSTALL_DIR}"
  rm -rf "${INSTALL_DIR}"
  note "Uninstalled."
}

cmd_install() {
  require_macos
  ensure_homebrew
  ensure_java17
  download_and_unpack
  start_sonarqube
  # Comment out if you don't want the scanner by default:
  install_scanner
  bold "Done! Open ${HOST} in your browser."
}

case "${ACTION}" in
  install|"") cmd_install ;;
  stop)        cmd_stop ;;
  uninstall)   cmd_uninstall ;;
  status)      cmd_status ;;
  *)
    die "Unknown action: ${ACTION}. Use: install | stop | status | uninstall"
    ;;
esac
#!/usr/bin/env bash
set -Eeuo pipefail

# 拉取/更新 GitHub 仓库代码（支持首次 clone / 后续更新）
# 默认仓库地址：  https://github.com/WJQ6868/bishe002
# 默认服务器路径：/root/one-liunx/bishe002

REPO_URL_DEFAULT="https://github.com/WJQ6868/bishe002.git"
TARGET_DIR_DEFAULT="/root/one-liunx/bishe002"

REPO_URL="${REPO_URL_DEFAULT}"
TARGET_DIR="${TARGET_DIR_DEFAULT}"
BRANCH=""          # 空表示自动检测：优先当前分支，否则 main/master
FORCE=0             # 0=有本地改动就退出；1=强制覆盖本地改动

usage() {
  cat <<'EOF'
用法:
  ./pull_github_updates.sh [--dir <路径>] [--repo <git_url>] [--branch <分支>] [--force]

说明:
  - 目录不存在：自动 git clone
  - 目录存在：git fetch 后更新到远程最新提交
  - 默认安全模式：检测到本地改动会退出，避免误覆盖
  - 使用 --force：会执行 reset --hard + clean -fd，强制与远程保持一致

示例:
  ./pull_github_updates.sh
  ./pull_github_updates.sh --dir /root/one-liunx/bishe002
  ./pull_github_updates.sh --branch main
  ./pull_github_updates.sh --force
EOF
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      TARGET_DIR="$2"; shift 2 ;;
    --repo)
      REPO_URL="$2"; shift 2 ;;
    --branch)
      BRANCH="$2"; shift 2 ;;
    --force)
      FORCE=1; shift 1 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "未知参数: $1" >&2
      usage
      exit 2
      ;;
  esac
done

have_cmd git || die "未安装 git。请先安装：apt-get install -y git 或 yum/dnf install -y git"

pick_branch() {
  local repo_dir="$1"

  if [[ -n "${BRANCH}" ]]; then
    echo "${BRANCH}"
    return
  fi

  # 如果已经是 git 仓库，优先使用当前分支（非 detached）
  if [[ -d "${repo_dir}/.git" ]]; then
    local current
    current="$(git -C "${repo_dir}" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ -n "${current}" && "${current}" != "HEAD" ]]; then
      echo "${current}"
      return
    fi
  fi

  # 否则按 main -> master 探测远程存在的分支
  if git ls-remote --exit-code --heads "${REPO_URL}" main >/dev/null 2>&1; then
    echo "main"; return
  fi
  if git ls-remote --exit-code --heads "${REPO_URL}" master >/dev/null 2>&1; then
    echo "master"; return
  fi

  die "无法自动判断分支（远程不存在 main/master）。请手动指定：--branch <分支名>"
}

ensure_parent_dir() {
  local dir="$1"
  local parent
  parent="$(dirname "${dir}")"
  mkdir -p "${parent}"
}

is_dirty_repo() {
  local dir="$1"
  [[ -n "$(git -C "${dir}" status --porcelain 2>/dev/null || true)" ]]
}

update_existing_repo() {
  local dir="$1"
  local branch="$2"

  log "进入目录：${dir}"

  # 确保 remote 是期望的地址
  git -C "${dir}" remote set-url origin "${REPO_URL}" >/dev/null 2>&1 || true

  if is_dirty_repo "${dir}"; then
    if [[ "${FORCE}" -eq 1 ]]; then
      log "检测到本地改动，--force 已启用：将强制覆盖本地改动"
    else
      echo "" >&2
      echo "检测到本地改动（未提交/未推送）。为避免覆盖，已退出。" >&2
      echo "你可以先查看有哪些改动：" >&2
      echo "  git -C \"${dir}\" status" >&2
      echo "  git -C \"${dir}\" diff" >&2
      echo "" >&2
      echo "如果你确认要丢弃本地改动并强制与远程一致，请运行（注意 --force 要跟在脚本命令后面）：" >&2
      echo "  bash pull_github_updates.sh --dir \"${dir}\" --force" >&2
      echo "" >&2
      exit 1
    fi
  fi

  log "拉取远程更新：git fetch --prune origin"
  git -C "${dir}" fetch --prune origin

  # 切换到目标分支（本地不存在则从远程创建）
  if ! git -C "${dir}" show-ref --verify --quiet "refs/heads/${branch}"; then
    log "本地分支不存在，创建并跟踪：${branch}"
    git -C "${dir}" checkout -b "${branch}" "origin/${branch}"
  else
    git -C "${dir}" checkout "${branch}"
  fi

  if [[ "${FORCE}" -eq 1 ]]; then
    log "强制同步到 origin/${branch}：reset --hard + clean -fd"
    git -C "${dir}" reset --hard "origin/${branch}"
    git -C "${dir}" clean -fd
  else
    log "安全更新（仅快进）：merge --ff-only origin/${branch}"
    git -C "${dir}" merge --ff-only "origin/${branch}"
  fi

  log "更新完成：$(git -C "${dir}" rev-parse --short HEAD)  $(git -C "${dir}" log -1 --pretty=%s)"
}

clone_repo() {
  local dir="$1"
  local branch="$2"

  ensure_parent_dir "${dir}"

  log "目录不存在，开始 clone：${REPO_URL} -> ${dir}（分支：${branch}）"
  git clone --single-branch --branch "${branch}" "${REPO_URL}" "${dir}"

  log "clone 完成：$(git -C "${dir}" rev-parse --short HEAD)  $(git -C "${dir}" log -1 --pretty=%s)"
}

main() {
  local branch
  branch="$(pick_branch "${TARGET_DIR}")"

  log "repo:   ${REPO_URL}"
  log "dir:    ${TARGET_DIR}"
  log "branch: ${branch}"

  if [[ -d "${TARGET_DIR}/.git" ]]; then
    update_existing_repo "${TARGET_DIR}" "${branch}"
  elif [[ -e "${TARGET_DIR}" ]]; then
    die "目标路径已存在但不是 git 仓库：${TARGET_DIR}（找不到 .git）。请检查路径或清理后再运行。"
  else
    clone_repo "${TARGET_DIR}" "${branch}"
  fi
}

main "$@"

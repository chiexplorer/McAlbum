#!/usr/bin/env bash

# 创建 McAlbum 数据库、媒体和静态站点快照，并对备份进行完整性校验。
set -Eeuo pipefail

PROJECT_ROOT="${1:-$(pwd -P)}"
MYSQL_DEFAULTS_FILE="/etc/mysql/mcalbum-backup.cnf"
API_SERVICE="mcalbum-api"
BACKUP_ID="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${PROJECT_ROOT}/backups/${BACKUP_ID}"
API_WAS_ACTIVE=0
API_STOPPED=0

finish() {
  local status=$?
  trap - EXIT INT TERM
  if [[ "$API_STOPPED" -eq 1 ]]; then
    if ! systemctl start "$API_SERVICE"; then
      printf '%s\n' "警告：备份结束后无法重新启动 ${API_SERVICE}，请立即人工处理。" >&2
      status=1
    fi
  fi
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ "$EUID" -ne 0 ]]; then
  printf '%s\n' '请使用 root 账号执行备份脚本。' >&2
  exit 1
fi

for command_name in flock mysqldump gzip tar sha256sum systemctl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf '缺少必要命令：%s\n' "$command_name" >&2
    exit 1
  fi
done

if [[ ! -f "${PROJECT_ROOT}/package.json" || ! -d "${PROJECT_ROOT}/apps/api" ]]; then
  printf '项目根目录无效：%s\n' "$PROJECT_ROOT" >&2
  exit 1
fi
if [[ ! -r "$MYSQL_DEFAULTS_FILE" ]]; then
  printf '无法读取 MySQL 备份配置：%s\n' "$MYSQL_DEFAULTS_FILE" >&2
  exit 1
fi
for media_directory in storage/originals storage/variants; do
  if [[ ! -d "${PROJECT_ROOT}/${media_directory}" ]]; then
    printf '媒体目录不存在：%s\n' "${PROJECT_ROOT}/${media_directory}" >&2
    exit 1
  fi
done

exec 9>/run/lock/mcalbum-backup.lock
if ! flock -n 9; then
  printf '%s\n' '已有另一个 McAlbum 备份任务在运行。' >&2
  exit 1
fi

install -d -m 0700 "$BACKUP_DIR"
printf '备份目录：%s\n' "$BACKUP_DIR"

if systemctl is-active --quiet "$API_SERVICE"; then
  API_WAS_ACTIVE=1
  API_STOPPED=1
  systemctl stop "$API_SERVICE"
fi

mysqldump \
  --defaults-file="$MYSQL_DEFAULTS_FILE" \
  --single-transaction \
  --quick \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  --no-tablespaces \
  --set-gtid-purged=OFF \
  --default-character-set=utf8mb4 \
  mcalbum | gzip -9 > "${BACKUP_DIR}/mcalbum.sql.gz"

tar -C "$PROJECT_ROOT" -czf "${BACKUP_DIR}/media.tar.gz" \
  storage/originals storage/variants

if [[ -f "${PROJECT_ROOT}/apps/web/.output/public/index.html" ]]; then
  static_items=(public)
  if [[ -f "${PROJECT_ROOT}/apps/web/.output/release-manifest.json" ]]; then
    static_items+=(release-manifest.json)
  fi
  tar -C "${PROJECT_ROOT}/apps/web/.output" \
    -czf "${BACKUP_DIR}/web-static.tar.gz" "${static_items[@]}"
else
  printf '%s\n' '提示：未发现可部署的静态前端，本次不生成 web-static.tar.gz。'
fi

(
  cd "$BACKUP_DIR"
  artifacts=(mcalbum.sql.gz media.tar.gz)
  if [[ -f web-static.tar.gz ]]; then
    artifacts+=(web-static.tar.gz)
  fi
  sha256sum "${artifacts[@]}" > SHA256SUMS
  gzip -t mcalbum.sql.gz
  tar -tzf media.tar.gz >/dev/null
  if [[ -f web-static.tar.gz ]]; then
    tar -tzf web-static.tar.gz >/dev/null
  fi
  sha256sum -c SHA256SUMS
)

chmod -R go-rwx "$BACKUP_DIR"

if [[ "$API_WAS_ACTIVE" -eq 1 && "$API_STOPPED" -eq 1 ]]; then
  systemctl start "$API_SERVICE"
  systemctl is-active --quiet "$API_SERVICE"
  API_STOPPED=0
fi

printf '\n备份完成：%s\n' "$BACKUP_DIR"
du -sh "$BACKUP_DIR"/*


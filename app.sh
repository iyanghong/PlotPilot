#!/usr/bin/env bash
# ============================================================
#  PlotPilot（墨枢）服务管理脚本 — 作者：Axelton
#
#  用法: ./app.sh <command> [service...]
#
#  命令:
#    start    启动全部服务（或指定 backend / frontend）
#    stop     停止全部服务（或指定 backend / frontend）
#    restart  重启全部服务（或指定 backend / frontend）
#    status   查看所有服务运行状态
#    logs     查看服务日志（默认全部，可指定 backend / frontend）
#    update   git pull → 重新构建镜像 → 重新启动（默认全部）
#    build    重新构建镜像（不启动）
#    help     显示此帮助
#
#  使用示例:
#    ./app.sh start              # 启动前后端
#    ./app.sh start backend      # 仅启动后端
#    ./app.sh stop frontend      # 仅停止前端（保持后端运行）
#    ./app.sh status             # 查看运行状态 + 健康检查
#    ./app.sh logs backend       # 跟踪后端日志
#    ./app.sh update             # 拉取最新代码，重建镜像，重启全部
#    ./app.sh update backend     # 仅更新重建后端
# ============================================================

set -euo pipefail

# ── 颜色 ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── 项目路径 ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yaml}"
COMPOSE_CMD="docker compose -f ${COMPOSE_FILE}"

# ── 默认端口 ──────────────────────────────────────────────
BACKEND_PORT="${PLOTPILOT_BACKEND_PORT:-8005}"
FRONTEND_PORT="${PLOTPILOT_FRONTEND_PORT:-3000}"

# ============================================================
#  辅助函数
# ============================================================

_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
_err()   { echo -e "${RED}[ERR]${NC}   $*"; }
_sep()   { echo -e "${CYAN}────────────────────────────────────────────${NC}"; }

_usage() {
    cat <<'HELP'

用法: ./app.sh <command> [service...]

命令:
  start    启动全部服务（或指定 backend / frontend）
  stop     停止全部服务（或指定 backend / frontend）
  restart  重启全部服务（或指定 backend / frontend）
  status   查看所有服务运行状态
  logs     查看服务日志（默认全部，可指定 backend / frontend）
  update   git pull → 重新构建镜像 → 重新启动（默认全部）
  build    重新构建镜像（不启动）
  help     显示此帮助

使用示例:
  ./app.sh start              # 启动前后端
  ./app.sh start backend      # 仅启动后端
  ./app.sh stop frontend      # 仅停止前端（保持后端运行）
  ./app.sh status             # 查看运行状态 + 健康检查
  ./app.sh logs backend       # 跟踪后端日志
  ./app.sh update             # 拉取最新代码，重建镜像，重启全部
  ./app.sh update backend     # 仅更新重建后端

HELP
    exit 0
}

# 检查 docker compose 是否可用
_check_docker() {
    if ! command -v docker &>/dev/null; then
        _err "Docker 未安装或未在 PATH 中。请先安装 Docker。"
        exit 1
    fi
    if ! docker compose version &>/dev/null; then
        _err "docker compose 不可用。请确保 Docker 版本 ≥ 20.10。"
        exit 1
    fi
}

# 检查服务是否响应 HTTP
_http_health() {
    local url="$1"
    local timeout=3
    curl -fsS --max-time "$timeout" "$url" >/dev/null 2>&1 && return 0 || return 1
}

# ============================================================
#  命令实现
# ============================================================

cmd_start() {
    local targets=("$@")
    _check_docker

    if [ ${#targets[@]} -eq 0 ]; then
        _info "启动全部服务…"
        $COMPOSE_CMD up -d --wait
    else
        _info "启动: ${targets[*]}"
        $COMPOSE_CMD up -d --wait "${targets[@]}"
    fi

    echo ""
    _sep
    cmd_status
}

cmd_stop() {
    local targets=("$@")
    _check_docker

    if [ ${#targets[@]} -eq 0 ]; then
        _info "停止全部服务…"
        $COMPOSE_CMD down
        _ok "全部服务已停止"
    else
        _info "停止: ${targets[*]}"
        $COMPOSE_CMD stop "${targets[@]}"
        _ok "${targets[*]} 已停止"
    fi
}

cmd_restart() {
    local targets=("$@")
    _check_docker

    if [ ${#targets[@]} -eq 0 ]; then
        _info "重启全部服务…"
        $COMPOSE_CMD restart
    else
        _info "重启: ${targets[*]}"
        $COMPOSE_CMD restart "${targets[@]}"
    fi

    echo ""
    _sep
    cmd_status
}

cmd_status() {
    _check_docker

    echo ""
    _sep
    echo -e "${CYAN}  PlotPilot 服务状态${NC}"
    _sep

    # ── Docker Compose 容器状态 ──
    echo ""
    echo -e "${BLUE}容器状态:${NC}"
    $COMPOSE_CMD ps 2>/dev/null || echo "  (无运行中的容器)"

    # ── HTTP 健康检查 ──
    echo ""
    echo -e "${BLUE}HTTP 探活:${NC}"

    if _http_health "http://127.0.0.1:${BACKEND_PORT}/health"; then
        echo -e "  backend   → http://127.0.0.1:${BACKEND_PORT}  ${GREEN}✓ 正常${NC}"
    else
        echo -e "  backend   → http://127.0.0.1:${BACKEND_PORT}  ${RED}✗ 不可达${NC}"
    fi

    if _http_health "http://127.0.0.1:${FRONTEND_PORT}"; then
        echo -e "  frontend  → http://127.0.0.1:${FRONTEND_PORT}  ${GREEN}✓ 正常${NC}"
    else
        echo -e "  frontend  → http://127.0.0.1:${FRONTEND_PORT}  ${RED}✗ 不可达${NC}"
    fi

    echo ""
}

cmd_logs() {
    local targets=("$@")
    _check_docker

    if [ ${#targets[@]} -eq 0 ]; then
        _info "查看全部服务日志 (Ctrl+C 退出)…"
        $COMPOSE_CMD logs -f
    else
        _info "查看 ${targets[*]} 日志 (Ctrl+C 退出)…"
        $COMPOSE_CMD logs -f "${targets[@]}"
    fi
}

# ── update: git pull → 重新构建镜像 → 重启 ────────────────

cmd_update() {
    local targets=("$@")
    _check_docker

    _sep
    echo -e "${CYAN}  PlotPilot 更新 & 重建${NC}"
    _sep

    # 1. Git pull
    echo ""
    _info "第 1 步 — 拉取最新代码…"
    if git pull --ff-only; then
        _ok "git pull 完成"
    else
        _warn "git pull 未成功（可能是本地有修改或网络问题），继续构建…"
    fi

    # 2. 停止现有容器（仅对要重建的服务）
    echo ""
    _info "第 2 步 — 停止现有容器…"
    if [ ${#targets[@]} -eq 0 ]; then
        $COMPOSE_CMD down
    else
        $COMPOSE_CMD stop "${targets[@]}"
    fi
    _ok "容器已停止"

    # 3. 重新构建镜像
    echo ""
    _info "第 3 步 — 重建 Docker 镜像（--no-cache）…"
    if [ ${#targets[@]} -eq 0 ]; then
        $COMPOSE_CMD build --no-cache
    else
        $COMPOSE_CMD build --no-cache "${targets[@]}"
    fi
    _ok "镜像构建完成"

    # 4. 启动
    echo ""
    _info "第 4 步 — 启动服务…"
    if [ ${#targets[@]} -eq 0 ]; then
        $COMPOSE_CMD up -d --wait
    else
        $COMPOSE_CMD up -d --wait "${targets[@]}"
    fi
    _ok "服务已启动"

    # 5. 清理悬挂镜像
    echo ""
    _info "清理悬挂镜像…"
    docker image prune -f 2>/dev/null || true
    _ok "完成"

    echo ""
    _sep
    cmd_status
}

# ── build: 仅构建镜像（不启动）────────────────────────────

cmd_build() {
    local targets=("$@")
    _check_docker

    _info "重新构建镜像…"
    if [ ${#targets[@]} -eq 0 ]; then
        $COMPOSE_CMD build --no-cache
    else
        $COMPOSE_CMD build --no-cache "${targets[@]}"
    fi
    _ok "构建完成"
}

# ============================================================
#  主入口
# ============================================================

# 验证 service 参数
_valid_services=("backend" "frontend")

_validate_services() {
    for s in "$@"; do
        local found=false
        for vs in "${_valid_services[@]}"; do
            if [ "$s" == "$vs" ]; then found=true; break; fi
        done
        if ! $found; then
            _err "未知服务 '$s'。可用: ${_valid_services[*]}"
            exit 1
        fi
    done
}

main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        start)
            _validate_services "$@"
            cmd_start "$@"
            ;;
        stop)
            _validate_services "$@"
            cmd_stop "$@"
            ;;
        restart)
            _validate_services "$@"
            cmd_restart "$@"
            ;;
        status|ps)
            cmd_status
            ;;
        logs|log)
            _validate_services "$@"
            cmd_logs "$@"
            ;;
        update|upgrade)
            _validate_services "$@"
            cmd_update "$@"
            ;;
        build)
            _validate_services "$@"
            cmd_build "$@"
            ;;
        help|--help|-h)
            _usage
            ;;
        *)
            _err "未知命令: $cmd"
            echo ""
            _usage
            ;;
    esac
}

main "$@"

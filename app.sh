#!/usr/bin/env bash
# ============================================================
#  PlotPilot（墨枢）服务管理脚本 — 作者：Axelton
#
#  用法: ./app.sh <command> [service...]
#
#  生产命令（Docker Compose）:
#    start    启动全部服务（或指定 backend / frontend）
#    stop     停止全部服务（或指定 backend / frontend）
#    restart  重启全部服务（或指定 backend / frontend）
#    status   查看所有服务运行状态
#    logs     查看服务日志（默认全部，可指定 backend / frontend）
#    update   git pull → 重新构建镜像 → 重新启动（默认全部）
#    build    重新构建镜像（不启动）
#
#  开发命令（本地直启，不依赖 Docker）:
#    dev start    启动开发环境（后端 uvicorn + 前端 vite）
#    dev start -log  启动并持续监听日志（Ctrl+C 退出）
#    dev restart  重启开发环境（可指定 backend / frontend）
#    dev stop     停止开发环境
#    dev status   查看开发环境运行状态
#    dev logs     查看开发环境日志（可指定 backend / frontend）
#
#  使用示例:
#    ./app.sh start              # 启动前后端（Docker）
#    ./app.sh dev start          # 启动开发环境（本地直启）
#    ./app.sh dev start backend  # 仅启动后端开发服务
#    ./app.sh stop frontend      # 仅停止前端（保持后端运行）
#    ./app.sh status             # 查看生产服务状态
#    ./app.sh dev status         # 查看开发环境状态
#    ./app.sh logs backend       # 跟踪生产容器日志
#    ./app.sh dev logs backend   # 跟踪开发后端日志
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

生产命令（Docker Compose）:
  start    启动全部服务（或指定 backend / frontend）
  stop     停止全部服务（或指定 backend / frontend）
  restart  重启全部服务（或指定 backend / frontend）
  status   查看所有服务运行状态
  logs     查看服务日志（默认全部，可指定 backend / frontend）
  update   git pull → 重新构建镜像 → 重新启动（默认全部）
  build    重新构建镜像（不启动）

开发命令（本地直启，不依赖 Docker）:
  dev start         启动开发环境（可指定 backend / frontend）
  dev start -log    启动并持续监听日志（Ctrl+C 退出）
  dev restart       重启开发环境（可指定 backend / frontend）
  dev stop          停止开发环境（可指定 backend / frontend）
  dev status        查看开发环境运行状态
  dev logs          查看开发环境日志（可指定 backend / frontend）

使用示例:
  ./app.sh start              # 启动前后端（Docker）
  ./app.sh dev start          # 启动开发环境（本地直启）
  ./app.sh dev start backend  # 仅启动后端开发服务
  ./app.sh dev start frontend # 仅启动前端开发服务
  ./app.sh dev restart        # 重启全部开发服务
  ./app.sh dev restart backend # 仅重启后端开发服务
  ./app.sh dev start -log     # 启动并持续监听日志（Ctrl+C 退出）
  ./app.sh dev stop backend   # 仅停止后端开发服务
  ./app.sh stop frontend      # 仅停止生产前端（保持后端运行）
  ./app.sh status             # 查看生产服务状态
  ./app.sh dev status         # 查看开发环境状态
  ./app.sh logs backend       # 跟踪生产容器日志
  ./app.sh dev logs backend   # 跟踪开发后端日志

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
#  开发环境（本地直启，不依赖 Docker）
# ============================================================

DEV_PID_DIR="${TMPDIR:-/tmp}/plotpilot-dev"
DEV_LOG_DIR="${DEV_PID_DIR}/logs"
DEV_BACKEND_PID_FILE="${DEV_PID_DIR}/backend.pid"
DEV_FRONTEND_PID_FILE="${DEV_PID_DIR}/frontend.pid"
DEV_BACKEND_LOG="${DEV_LOG_DIR}/backend.log"
DEV_FRONTEND_LOG="${DEV_LOG_DIR}/frontend.log"

# ── 确保开发环境目录存在 ──────────────────────────────────
_init_dev_dirs() {
    mkdir -p "$DEV_PID_DIR" "$DEV_LOG_DIR"
}

# ── 读 PID 文件 ──────────────────────────────────────────
_read_pid() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    fi
}

# ── 写 PID 文件 ──────────────────────────────────────────
_write_pid() {
    local pid_file="$1" pid="$2"
    echo "$pid" > "$pid_file"
}

# ── 检查 PID 对应进程是否存活 ─────────────────────────────
_pid_alive() {
    local pid="$1"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# ── 检查开发环境依赖 ──────────────────────────────────────
_check_dev_deps() {
    local target="$1"  # backend / frontend / all

    if [ "$target" = "backend" ] || [ "$target" = "all" ]; then
        if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
            _err "缺少 Python 虚拟环境: ${SCRIPT_DIR}/.venv"
            echo "  请先创建: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
            return 1
        fi
        if [ ! -f "${SCRIPT_DIR}/.env" ]; then
            _warn "未找到 .env 文件，后端可能缺少 LLM API Key"
        fi
    fi

    if [ "$target" = "frontend" ] || [ "$target" = "all" ]; then
        if [ ! -d "${SCRIPT_DIR}/frontend/node_modules" ]; then
            _err "缺少前端依赖: ${SCRIPT_DIR}/frontend/node_modules"
            echo "  请先安装: cd frontend && npm install"
            return 1
        fi
    fi
    return 0
}

# ── 启动后端开发服务 ─────────────────────────────────────
_dev_start_backend() {
    local pid
    pid=$(_read_pid "$DEV_BACKEND_PID_FILE")

    if _pid_alive "$pid"; then
        _warn "后端开发服务已在运行 (pid=${pid})"
        return 0
    fi

    _info "启动后端开发服务 → http://127.0.0.1:${BACKEND_PORT}"
    (
        cd "$SCRIPT_DIR"
        source ".venv/bin/activate"
        python -m uvicorn interfaces.main:app \
            --host 127.0.0.1 --port "${BACKEND_PORT}" --reload \
            >> "$DEV_BACKEND_LOG" 2>&1
    ) &
    _write_pid "$DEV_BACKEND_PID_FILE" "$!"
    _ok "后端已启动 (pid=$!, 日志: ${DEV_BACKEND_LOG})"
}

# ── 启动前端开发服务 ─────────────────────────────────────
_dev_start_frontend() {
    local pid
    pid=$(_read_pid "$DEV_FRONTEND_PID_FILE")

    if _pid_alive "$pid"; then
        _warn "前端开发服务已在运行 (pid=${pid})"
        return 0
    fi

    _info "启动前端开发服务 → http://127.0.0.1:${FRONTEND_PORT}"
    (
        cd "${SCRIPT_DIR}/frontend"
        npm run dev -- --host 127.0.0.1 --port "${FRONTEND_PORT}" \
            >> "$DEV_FRONTEND_LOG" 2>&1
    ) &
    _write_pid "$DEV_FRONTEND_PID_FILE" "$!"
    _ok "前端已启动 (pid=$!, 日志: ${DEV_FRONTEND_LOG})"
}

# ── 停止开发服务 ─────────────────────────────────────────
_dev_stop_service() {
    local label="$1" pid_file="$2"
    local pid
    pid=$(_read_pid "$pid_file")

    if _pid_alive "$pid"; then
        _info "停止 ${label} (pid=${pid})…"
        kill "$pid" 2>/dev/null || true
        # 等 3 秒，若未退出则强制 kill
        local waited=0
        while _pid_alive "$pid" && [ $waited -lt 30 ]; do
            sleep 0.1; waited=$((waited + 1))
        done
        if _pid_alive "$pid"; then
            _warn "${label} 未响应，强制终止…"
            kill -9 "$pid" 2>/dev/null || true
        fi
        _ok "${label} 已停止"
    else
        _info "${label} 未在运行"
    fi
    rm -f "$pid_file"
}

# ── 查看开发服务状态 ─────────────────────────────────────
_dev_status() {
    echo ""
    _sep
    echo -e "${CYAN}  PlotPilot 开发环境状态${NC}"
    _sep

    echo ""
    echo -e "${BLUE}本地直启服务:${NC}"

    local backend_pid frontend_pid
    backend_pid=$(_read_pid "$DEV_BACKEND_PID_FILE")
    frontend_pid=$(_read_pid "$DEV_FRONTEND_PID_FILE")

    if _pid_alive "$backend_pid"; then
        echo -e "  backend   → http://127.0.0.1:${BACKEND_PORT}  ${GREEN}✓ 运行中${NC} (pid=${backend_pid})"
    else
        echo -e "  backend   → http://127.0.0.1:${BACKEND_PORT}  ${RED}✗ 未运行${NC}"
    fi

    if _pid_alive "$frontend_pid"; then
        echo -e "  frontend  → http://127.0.0.1:${FRONTEND_PORT}  ${GREEN}✓ 运行中${NC} (pid=${frontend_pid})"
    else
        echo -e "  frontend  → http://127.0.0.1:${FRONTEND_PORT}  ${RED}✗ 未运行${NC}"
    fi

    # HTTP 探活
    echo ""
    echo -e "${BLUE}HTTP 探活:${NC}"

    if _http_health "http://127.0.0.1:${BACKEND_PORT}/health" 2>/dev/null; then
        echo -e "  backend   → http://127.0.0.1:${BACKEND_PORT}  ${GREEN}✓ 正常${NC}"
    else
        echo -e "  backend   → http://127.0.0.1:${BACKEND_PORT}  ${RED}✗ 不可达${NC}"
    fi

    if _http_health "http://127.0.0.1:${FRONTEND_PORT}" 2>/dev/null; then
        echo -e "  frontend  → http://127.0.0.1:${FRONTEND_PORT}  ${GREEN}✓ 正常${NC}"
    else
        echo -e "  frontend  → http://127.0.0.1:${FRONTEND_PORT}  ${RED}✗ 不可达${NC}"
    fi

    echo ""
}

# ── 查看开发服务日志 ─────────────────────────────────────
_dev_logs() {
    local target="${1:-all}"

    if [ "$target" = "backend" ]; then
        if [ -f "$DEV_BACKEND_LOG" ]; then
            _info "跟踪后端日志 (Ctrl+C 退出)…"
            tail -f "$DEV_BACKEND_LOG"
        else
            _warn "后端日志不存在: ${DEV_BACKEND_LOG}"
        fi
    elif [ "$target" = "frontend" ]; then
        if [ -f "$DEV_FRONTEND_LOG" ]; then
            _info "跟踪前端日志 (Ctrl+C 退出)…"
            tail -f "$DEV_FRONTEND_LOG"
        else
            _warn "前端日志不存在: ${DEV_FRONTEND_LOG}"
        fi
    else
        _info "跟踪全部开发日志 (Ctrl+C 退出)…"
        tail -f "$DEV_BACKEND_LOG" "$DEV_FRONTEND_LOG" 2>/dev/null || {
            _warn "暂无日志文件"
        }
    fi
}

# ── dev 命令主入口 ────────────────────────────────────────
cmd_dev() {
    local sub="${1:-status}"
    shift || true

    # 解析通用标志
    local follow_log=false
    local filtered_args=()
    for arg in "$@"; do
        if [ "$arg" = "-log" ] || [ "$arg" = "--log" ]; then
            follow_log=true
        else
            filtered_args+=("$arg")
        fi
    done
    set -- "${filtered_args[@]}"

    case "$sub" in
        start)
            _validate_services "$@"
            local targets=("${@}")
            _init_dev_dirs

            if [ ${#targets[@]} -eq 0 ]; then
                if ! _check_dev_deps "all"; then exit 1; fi
                _dev_start_backend
                _dev_start_frontend
            else
                for t in "${targets[@]}"; do
                    if ! _check_dev_deps "$t"; then exit 1; fi
                    if [ "$t" = "backend" ]; then
                        _dev_start_backend
                    elif [ "$t" = "frontend" ]; then
                        _dev_start_frontend
                    fi
                done
            fi

            # 等一等再探活
            echo ""
            _info "等待服务就绪…"
            sleep 2
            if $follow_log; then
                _dev_logs "${1:-all}"
            else
                _dev_status
            fi
            ;;
        stop)
            _init_dev_dirs
            local stop_targets=("${@}")
            if [ ${#stop_targets[@]} -eq 0 ]; then
                _dev_stop_service "backend" "$DEV_BACKEND_PID_FILE"
                _dev_stop_service "frontend" "$DEV_FRONTEND_PID_FILE"
                _ok "开发环境已全部停止"
            else
                for t in "${stop_targets[@]}"; do
                    if [ "$t" = "backend" ]; then
                        _dev_stop_service "backend" "$DEV_BACKEND_PID_FILE"
                    elif [ "$t" = "frontend" ]; then
                        _dev_stop_service "frontend" "$DEV_FRONTEND_PID_FILE"
                    fi
                done
            fi
            ;;
        restart)
            _validate_services "$@"
            _init_dev_dirs
            local restart_targets=("${@}")

            if [ ${#restart_targets[@]} -eq 0 ]; then
                _info "重启全部开发服务…"
                _dev_stop_service "backend" "$DEV_BACKEND_PID_FILE"
                _dev_stop_service "frontend" "$DEV_FRONTEND_PID_FILE"
                _check_dev_deps "all" || exit 1
                _dev_start_backend
                _dev_start_frontend
            else
                for t in "${restart_targets[@]}"; do
                    _info "重启 ${t} 开发服务…"
                    if [ "$t" = "backend" ]; then
                        _dev_stop_service "backend" "$DEV_BACKEND_PID_FILE"
                        _check_dev_deps "backend" || exit 1
                        _dev_start_backend
                    elif [ "$t" = "frontend" ]; then
                        _dev_stop_service "frontend" "$DEV_FRONTEND_PID_FILE"
                        _check_dev_deps "frontend" || exit 1
                        _dev_start_frontend
                    fi
                done
            fi

            echo ""
            _info "等待服务就绪…"
            sleep 2
            if $follow_log; then
                _dev_logs "${1:-all}"
            else
                _dev_status
            fi
            ;;
        status|ps)
            _dev_status
            ;;
        logs|log)
            _validate_services "$@"
            _dev_logs "${1:-all}"
            ;;
        *)
            _err "未知 dev 子命令: $sub"
            echo "  可用: dev start [-log] [backend|frontend] | dev restart [backend|frontend] | dev stop [backend|frontend] | dev status | dev logs [backend|frontend]"
            exit 1
            ;;
    esac
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
        dev)
            cmd_dev "$@"
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

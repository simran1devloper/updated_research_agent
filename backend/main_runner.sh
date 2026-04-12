#!/bin/bash

SERVICES=(api-gateway intent-service memory-service search-service synthesis-service research-service auth-service conversation-service)
PID_DIR="$(dirname "$0")/.pids"
mkdir -p "$PID_DIR"

usage() {
  echo "Usage: $0 [start|stop|restart|status] [service|all]"
  echo "  Services: ${SERVICES[*]}"
  echo "  Example:  $0 start all"
  echo "            $0 start api-gateway intent-service"
  echo "            $0 stop all"
  exit 1
}

resolve_services() {
  if [[ "$*" == "all" ]]; then
    echo "${SERVICES[@]}"
  else
    for s in "$@"; do
      if [[ ! " ${SERVICES[*]} " =~ " $s " ]]; then
        echo "Unknown service: $s" >&2; exit 1
      fi
    done
    echo "$@"
  fi
}

start_service() {
  local svc="$1"
  local pid_file="$PID_DIR/$svc.pid"
  local svc_dir="$(dirname "$0")/$svc"
  local log_dir="$svc_dir/logs"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[$svc] already running (pid $(cat "$pid_file"))"
    return
  fi

  mkdir -p "$log_dir"
  > "$log_dir/run.log"; > "$log_dir/error.log"
  bash "$svc_dir/run.sh" >> "$log_dir/run.log" 2>> "$log_dir/error.log" &
  echo $! > "$pid_file"
  echo "[$svc] started (pid $!) — run: $svc/logs/run.log | error: $svc/logs/error.log"
}

# map service name → HTTP port for fallback kill
declare -A SVC_PORT=(
  [api-gateway]=8000 [intent-service]=8001 [memory-service]=8002
  [search-service]=8003 [synthesis-service]=8004 [research-service]=8005
  [auth-service]=8007 [conversation-service]=8008
)

stop_service() {
  local svc="$1"
  local pid_file="$PID_DIR/$svc.pid"
  local killed=0

  if [[ -f "$pid_file" ]]; then
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      # kill the whole process tree (uvicorn reloader + worker)
      pkill -TERM -P "$pid" 2>/dev/null
      kill "$pid" 2>/dev/null
      sleep 0.5
      kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null
      echo "[$svc] stopped (pid $pid)"
      killed=1
    fi
    rm -f "$pid_file"
  fi

  # fallback: kill any process still holding the port
  local port="${SVC_PORT[$svc]}"
  if [[ -n "$port" ]]; then
    local orphans
    orphans=$(lsof -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null)
    if [[ -n "$orphans" ]]; then
      echo "[$svc] killing orphaned process(es) on port $port: $orphans"
      kill $orphans 2>/dev/null
      killed=1
    fi
  fi

  [[ $killed -eq 0 ]] && echo "[$svc] was not running"
}

status_service() {
  local svc="$1"
  local pid_file="$PID_DIR/$svc.pid"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[$svc] running (pid $(cat "$pid_file"))"
  else
    echo "[$svc] stopped"
    rm -f "$pid_file"
  fi
}

[[ $# -lt 2 ]] && usage

CMD="$1"; shift
TARGETS=$(resolve_services "$@")

for svc in $TARGETS; do
  case "$CMD" in
    start)   start_service  "$svc" ;;
    stop)    stop_service   "$svc" ;;
    restart) stop_service   "$svc"; sleep 1; start_service "$svc" ;;
    status)  status_service "$svc" ;;
    *)       usage ;;
  esac
done

# 06. 프로덕션 이중화 계획 — 파일 기반 인프라 유지 전략

## 1. 현재 아키텍처 분석

### 1.1 파일 기반 컴포넌트 현황

| 컴포넌트 | 저장 형식 | 경로 | 특성 |
|----------|-----------|------|------|
| LanceDB (벡터 DB) | Lance 파일 | `data/lancedb/` | 읽기 많음, 쓰기는 파이프라인 실행 시에만 |
| Entity Store | JSONL | `data/output/ent.json` | 파이프라인 실행 시 전체 재생성 |
| Lexical Graph | JSON | `data/output/lex.json` | 파이프라인 실행 시 전체 재생성 |
| Knowledge Graph | JSON | `data/output/erkg.json` | 파이프라인 실행 시 전체 재생성 |
| Word2Vec 모델 | Binary | `data/output/ent.w2v` | 파이프라인 실행 시 전체 재생성 |
| 설정 파일 | TOML/JSON | `config.toml`, `domain.json` | 거의 변경 없음 |
| 입력 문서 | docx/txt/md | `data/documents/` | 읽기 전용 |

### 1.2 외부 서비스 의존성

| 서비스 | 프로토콜 | 용도 | 현재 구성 |
|--------|----------|------|-----------|
| Ollama (LLM) | HTTP REST | 답변 생성 (`gemma3:4b`) | `192.168.68.68:11434` |
| Ollama (Embed) | HTTP REST | BGE-M3 임베딩 (1024차원) | `192.168.68.68:11434` |
| Senzing gRPC | gRPC | Entity Resolution (선택) | `localhost:8261` |

### 1.3 단일 장애점 (Single Points of Failure)

```
┌─────────────────────────────────────────────────────────┐
│                   현재 아키텍처 (SPOF)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Streamlit UI] ──── 단일 프로세스, 세션 기반 상태       │
│       │                                                 │
│  [AgenticPipeline] ── 인메모리 _chunks, _entities       │
│       │                                                 │
│  [Local Disk] ─────── data/ 전체가 단일 디스크 의존      │
│       │                                                 │
│  [Ollama Server] ──── 단일 인스턴스                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 이중화 전략 개요

파일 기반 아키텍처를 **그대로 유지**하면서 점진적으로 이중화하는 3단계 전략을 제안합니다.

```
Phase 1                  Phase 2                   Phase 3
단일 노드 안정화          Active-Standby             Active-Active (읽기)
─────────────────────   ─────────────────────────  ─────────────────────────
• 프로세스 감시           • 파일 동기화 (lsyncd)      • 로드밸런서 도입
• 자동 재시작             • Ollama 다중 인스턴스       • 읽기 분산
• 정기 백업               • 헬스체크 + 자동 전환       • 쓰기는 Primary 전용
• 디스크 미러링(RAID)     • Warm Standby 노드         • 무중단 파이프라인 실행
```

---

## 3. Phase 1 — 단일 노드 안정화 (즉시 적용 가능)

### 3.1 프로세스 관리: systemd 서비스화

```ini
# /etc/systemd/system/graphrag-streamlit.service
[Unit]
Description=GraphRAG-Senzing Streamlit UI
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=graphrag
WorkingDirectory=/opt/graphrag-senzing
ExecStart=/opt/graphrag-senzing/.venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0
Restart=always
RestartSec=5
# 메모리 제한 (OOM 방지)
MemoryMax=16G
# 자동 재시작 횟수 제한
StartLimitBurst=5
StartLimitIntervalSec=60

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/ollama.service (이미 존재할 수 있음)
[Unit]
Description=Ollama LLM Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
# GPU 메모리 관리
Environment="OLLAMA_NUM_PARALLEL=2"

[Install]
WantedBy=multi-user.target
```

### 3.2 디스크 이중화: RAID 1 미러링

```bash
# data/ 디렉토리가 위치한 볼륨을 RAID 1으로 구성
# (신규 서버 셋업 시 적용)
mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc
mkfs.ext4 /dev/md0
mount /dev/md0 /opt/graphrag-senzing/data
```

운영 중인 서버라면 **LVM 미러링**이 더 실용적입니다:

```bash
# LVM 미러 (운영 중 온라인 적용 가능)
lvcreate --type mirror -m 1 -L 100G -n data_mirror vg0
```

### 3.3 정기 백업: 스냅샷 기반

```bash
#!/bin/bash
# /opt/graphrag-senzing/scripts/backup.sh
# crontab: 0 */6 * * * /opt/graphrag-senzing/scripts/backup.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/graphrag/${TIMESTAMP}"
DATA_DIR="/opt/graphrag-senzing/data"

mkdir -p "${BACKUP_DIR}"

# 파이프라인이 실행 중이 아닐 때만 백업 (락 파일 확인)
LOCK_FILE="${DATA_DIR}/.pipeline.lock"
if [ -f "${LOCK_FILE}" ]; then
    echo "Pipeline running, skipping backup"
    exit 0
fi

# rsync 증분 백업 (변경된 파일만 복사)
rsync -a --delete \
    "${DATA_DIR}/output/" \
    "${BACKUP_DIR}/output/"

rsync -a --delete \
    "${DATA_DIR}/lancedb/" \
    "${BACKUP_DIR}/lancedb/"

# 설정 파일 백업
cp /opt/graphrag-senzing/config.toml "${BACKUP_DIR}/"
cp /opt/graphrag-senzing/domain.json "${BACKUP_DIR}/"

# 7일 이상 된 백업 삭제
find /backup/graphrag/ -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: ${BACKUP_DIR}"
```

### 3.4 헬스체크 스크립트

```python
#!/usr/bin/env python3
"""
/opt/graphrag-senzing/scripts/healthcheck.py
crontab: */5 * * * * python3 /opt/graphrag-senzing/scripts/healthcheck.py
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx

OLLAMA_URL = "http://192.168.68.68:11434"
STREAMLIT_URL = "http://localhost:8501"
ALERT_SCRIPT = "/opt/graphrag-senzing/scripts/alert.sh"
STATUS_FILE = "/tmp/graphrag_health.json"


def check_ollama() -> dict:
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_streamlit() -> dict:
    try:
        resp = httpx.get(f"{STREAMLIT_URL}/_stcore/health", timeout=10)
        return {"status": "ok" if resp.status_code == 200 else "error"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_data_files() -> dict:
    critical_paths = [
        Path("/opt/graphrag-senzing/data/lancedb"),
        Path("/opt/graphrag-senzing/config.toml"),
    ]
    missing = [str(p) for p in critical_paths if not p.exists()]
    return {"status": "ok" if not missing else "warning", "missing": missing}


def check_disk_space() -> dict:
    import shutil
    usage = shutil.disk_usage("/opt/graphrag-senzing/data")
    free_pct = (usage.free / usage.total) * 100
    return {
        "status": "ok" if free_pct > 10 else "critical",
        "free_percent": round(free_pct, 1),
        "free_gb": round(usage.free / (1024**3), 1),
    }


def main():
    results = {
        "timestamp": datetime.now().isoformat(),
        "ollama": check_ollama(),
        "streamlit": check_streamlit(),
        "data_files": check_data_files(),
        "disk_space": check_disk_space(),
    }

    # 상태 파일 기록
    with open(STATUS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # 장애 감지 시 알림
    errors = [k for k, v in results.items()
              if isinstance(v, dict) and v.get("status") in ("error", "critical")]

    if errors:
        msg = f"GraphRAG ALERT: {', '.join(errors)} 장애 감지"
        subprocess.run([ALERT_SCRIPT, msg], check=False)
        print(msg, file=sys.stderr)
        sys.exit(1)

    print("All healthy")


if __name__ == "__main__":
    main()
```

---

## 4. Phase 2 — Active-Standby 구성 (파일 동기화 기반)

### 4.1 아키텍처

```
                    ┌─────────────────┐
                    │   Keepalived    │
                    │  VIP: 10.0.0.10 │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │   Node A (Active)│          │ Node B (Standby) │
     │                  │          │                   │
     │ Streamlit :8501  │  lsyncd  │ Streamlit :8501   │
     │ Pipeline         │ ──────► │ Pipeline           │
     │ data/            │  (실시간) │ data/              │
     │                  │          │                    │
     │ Ollama :11434    │          │ Ollama :11434      │
     └──────────────────┘          └───────────────────┘
```

### 4.2 lsyncd를 이용한 실시간 파일 동기화

```lua
-- /etc/lsyncd/lsyncd.conf.lua (Node A에 설치)
settings {
    logfile    = "/var/log/lsyncd/graphrag.log",
    statusFile = "/var/log/lsyncd/graphrag.status",
    -- 변경 감지 후 즉시 동기화 (최대 1초 지연)
    delay = 1,
}

-- data/ 디렉토리 동기화
sync {
    default.rsync,
    source = "/opt/graphrag-senzing/data/",
    target = "graphrag@node-b:/opt/graphrag-senzing/data/",
    rsync = {
        binary   = "/usr/bin/rsync",
        archive  = true,
        compress = true,
        -- LanceDB .lance 파일은 바이너리이므로 checksum 사용
        checksum = true,
    },
    -- 파이프라인 실행 중 부분 쓰기 방지
    filter = {
        "- .pipeline.lock",
        "- __pycache__/",
        "- uploads/",  -- 임시 업로드는 동기화 불필요
    },
}

-- 설정 파일 동기화
sync {
    default.rsync,
    source = "/opt/graphrag-senzing/",
    target = "graphrag@node-b:/opt/graphrag-senzing/",
    rsync = {
        binary  = "/usr/bin/rsync",
        archive = true,
    },
    filter = {
        "+ config.toml",
        "+ domain.json",
        "+ domain.ttl",
        "- *",  -- 나머지는 제외
    },
}
```

### 4.3 Keepalived를 이용한 자동 Failover

```conf
# /etc/keepalived/keepalived.conf (Node A - MASTER)
vrrp_script check_graphrag {
    script "/opt/graphrag-senzing/scripts/healthcheck.py"
    interval 10
    weight -20
    fall 3      # 3회 연속 실패 시 전환
    rise 2      # 2회 연속 성공 시 복구
}

vrrp_instance GRAPHRAG {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass graphrag_ha
    }

    virtual_ipaddress {
        10.0.0.10/24    # 사용자가 접속하는 VIP
    }

    track_script {
        check_graphrag
    }

    notify_master "/opt/graphrag-senzing/scripts/on_become_master.sh"
    notify_backup "/opt/graphrag-senzing/scripts/on_become_backup.sh"
}
```

```bash
#!/bin/bash
# /opt/graphrag-senzing/scripts/on_become_master.sh
# Standby → Active 전환 시 실행

echo "$(date) Becoming MASTER" >> /var/log/graphrag-failover.log

# Streamlit 서비스 시작
systemctl start graphrag-streamlit

# lsyncd 동기화 방향 전환 (이 노드가 소스가 됨)
systemctl restart lsyncd
```

```bash
#!/bin/bash
# /opt/graphrag-senzing/scripts/on_become_backup.sh
# Active → Standby 전환 시 실행

echo "$(date) Becoming BACKUP" >> /var/log/graphrag-failover.log

# Streamlit은 계속 실행하되, VIP가 없으므로 트래픽은 안 옴
# 또는 중지: systemctl stop graphrag-streamlit
```

### 4.4 Ollama 이중화

Ollama는 Stateless HTTP 서비스이므로 간단히 이중화할 수 있습니다.

```toml
# config.toml 변경 없이, 앞단에 HAProxy를 둠
```

```conf
# /etc/haproxy/haproxy.cfg
frontend ollama_front
    bind *:11434
    default_backend ollama_back

backend ollama_back
    balance roundrobin
    option httpchk GET /api/tags
    http-check expect status 200

    server ollama-a 10.0.0.11:11434 check inter 5s fall 3 rise 2
    server ollama-b 10.0.0.12:11434 check inter 5s fall 3 rise 2 backup
```

이렇게 하면 `config.toml`에서 Ollama URL을 HAProxy VIP로만 변경하면 됩니다:

```toml
[rag]
api_base = "http://10.0.0.10:11434"  # HAProxy VIP

[embed]
ollama_url = "http://10.0.0.10:11434"  # HAProxy VIP
```

---

## 5. Phase 3 — Active-Active 읽기 분산 (선택적 확장)

### 5.1 아키텍처

```
                        ┌─────────────────┐
                        │   Nginx / LB     │
                        │  10.0.0.10:443   │
                        └────────┬─────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
     ┌────────▼───────┐ ┌───────▼────────┐ ┌───────▼────────┐
     │ Node A (RW)     │ │ Node B (RO)     │ │ Node C (RO)    │
     │ Primary         │ │ Read Replica    │ │ Read Replica   │
     │                 │ │                 │ │                │
     │ Streamlit       │ │ Streamlit       │ │ Streamlit      │
     │ Pipeline (쓰기) │ │ Q&A (읽기 전용) │ │ Q&A (읽기 전용)│
     │ data/ (원본)    │ │ data/ (복제)    │ │ data/ (복제)   │
     └────────────────┘ └────────────────┘ └────────────────┘
              │                 ▲                    ▲
              │     lsyncd      │       lsyncd       │
              └─────────────────┴────────────────────┘
```

### 5.2 읽기/쓰기 분리 구현

파이프라인 코드 변경을 최소화하면서 읽기 전용 모드를 지원하는 방법:

```python
# config.toml에 추가
# [ha]
# role = "primary"   # "primary" 또는 "replica"
# read_only = false  # replica는 true
```

`pipeline.py`에 대한 변경은 최소화하고, **Streamlit 앱 레벨에서 제어**합니다:

```python
# app.py에서 읽기 전용 모드 지원 (예시)
# HA 설정 확인
ha_config = config.get("ha", {})
is_replica = ha_config.get("role", "primary") == "replica"

# Tab 1에서 파이프라인 실행 버튼 비활성화
if is_replica:
    st.warning("이 노드는 읽기 전용 레플리카입니다. "
               "파이프라인 실행은 Primary 노드에서만 가능합니다.")
```

### 5.3 Nginx 로드밸런서

```nginx
# /etc/nginx/conf.d/graphrag.conf
upstream graphrag_read {
    # Q&A 읽기 요청은 모든 노드에 분산
    server 10.0.0.11:8501;  # Node A
    server 10.0.0.12:8501;  # Node B
    server 10.0.0.13:8501;  # Node C
}

upstream graphrag_write {
    # 파이프라인 실행은 Primary 노드로만
    server 10.0.0.11:8501;  # Node A (Primary)
}

server {
    listen 443 ssl;
    server_name graphrag.example.com;

    ssl_certificate     /etc/ssl/certs/graphrag.crt;
    ssl_certificate_key /etc/ssl/private/graphrag.key;

    # Streamlit WebSocket 지원
    location / {
        proxy_pass http://graphrag_read;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

---

## 6. LanceDB 특화 이중화 고려사항

### 6.1 LanceDB의 파일 구조

LanceDB는 Apache Arrow 기반의 Lance 포맷을 사용하며, 내부적으로 다음과 같은 파일 구조를 가집니다:

```
data/lancedb/
└── chunk.lance/
    ├── _versions/
    │   ├── 1.manifest
    │   └── 2.manifest
    ├── data/
    │   ├── 00000000-...-0.lance
    │   └── 00000001-...-0.lance
    └── _indices/
        └── ...
```

### 6.2 동기화 시 주의사항

```bash
# LanceDB 동기화 시 파일 일관성 보장을 위해
# 1. manifest 파일이 마지막에 동기화되어야 함
# 2. 파이프라인 실행 중에는 동기화하지 않아야 함

# 안전한 동기화 스크립트
#!/bin/bash
LOCK="/opt/graphrag-senzing/data/.pipeline.lock"

if [ -f "$LOCK" ]; then
    echo "Pipeline running, deferring sync"
    exit 0
fi

# data 파일 먼저, manifest 나중에 (쓰기 순서 보장)
rsync -a --exclude='_versions/' \
    /opt/graphrag-senzing/data/lancedb/ \
    graphrag@node-b:/opt/graphrag-senzing/data/lancedb/

rsync -a \
    /opt/graphrag-senzing/data/lancedb/chunk.lance/_versions/ \
    graphrag@node-b:/opt/graphrag-senzing/data/lancedb/chunk.lance/_versions/
```

### 6.3 향후 고려: LanceDB S3 Backend

LanceDB는 S3 호환 스토리지를 지원합니다. 향후 MinIO를 도입하면 별도의 파일 동기화 없이 공유 스토리지를 사용할 수 있습니다:

```python
# 현재 코드 (파일 기반)
db = lancedb.connect("data/lancedb")

# S3 Backend로 전환 시 (config.toml만 변경)
db = lancedb.connect("s3://graphrag-bucket/lancedb")
```

이 방식은 코드 변경이 `config.toml`의 `lancedb_uri` 한 줄이므로 가장 영향이 적습니다.

---

## 7. 파이프라인 코드 최소 변경 사항

파일 기반 이중화를 위해 `pipeline.py`에 필요한 최소한의 변경:

### 7.1 파이프라인 실행 락 (Lock)

```python
# pipeline.py의 run() 메서드에 추가할 내용
import fcntl

LOCK_PATH = pathlib.Path("data/.pipeline.lock")

def run(self, input_paths, *, skip_nlp=False):
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()

        # ... 기존 파이프라인 로직 ...

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        LOCK_PATH.unlink(missing_ok=True)
```

### 7.2 Atomic File Write (파일 손상 방지)

```python
# JSON 파일 쓰기 시 atomic write 적용
import tempfile

def _atomic_write(path: pathlib.Path, content: str) -> None:
    """임시 파일에 쓰고 rename (atomic operation)."""
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)  # atomic on POSIX
    except Exception:
        os.unlink(tmp_path)
        raise
```

이 두 가지 변경만으로 파일 동기화 기반 이중화의 데이터 일관성을 크게 향상시킬 수 있습니다.

---

## 8. 단계별 적용 로드맵

```
                현재            1개월 후        3개월 후          6개월 후
                ─────           ─────────       ─────────         ─────────
가용성(목표):    ~95%            99%             99.5%             99.9%

적용 항목:
  systemd 서비스화    ████████
  헬스체크 스크립트   ████████
  정기 백업 (rsync)  ████████
  디스크 미러링       ████████
  파이프라인 락             ████████
  Atomic File Write        ████████
  lsyncd 동기화                     ████████
  Keepalived VIP                    ████████
  Ollama HAProxy                    ████████
  Active-Active 읽기                          ████████
  Nginx LB                                    ████████
  LanceDB S3 Backend                                    ████████ (선택)
```

---

## 9. 비용 및 리소스 예측

### Phase 1 (추가 비용 없음)
- 기존 서버에 systemd, cron, rsync 설정만 추가
- 백업 스토리지: 데이터 크기 × 7일 분량 ≈ **50~100GB**

### Phase 2 (서버 1대 추가)
- Standby 서버 1대: 기존과 동일 스펙
  - CPU 8코어 / RAM 32GB / GPU 16GB VRAM / SSD 500GB
- lsyncd, keepalived: 오픈소스 (무료)
- 네트워크 대역폭: 동기화용 **1Gbps** 권장

### Phase 3 (서버 1~2대 추가)
- Read Replica 노드: GPU 없이도 가능 (Q&A 시 Ollama는 별도 서버)
  - CPU 8코어 / RAM 16GB / SSD 200GB
- Nginx: 오픈소스 (무료)

---

## 10. 장애 시나리오별 복구 절차

| 장애 시나리오 | Phase 1 대응 | Phase 2 대응 |
|--------------|-------------|-------------|
| Streamlit 프로세스 다운 | systemd 자동 재시작 (5초) | VIP 자동 전환 (~30초) |
| Ollama 서버 다운 | systemd 재시작 | HAProxy가 Backup으로 전환 |
| 디스크 1개 고장 | RAID 1 자동 복구 | + Standby 노드 보유 |
| 전체 서버 다운 | 백업에서 수동 복구 | Keepalived 자동 전환 (~10초) |
| data/ 파일 손상 | 백업 복원 (최대 6시간 유실) | Standby의 최신 복제본 사용 |
| 파이프라인 실행 중 장애 | 락 파일로 감지 → 재실행 | Primary 복구 후 재실행 |

---

## 11. 결론

현재 파일 기반 아키텍처는 프로덕션 이중화에 적합합니다. 핵심 이유:

1. **데이터가 읽기 중심**: Q&A 서빙 시 파일은 읽기만 하므로 다중 노드에서 안전하게 공유 가능
2. **쓰기가 배치성**: 파이프라인 실행은 비정기적이며, 실행 완료 후 파일이 안정 상태
3. **Stateless 서비스**: Ollama는 모델만 로드하면 되므로 이중화가 간단
4. **파일 동기화 기술 성숙**: lsyncd/rsync는 수십 년간 검증된 기술

**DB 마이그레이션 없이, 코드 변경 최소화로 99.5% 이상의 가용성을 달성할 수 있습니다.**

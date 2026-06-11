# Flask 앱 리눅스 서버 배포/운영 매뉴얼

운영 실행은 하나의 Gunicorn 프로세스와 하나의 Nginx 도메인 설정을 사용합니다.

---

## 1. SSH 접속

```bash
ssh root@210.114.22.173
```

root 비밀번호를 입력합니다.

---

## 2. 코드 파일 업로드

로컬 터미널에서 `monitor` 폴더가 있는 상위 폴더로 이동한 뒤 실행합니다.

```bash
scp -r monitor root@210.114.22.173:/root/
```

---


## 3. `.env` 파일 관리

현재 통합 구조에서는 `.env`가 각 프로젝트 폴더가 아니라 루트에 있어야 합니다.

권한 설정:

```bash
chmod 600 /root/monitor/.env
ls -l /root/monitor/.env
```

정상 예시:

```bash
-rw------- 1 root root 1200 May 15 10:00 /root/monitor/.env
```

HTTPS 적용 후에는 세션 쿠키 보호를 위해 다음으로 변경하는 것을 권장합니다.

```env
SESSION_COOKIE_SECURE=true
```

---

## 4. Python 가상환경 및 패키지 설치

서버에서 실행합니다.

```bash
cd /root/monitor
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Playwright를 사용한다면, Chromium과 리눅스 의존성을 설치합니다.

```bash
python3 -m playwright install --with-deps chromium
```

가상환경 종료:

```bash
deactivate
```

---

## 5. 최초 테스트 실행

서버 터미널에서 먼저 직접 실행해 import 오류와 `.env` 설정을 확인합니다.
`python3 app.py` 직접 실행 시 기본 포트는 `5001`입니다(맥 로컬 개발 기준).
운영 gunicorn은 `5000`을 사용하므로, 테스트도 운영 포트(5000)에 맞추려면 아래처럼 포트를 지정해 실행합니다.

```bash
cd /root/monitor
source venv/bin/activate
FLASK_PORT=5000 python3 app.py
```

정상 실행 시 내부 포트에서 Flask가 실행됩니다.

```text
http://127.0.0.1:5000
```

테스트 실행 종료는 실행 중인 터미널에서 `Ctrl + C`를 누릅니다.

---

## 6. 운영 백그라운드 실행(systemd)

통합 구조에서는 앱별 서비스를 여러 개 만들지 않고 하나의 서비스만 만듭니다.

서비스명 예시:

```text
monitor_unified
```

서비스 파일 생성:

```bash
cat >/etc/systemd/system/monitor_unified.service <<'EOF'
[Unit]
Description=monitor Unified Flask Gunicorn Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/monitor
EnvironmentFile=/root/monitor/.env
ExecStart=/root/monitor/venv/bin/gunicorn -w 1 --timeout 180 --graceful-timeout 30 -b 127.0.0.1:5000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

적용 및 실행:

```bash
systemctl daemon-reload
systemctl enable monitor_unified
systemctl start monitor_unified
systemctl status monitor_unified
journalctl -u monitor_unified -n 50 --no-pager
```

---


## 7. Nginx 도메인 연결

Nginx 설정 파일 생성:

```bash
cat >/etc/nginx/sites-available/monitor_unified <<'EOF'
server {
    listen 80;
    server_name monitor.steeleon.kr;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 180s;
        proxy_send_timeout 180s;
        proxy_read_timeout 180s;
    }
}
EOF
```

적용:

```bash
ln -sf /etc/nginx/sites-available/monitor_unified /etc/nginx/sites-enabled/monitor_unified
nginx -t
systemctl restart nginx
```

---

## 8. HTTPS 적용 권장(현재는 사용 안함)

도메인 연결 후 Certbot을 사용할 수 있습니다.

```bash
apt update
apt install -y certbot python3-certbot-nginx
certbot --nginx -d monitor.steeleon.kr
```

HTTPS 적용 후 `/root/monitor/.env`에서 다음 값을 권장합니다.

```env
SESSION_COOKIE_SECURE=true
```

변경 후 재시작:

```bash
systemctl restart monitor_unified
systemctl restart nginx
```

---

## 9. 소스 코드 수정 시 업데이트

가장 안전한 방식은 전체 `monitor` 폴더를 다시 올리는 것입니다.
로컬 터미널에서 `monitor` 폴더가 있는 상위 폴더로 이동한 뒤 실행합니다.

로컬 터미널:

```bash
scp -r monitor root@183.111.227.182:/root/
```

서버에서 패키지 변경 반영 및 재시작:

```bash
cd /root/monitor
source venv/bin/activate
pip install -r requirements.txt
systemctl restart monitor_unified
systemctl status monitor_unified
journalctl -u monitor_unified -n 50 --no-pager
```

venv로 들어간 상태이면 아래처럼 실행해서 빠져 나옵니다.

```bash
deactivate
```

`.env`는 서버의 실제 비밀값 파일이므로 로컬 예시 파일로 덮어쓰지 않도록 주의합니다.
업로드 후 권한을 다시 확인합니다.

```bash
chmod 600 /root/monitor/.env
```

---

## 10. 서비스 중지 및 초기화

실행 중인 Gunicorn 확인:

```bash
ps -ef | grep gunicorn
```

systemd 서비스 확인:

```bash
systemctl | grep monitor_
```

서비스 중지: monitor_unified 는 서비스 이름

```bash
systemctl stop monitor_unified.service
```

현재 등록된 사비스명 확인:
```bash
ls /etc/systemd/system/ | grep monitor_
```

자동 시작 해제:

```bash
systemctl disable monitor_unified.service
```

포트 확인:

```bash
ss -tulpn | grep 5000
```

아무것도 나오지 않으면 해당 포트는 사용 중이 아닙니다.

전체 폴더 삭제:

```bash
rm -rf /root/monitor
```

서비스 파일 삭제:

```bash
rm -f /etc/systemd/system/monitor_unified.service
systemctl daemon-reload
```

마지막 확인:

```bash
systemctl | grep monitor_
ps -ef | grep gunicorn
ss -tulpn | grep 5000
```

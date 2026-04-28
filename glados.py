import requests
import os
import sys
from datetime import datetime

# -------------------------------------------------------------------------------------------
# GLADOS 签到 + 满500自动兑换（GitHub Actions 专用）
# -------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # 读取环境变量
    WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")
    GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")

    # 域名（GitHub 只能用这个）
    DOMAIN = "https://glados.rocks"
    
    headers = {
        "cookie": GLADOS_COOKIE,
        "user-agent": "Mozilla/5.0",
        "content-type": "application/json;charset=UTF-8"
    }

    payload = {"token": "glados.network"}

    # ---------------- 异常推送 ----------------
    def send_error(msg):
        if WECOM_WEBHOOK:
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text", "text": {"content": f"GLADOS签到失败\n{msg}"}
            })

    # ---------------- 开始执行 ----------------
    try:
        # 1. 签到
        checkin = requests.post(f"{DOMAIN}/api/user/checkin", headers=headers, json=payload, timeout=10).json()
        
        # 2. 获取信息
        status = requests.get(f"{DOMAIN}/api/user/status", headers=headers, timeout=10).json()

        if status.get("code") != 0:
            send_error("Cookie 已失效")
            sys.exit(1)

        # 解析数据
        data = status["data"]
        email = data["email"]
        left_days = float(data.get("leftDays", 0))
        balance = float(data.get("balance", 0))
        message = checkin.get("message", "成功")
        point = float(checkin.get("data", {}).get("point", 0))
        check_result = "Checkin OK" if checkin.get("code") == 0 else "FAIL"

        # 兑换
        exchange_msg = "无需兑换"
        if balance >= 500:
            try:
                res = requests.post(f"{DOMAIN}/api/user/exchange", headers=headers, json=payload, timeout=10).json()
                exchange_msg = "兑换成功 500积分→30天" if res.get("code") == 0 else "兑换失败"
            except:
                exchange_msg = "兑换失败"

        # 企业微信推送
        if WECOM_WEBHOOK:
            content = (
                f"账号:{email}\n"
                f"日期:{datetime.utcnow().isoformat()[:23]}Z\n"
                f"签到结果:{check_result}\n"
                f"签到消息:{message}\n"
                f"随机积分:{int(point)}\n"
                f"积分余额:{int(balance)}\n"
                f"剩余天数:{int(left_days)}\n"
                f"兑换状态:{exchange_msg}"
            )
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text", "text": {"content": f"GLADOS签到通知\n{content}"}
            })

    except Exception as e:
        send_error(f"脚本异常：{str(e)}")
        sys.exit(1)

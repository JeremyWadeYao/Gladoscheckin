import requests
import os
import sys
from datetime import datetime

# -------------------------------------------------------------------------------------------
# GLADOS 签到 + 积分修复 + 满500自动兑换 + 企业微信通知（稳定版）
# -------------------------------------------------------------------------------------------

DOMAIN = "https://glados.rocks"

CHECKIN_URL = f"{DOMAIN}/api/user/checkin"
STATUS_URL = f"{DOMAIN}/api/user/status"
EXCHANGE_URL = f"{DOMAIN}/api/user/exchange"

WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")
GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")

HEADERS = {
    "cookie": GLADOS_COOKIE,
    "referer": f"{DOMAIN}/console/checkin",
    "origin": DOMAIN,
    "user-agent": "Mozilla/5.0",
    "content-type": "application/json;charset=UTF-8"
}

PAYLOAD = {"token": "glados.network"}


def send_wecom(msg):
    if not WECOM_WEBHOOK:
        return
    try:
        requests.post(WECOM_WEBHOOK, json={
            "msgtype": "text",
            "text": {"content": msg}
        }, timeout=10)
    except Exception as e:
        print("企业微信发送失败:", e)


def send_error(msg):
    print("ERROR:", msg)
    send_wecom(f"GLADOS签到失败\n{msg}")


def get_balance(data):
    """
    兼容不同版本字段
    """
    return float(
        data.get("points") or
        data.get("point") or
        data.get("balance") or
        0
    )


def main():
    if not GLADOS_COOKIE:
        send_error("未配置 GLADOS_COOKIE")
        sys.exit(1)

    try:
        # ---------------- 签到 ----------------
        checkin_res = requests.post(CHECKIN_URL, headers=HEADERS, json=PAYLOAD, timeout=15)
        checkin_json = checkin_res.json()

        # ---------------- 状态 ----------------
        status_res = requests.get(STATUS_URL, headers=HEADERS, timeout=15)
        status_json = status_res.json()

        # 👉 调试用（必要时打开）
        print("DEBUG STATUS:", status_json)

        if status_json.get("code") != 0:
            send_error("Cookie失效或接口异常")
            sys.exit(1)

        data = status_json.get("data", {})

        # 强校验
        email = data.get("email")
        if not email:
            send_error("Cookie无效（未获取到用户信息）")
            sys.exit(1)

        left_days = float(data.get("leftDays", 0))
        balance = get_balance(data)

        # ---------------- 签到结果 ----------------
        check_msg = checkin_json.get("message", "")
        check_code = checkin_json.get("code", -1)
        today_point = float(checkin_json.get("data", {}).get("point", 0))

        check_result = "✅ 成功" if check_code == 0 else "❌ 失败"

        # ---------------- 自动兑换 ----------------
        exchange_msg = "无需兑换（积分不足500）"

        if balance >= 500:
            try:
                ex_res = requests.post(EXCHANGE_URL, headers=HEADERS, json=PAYLOAD, timeout=15)
                ex_json = ex_res.json()

                if ex_json.get("code") == 0:
                    exchange_msg = "🎉 兑换成功：500积分 → 30天"
                else:
                    exchange_msg = f"⚠️ 兑换失败：{ex_json.get('message', '未知错误')}"
            except Exception as e:
                exchange_msg = f"❌ 兑换异常：{str(e)}"

        # ---------------- 输出 ----------------
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        result = (
            f"GLADOS签到通知\n"
            f"账号：{email}\n"
            f"时间：{now}\n"
            f"签到：{check_result}\n"
            f"消息：{check_msg}\n"
            f"今日积分：{int(today_point)}\n"
            f"积分余额：{int(balance)}\n"
            f"剩余天数：{int(left_days)}\n"
            f"兑换状态：{exchange_msg}"
        )

        print(result)
        send_wecom(result)

    except Exception as e:
        send_error(f"脚本异常：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

import requests
import os
import sys
from datetime import datetime

# -------------------------------------------------------------------------------------------
# GLADOS 自动签到（GITHUB 专用，可直接运行）
# -------------------------------------------------------------------------------------------

if __name__ == '__main__':
    print("=== GitHub 环境运行 GLADOS 签到 ===")

    WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")
    GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")

    if not GLADOS_COOKIE:
        print("❌ 未获取到 GLADOS_COOKIE")
        sys.exit(1)

    # ========== GitHub 必须用这个域名 ==========
    DOMAIN = "https://glados.rocks"
    checkin_url = f"{DOMAIN}/api/user/checkin"
    status_url = f"{DOMAIN}/api/user/status"
    exchange_url = f"{DOMAIN}/api/user/exchange"

    headers = {
        "cookie": GLADOS_COOKIE,
        "referer": f"{DOMAIN}/console/checkin",
        "origin": DOMAIN,
        "user-agent": "Mozilla/5.0",
        "content-type": "application/json;charset=UTF-8"
    }

    payload = {"token": "glados.network"}

    # 签到
    try:
        checkin = requests.post(checkin_url, headers=headers, json=payload, timeout=15)
        checkin_json = checkin.json()
    except Exception as e:
        print(f"❌ 签到失败: {e}")
        sys.exit(1)

    # 获取状态
    try:
        state = requests.get(status_url, headers=headers, timeout=15)
        state_json = state.json()
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")
        sys.exit(1)

    if state_json.get("code") != 0:
        print("❌ Cookie 已失效")
        sys.exit(1)

    # 解析数据
    try:
        left_days = float(state_json["data"].get("leftDays", 0))
        email = state_json["data"]["email"]
        balance = float(state_json["data"]["balance"])
    except:
        print("❌ 数据解析异常")
        sys.exit(1)

    # 签到结果
    message = checkin_json.get("message", "成功")
    check_result = "Checkin OK" if checkin_json.get("code") == 0 else "FAIL"
    point = float(checkin_json.get("data", {}).get("point", 0))

    # 兑换
    exchange_msg = "无需兑换"
    if balance >= 500:
        try:
            res = requests.post(exchange_url, headers=headers, json=payload, timeout=10)
            rjson = res.json()
            exchange_msg = "兑换成功 500积分→30天" if rjson.get("code") == 0 else "兑换失败"
        except:
            exchange_msg = "兑换异常"

    now_utc = datetime.utcnow().isoformat()[:23] + "Z"

    # 输出
    print(f"{email} | {message} | 剩余{int(left_days)}天 | {exchange_msg}")

    # 企业微信
    if WECOM_WEBHOOK:
        wx_content = (
            f"账号:{email}\n"
            f"日期:{now_utc}\n"
            f"签到结果:{check_result}\n"
            f"签到消息:{message}\n"
            f"随机积分:{int(point)}\n"
            f"积分余额:{int(balance)}\n"
            f"剩余天数:{int(left_days)}\n"
            f"兑换状态:{exchange_msg}"
        )
        requests.post(WECOM_WEBHOOK, json={
            "msgtype": "text", "text": {"content": f"GLADOS签到通知\n{wx_content}"}
        })

    print("=== 签到完成 ===")
    sys.exit(0)

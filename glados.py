import requests
import os
import sys
from datetime import datetime

# -------------------------------------------------------------------------------------------
# GLADOS 签到 修复积分读取 + 满500自动兑换 GitHub版
# -------------------------------------------------------------------------------------------

if __name__ == '__main__':
    WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")
    GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")

    if not GLADOS_COOKIE:
        if WECOM_WEBHOOK:
            requests.post(WECOM_WEBHOOK, json={"msgtype":"text","text":{"content":"GLADOS签到失败：未配置Cookie"}})
        sys.exit(1)

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

    def send_err(txt):
        if WECOM_WEBHOOK:
            requests.post(WECOM_WEBHOOK, json={"msgtype":"text","text":{"content":f"GLADOS签到失败\n{txt}"}})

    try:
        # 签到
        checkin_res = requests.post(checkin_url, headers=headers, json=payload, timeout=15)
        checkin_json = checkin_res.json()

        # 用户状态
        state_res = requests.get(status_url, headers=headers, timeout=15)
        state_json = state_res.json()

        if state_json.get("code") != 0:
            send_err("Cookie失效或登录异常")
            sys.exit(1)

        data = state_json["data"]
        email = data["email"]
        left_days = float(data.get("leftDays", 0))
        
        # ========== 修复：读取真实积分 Points ==========
        balance = float(data.get("point", 0))

        # 签到信息
        msg = checkin_json.get("message", "")
        code = checkin_json.get("code", -1)
        point = float(checkin_json.get("data", {}).get("point", 0))
        check_result = "Checkin OK" if code == 0 else "Checkin FAIL"

        now_utc = datetime.utcnow().isoformat()[:23] + "Z"
        exchange_msg = "无需兑换（积分不足500）"

        # 满500自动兑换
        if balance >= 500:
            try:
                ex_res = requests.post(exchange_url, headers=headers, json=payload, timeout=15)
                ex_json = ex_res.json()
                if ex_json.get("code") == 0:
                    exchange_msg = "兑换成功 500积分 → 30天"
                else:
                    exchange_msg = f"兑换失败：{ex_json.get('message','未知')}"
            except Exception as e:
                exchange_msg = f"兑换异常：{str(e)}"

        # 企业微信推送
        if WECOM_WEBHOOK:
            wx_content = (
                f"账号:{email}\n"
                f"日期:{now_utc}\n"
                f"签到结果:{check_result}\n"
                f"签到消息:{msg}\n"
                f"随机积分:{int(point)}\n"
                f"积分余额:{int(balance)}\n"
                f"剩余天数:{int(left_days)}\n"
                f"兑换状态:{exchange_msg}"
            )
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text",
                "text": {"content": f"GLADOS签到通知\n{wx_content}"}
            })

    except Exception as e:
        send_err(f"脚本异常：{str(e)}")
        sys.exit(1)

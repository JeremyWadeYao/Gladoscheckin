import requests
import os
import sys
from datetime import datetime

if __name__ == '__main__':
    WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")
    GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")

    if not GLADOS_COOKIE:
        if WECOM_WEBHOOK:
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text",
                "text": {"content": "GLADOS签到失败：未配置GLADOS_COOKIE环境变量"}
            })
        sys.exit(1)

    DOMAIN = "https://glados.rocks"
    checkin_url = f"{DOMAIN}/api/user/checkin"
    status_url = f"{DOMAIN}/api/user/status"
    exchange_url = f"{DOMAIN}/api/user/exchange"

    headers = {
        "cookie": GLADOS_COOKIE,
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "content-type": "application/json;charset=UTF-8"
    }
    payload = {"token": "glados.network"}

    def send_wechat_err(msg):
        if WECOM_WEBHOOK:
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text",
                "text": {"content": f"GLADOS签到异常\n{msg}"}
            })

    try:
        # 签到接口
        checkin_resp = requests.post(checkin_url, headers=headers, json=payload, timeout=12)
        checkin_json = checkin_resp.json()

        # 用户状态接口
        status_resp = requests.get(status_url, headers=headers, timeout=12)
        status_json = status_resp.json()

        if status_json.get("code") != 0:
            send_wechat_err(f"登录校验失败，接口返回：{status_json}")
            sys.exit(1)

        data = status_json["data"]
        email = data["email"]
        left_days = float(data.get("leftDays", 0))

        # 签到信息解析
        check_msg = checkin_json.get("message", "")
        check_code = checkin_json.get("code", -1)
        today_point = float(checkin_json.get("data", {}).get("point", 0))
        check_result = "Checkin OK" if check_code == 0 else "Checkin FAIL"
        now_utc = datetime.utcnow().isoformat()[:23] + "Z"
        exchange_msg = "无需兑换（无积分数据）"

        # 兑换逻辑说明：无法读取总积分，关闭自动兑换判断
        # 如需兑换需手动网页操作
        exchange_msg = "暂不支持自动兑换（接口无总积分字段）"

        # 企业微信推送（移除积分余额，消除0的误导）
        if WECOM_WEBHOOK:
            wx_content = (
                f"账号:{email}\n"
                f"日期:{now_utc}\n"
                f"签到结果:{check_result}\n"
                f"签到消息:{check_msg}\n"
                f"本次获得积分:{int(today_point)}\n"
                f"剩余会员天数:{int(left_days)}\n"
                f"兑换状态:{exchange_msg}"
            )
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text",
                "text": {"content": f"GLADOS签到通知\n{wx_content}"}
            })

    except Exception as err:
        send_wechat_err(f"脚本运行捕获异常：{str(err)}")
        sys.exit(1)

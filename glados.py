import requests
import os
import sys
from datetime import datetime

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
    point_url = f"{DOMAIN}/api/user/point" # 积分专用接口

    headers = {
        "cookie": GLADOS_COOKIE,
        "user-agent": "Mozilla/5.0",
        "content-type": "application/json;charset=UTF-8"
    }
    payload = {"token": "glados.network"}

    def send_err(txt):
        if WECOM_WEBHOOK:
            requests.post(WECOM_WEBHOOK, json={"msgtype":"text","text":{"content":f"GLADOS签到失败\n{txt}"}})

    try:
        # 签到
        checkin_json = requests.post(checkin_url, headers=headers, json=payload, timeout=10).json()
        # 用户基础状态
        status_json = requests.get(status_url, headers=headers, timeout=10).json()
        # 单独获取总积分
        point_res = requests.get(point_url, headers=headers, timeout=10)
        point_json = point_res.json()

        if status_json.get("code") != 0:
            send_err("Cookie失效或登录异常")
            sys.exit(1)

        data = status_json["data"]
        email = data["email"]
        left_days = float(data.get("leftDays", 0))

        # 从积分接口读取总积分
        total_point = float(point_json.get("data", {}).get("point", 0))

        check_msg = checkin_json.get("message", "")
        get_point = float(checkin_json.get("data", {}).get("point", 0))
        check_result = "Checkin OK" if checkin_json.get("code") == 0 else "Checkin FAIL"
        now_utc = datetime.utcnow().isoformat()[:23] + "Z"
        exchange_msg = "无需兑换（积分不足500）"

        # 兑换判断使用真实总积分
        if total_point >= 500:
            try:
                ex_json = requests.post(f"{DOMAIN}/api/user/exchange", headers=headers, json=payload, timeout=10).json()
                exchange_msg = "兑换成功 500积分 → 30天" if ex_json.get("code") == 0 else f"兑换失败：{ex_json.get('message','未知')}"
            except Exception as e:
                exchange_msg = f"兑换异常：{str(e)}"

        # 企微推送
        if WECOM_WEBHOOK:
            wx_content = (
                f"账号:{email}\n"
                f"日期:{now_utc}\n"
                f"签到结果:{check_result}\n"
                f"签到消息:{check_msg}\n"
                f"本次积分:{int(get_point)}\n"
                f"积分余额:{int(total_point)}\n"
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

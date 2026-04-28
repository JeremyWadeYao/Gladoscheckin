import requests
import os
import sys

# -------------------------------------------------------------------------------------------
# GLADOS 自动签到 - 企业微信机器人版
# -------------------------------------------------------------------------------------------

if __name__ == '__main__':

    # 企业微信机器人 webhook
    WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")

    # GLADOS Cookie
    GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")

    # 本地测试可手动填写
    # GLADOS_COOKIE = ""
    # WECOM_WEBHOOK = ""

    if not GLADOS_COOKIE:
        print("未获取到 GLADOS_COOKIE")
        sys.exit(0)

    checkin_url = "https://glados.cloud/api/user/checkin"
    status_url = "https://glados.cloud/api/user/status"

    headers = {
        "cookie": GLADOS_COOKIE,
        "referer": "https://glados.cloud/console/checkin",
        "origin": "https://glados.cloud",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "content-type": "application/json;charset=UTF-8"
    }

    payload = {
        "token": "glados.cloud"
    }

    try:
        # -------------------- 签到 --------------------
        checkin = requests.post(checkin_url, headers=headers, json=payload, timeout=15)
        checkin_json = checkin.json()
    except Exception as e:
        print("签到请求失败:", e)
        sys.exit(1)

    try:
        # -------------------- 获取状态 --------------------
        state = requests.get(status_url, headers=headers, timeout=15)
        state_json = state.json()
    except Exception as e:
        print("状态请求失败:", e)
        sys.exit(1)

    # -------------------- 权限检测 --------------------
    if state_json.get("code") != 0:
        message = state_json.get("message", "未知错误")
        print("Cookie失效或无权限:", message)

        if WECOM_WEBHOOK:
            msg = {
                "msgtype": "text",
                "text": {
                    "content": f"GLADOS签到失败\n原因: {message}"
                }
            }
            requests.post(WECOM_WEBHOOK, json=msg)

        sys.exit(0)

    # -------------------- 正常数据 --------------------
    try:
        left_days = state_json["data"]["leftDays"].split('.')[0]
        email = state_json["data"]["email"]
        balance = float(state_json["data"]["balance"])
    except KeyError:
        print("接口结构发生变化:", state_json)
        sys.exit(1)

    now_utc = datetime.utcnow().isoformat()[:23] + "Z"
    exchange_msg = "无需兑换（积分不足500）"

    # ========== 积分大于等于500 自动兑换 ==========
    if balance >= 500:
        try:
            res = requests.post(exchange_url, headers=headers, json=payload, timeout=15)
            res_json = res.json()
            if res_json.get("code") == 0:
                exchange_msg = "兑换成功 500积分 → 30天"
            else:
                exchange_msg = f"兑换失败：{res_json.get('message','未知原因')}"
        except Exception as e:
            exchange_msg = f"兑换请求异常：{str(e)}"
            
    # -------------------- 签到结果 --------------------
    if checkin_json.get("code") == 0:
        message = checkin_json.get("message", "签到成功")
        check_result = "Checkin OK"
        point = float(checkin_json.get("data", {}).get("point", 0))
    else:
        message = checkin_json.get("message", "未知状态")
        check_result = "Checkin FAIL"
        point = 0

    result_text = f"{email} ---- {message} ---- 剩余({int(left_days)})天 | {exchange_msg}"

    print(result_text)

    # -------------------- 企业微信推送 --------------------
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
        msg = {
            "msgtype": "text",
            "text": {
                "content": f"GLADOS签到通知\n{wx_content}"
            }
        }
        requests.post(WECOM_WEBHOOK, json=msg)

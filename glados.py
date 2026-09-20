import requests
import os
import sys
from datetime import datetime

# ========== 配置区 ==========
# 个人微信推送：Server酱 SendKey（必填）
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")
# 企业微信 Webhook（可选，留空则不推送）
WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")
# GLADOS Cookie（必填）
GLADOS_COOKIE = os.environ.get("GLADOS_COOKIE", "")
# ============================


def send_wechat(title, content):
    """推送到个人微信（Server酱），失败时回退到企业微信"""
    sent = False

    # 优先用 Server酱 推送到个人微信
    if SERVERCHAN_KEY:
        try:
            resp = requests.post(
                f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send",
                data={"title": title, "desp": content},
                timeout=12
            )
            if resp.json().get("code") == 0:
                sent = True
            else:
                print(f"[警告] Server酱推送失败: {resp.text}")
        except Exception as e:
            print(f"[警告] Server酱推送异常: {e}")

    # 回退：企业微信 Webhook
    if not sent and WECOM_WEBHOOK:
        try:
            requests.post(WECOM_WEBHOOK, json={
                "msgtype": "text",
                "text": {"content": f"{title}\n{content}"}
            }, timeout=12)
            sent = True
        except Exception as e:
            print(f"[警告] 企业微信推送异常: {e}")

    if not sent:
        print("[警告] 未配置任何推送渠道，消息未发送")

    return sent


if __name__ == '__main__':
    # 启动前检查必要配置
    if not GLADOS_COOKIE:
        send_wechat("GLADOS签到失败", "未配置GLADOS_COOKIE环境变量")
        sys.exit(1)

    DOMAIN = "https://glados.rocks"
    checkin_url = f"{DOMAIN}/api/user/checkin"
    status_url = f"{DOMAIN}/api/user/status"

    headers = {
        "cookie": GLADOS_COOKIE,
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "Chrome/120.0.0.0 Safari/537.36",
        "content-type": "application/json;charset=UTF-8"
    }
    payload = {"token": "glados.network"}

    try:
        # 1. 签到
        checkin_resp = requests.post(checkin_url, headers=headers,
                                     json=payload, timeout=12)
        checkin_json = checkin_resp.json()

        # 2. 查询账号状态
        status_resp = requests.get(status_url, headers=headers, timeout=12)
        status_json = status_resp.json()

        if status_json.get("code") != 0:
            send_wechat("GLADOS签到异常",
                        f"登录校验失败，接口返回：{status_json}")
            sys.exit(1)

        data = status_json["data"]
        email = data["email"]
        left_days = float(data.get("leftDays", 0))

        # 3. 解析签到结果
        check_msg = checkin_json.get("message", "")
        check_code = checkin_json.get("code", -1)
        today_point = float(checkin_json.get("data", {}).get("point", 0))
        check_result = "Checkin OK" if check_code == 0 else "Checkin FAIL"

        now_utc = datetime.utcnow().isoformat()[:23] + "Z"
        exchange_msg = "暂不支持自动兑换（接口无总积分字段）"

        # 4. 组装消息并推送
        content = (
            f"账号: {email}\n"
            f"日期: {now_utc}\n"
            f"签到结果: {check_result}\n"
            f"签到消息: {check_msg}\n"
            f"本次获得积分: {int(today_point)}\n"
            f"剩余会员天数: {int(left_days)}\n"
            f"兑换状态: {exchange_msg}"
        )
        send_wechat("GLADOS签到通知", content)

    except Exception as err:
        send_wechat("GLADOS签到异常", f"脚本运行捕获异常：{str(err)}")
        sys.exit(1)

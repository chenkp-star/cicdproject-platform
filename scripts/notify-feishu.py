"""Send deployment notifications; credentials are read only from the environment."""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from urllib.request import Request, urlopen


def signature(timestamp, secret):
    key = f"{timestamp}\n{secret}".encode()
    return base64.b64encode(hmac.new(key, b"", hashlib.sha256).digest()).decode()


def payload(environment):
    text = (
        f"前端部署成功 | {environment.get('JOB_NAME', 'demo')} "
        f"#{environment.get('BUILD_NUMBER', '0')}\n"
        f"分支：{environment.get('FRONTEND_BRANCH', 'main')}\n"
        f"镜像：{environment.get('IMAGE', 'cicd-vite-demo:demo')}\n"
        "访问：http://localhost:8080（部署机器本地地址）\n"
        f"构建日志：{environment.get('BUILD_URL', 'http://localhost:8081/')}"
    )
    return {"msg_type": "text", "content": {"text": text}}


def main():
    data = payload(os.environ)
    if '--mock' in sys.argv:
        print('MOCK：仅输出通知正文，不读取密钥，不发送网络请求。')
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    webhook = os.environ.get('FEISHU_WEBHOOK', '')
    secret = os.environ.get('FEISHU_SECRET', '')
    if not webhook.startswith('https://open.feishu.cn/open-apis/bot/v2/hook/') or not secret:
        raise ValueError('Missing or invalid Feishu credentials')
    timestamp = str(int(time.time()))
    data.update(timestamp=timestamp, sign=signature(timestamp, secret))
    request = Request(webhook, data=json.dumps(data).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(request, timeout=15) as response:
        result = json.load(response)
    # 飞书业务错误也可能返回 HTTP 200，必须检查响应码。
    code = result.get('code', result.get('StatusCode'))
    if code != 0:
        raise ValueError('Feishu returned a nonzero or missing response code')
    print('飞书通知发送成功。')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # 不打印 URL、密钥或签名，避免异常信息暴露凭据。
        print(f'飞书通知失败：{type(error).__name__}。请检查凭据、网络和机器人安全设置。', file=sys.stderr)
        sys.exit(1)

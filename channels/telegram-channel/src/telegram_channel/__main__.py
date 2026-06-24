import json
import logging
import os
import threading
import urllib.request
import urllib.error

from .bot import create_bot
from .k8s import K8sClient
from .state import ConversationState
from .web import start_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("telegram-channel")

SECRET_NAME = "telegram-bot-token"


def verify_telegram(token: str, base_url: str) -> tuple[dict | None, str | None]:
    url = f"{base_url}{token}/getMe"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["result"], None
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return None, "Invalid bot token. Check your token or create a new bot via @BotFather."
        return None, f"Telegram API returned HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, (
            f"Cannot reach Telegram API ({e.reason}). "
            "If you cannot access the Telegram APIs directly, set a Telegram API URL."
        )


def resolve_config(k8s: K8sClient) -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    base_url = os.environ.get("TELEGRAM_API_BASE", "").strip()

    if token:
        logger.info("Using token from environment")
        return token, base_url or "https://api.telegram.org/bot"

    try:
        secret = k8s.get_secret(SECRET_NAME)
        if secret and secret.get("token"):
            logger.info(f"Using token from Secret {k8s.namespace}/{SECRET_NAME}")
            return (
                secret["token"],
                secret.get("bridge-url", "") or "https://api.telegram.org/bot",
            )
    except Exception as e:
        logger.warning(f"Could not read secret: {e}")

    return "", "https://api.telegram.org/bot"


def main():
    namespace = os.environ.get("ARK_NAMESPACE", "default")
    health_port = int(os.environ.get("HEALTH_PORT", "8352"))

    logger.info("Starting Telegram Channel for Ark")
    logger.info(f"Namespace: {namespace}")

    k8s = K8sClient(namespace=namespace)
    state = ConversationState()
    configured = threading.Event()

    start_web_server(
        port=health_port,
        k8s=k8s,
        state=state,
        secret_name=SECRET_NAME,
        configured=configured,
    )

    # Wait for credentials — either already in the secret or set via the web UI
    while True:
        token, base_url = resolve_config(k8s)
        if not token:
            logger.info(f"No credentials found — open http://localhost:{health_port} to configure")
            configured.wait()
            configured.clear()
            continue

        bot_info, error = verify_telegram(token, base_url)
        if bot_info:
            break

        logger.warning(f"Telegram connection failed: {error}")
        from .web import _ctx
        _ctx["error"] = error
        configured.wait()
        configured.clear()

    if "api.telegram.org" not in base_url:
        logger.info(f"Telegram API URL: {base_url}")

    from .web import _ctx
    _ctx["bot_info"] = bot_info
    _ctx["error"] = None
    logger.info(f"Connected to Telegram as @{bot_info.get('username')}")

    app = create_bot(token, namespace, base_url, k8s=k8s, state=state)
    logger.info("Polling for updates...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

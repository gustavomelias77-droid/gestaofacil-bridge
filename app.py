import os, logging, sys
import requests
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

COOKIE_JAR = None
AUTHENTICATED = False
BASE_URL = "https://logus.gfsis.com.br"
USERNAME = os.environ.get("USERNAME", "teste2")
SENHA = os.environ.get("SENHA", "654321")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

def realizar_login_playwright():
    global AUTHENTICATED
    try:
        logger.info("Iniciando Playwright para login...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            page.goto(f"{BASE_URL}/gestaofacil/login/Index", timeout=30000)
            page.fill("input[name='username']", USERNAME, timeout=30000)
            page.fill("input[name='password']", SENHA, timeout=30000)
            page.click("input#btn-login", timeout=30000)

            # Aguarda redirecionamento (saiu da pagina de login)
            page.wait_for_url(lambda url: "/login/Index" not in url, timeout=30000)
            logger.info(f"URL pos-login: {page.url}")

            cookies = context.cookies()
            browser.close()

            for c in cookies:
                if c['name'] == 'JSESSIONID':
                    logger.info(f"JSESSIONID obtido: {c['value'][:20]}...")
                    AUTHENTICATED = True
                    return c['value']

            logger.error("JSESSIONID nao encontrado")
            AUTHENTICATED = False
            return None

    except Exception as e:
        logger.error(f"Erro Playwright: {e}")
        AUTHENTICATED = False
        return None

def atualizar_sessao():
    global COOKIE_JAR
    valor = realizar_login_playwright()
    if valor:
        COOKIE_JAR = requests.cookies.create_cookie(
            domain="logus.gfsis.com.br", name="JSESSIONID",
            value=valor, path="/"
        )
        return True
    COOKIE_JAR = None
    return False

@app.route('/health')
def health():
    return jsonify({"status": "ok", "autenticado": AUTHENTICATED})

@app.route('/refresh-login', methods=['POST'])
def refresh_login():
    if atualizar_sessao():
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Falha no login"}), 500

@app.route('/fetch', methods=['POST'])
def fetch():
    dados = request.get_json()
    if not dados or 'url' not in dados:
        return jsonify({"error": "url obrigatoria"}), 400

    s = requests.Session()
    if COOKIE_JAR:
        s.cookies.set_cookie(COOKIE_JAR)

    try:
        r = s.get(BASE_URL + dados['url'], timeout=30)
        return jsonify({"status": r.status_code, "body": r.text, "url": r.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Iniciando...")
    if not atualizar_sessao():
        logger.warning("Login inicial falhou. Use /refresh-login depois.")
    app.run(host="0.0.0.0", port=PORT)

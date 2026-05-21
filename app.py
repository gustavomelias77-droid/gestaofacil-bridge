import os
import logging
import sys

import requests
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

# Configuração de logging em português brasileiro
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Variáveis globais
COOKIE_JAR = None  # Armazenará o dicionário de cookies do requests
AUTHENTICATED = False
BASE_URL = "https://logus.gfsis.com.br"
USERNAME = os.environ.get("USERNAME", "teste2")
SENHA = os.environ.get("SENHA", "654321")

app = Flask(__name__)

def realizar_login_playwright():
    """
    Executa o login utilizando Playwright e retorna o cookie JSESSIONID.
    Retorna None em caso de falha.
    """
    global AUTHENTICATED
    cookie_jsessionid = None
    try:
        logger.info("Iniciando automação Playwright para login...")
        with sync_playwright() as p:
            logger.info("Lançando navegador Chromium headless...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = context.new_page()
            
            logger.info("Navegando para a página de login...")
            page.goto(f"{BASE_URL}/gestaofacil/login/Index", timeout=30000)
            
            logger.info("Preenchendo campo de usuário...")
            page.fill("input#login-username, input[name='username']", USERNAME, timeout=30000)
            
            logger.info("Preenchendo campo de senha...")
            page.fill("input#login-password, input[name='password']", SENHA, timeout=30000)
            
            logger.info("Clicando no botão de login...")
            page.click("input#btn-login, input[type='submit'][value='ENTRAR']", timeout=30000)
            
            logger.info("Aguardando redirecionamento pós-login...")
            page.wait_for_url(lambda url: "/login/Index" not in url, timeout=30000)
            
            logger.info("Login aparentemente bem-sucedido, extraindo cookies...")
            cookies = context.cookies()
            for cookie in cookies:
                if cookie['name'] == 'JSESSIONID':
                    cookie_jsessionid = cookie['value']
                    logger.info(f"JSESSIONID encontrado: {cookie_jsessionid}")
                    break
            
            browser.close()
            
        if cookie_jsessionid:
            logger.info("Login realizado com sucesso!")
            AUTHENTICATED = True
            return cookie_jsessionid
        else:
            logger.error("JSESSIONID não encontrado nos cookies após login.")
            AUTHENTICATED = False
            return None
    except Exception as e:
        logger.error(f"Erro durante automação Playwright: {str(e)}")
        AUTHENTICATED = False
        return None

def atualizar_sessao():
    """
    Atualiza a sessão requests com o cookie JSESSIONID obtido via Playwright.
    Retorna True se sucesso, False caso contrário.
    """
    global COOKIE_JAR
    cookie_valor = realizar_login_playwright()
    if cookie_valor:
        COOKIE_JAR = requests.cookies.create_cookie(
            domain="logus.gfsis.com.br",
            name="JSESSIONID",
            value=cookie_valor,
            path="/"
        )
        logger.info("Sessão atualizada com sucesso.")
        return True
    else:
        logger.error("Falha ao atualizar sessão.")
        COOKIE_JAR = None
        return False

@app.route('/health', methods=['GET'])
def health():
    logger.info("Endpoint /health acessado.")
    return jsonify({
        "status": "ok",
        "autenticado": AUTHENTICATED
    })

@app.route('/refresh-login', methods=['POST'])
def refresh_login():
    logger.info("Endpoint /refresh-login acessado. Executando novo login...")
    sucesso = atualizar_sessao()
    if sucesso:
        return jsonify({"success": True, "message": "Login renovado com sucesso."})
    else:
        return jsonify({"success": False, "message": "Falha ao renovar login."}), 500

@app.route('/fetch', methods=['POST'])
def fetch():
    logger.info("Endpoint /fetch acessado.")
    dados = request.get_json()
    if not dados or 'url' not in dados:
        return jsonify({"error": "Campo 'url' é obrigatório."}), 400
    
    url_relativa = dados['url']
    if not url_relativa.startswith('/'):
        url_relativa = '/' + url_relativa
    url_completa = f"{BASE_URL}{url_relativa}"
    
    logger.info(f"Fazendo requisição para: {url_completa}")
    
    try:
        session = requests.Session()
        if COOKIE_JAR:
            session.cookies.set_cookie(COOKIE_JAR)
        response = session.get(url_completa, timeout=30)
        response.raise_for_status()
        logger.info(f"Resposta recebida: status {response.status_code}")
        return jsonify({
            "success": True,
            "content": response.text,
            "status_code": response.status_code
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição: {str(e)}")
        return jsonify({"error": f"Erro ao acessar URL: {str(e)}"}), 500

if __name__ == "__main__":
    # Comentário para deploy no Render:
    # Comando de build: pip install -r requirements.txt && playwright install chromium
    # A imagem deve incluir as dependências do sistema para rodar Chromium headless.
    
    logger.info("Iniciando aplicação Flask...")
    if not atualizar_sessao():
        logger.warning("Falha no login inicial. O serviço será iniciado, mas o endpoint /fetch pode falhar até que /refresh-login seja chamado com sucesso.")
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=porta, debug=False)

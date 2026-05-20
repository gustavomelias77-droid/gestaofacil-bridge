import os, logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))
USERNAME = os.environ.get('USERNAME', 'teste2')
SENHA = os.environ.get('SENHA', '654321')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STORAGE_FILE = 'state.json'

# NÃO inicializa Playwright na partida

@app.route('/health')
def health():
    auth = os.path.exists(STORAGE_FILE)
    return jsonify({'status': 'ok', 'authenticated': auth})

@app.route('/login', methods=['POST'])
def login():
    """Inicializa o navegador sob demanda e faz login."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context()
            page = context.new_page()
            page.goto('https://logus.gfsis.com.br/gestaofacil/login/Index', wait_until='networkidle')
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', SENHA)
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=15000)
            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login bem-sucedido')
                return jsonify({'success': True})
            browser.close()
            return jsonify({'error': 'Login falhou - URL ainda contém "login"'}), 502
    except Exception as e:
        logger.error(f'Erro no login: {e}')
        return jsonify({'error': str(e)}), 502

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatória'}), 400
    if not os.path.exists(STORAGE_FILE):
        return jsonify({'error': 'Não autenticado. Execute /login primeiro.'}), 401
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(storage_state=STORAGE_FILE)
            page = context.new_page()
            resp = page.goto(data['url'], wait_until='networkidle')
            result = {
                'status': resp.status if resp else 200,
                'body': page.content(),
                'url': page.url
            }
            browser.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f'Erro no fetch: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

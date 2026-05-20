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
BASE = 'https://logus.gfsis.com.br'

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'authenticated': os.path.exists(STORAGE_FILE)})

@app.route('/login', methods=['POST'])
def login():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            page.goto(f'{BASE}/gestaofacil/login/Index', wait_until='networkidle', timeout=30000)
            logger.info(f'URL: {page.url}')

            page.evaluate('''(user) => {
                const el = document.querySelector('input[name="username"]');
                if (el) el.value = user;
            }''', USERNAME)

            page.evaluate('''(pass) => {
                const el = document.querySelector('input[name="password"]');
                if (el) el.value = pass;
            }''', SENHA)

            page.evaluate('() => { document.querySelector("form").submit(); }')

            try:
                page.wait_for_load_state('networkidle', timeout=20000)
            except:
                pass

            logger.info(f'URL pós-login: {page.url}')

            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                return jsonify({'success': True})

            browser.close()
            return jsonify({'error': 'Login falhou', 'url_final': page.url}), 502

    except Exception as e:
        logger.error(f'Erro: {e}')
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
            context = browser.new_context(storage_state=STORAGE_FILE, ignore_https_errors=True)
            page = context.new_page()
            resp = page.goto(data['url'], wait_until='networkidle', timeout=30000)
            result = {
                'status': resp.status if resp else 200,
                'body': page.content(),
                'url': page.url
            }
            browser.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f'Erro fetch: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

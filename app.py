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

@app.route('/health')
def health():
    auth = os.path.exists(STORAGE_FILE)
    return jsonify({'status': 'ok', 'authenticated': auth})

@app.route('/login', methods=['POST'])
def login():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context()
            page = context.new_page()
            
            # Passo 1: acessa página de login
            page.goto('https://logus.gfsis.com.br/gestaofacil/login/Index', wait_until='networkidle')
            
            # Passo 2: preenche campos (tenta múltiplos nomes possíveis)
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', SENHA)
            
            # Passo 3: tenta múltiplos seletores de submit
            try:
                page.click('input[type="submit"]', timeout=5000)
            except:
                try:
                    page.click('button[type="submit"]', timeout=5000)
                except:
                    page.click('button:has-text("Entrar"), input[value="Entrar"], button:has-text("OK")', timeout=5000)
            
            page.wait_for_load_state('networkidle', timeout=15000)
            
            # Passo 4: verifica se saiu da página de login
            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login OK')
                return jsonify({'success': True})
            
            # Fallback: tenta POST direto via JavaScript
            logger.info('Tentando fallback via POST direto')
            result = page.evaluate('''
                async () => {
                    const resp = await fetch("/gestaofacil/login/neo_security_manager", {
                        method: "POST",
                        headers: {"Content-Type": "application/x-www-form-urlencoded"},
                        body: new URLSearchParams({
                            username: arguments[0],
                            password: arguments[1]
                        })
                    });
                    return resp.url;
                }
            ''', USERNAME, SENHA)
            
            page.goto('https://logus.gfsis.com.br/gestaofacil/', wait_until='networkidle')
            
            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login OK via fallback')
                return jsonify({'success': True})
            
            browser.close()
            return jsonify({'error': 'Login falhou em todas as tentativas'}), 502
            
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
        logger.error(f'Erro fetch: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

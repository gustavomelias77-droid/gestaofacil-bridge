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
BASE_URL = 'https://logus.gfsis.com.br'

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'authenticated': os.path.exists(STORAGE_FILE)})

@app.route('/login', methods=['POST'])
def login():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])
            context = browser.new_context()
            page = context.new_page()

            # Passo 1: acessar página de login (captura JSESSIONID automaticamente)
            resp = page.goto(f'{BASE_URL}/gestaofacil/login/Index', wait_until='networkidle')
            logger.info(f'URL inicial: {page.url}')
            logger.info(f'Status: {resp.status if resp else "N/A"}')

            # Passo 2: preencher formulário via JavaScript para garantir que funciona
            page.evaluate('''({ user, pass }) => {
                const form = document.querySelector('form');
                if (!form) return 'form nao encontrado';
                const u = form.querySelector('input[name="username"]');
                const p = form.querySelector('input[name="password"]');
                if (!u || !p) return 'campos nao encontrados';
                u.value = user;
                p.value = pass;
                return 'preenchido';
            }''', {'user': USERNAME, 'pass': SENHA})

            logger.info('Campos preenchidos via JS')

            # Passo 3: submit do form via JavaScript
            resultado = page.evaluate('''() => {
                const form = document.querySelector('form');
                if (!form) return 'form ausente';
                // Tenta o botão submit primeiro
                const btn = form.querySelector('input[type="submit"], button[type="submit"]');
                if (btn) {
                    btn.click();
                    return 'click submit';
                }
                // Fallback: submit direto
                form.submit();
                return 'form submit';
            }''')
            logger.info(f'Submit: {resultado}')

            # Passo 4: aguardar navegação
            page.wait_for_load_state('networkidle', timeout=20000)
            logger.info(f'URL pós-login: {page.url}')

            # Passo 5: verificar se logou
            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login OK')
                return jsonify({'success': True, 'url': page.url})

            # Se ainda está no login, tenta POST direto
            logger.info('Tentando POST direto para neo_security_manager')
            
            # Captura cookies atuais
            cookies = context.cookies()
            logger.info(f'Cookies: {len(cookies)}')
            
            # Navega direto via POST
            resp2 = page.goto(f'{BASE_URL}/gestaofacil/login/neo_security_manager', wait_until='networkidle')
            logger.info(f'URL após POST direto: {page.url}')
            
            # Tenta fazer o POST com form data
            resposta = page.evaluate('''async ({ user, pass }) => {
                const resp = await fetch('/gestaofacil/login/neo_security_manager', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': 'https://logus.gfsis.com.br',
                        'Referer': 'https://logus.gfsis.com.br/gestaofacil/login/Index'
                    },
                    body: new URLSearchParams({ username: user, password: pass })
                });
                return { status: resp.status, url: resp.url };
            }''', {'user': USERNAME, 'pass': SENHA})
            
            logger.info(f'Resposta POST direto: {resposta}')
            
            # Vai pra home
            page.goto(f'{BASE_URL}/gestaofacil/', wait_until='networkidle')
            logger.info(f'URL final: {page.url}')

            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login OK via POST direto')
                return jsonify({'success': True, 'url': page.url, 'metodo': 'post_direto'})

            browser.close()
            return jsonify({
                'error': 'Login falhou em todas tentativas',
                'url_final': page.url
            }), 502

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

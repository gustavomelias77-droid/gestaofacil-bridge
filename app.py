import os, logging, base64
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

            page.goto('https://logus.gfsis.com.br/gestaofacil/login/Index', wait_until='networkidle')
            logger.info(f'URL: {page.url}')
            logger.info(f'Título: {page.title()}')

            # Captura o HTML para debug
            html = page.content()

            # Tenta descobrir os names dos campos olhando o HTML
            input_names = page.evaluate('''() => {
                const inputs = document.querySelectorAll('input[type="text"], input[type="password"], input:not([type="hidden"])');
                return Array.from(inputs).map(i => ({name: i.name, id: i.id, type: i.type, placeholder: i.placeholder}));
            }''')
            logger.info(f'Inputs encontrados: {input_names}')

            # Tenta preencher por vários nomes possíveis
            tentativas_user = ['username', 'login', 'usuario', 'user', 'email', 'cpf']
            tentativas_senha = ['password', 'senha', 'pass', 'pwd']

            campo_user = None
            campo_senha = None

            for nome in tentativas_user:
                try:
                    page.fill(f'input[name="{nome}"]', USERNAME, timeout=2000)
                    campo_user = nome
                    logger.info(f'Campo user encontrado: {nome}')
                    break
                except:
                    continue

            if not campo_user:
                # Tenta por placeholder
                for nome in tentativas_user:
                    try:
                        page.fill(f'input[placeholder*="{nome}" i]', USERNAME, timeout=2000)
                        campo_user = nome
                        logger.info(f'Campo user por placeholder: {nome}')
                        break
                    except:
                        continue

            for nome in tentativas_senha:
                try:
                    page.fill(f'input[name="{nome}"]', SENHA, timeout=2000)
                    campo_senha = nome
                    logger.info(f'Campo senha encontrado: {nome}')
                    break
                except:
                    continue

            if not campo_user or not campo_senha:
                browser.close()
                return jsonify({
                    'error': 'Não encontrou campos de login',
                    'inputs_encontrados': input_names,
                    'html_preview': html[:2000]
                }), 502

            # Tenta submit por vários métodos
            submit_feito = False
            for seletor in ['input[type="submit"]', 'button[type="submit"]', 'button:has-text("Entrar")', 'button:has-text("OK")', 'input[value="Entrar"]', 'input[value="OK"]', 'form']:
                try:
                    if seletor == 'form':
                        page.evaluate('document.querySelector("form").submit()')
                    else:
                        page.click(seletor, timeout=3000)
                    submit_feito = True
                    logger.info(f'Submit com seletor: {seletor}')
                    break
                except:
                    continue

            if not submit_feito:
                browser.close()
                return jsonify({'error': 'Não encontrou botão de submit', 'inputs': input_names}), 502

            page.wait_for_load_state('networkidle', timeout=15000)
            logger.info(f'URL pós-login: {page.url}')

            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login OK')
                return jsonify({'success': True})

            browser.close()
            return jsonify({
                'error': 'Login falhou',
                'url_final': page.url,
                'inputs_encontrados': input_names
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

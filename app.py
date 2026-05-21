import os, logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SESSION_TOKEN = os.environ.get('SESSION_TOKEN')
if not SESSION_TOKEN:
    logger.error('SESSION_TOKEN não definida')
    raise SystemExit(1)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9',
})
session.cookies.set('JSESSIONID', SESSION_TOKEN, domain='logus.gfsis.com.br', path='/gestaofacil')

BASE = 'https://logus.gfsis.com.br'

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatória'}), 400
    try:
        r = session.get(BASE + data['url'], timeout=30)
        return jsonify({'status': r.status_code, 'body': r.text, 'url': r.url})
    except Exception as e:
        logger.error(f'Erro: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

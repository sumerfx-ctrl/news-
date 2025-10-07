from flask import Flask, request, jsonify, Response
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
import requests
import hashlib
import os
import re
import time

app = Flask(__name__)
DATA_DIR = './data'
os.makedirs(DATA_DIR, exist_ok=True)

# قاعدة بيانات مؤقتة (يمكن استبدال SQLite لاحقًا)
FEEDS_DB = {}

def slugify(s): 
    return re.sub(r'[^a-z0-9]+','-', s.lower()).strip('-')

@app.route('/api/feeds', methods=['POST'])
def create_feed():
    payload = request.get_json()
    src = payload['source']
    owner = payload.get('owner')
    feed_id = str(int(time.time()*1000))
    slug = slugify(src.split('/')[-1] + '-' + feed_id[-4:])
    FEEDS_DB[feed_id] = {
        'id': feed_id,
        'slug': slug,
        'source': src,
        'owner': owner,
        'interval': 300,
        'last_polled': 0,
        'output_mode': 'title_details',
        'header': '',
        'footer': '',
        'replacements': [],  # [{'pattern':'Bitcoin','replacement':'BTC'}]
        'blacklist': []      # ['spam','forbidden']
    }
    return jsonify({'id': feed_id, 'slug': slug}), 201

@app.route('/api/feeds', methods=['GET'])
def list_feeds():
    owner = request.args.get('owner')
    feeds = [f for f in FEEDS_DB.values() if str(f['owner']) == str(owner)]
    return jsonify(feeds)

def fetch_tme_html(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text

def parse_channel_messages(html):
    soup = BeautifulSoup(html, 'html.parser')
    msgs=[]
    for m in soup.select('.tgme_widget_message'):
        text_el = m.select_one('.tgme_widget_message_text')
        txt = text_el.get_text(separator='\n').strip() if text_el else ''
        # الصور
        imgs=[]
        for a in m.select('a.tgme_widget_message_photo_wrap'):
            st = a.get('style','')
            if 'url(' in st:
                u = st[st.find('url(')+4:st.find(')')].strip('"\' ')
                imgs.append(u)
        msgs.append({'text': txt, 'images': imgs})
    return msgs

def build_rss_for_feed(feed):
    html = fetch_tme_html(feed['source'])
    msgs = parse_channel_messages(html)
    fg = FeedGenerator()
    fg.title(feed['source'])
    fg.link(href=feed['source'], rel='alternate')
    fg.description(f'RSS for {feed["source"]}')
    for i, m in enumerate(msgs[:30]):
        # blacklist
        drop=False
        for p in feed['blacklist']:
            if re.search(p, m['text'], re.I):
                drop=True
                break
        if drop: continue
        content = m['text']
        # replacements
        for rule in feed['replacements']:
            content = re.sub(rule['pattern'], rule['replacement'], content)
        # header/footer
        content = (feed.get('header','') or '') + content + (feed.get('footer','') or '')
        # images
        if m['images']:
            content += '<br>' + '<br>'.join([f'<img src="{img}"/>' for img in m['images']])
        fe = fg.add_entry()
        fe.id(hashlib.sha1((feed['id']+str(i)).encode()).hexdigest())
        title_text = content[:50] or f'post {i}'
        fe.title(title_text)
        fe.content(content, type='html')
    return fg.rss_str(pretty=True)

@app.route('/rss/<slug>.xml')
def serve_rss(slug):
    feed = next((f for f in FEEDS_DB.values() if f['slug']==slug), None)
    if not feed: return "Not found", 404
    rss = build_rss_for_feed(feed)
    return Response(rss, mimetype='application/rss+xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))

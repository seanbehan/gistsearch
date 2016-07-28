from flask import Flask, render_template as render, request, redirect, jsonify, session
from os import environ as env, path
from requests import post
from urllib import urlencode, unquote, quote
from urlparse import parse_qs
from lib import db, gists, save_gists
from rq import Queue
from worker import conn

q = Queue(connection=conn)
app = Flask(__name__)
app.secret_key = '\x9aT\xa5rm\xeah\xe6\xf3\xdb\x11\x00\x8f\x16\x084\xc1\x0e\x13\x0bYM\x11R'

@app.before_request
def before_request():
    if request.path in ('/login', '/authorize', '/callback'):
        return None
    if not session.get('access_token'):
        return redirect('/login')

@app.route("/login")
def login():
    return render('login.html')

@app.route("/logout", methods=["POST"])
def logout():
    session.pop('access_token')
    return redirect('/login')

@app.route("/")
def home():
    files = [f for f in db.query('select distinct language from files') if f['language']]
    return render('home.html', files=files)

@app.route("/search")
def search():
    q = request.args.get('desc')
    gists = [gist for gist in db.query('select * from gists where description ~* :q', q=q)]
    return render('search.html', gists=gists)

@app.route("/language/<language>")
def language(language):
    q = str(language).lower()
    gists = [gist for gist in db.query('select distinct (f.gist_id, f.filename), g.*,f.* from gists g join files f on g.gist_id = f.gist_id where f.language = :q order by f.gist_id,f.filename', q=q)]

    return render('search.html', gists=gists)

@app.route("/file_contents")
def file_contents():
    q = unquote(request.args.get('txt'))
    gists = [gist for gist in db.query('select distinct (g.gist_id), * from gists g, files f where g.gist_id = f.gist_id and f.content ilike :q', q="%"+q+"%")]
    return render('search.html', gists=gists)

@app.route("/authorize")
def authorize():
    url = "https://github.com/login/oauth/authorize?%s&scope=gist" % urlencode({'client_id':env.get('CLIENT_ID', ''), 'redirect_uri': env.get('REDIRECT_URI', '')})
    return redirect(url)

@app.route("/callback")
def callback():
    query_string = urlencode({'client_id':env.get('CLIENT_ID', ''), 'client_secret': env.get('CLIENT_SECRET'), 'redirect_uri': env.get('REDIRECT_URI', ''), 'code': request.args.get('code')})
    resp = post("https://github.com/login/oauth/access_token?%s" % query_string).content

    access_token = parse_qs(resp)['access_token'][0]
    db['users'].upsert(dict(access_token=access_token), ['access_token'])

    result = q.enqueue(save_gists, access_token)
    session['access_token'] = access_token

    return redirect('/')

if __name__=='__main__':
    app.run(debug=True)

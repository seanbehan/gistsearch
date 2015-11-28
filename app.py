from flask import Flask, render_template as render, request, redirect, jsonify
from os import environ as env, path
from requests import post
from urllib import urlencode, unquote
from urlparse import parse_qs
from lib import db, gists, save_gists
from rq import Queue
from worker import conn

q = Queue(connection=conn)
app = Flask(__name__)

@app.route("/")
def home():
    return render('home.html')

@app.route("/gists.json")
def gists():
    return jsonify(
        gists=[g for g in db['gists'].all()]
    )

@app.route("/authorize")
def authorize():
    url = "https://github.com/login/oauth/authorize?%s&scope=gist" % urlencode({'client_id':env.get('CLIENT_ID', ''), 'redirect_uri': env.get('REDIRECT_URI', '')})
    return redirect(url)

@app.route("/callback")
def callback():
    query_string = urlencode({'client_id':env.get('CLIENT_ID', ''), 'client_secret': env.get('CLIENT_SECRET'), 'redirect_uri': env.get('REDIRECT_URI', ''), 'code': request.args.get('code')})
    resp = post("https://github.com/login/oauth/access_token?%s" % query_string).content

    access_token = parse_qs(resp)['access_token'][0]
    db['users'].upsert(dict(id=1, access_token=access_token), ['id'])

    result = q.enqueue(save_gists, access_token)

    return redirect('/')

if __name__=='__main__':
    app.run(debug=True)

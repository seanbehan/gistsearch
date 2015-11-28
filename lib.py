from requests import get
from dataset import connect
from os import environ as env, path
from urllib import urlencode, unquote
from rq import Queue
from worker import conn

if path.exists("./ENV"):
    for line in open("./ENV").read().split("\n"):
        if not line: continue
        data = line.split("=")
        env[data[0]]=unquote(data[1])


q = Queue(connection=conn)
db = connect(env.get('DATABASE_URL'))

def gists(access_token=None):
    i = 0
    gists = []
    while True:
        data = get('https://api.github.com/gists?access_token=%s&page=%s' % (access_token, i)).json()
        if len(data):
            gists.append(data)
            i+=1
        else:
            break
    return reduce(lambda a,b: a+b, gists)

def save_gists(access_token=None):
    if not access_token: return None

    for gist in gists(access_token):
        gist['user_id'] = gist['owner']['id']
        gist['gist_id'] = gist.pop('id')

        db['gists'].upsert(gist, ['gist_id'])
        files = gist['files'].values()

        for f in files:
            f['gist_id'] = gist['gist_id']
            q.enqueue(save_file, {'file':f, 'access_token':access_token})

def save_file(data):
    f = data['file']
    access_token = data['access_token']
    f['content'] = get(f['raw_url'], headers = {'Authorization': 'token %s'%access_token}).content
    db['files'].upsert(f, ['gist_id', 'filename'])


def save_gist(url):
    gist_id = '1d04edad3409812dcb35'
    access_token = '396b224e167926e5c8bb62a95158bc514b519365'
    data = get('https://api.github.com/gists/%s?access_token=%s' % (gist_id, access_token)).json()
    pass

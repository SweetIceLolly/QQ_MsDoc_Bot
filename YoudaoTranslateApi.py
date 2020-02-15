import sys
import uuid
import requests
import hashlib
import time
import json


YOUDAO_URL = 'https://openapi.youdao.com/api'
APP_KEY = 'YOUR_APP_KEY'
APP_SECRET = 'YOUR_SECRET'


def encrypt(signStr):
    hash_algorithm = hashlib.sha256()
    hash_algorithm.update(signStr.encode('utf-8'))
    return hash_algorithm.hexdigest()


def truncate(q):
    if q is None:
        return None
    size = len(q)
    return q if size <= 20 else q[0:10] + str(size) + q[size - 10:size]


def do_request(data):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    return requests.post(YOUDAO_URL, data=data, headers=headers)


def youdao_translate(original_text, from_chinese = True):
    print('Translating: ' + original_text)
    q = original_text

    data = {}
    if from_chinese:
        data['from'] = 'zh-CHS'
        data['to'] = 'en'
    else:
        data['from'] = 'en'
        data['to'] = 'zh-CHS'
    data['signType'] = 'v3'
    curtime = str(int(time.time()))
    data['curtime'] = curtime
    salt = str(uuid.uuid1())
    signStr = APP_KEY + truncate(q) + salt + curtime + APP_SECRET
    sign = encrypt(signStr)
    data['appKey'] = APP_KEY
    data['q'] = q
    data['salt'] = salt
    data['sign'] = sign

    response = do_request(data)
    contentType = response.headers['Content-Type']
    rtn = json.loads(response.content)['translation'][0]
    print('Translated to: ' + rtn)
    return rtn

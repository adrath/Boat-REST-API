from flask import Flask, Blueprint, request, make_response
from google.cloud import datastore
from requests_oauthlib import OAuth2Session
import json
import datetime
import calendar
import constants
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

client = datastore.Client()

client_id = r'401505031584-fgga6trmo2rvb5ke81ge51u5hnn5a72b.apps.googleusercontent.com'
PREFIX = 'Bearer '



#How to compare the time was figured out by using these sources:
# https://github.com/googleapis/google-auth-library-python/blob/master/google/auth/jwt.py
# https://github.com/googleapis/google-auth-library-python/blob/master/google/auth/_helpers.py
# https://docs.python.org/2/library/datetime.html
def compareTime():
    dateTimeNow = datetime.datetime.utcnow()
    now = calendar.timegm(dateTimeNow.utctimetuple())
    return now


def verify():
    if 'Authorization' in request.headers and request.headers['Authorization'] is not None:
        headAuth = request.headers['Authorization']
        req = requests.Request()
        if(headAuth):
            if not headAuth.startswith(PREFIX):
                return -1
            else:
                now = compareTime()
                token = headAuth[len(PREFIX):]
                id_info = ""
                try:
                    id_info = id_token.verify_oauth2_token(token, req, client_id)
                except ValueError:
                    return -1
                if now < (id_info['iat']):
                    return -1
                if id_info['exp'] < now:
                    return -1
                if id_info["sub"] is None:
                    return -1
                else:
                    return id_info["sub"]
        else:
            return -1
    else:
        return -1

def get_boats_schema():
    schema = {
        'name': {
            'type': 'string',
            'minlength': 3,
            'maxlength': 25,
            'regex': '^(?!.*__)(?!.*_$)[A-Za-z]\w*$'},
        'type': {
            'type': 'string',
            'minlength': 3,
            'maxlength': 25,
            'regex': '^(?!.*__)(?!.*_$)[A-Za-z]\w*$'},
        'length': {
            'type': 'integer',
            'min': 5,
            'max': 1000000,
            'regex': '^[0-9]+$'}
        }
    return schema

# Regex resources: https://gist.github.com/diyan/5dddc7dbd45e4ce3450a
def get_loads_schema():
    schema = {
        'weight': {
            'type': 'integer',
            'min': 3,
            'max': 1000000,
            'regex': '^[0-9]+$'},
        'contents': {
            'type': 'string',
            'minlength': 3,
            'maxlength': 25,
            'regex': '^(?!.*__)(?!.*_$)[A-Za-z]\w*$'},
        'delivery_date': {
            'type': 'string',
            'regex': '^\d{4}-\d{2}-\d{2}$'}
        }
    return schema

'''
mt = mimetype
sc = status code
cl = Content-Location
l = Location
'''
def response_status_json(output, mt, sc, cl, l):
    response = make_response(json.dumps(output))
    response.mimetype = mt
    response.status_code = sc
    if(cl != None):
        response.headers.set('Content-Location', cl)
    if(l != None):
        response.headers.set('Location', l)
    return response


def add_user(input):
    if check_for_user(input):
        return
    else:
        new_user = datastore.entity.Entity(key=client.key(constants.users))
        new_user.update({"user": input})
        client.put(new_user)
        return

def check_for_user(input):
    query = client.query(kind=constants.users)
    query.add_filter('user', '=', input)
    results = list(query.fetch())
    if results != []:
        return 1
    else:
        return 0
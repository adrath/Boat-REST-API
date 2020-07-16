from google.cloud import datastore
from flask import Flask, Blueprint, request
from requests_oauthlib import OAuth2Session
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests
import json
import constants
from helper import verify, check_for_user, response_status_json

client = datastore.Client()

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/<user_id>/boats', methods=['GET'])
def users_boats_get(user_id):
    if request.method == 'GET':
        owner_results = verify()
        if owner_results and owner_results != -1:
            if not check_for_user(owner_results):
                errObj = {"Error": "Not a valid user, please register"}
                return (json.dumps(errObj), 401)
            elif int(user_id) != int(owner_results):
                errObj = {"Error": "This is not your user_id"}
                return (json.dumps(errObj), 401)
            else:
                query = client.query(kind=constants.boats)
                query.add_filter('owner', '=', user_id)
                results = list(query.fetch())
                for e in results:
                    e["id"] = e.key.id
                    e["self"] = str(request.base_url) + "/" + str(e.key.id)
                    for f in e["loads"]:
                        f["self"] = str(request.base_url) + "loads/" + str(f["id"])
                return response_status_json(results, 'application/json', 200, None, None)
        else:
            errObj = {"Error": "Missing or Invalid JWTs"}
            return (json.dumps(errObj), 401)
    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)

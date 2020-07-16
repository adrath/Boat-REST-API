from flask import Blueprint, request, make_response
from google.cloud import datastore
from cerberus import Validator
import json
import constants
from helper import get_boats_schema, response_status_json, verify, check_for_user

client = datastore.Client()

bp = Blueprint('boats', __name__, url_prefix='/boats')

@bp.route('', methods=['POST', 'PUT', 'PATCH', 'GET', 'DELETE'])
def boats_get_post():
    if request.method == 'POST':
        if request.mimetype == 'application/json':
            if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
               error_obj = {"Error": "Accept header must be application/json"}
               return (json.dumps(error_obj), 406)
                
            content = request.get_json()
            schema = get_boats_schema()
        
            v = Validator(schema)
            if v.validate(content, schema) is False:
                error_obj = {"Error": "The request object contains inappropriate attributes or attribute input"}
                return (json.dumps(error_obj), 400)
        
            error_obj = {"Error": "The request object is missing at least one of the required attributes"}
            if "name" not in content:
                return (json.dumps(error_obj), 400)
            elif "type" not in content:
                return (json.dumps(error_obj), 400)
            elif "length" not in content:
                return (json.dumps(error_obj), 400)
            else:
                owner_results = verify()
                if(owner_results and owner_results != -1):
                    if not check_for_user(owner_results):
                        errObj = {"Error": "Not a valid user, please register"}
                        return (json.dumps(errObj), 401)
                    owner = owner_results
                    boat_name = content["name"]
                    query = client.query(kind=constants.boats)
                    query.add_filter('name', '=', boat_name)
                    results = list(query.fetch())
                    if results != []:
                        err_obj = {"Error": "The requested boat name is already in use"}
                        return (json.dumps(err_obj), 403)
                    new_boat = datastore.entity.Entity(key=client.key(constants.boats))
                    new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "owner": owner, "loads": []})
                    client.put(new_boat)
                    new_boat["id"] = new_boat.key.id
                    self_url = str(request.base_url) + "/" + str(new_boat.key.id)
                    new_boat["self"] = self_url
                    return response_status_json(new_boat, 'application/json', 201, self_url, None)
                else:
                    errObj = {"Error": "Missing or Invalid JWTs"}
                    return (json.dumps(errObj), 401)
        else:
            error_obj = {"Error": "The request mimetype should be application/json"}
            return(json.dumps(error_obj), 400)
    
    elif request.method == 'GET':
        if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
            error_obj = {"Error": "Accept header must be application/json"}
            return (json.dumps(error_obj), 406)
        else:
            query = client.query(kind=constants.boats)
            q_limit = int(request.args.get('limit', '5'))
            q_offset = int(request.args.get('offset', '0'))
            l_iterator = query.fetch(limit=q_limit, offset=q_offset)
            pages = l_iterator.pages
            results = list(next(pages))
            if l_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            for e in results:
                e["id"] = e.key.id
                e["self"] = str(request.base_url) + "/" + str(e.key.id)
                for f in e["loads"]:
                    f["self"] = str(request.base_url) + "loads/" + str(f["id"])
            output = {"boats": results}
            if next_url:
                output["next"] = next_url
            return response_status_json(output, 'application/json', 200, None, None)
            
    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)


@bp.route('/<boat_id>', methods=['GET', 'PATCH' , 'PUT', 'DELETE'])
def boats_put_patch_delete(boat_id):
    if request.method == 'GET':
        if request.headers['Accept'] == '*/*' or 'application/json' in request.headers['Accept']:
            boat_key = client.key(constants.boats, int(boat_id))
            boat = client.get(boat_key)
            error_obj = {"Error": "No boat with this boat_id exists"}
            if boat is None:
                return (json.dumps(error_obj), 404)
            else:
                boat["id"] = boat.key.id
                boat["self"] = str(request.base_url)
                for e in boat["loads"]:
                    load_id = e["id"]
                    e["self"] = str(request.url_root) + "loads/" + str(load_id)
                return response_status_json(boat, 'application/json', 200, None, None)

        else:
            error_obj = {"Error": "Accept header must be application/json"}
            return(json.dumps(error_obj), 406)


    elif request.method == 'PATCH':
        if request.mimetype == 'application/json':
            if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
               error_obj = {"Error": "Accept header must be application/json"}
               return (json.dumps(error_obj), 406)
            
            owner_results = verify()
            if(owner_results and owner_results != -1):

                if not check_for_user(owner_results):
                    errObj = {"Error": "Not a valid user, please register"}
                    return (json.dumps(errObj), 401)

                content = request.get_json()
                schema = get_boats_schema()
            
                v = Validator(schema)
                if v.validate(content, schema) is False or not content:
                    error_obj = {"Error": "The request object contains inappropriate attributes or attribute input"}
                    return (json.dumps(error_obj), 400)
            
                error_obj = {"Error": "The request object is missing at least one of the required attributes"}
                if "name" not in content and "type" not in content and "length" not in content:
                    return (json.dumps(error_obj), 400)

                boat_key = client.key(constants.boats, int(boat_id))
                boat = client.get(key=boat_key)
                if boat is None:
                    error_obj = {"Error": "No boat with this boat_id exists"}
                    return (json.dumps(error_obj), 404)
                
                elif int(boat["owner"]) != int(owner_results):
                    errObj = {"Error": "You are not the owner of this boat"}
                    return (json.dumps(errObj), 403)
                
                else:
                    updated_name = ""
                    updated_type = ""
                    updated_length = -1
                    if "name" not in content:
                        updated_name = boat["name"]
                    else:
                        updated_name = content["name"]
                        boat_name = content["name"]
                        query = client.query(kind=constants.boats)
                        query.add_filter('name', '=', boat_name)
                        results = list(query.fetch())
                        if results != [] and results[0] != boat.key.id:
                            err_obj = {"Error": "The requested boat name is already in use"}
                            return (json.dumps(err_obj), 403)
                    
                    if "type" not in content:
                        updated_type = boat["type"]
                    else:
                        updated_type = content["type"]

                    if "length" not in content:
                        updated_length = boat["length"]
                    else:
                        updated_length = content["length"]
                    
                    boat.update({"name": updated_name, "type": updated_type, "length": updated_length})
                    client.put(boat)
                    boat["id"] = boat.key.id
                    self_url = str(request.base_url)
                    boat["self"] = self_url
                    for e in boat["loads"]:
                        e["id"] = e.key.id
                        e["self"] = str(request.url_root) + "/" + str(e.key.id)
                    return response_status_json(boat, 'application/json', 200, None, None)
            else:
                errObj = {"Error": "Missing or Invalid JWTs"}
                return (json.dumps(errObj), 401)
        else:
            error_obj = {"Error": "The request mimetype should be application/json"}
            return(json.dumps(error_obj), 400)


    elif request.method == 'PUT':
        if request.mimetype == 'application/json':
            if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
               error_obj = {"Error": "Accept header must be application/json"}
               return (json.dumps(error_obj), 406)

            owner_results = verify()
            if(owner_results and owner_results != -1):

                if not check_for_user(owner_results):
                    errObj = {"Error": "Not a valid user, please register"}
                    return (json.dumps(errObj), 401)

                content = request.get_json()
                schema = get_boats_schema()
            
                v = Validator(schema)
                if v.validate(content, schema) is False or not content:
                    error_obj = {"Error": "The request object contains inappropriate attributes or attribute input"}
                    return (json.dumps(error_obj), 400)
            
                error_obj = {"Error": "The request object is missing at least one of the required attributes"}
                if "name" not in content:
                    return (json.dumps(error_obj), 400)
                elif "type" not in content:
                    return (json.dumps(error_obj), 400)
                elif "length" not in content:
                    return (json.dumps(error_obj), 400)
                else:
                    boat_key = client.key(constants.boats, int(boat_id))
                    boat = client.get(key=boat_key)
                    if boat is None:
                        error_obj = {"Error": "No boat with this boat_id exists"}
                        return (json.dumps(error_obj), 404)
                    
                    elif int(boat["owner"]) != int(owner_results):
                        errObj = {"Error": "You are not the owner of this boat"}
                        return (json.dumps(errObj), 403)
                    
                    else:
                        boat_name = content["name"]
                        query = client.query(kind=constants.boats)
                        query.add_filter('name', '=', boat_name)
                        results = list(query.fetch())
                        if results != [] and results[0] != boat.key.id:
                            err_obj = {"Error": "The requested boat name is already in use"}
                            return (json.dumps(err_obj), 403)
                        boat.update({"name": content["name"], "type": content["type"], "length": content["length"]})
                        client.put(boat)
                        boat["id"] = boat.key.id
                        self_url = str(request.base_url)
                        boat["self"] = self_url
                        for e in boat["loads"]:
                            e["id"] = e.key.id
                            e["self"] = str(request.url_root) + "/" + str(e.key.id)
                        return response_status_json(boat, 'application/json', 200, None, None)
            else:
                errObj = {"Error": "Missing or Invalid JWTs"}
                return (json.dumps(errObj), 401)
        
        else:
            error_obj = {"Error": "The request mimetype should be application/json"}
            return(json.dumps(error_obj), 400)


    elif request.method == 'DELETE':
        owner_results = verify()
        if(owner_results and owner_results != -1):
            if not check_for_user(owner_results):
                errObj = {"Error": "Not a valid user, please register"}
                return (json.dumps(errObj), 401)

            boat_key = client.key(constants.boats, int(boat_id))
            boat = client.get(key=boat_key)
            if boat is None:
                error_obj = {"Error": "No boat with this boat_id exists"}
                return (json.dumps(error_obj), 404)
            elif int(boat["owner"]) != int(owner_results):
                errObj = {"Error": "You are not the owner of this boat"}
                return (json.dumps(errObj), 403) 
            else:
                if len(boat["loads"]) > 0:
                    for e in boat["loads"]:
                        load_id = e["id"]
                        load_key = client.key(constants.loads, int(load_id))
                        load = client.get(key=load_key)
                        if load is not None:
                            load["carrier"] = None
                            client.put(load)
                    client.delete(boat_key)
                    return ('', 204)
                else:
                    client.delete(boat_key)
                    return ('', 204)
        else:
                errObj = {"Error": "Missing or Invalid JWTs"}
                return (json.dumps(errObj), 401)


    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)

@bp.route('/<boat_id>/loads', methods=['GET', 'PATCH' , 'PUT', 'DELETE'])
def get_boats_loads(boat_id):
    if request.method == 'GET':
        if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
            error_obj = {"Error": "Accept header must be application/json"}
            return (json.dumps(error_obj), 406)
        boat_key = client.key(constants.boats, int(boat_id))
        boat = client.get(key=boat_key)
        if boat is None:
            error_obj = {"Error": "No boat with this boat_id exists"}
            return (json.dumps(error_obj), 404)
        elif len(boat["loads"]) > 0:
            for e in boat["loads"]:
                e["id"] = e.key.id
                e["self"] = str(request.base_url) + "/" + str(e.key.id)
            return json.dumps(boat["loads"])
        else:
            return json.dumps([])

    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)


from flask import Blueprint, request, make_response
from google.cloud import datastore
from cerberus import Validator
import json
import constants
from helper import get_loads_schema, response_status_json, check_for_user, verify

client = datastore.Client()

bp = Blueprint('loads', __name__, url_prefix='/loads')

@bp.route('', methods=['POST', 'PUT', 'PATCH', 'GET', 'DELETE'])
def loads_get_post():
    if request.method == 'POST':
        if request.mimetype == 'application/json':
            if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
               error_obj = {"Error": "Accept header must be application/json"}
               return (json.dumps(error_obj), 406)
            else:    
                content = request.get_json()
                schema = get_loads_schema()
            
                v = Validator(schema)
                if v.validate(content, schema) is False:
                    error_obj = {"Error": "The request object contains inappropriate attributes or attribute input"}
                    return (json.dumps(error_obj), 400)
            
                error_obj = {"Error": "The request object is missing at least one of the required attributes"}
                if "contents" not in content:
                    return (json.dumps(error_obj), 400)
                elif "delivery_date" not in content:
                    return (json.dumps(error_obj), 400)
                elif "weight" not in content:
                    return (json.dumps(error_obj), 400)
                else:
                    owner_results = verify()
                    if(owner_results and owner_results != -1):
                        if not check_for_user(owner_results):
                            errObj = {"Error": "Not a valid user, please register"}
                            return (json.dumps(errObj), 401)
                        new_load = datastore.entity.Entity(key=client.key(constants.loads))
                        new_load.update({"contents": content["contents"], "delivery_date": content["delivery_date"], "weight": content["weight"], "carrier": None})
                        client.put(new_load)
                        new_load["id"] = new_load.key.id
                        self_url = str(request.base_url) + "/" + str(new_load.key.id)
                        new_load["self"] = self_url
                        return response_status_json(new_load, 'application/json', 201, self_url, None)
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
            query = client.query(kind=constants.loads)
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
                if e['carrier'] is not None:
                    for f in e["carrier"]:
                        f["self"] = str(request.base_url) + "/" + str(f.key.id)
            output = {"loads": results}
            if next_url:
                output["next"] = next_url
            return response_status_json(output, 'application/json', 200, None, None)
            
    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)


@bp.route('/<load_id>', methods=['GET', 'PATCH' , 'PUT', 'DELETE'])
def loads_put_patch_delete(load_id):
    if request.method == 'GET':
        if request.headers['Accept'] == '*/*' or 'application/json' in request.headers['Accept']:
            load_key = client.key(constants.loads, int(load_id))
            load = client.get(load_key)
            error_obj = {"Error": "No load with this load_id exists"}
            if load is None:
                return (json.dumps(error_obj), 404)
            else:
                load["id"] = load.key.id
                load["self"] = str(request.base_url)
                return response_status_json(load, 'application/json', 200, None, None)

        else:
            error_obj = {"Error": "Accept header must be application/json"}
            return(json.dumps(error_obj), 406)


    elif request.method == 'PATCH':
        if request.mimetype == 'application/json':
            if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
               error_obj = {"Error": "Accept header must be application/json"}
               return (json.dumps(error_obj), 406)
            else:
                owner_results = verify()
                if(owner_results and owner_results != -1):

                    if not check_for_user(owner_results):
                        errObj = {"Error": "Not a valid user, please register"}
                        return (json.dumps(errObj), 401)

                    content = request.get_json()
                    schema = get_loads_schema()
                
                    v = Validator(schema)
                    if v.validate(content, schema) is False or not content:
                        error_obj = {"Error": "The request object contains inappropriate attributes or attribute input"}
                        return (json.dumps(error_obj), 400)
                
                    error_obj = {"Error": "The request object is missing at least one of the required attributes"}
                    if "contents" not in content and "delivery_date" not in content and "weight" not in content:
                        return (json.dumps(error_obj), 400)
                    else:

                        load_key = client.key(constants.loads, int(load_id))
                        load = client.get(key=load_key)
                        if load is None:
                            error_obj = {"Error": "No load with this load_id exists"}
                            return (json.dumps(error_obj), 404)
                        
                        else:
                            updated_content = ""
                            updated_delivery_date = ""
                            updated_weight = -1
                            if "contents" not in content:
                                updated_content = load["contents"]
                            else:
                                updated_content = content["contents"]
                            
                            if "delivery_date" not in content:
                                updated_delivery_date = load["delivery_date"]
                            else:
                                updated_delivery_date = content["delivery_date"]

                            if "weight" not in content:
                                updated_weight = load["weight"]
                            else:
                                updated_weight = content["weight"]
                            
                            load.update({"contents": updated_content, "delivery_date": updated_delivery_date, "weight": updated_weight})
                            client.put(load)
                            load["id"] = load.key.id
                            self_url = str(request.base_url)
                            load["self"] = self_url
                            if load['carrier'] is not None:
                                for e in load["carrier"]:
                                    e["self"] = str(request.base_url) + "/" + str(e["id"])
                            return response_status_json(load, 'application/json', 200, None, None)
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

            else:
                owner_results = verify()
                if(owner_results and owner_results != -1):

                    if not check_for_user(owner_results):
                        errObj = {"Error": "Not a valid user, please register"}
                        return (json.dumps(errObj), 401)

                    content = request.get_json()
                    schema = get_loads_schema()
                
                    v = Validator(schema)
                    if v.validate(content, schema) is False or not content:
                        error_obj = {"Error": "The request object contains inappropriate attributes or attribute input"}
                        return (json.dumps(error_obj), 400)
                
                    error_obj = {"Error": "The request object is missing at least one of the required attributes"}
                    if "contents" not in content:
                        return (json.dumps(error_obj), 400)
                    elif "delivery_date" not in content:
                        return (json.dumps(error_obj), 400)
                    elif "weight" not in content:
                        return (json.dumps(error_obj), 400)
                    else:

                        load_key = client.key(constants.loads, int(load_id))
                        load = client.get(key=load_key)
                        if load is None:
                            error_obj = {"Error": "No load with this load_id exists"}
                            return (json.dumps(error_obj), 404)
                        
                        else:
                            load.update({"contents": content["contents"], "delivery_date": content["delivery_date"], "weight": content["weight"]})
                            client.put(load)
                            load["id"] = load.key.id
                            self_url = str(request.base_url)
                            load["self"] = self_url
                            if load['carrier'] is not None:
                                for e in load['carrier']:
                                    e["self"] = str(request.base_url) + "/" + str(e["id"])
                            return response_status_json(load, 'application/json', 200, None, None)
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

            load_key = client.key(constants.loads, int(load_id))
            load = client.get(key=load_key)
            
            if load is None:
                error_obj = {"Error": "No load with this load_id exists"}
                return (json.dumps(error_obj), 404)

            else:
                if load["carrier"] is not None:
                    boat_id = load["carrier"]["id"]
                    boat_key = client.key(constants.boats, int(boat_id))
                    boat = client.get(key=boat_key)
                    owner = -1
                    if boat is not None:
                        if boat["loads"] is not None:
                            for e in boat["loads"]:
                                if int(e["id"]) == int(id):
                                    if int(e["owner"]) != owner_results:
                                        owner = 1
                                    else:
                                        boat["loads"].remove(e)
                                        client.put(boat)
                    
                    if owner:
                        errObj = {"Error": "You are not the owner of this boat"}
                        return (json.dumps(errObj), 403)
                    else:
                        client.delete(load_key)
                        return ('', 204)
                else:
                    client.delete(load_key)
                    return ('', 204)
        else:
            errObj = {"Error": "Missing or Invalid JWTs"}
            return (json.dumps(errObj), 401)


    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)

@bp.route('/<load_id>/boats/<boat_id>', methods=['GET', 'POST', 'PATCH' , 'PUT', 'DELETE'])
def get_loads_loads(load_id, boat_id):
    if request.method == 'PATCH':
        if request.headers['Accept'] != '*/*' and 'application/json' not in request.headers['Accept']:
            error_obj = {"Error": "Accept header must be application/json"}
            return (json.dumps(error_obj), 406)
        else:
            owner_results = verify()
            if owner_results and owner_results != -1:
                if not check_for_user(owner_results):
                    errObj = {"Error": "Not a valid user, please register"}
                    return (json.dumps(errObj), 401)

                load_key = client.key(constants.loads, int(load_id))
                load = client.get(key=load_key)
                boat_key = client.key(constants.boats, int(boat_id))
                boat = client.get(key=boat_key)
                
                if load is None:
                    error_obj = {"Error": "This load_id is already on a boat or this load_id does not exist"}
                    return (json.dumps(error_obj), 404)
                
                elif boat is None:
                    error_obj = {"Error": "No boat with this boat_id exists"}
                    return (json.dumps(error_obj), 404)

                else:
                    if int(boat["owner"]) != int(owner_results):
                        errObj = {"Error": "You are not the owner of this boat"}
                        return (json.dumps(errObj), 403)
                    
                    else:
                        if load["carrier"] is None:
                            load.update({"carrier": {"id": int(boat_id), "name": boat["name"]}})
                            client.put(load)
                            load["self"] = str(request.url_root) + "loads/" + str(load_id)
                            load["carrier"]["self"] = str(request.url_root) + "boats/" + str(boat_id)
                            
                            boat["loads"].append({"id": int(load_id)})
                            client.put(boat)
                            boat["id"] = boat_id

                            return response_status_json(load, 'application/json', 200, None, None)

                        else:
                            errObj = {"Error": "Load currently has a carrier"}
                            return (json.dumps(errObj), 403)

            else:
                errObj = {"Error": "Missing or Invalid JWTs"}
                return (json.dumps(errObj), 401)
    
    elif request.method == 'DELETE':
        owner_results = verify()
        if owner_results and owner_results != -1:
            if not check_for_user(owner_results):
                errObj = {"Error": "Not a valid user, please register"}
                return (json.dumps(errObj), 401)

            load_key = client.key(constants.loads, int(load_id))
            load = client.get(key=load_key)
            boat_key = client.key(constants.boats, int(boat_id))
            boat = client.get(key=boat_key)
            
            if load is None:
                error_obj = {"Error": "No load with this load_id exists"}
                return (json.dumps(error_obj), 404)
            
            elif boat is None:
                error_obj = {"Error": "No boat with this boat_id exists"}
                return (json.dumps(error_obj), 404)

            elif int(boat["owner"]) != int(owner_results):
                errObj = {"Error": "You are not the owner of this boat"}
                return (json.dumps(errObj), 403)
                
            elif load["carrier"] is None:
                errObj = {"Error": "The load is not loaded on a boat"}
                return (json.dumps(errObj), 404)

            elif int(load["carrier"]["id"]) != int(boat_id):
                errObj = {"Error": "The load_id selected is not on this boat_id"}
                return (json.dumps(errObj), 404)

            else:
                for e in boat["loads"]:
                    if int(e["id"]) == int(load_id):
                        boat["loads"].remove(e)

                client.put(boat)
                load.update({"carrier": None})
                client.put(load)
                return ('', 204)

        else:
            errObj = {"Error": "Missing or Invalid JWTs"}
            return (json.dumps(errObj), 401)
                    
    else:
        error_obj = {"Error": "Method not recognized"}
        return(json.dumps(error_obj), 405)


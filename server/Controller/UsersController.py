import logging, json
from flask import request, jsonify
from flask_restful import Resource, abort
from models import validate_user, User, UserSchema, Role
from config import db, flask_bcrypt
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                    jwt_required, jwt_refresh_token_required, get_jwt_identity)
from Manager.UserManager import UserManager
from Manager.RoleManager import RoleManager


userManager = UserManager()
roleManager = RoleManager()

# user/all [POST]
class UserAll(Resource):
    
    # get all users
    def get(self):
        logging.debug('Received request: GET user/all')

        users = userManager.read_all_no_password()
        if users is None:
            abort(404, message="No users currently exist.")
        return users

# user/vhts [GET]
class UserAllVHT(Resource):
    
    # get all VHT Ids 
    def get(self):
        logging.debug('Received request: GET user/vhts')

        vhtId_list = userManager.read_all_vhts()
        if vhtId_list is None:
            return []
        return vhtId_list


# user/register [POST]
class UserApi(Resource):

    # Create a new user
    def post(self):
        # register user endpoint
        data = validate_user(request.get_json())
        if data['ok']:
            data = data['data']

            # check if user exists
            user = User.query.filter_by(email=data['email']).first()
            if user:
                return { "message" : "Email has already been taken"}, 400

            # get password
            data['password'] = flask_bcrypt.generate_password_hash(data['password'])

            # find the role of the user
            role = Role.query.filter_by(name=data['role']).first()
            del data['role']
            
            # Add a new patient to db
            user_schema = UserSchema()
            new_user = user_schema.load(data, session=db.session)

            role.users.append(new_user) # add new user to their role

            db.session.add(role) # add user and role
            db.session.commit()

            return {}, 200
        else:
            return {'message': 'Please check the fields'}, 400


# user/auth [POST]
class UserAuthApi(Resource):

    # login to account
    def post(self):
        data = validate_user(request.get_json())
        if data['ok']:
            data = data['data']

            user = User.query.filter_by(email=data['email']).first()

            if user and flask_bcrypt.check_password_hash(user.password, data['password']):
                del data['password']

                # setup any extra user params
                roles = []
                if user.roleIds:
                    for role in user.roleIds:
                        roles.append(role.name.name)
                
                data['roles'] = roles
                data['firstName'] = user.firstName
                data['healthFacilityName'] = user.healthFacilityName
                data['isLoggedIn'] = True
                data['userId'] = user.id

                vhtList = []
                data['vhtList'] = []
                if 'CHO' in roles:
                    if user.vhtList:
                        for user in user.vhtList:
                            vhtList.append(user.id)
                        data['vhtList'] = vhtList

                access_token = create_access_token(identity=data)
                refresh_token = create_refresh_token(identity=data)
                data['token'] = access_token
                data['refresh'] = refresh_token

                return data, 200
            else:
                return {'message': 'Invalid email or password'}, 401
        else:
            return {'message': 'Bad request parameters: {}'.format(data['message'])}, 400

# Get identity of current user with jwt token
class UserTokenApi(Resource):
    @jwt_required
    def get(self):
        current_user = get_jwt_identity()
        return current_user, 200

# user/edit/<int:id> [PUT]
class UserEdit(Resource):

    @staticmethod
    def _get_request_body():
        raw_req_body = request.get_json(force=True)
        print('Request body: ' + json.dumps(raw_req_body, indent=2, sort_keys=True))
        return raw_req_body
    
    # edit user with id
    def put(self, id):

        # validate inputs
        if not id:
            abort(400, message="User ID is required")

        new_user = UserEdit._get_request_body()
        
        newVhtIds = new_user.get('newVhtIds')
        if newVhtIds is not None:
            # add vht to CHO's vht list
            roleManager.add_vht_to_supervise(id, new_user['newVhtIds'])
            new_user.pop('newVhtIds', None)

        newRoleIds = new_user.get('newRoleIds')
        if newRoleIds is not None:
            # add user to role
            roleManager.add_user_to_role(id, new_user['newRoleIds'])
            new_user.pop('newRoleIds', None)
        
        update_res = userManager.update("id", id, new_user)

        if not update_res:
            abort(400, message=f'No user exists with id "{id}"')
        else:
            return update_res

# user/delete/<int:id>
class UserDelete(Resource):

    @jwt_required
    def delete(self, id=None):
        current_user = get_jwt_identity()
        if 'ADMIN' in current_user['roles']:
            if id:
                logging.debug('Received request: DELETE /user/delete/<id>')
                del_res = userManager.delete("id", id)
                if not del_res:
                    abort(400, message=f'No user exists with id "{id}"')
            else:
                abort(400, message='No id supplied for user delete')
        else:
            abort(400, message='Only Admins can delete users') 
        return {}
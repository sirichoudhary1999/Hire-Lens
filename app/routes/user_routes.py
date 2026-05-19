from flask import Blueprint, request, jsonify
from app.models import User
from app.extensions import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

user_bp = Blueprint("users", __name__)

#USER LOGIN
@user_bp.route("/user/login", methods = ["POST"])
def login_user():
    data = request.get_json()
    response = {
        "meta" : {
            "success": True,
            "message": ""
        },
        "data" :{}
    }

    if not data or not data.get("email") or not data.get("password"):

        response["meta"] = {
            "success"  : False,
            "message" : "Email and Password are requied",
            "status"  : 1000,
        }
        return jsonify(response), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user :
        response["meta"] = {
            "status"  : 1001,
            "message" : "User not found",
            "success" : False
        }
        return jsonify(response), 404

    if not user.check_password(data["password"]):
        response["meta"] = {
            "status"  : 100,
            "message" : "Invalid Credentials",
            "success" : False
        }
        return jsonify(response), 401
    
    access_token = create_access_token(identity=str(user.id))
    response["data"] = {
            "user" : user.get_username_id(),
            "access_token": access_token
        }

    response["meta"] = {
            "success"  : True,
            "message" : "user logged successfully",
        }
    return jsonify(response), 200


# CREATE USER
@user_bp.route("/user/register", methods = ["POST"])
def create_user():
    data = request.get_json()
    response = {
        "data" : {},
        "meta" : {
            "success" : True,
            "message" : "",
        }
    }

    if not data or not data.get("email") or not data.get("username") or not data.get("password"):
        response["meta"] = {
            "success" : True,
            "status"  : 1010,
            "message": "Mandatory fields are required"
            }
        return jsonify(response), 200

    if User.query.filter_by(email=data["email"]).first():
        response["meta"] = {
            "success" : True,
            "status"  : 1011,
            "error": "Email already exists"
        }
        return jsonify(response), 200

    if User.query.filter_by(username=data["username"]).first():
        response["meta"] = {
            "success" : True,
            "status"  : 1012,
            "error": "Username already exists"
        }
        return jsonify(response), 200

    user = User(
        email = data["email"],
        username = data["username"]
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()
    access_token = create_access_token(identity=str(user.id))
    response["data"] = {
                "user" : user.get_username_id(),
                "access_token": access_token
        }    
    response["meta"] =  {
                "success" : True,
                "message" : "User registered successfully",
        }
    return jsonify(response), 200


# GET ALL USERS
@user_bp.route("/users", methods = ["GET"])
@jwt_required()
def get_users():
    users = User.query.all()
    return jsonify([user.get_username_id() for user in users])


# GET USER BY ID
@user_bp.route("/user/primaryProfileDatabyId/<int:user_id>", methods = ["GET"])
@jwt_required()
def get_user(user_id):
    response = {
        "data" : {},
        "meta" : {
            "success" : True,
            "message" : "",
        }
    }
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        response["meta"] ={
            "message": "Unauthorized user",
            "success": False
        }
        return jsonify(response), 403

    user = User.query.get(user_id)

    if not user:
        response["meta"] = {
            "success"  : True,
            "message" : "User not found"
        }
        return jsonify(response), 400

    user_details_response = {

        'data': user.get_user_details(),
        "meta": {
            "success": True,
            "message": "User details fetched successfully"
        }
    }
    return jsonify(user_details_response), 200

# UPDATE USER
@user_bp.route("/user/updatePrimaryProfileData/<int:user_id>", methods = ["PUT"])
@jwt_required()
def update_user(user_id):
    response = {
        "data" : {},
        "meta" : {
            "success" : True,
            "message" : "",
        }
    }
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        response["meta"] ={
            "message": "Unauthorized user",
            "success": False
        }
        return jsonify(response), 403

    user = User.query.get(user_id)

    if not user:
        response["meta"] = {
            "success"  : True,
            "message" : "User not found"
        }
        return jsonify(response), 400
    data = request.get_json()

    for key, value in data.items():
        if hasattr(user, key) :
            setattr(user, key, value)

    db.session.commit()
    return jsonify(
        {
            "data": user.get_username_id(),
            "meta": {
                "success": True,
                "message": "User updated successfully"
            }
        }), 200


# DELETE USER
@user_bp.route("/user/<int:user_id>", methods = ["DELETE"])
@jwt_required()
def delete_user(user_id):
    user = User.query.filter_by(id = user_id).first()
    if not user :
        return jsonify({
            "status"  : 1001,
            "message" : "User not found"
        })

    db.session.delete(user)
    db.session.commit()
    return jsonify({
        "message": "User deleted successfully"
    })

#UPDATE PASSWORD
@user_bp.route("/users/<int:user_id>/password", methods = ["PUT"])
@jwt_required()
def update_password(user_id):
    response = {
        "data" : {},
        "meta" : {
            "success" : True,
            "message" : "",
        }
    }
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        response["meta"] ={
            "message": "Unauthorized user",
            "success": False
        }
        return jsonify(response), 403

    user = User.query.get(user_id)

    if not user:
        response["meta"] = {
            "success"  : True,
            "message" : "User not found"
        }
        return jsonify(response), 404
    data = request.get_json()
    new_password = data.get("new_password")
    current_password = data.get("current_password")

    if current_password in data and new_password in data:

        if not user.check_password(current_password):
            return jsonify({
                "meta": {"success": False, "message": "Current password incorrect"}
            }), 400

    user.set_password(data["new_password"])

    user.set_password(new_password)
    db.session.commit()
    return jsonify(
        {
            "data": user.get_username_id(),
            "meta": {
                "success": True,
                "message": "Password updated successfully"
            }
        }), 200
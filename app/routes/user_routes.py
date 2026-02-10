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
        return response

    user = User.query.filter_by(email=data["email"]).first()

    if not user :
        response["meta"] = {
            "status"  : 1001,
            "message" : "User not found",
            "success" : False
        }
        return jsonify(response)

    if not user.check_password(data["password"]):
        response["meta"] = {
            "status"  : 100,
            "message" : "Invalid Credentials",
            "success" : False
        }
        return jsonify(response)
    
    access_token = create_access_token(identity=user.id)
    response["data"] = {
            "user" : user.to_dict(),
            "access_token": access_token
        }

    response["meta"] = {
            "success"  : True,
            "message" : "user logged successfully",
        }
    return jsonify(response), 200


# CREATE USER
@user_bp.route("/users", methods = ["POST"])
@jwt_required()
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

    response["data"] = user.to_dict()
    response["meta"] =  {
            "success" : True,
            "message" : "User registered successfully",
        }
    return jsonify(response), 200


# GET ALL USERS
@user_bp.route("/users", methods = ["GET"])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


# GET USER BY ID
@user_bp.route("/users/<int:user_id>", methods = ["GET"])
def get_user(user_id):
    user = User.query.filter_by(id = user_id).first()

    if not user :
        return jsonify({
            "status"  : 1001,
            "message" : "User not found"
        })

    return jsonify(user.to_dict()), 200

# UPDATE USER
@user_bp.route("/users/<int:user_id>", methods = ["PUT"])
def update_user(user_id):
    response = {
        "data" : {},
        "meta" : {
            "success" : True,
            "message" : "",
        }
    }
    current_user_id = get_jwt_identity()
    if current_user_id != user_id:
        response["meta"] ={
            "message": "Unauthorized user",
            "success": False
        }
        return jsonify(response), 403

    user = User.query.get(id = user_id)

    if not user:
        response["meta"] = {
            "success"  : True,
            "message" : "User not found"
        }
        return jsonify(response), 200
    data = request.get_json()

    if "email" in data:
        user.email = data["email"]
    if "username" in data:
        user.username = data["username"]

    db.session.commit()
    return jsonify(user.to_dict()), 200


# DELETE USER
@user_bp.route("/users/<int:user_id>", methods = ["DELETE"])
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

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Experience, Academics, Skills
from app.extensions import db

experience_bp = Blueprint("experience", __name__)
skills_bp = Blueprint("skills", __name__)
academics_bp = Blueprint("academics", __name__)


#POST SKILLS
@skills_bp.route("/profile/updateSkills", methods=["PUT"])
@jwt_required()
def add_skills():
    data = request.get_json()
    user_id = int(get_jwt_identity())
    skills = Skills.query.filter_by(user_id = user_id).first()

    if skills:
        skills.skill_name = data.get("skill_name", [])
    else:
        skills = Skills(
            user_id=user_id, 
            skill_name=data.get("skill_name", [])
        )
        db.session.add(skills)

    db.session.commit()

    return jsonify({
        "data": {
            "skills": skills.skill_name
        },
        "meta": {
            "success": True,
            "message": "Skills added successfully"
        }
    }), 201

#GET SKILLS
@skills_bp.route("/profile/getSkills", methods=["GET"])
@jwt_required()
def get_skills():
    user_id = int(get_jwt_identity())
    skills = Skills.query.filter_by(user_id=user_id).first()

    if not skills:
        return jsonify({
            "data": {
                "skills": []
            },
            "meta": {
                "success": True,
                "message": "No skills found for the user"
            }
        }), 200

    return jsonify({
        "data": {
            "skills": skills.skill_name
        },
        "meta": {
            "success": True,
            "message": "Skills retrieved successfully"
        }
    }), 200

#add ACADEMICS
@academics_bp.route("/profile/addAcademics", methods=["POST"])
@jwt_required()
def add_academics():
    data = request.get_json()
    user_id = int(get_jwt_identity())

    academics_list = data.get("academics", [])

    for academic_data in academics_list:
        academic = Academics(user_id=user_id)
        for key, value in academic_data.items():
            if hasattr(academic, key):
                setattr(academic, key, value)

        db.session.add(academic)
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Academics added successfully"
        }
    }), 200

#UPDATE ACADEMICS
@academics_bp.route("/profile/updateAcademics/<int:academics_id>", methods=["PUT"])
@jwt_required()
def edit_academics(academics_id):
    data = request.get_json()
    user_id = int(get_jwt_identity())
    academics = Academics.query.filter_by(user_id=user_id, id=academics_id).first()

    if academics:
        for key, value in data.items():
            if hasattr(academics, key):
                setattr(academics, key, value)
        db.session.commit()
        return jsonify({
            "meta": {
                "success": True,
                "message": "Academics updated successfully"
            }
        }), 200
    else:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Academics not found for the user"
            }
        }), 404

#GET ACADEMICS
@academics_bp.route("/profile/getAllAcademics", methods=["GET"])
@jwt_required()
def get_academics():
    user_id = int(get_jwt_identity())
    academics = Academics.query.filter_by(user_id=user_id).all()

    if not academics:
        return jsonify({
            "data": {
                "academics": []
            },
            "meta": {
                "success": True,
                "message": "No academics found for the user"
            }
        }), 200

    return jsonify({
        "data": {
            "academics": [a.to_dict() for a in academics]
        },
        "meta": {
            "success": True,
            "message": "Academics retrieved successfully"
        }
    }), 200

#GET ACADEMICS BY ID
@academics_bp.route("/profile/getAcademicsById/<int:academics_id>", methods=["GET"])
@jwt_required()
def get_academics_by_id(academics_id):
    user_id = int(get_jwt_identity())
    academics = Academics.query.filter_by(user_id=user_id, id=academics_id).first()

    if not academics:
        return jsonify({
            "data": {
                "academics": None
            },
            "meta": {
                "success": True,
                "message": "Academics not found for the user"
            }
        }), 404

    return jsonify({
        "data": {
            "academics": academics.get_academics_by_user_id(user_id)
        },
        "meta": {
            "success": True,
            "message": "Academics retrieved successfully"
        }
    }), 200


#DELETE ACADEMICS
@academics_bp.route("/profile/deleteAcademics/<int:academics_id>", methods=["DELETE"])
@jwt_required()
def delete_academics(academics_id):
    user_id = int(get_jwt_identity())
    academics = Academics.query.filter_by(user_id=user_id, id=academics_id).first()

    if not academics:
        return jsonify({
            "meta": {
                "success": False,
                "message": "No academics found for the user"
            }
        }), 404

    db.session.delete(academics)
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Academics deleted successfully"
        }
    }), 200

#ADD EXPERIENCE
@experience_bp.route("/profile/addExperience", methods=["POST"])
@jwt_required()
def add_experience():
    data = request.get_json()
    user_id = int(get_jwt_identity())
    experience = Experience(
        user_id=user_id,
        experiences=data.get("experiences", [])
    )

    db.session.add(experience)
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Experience updated successfully"
        }
    }), 200

#UPDATE EXPERIENCE
@experience_bp.route("/profile/updateExperienceById/<int:experience_id>", methods=["PUT"])
@jwt_required()
def update_experience(experience_id):
    data = request.get_json()
    user_id = int(get_jwt_identity())
    experience = Experience.query.filter_by(user_id=user_id, id=experience_id).first()

    if experience:
        experience.experiences = data.get("experiences", [])
        db.session.commit()
        return jsonify({
            "meta": {
                "success": True,
                "message": "Experience updated successfully"
            }
        }), 200
    else:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Experience not found for the user"
            }
        }), 404

#GET EXPERIENCE
@experience_bp.route("/profile/getAllExperiences", methods=["GET"])
@jwt_required()
def get_experience():
    user_id = int(get_jwt_identity())
    experience = Experience.query.filter_by(user_id=user_id).first()

    if not experience:
        return jsonify({
            "data": {
                "experience": []
            },
            "meta": {
                "success": True,
                "message": "No experience found for the user"
            }
        }), 200

    return jsonify({
        "data": {
            "experience": experience.experiences
        },
        "meta": {
            "success": True,
            "message": "Experience retrieved successfully"
        }
    }), 200

#DELETE EXPERIENCE
@experience_bp.route("/profile/deleteExperienceById/<int:experience_id>", methods=["DELETE"])  
@jwt_required()
def delete_experience(experience_id):
    user_id = int(get_jwt_identity())
    experience = Experience.query.filter_by(user_id=user_id, id=experience_id).first()

    if not experience:
        return jsonify({
            "meta": {
                "success": False,
                "message": "No experience found for the user"
            }
        }), 404

    db.session.delete(experience)
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Experience deleted successfully"
        }
    }), 200
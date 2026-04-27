from app.extensions import db
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.job_application import JobApplication
from datetime import datetime

job_application_bp = Blueprint("job_application", __name__)

#POST JOB APPLICATION
@job_application_bp.route("/jobs/add", methods=["POST"])
@jwt_required()
def add_job_application():
    data = request.get_json()
    user_id = int(get_jwt_identity())

    job_application = JobApplication(
        user_id=user_id,
        company=data.get("company"),
        role=data.get("role"),
        status=data.get("status"),
        notes=data.get("notes"),
        applied_at=datetime.utcnow()
    )

    db.session.add(job_application)        
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Job application added successfully"
        }
    }), 201

#GET ALL JOB APPLICATIONS
@job_application_bp.route("/jobs/fetchAllJobs", methods=["GET"])
@jwt_required()
def get_job_applications():
    user_id = int(get_jwt_identity())
    job_applications = JobApplication.query.filter_by(user_id=user_id).all()

    response = {
       "jobs": [app.to_dict() for app in job_applications],
        "meta" : {
            "success": True,
            "message": ""
        }
    }
    if not job_applications:

        response["meta"]: {
                "success": True,
                "message": "No job applications found for the user"
        }

        response["meta"]: {
            "success": True,
            "message": "Job applications retrieved successfully"
        }
      
    return jsonify(response), 200


#GET JOB APPLICATION BY ID
@job_application_bp.route("/jobs/fetchJob/<int:job_id>", methods=["GET"])
@jwt_required()
def get_job_application_by_id(job_id):
    user_id = int(get_jwt_identity())
    job_application = JobApplication.query.filter_by(user_id=user_id, job_id=job_id).first()

    if not job_application:
        return jsonify({
            "data": {
                "job_application": []
            },
            "meta": {
                "success": True,
                "message": "Job application not found for the user"
            }
        }), 404

    return jsonify({
        "data": {
            "job_application": job_application.to_dict()
        },
        "meta": {
            "success": True,
            "message": "Job application retrieved successfully"
        }
    }), 200


#UPDATE JOB APPLICATION
@job_application_bp.route("/jobs/updateJob/<int:job_id>", methods=["PUT"])
@jwt_required()
def update_job_application(job_id):
    data = request.get_json()
    user_id = int(get_jwt_identity())
    job_application = JobApplication.query.filter_by(user_id=user_id, job_id=job_id).first()

    if not job_application:
        return jsonify({
            "data": {
                "job_application": None
            },
            "meta": {
                "success": True,
                "message": "Job application not found for the user"
            }
        }), 404

    job_application.company = data.get("company", job_application.company)
    job_application.role = data.get("role", job_application.role)
    job_application.status = data.get("status", job_application.status)
    job_application.notes = data.get("notes", job_application.notes)

    db.session.commit()

    return jsonify({
        "data": {
            "job_application": job_application.to_dict()
        },
        "meta": {
            "success": True,
            "message": "Job application updated successfully"
        }
    }), 200

#DELETE JOB APPLICATION
@job_application_bp.route("/jobs/deleteJob/<int:job_id>", methods=["DELETE"])
@jwt_required()
def delete_job_application(job_id):
    user_id = int(get_jwt_identity())
    job_application = JobApplication.query.filter_by(user_id=user_id, job_id=job_id).first()

    if not job_application:
        return jsonify({
            "data": {
                "job_application": None
            },
            "meta": {
                "success": True,
                "message": "Job application not found for the user"
            },
        }), 404

    db.session.delete(job_application)
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Job application deleted successfully"
        }
    }), 200
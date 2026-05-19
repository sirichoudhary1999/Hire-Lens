from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Resume, ResumeOptimizationLog
from app.extensions import db
from app.utils.file_handler import (
    validate_file_upload, save_uploaded_file, extract_text_from_file, delete_resume_file
)
from app.services.ai_service import get_optimizer
import datetime
import os

resume_bp = Blueprint("resume", __name__)


@resume_bp.route("/resume/upload", methods=["POST"])
@jwt_required()
def upload_resume():
    """Upload resume - supports both file upload and JSON data."""
    user_id = int(get_jwt_identity())

    # Check if request contains file or JSON
    if 'file' in request.files:
        # File upload flow
        file = request.files['file']

        # Validate file
        is_valid, message = validate_file_upload(file)
        if not is_valid:
            return jsonify({
                "meta": {
                    "success": False,
                    "message": message
                }
            }), 400

        # Get optional fields from form
        title = request.form.get('title', 'My Resume')
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'

        # Create resume record first to get ID
        resume = Resume(
            user_id=user_id,
            title=title,
            is_primary=is_primary
        )
        db.session.add(resume)
        db.session.flush()  # Get ID without committing

        # Save file
        file_path, original_filename, file_type, file_size = save_uploaded_file(file, user_id, resume.id)

        # Extract text from file
        try:
            text = extract_text_from_file(file_path, file_type)
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "meta": {
                    "success": False,
                    "message": f"Failed to extract text from file: {str(e)}"
                }
            }), 500

        # Update resume with file info
        resume.original_filename = original_filename
        resume.file_path = file_path
        resume.file_type = file_type
        resume.file_size = file_size

        # Parse extracted text into structured data using AI
        try:
            optimizer = get_optimizer()  # Uses default AI provider from config

            # Create a parsing prompt (no job description needed, just parse)
            parsing_result = optimizer.optimize_resume(
                resume_data={"personal_info": {"raw_text": text}},
                job_description="Parse this resume text into structured JSON format with all available information.",
                job_title=None
            )

            structured_data = parsing_result['optimized_resume']

            # Store structured data
            resume.personal_info = structured_data.get('personal_info', {"raw_text": text})
            resume.experiences = structured_data.get('experiences', [])
            resume.education = structured_data.get('education', [])
            resume.skills = structured_data.get('skills', {})
            resume.projects = structured_data.get('projects', [])
            resume.certifications = structured_data.get('certifications', [])

            message = "Resume uploaded and parsed successfully with AI"

        except Exception as e:
            # Fallback: if AI parsing fails, just store raw text
            print(f"AI parsing failed: {str(e)}")
            resume.personal_info = {"raw_text": text}
            message = "Resume uploaded and text extracted (AI parsing unavailable)"

        db.session.commit()

        return jsonify({
            "data": {
                "resume_id": resume.id,
                "resume": resume.to_dict()
            },
            "meta": {
                "success": True,
                "message": message
            }
        }), 201

    else:
        # JSON data flow
        data = request.get_json()

        if not data:
            return jsonify({
                "meta": {
                    "success": False,
                    "message": "No data provided"
                }
            }), 400

        resume = Resume(
            user_id=user_id,
            title=data.get('title', 'My Resume'),
            is_primary=data.get('is_primary', False),
            personal_info=data.get('personal_info', {}),
            experiences=data.get('experiences', []),
            education=data.get('education', []),
            skills=data.get('skills', {}),
            projects=data.get('projects', []),
            certifications=data.get('certifications', [])
        )

        db.session.add(resume)
        db.session.commit()

        return jsonify({
            "data": {
                "resume_id": resume.id,
                "resume": resume.to_dict()
            },
            "meta": {
                "success": True,
                "message": "Resume created successfully"
            }
        }), 201


@resume_bp.route("/resume/update/<int:resume_id>", methods=["PUT"])
@jwt_required()
def update_resume(resume_id):
    """Update existing resume."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    data = request.get_json()

    # Update fields
    updatable_fields = ['title', 'is_primary', 'personal_info', 'experiences',
                       'education', 'skills', 'projects', 'certifications']

    for field in updatable_fields:
        if field in data:
            setattr(resume, field, data[field])

    resume.version += 1
    db.session.commit()

    return jsonify({
        "data": {
            "resume": resume.to_dict()
        },
        "meta": {
            "success": True,
            "message": "Resume updated successfully"
        }
    }), 200


@resume_bp.route("/resume/optimize/<int:resume_id>", methods=["POST"])
@jwt_required()
def optimize_resume(resume_id):
    """AI-powered resume optimization based on job description."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    data = request.get_json()
    job_description = data.get('job_description')
    job_title = data.get('job_title')
    ai_provider = data.get('ai_provider', 'openai').lower()
    create_new_version = data.get('create_new_version', True)

    # Validate required fields
    if not job_description:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Job description is required"
            }
        }), 400

    # Validate AI provider
    if ai_provider not in ['openai', 'anthropic', 'demo']:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Invalid AI provider. Must be 'openai', 'anthropic', or 'demo'"
            }
        }), 400

    # Prepare resume data for optimization
    resume_data = {
        "personal_info": resume.personal_info,
        "experiences": resume.experiences,
        "education": resume.education,
        "skills": resume.skills,
        "projects": resume.projects,
        "certifications": resume.certifications
    }

    # Get AI optimizer
    try:
        optimizer = get_optimizer(ai_provider)
    except ValueError as e:
        return jsonify({
            "meta": {
                "success": False,
                "message": str(e)
            }
        }), 503

    # Optimize resume
    try:
        result = optimizer.optimize_resume(resume_data, job_description, job_title)
        optimized_data = result['optimized_resume']
    except Exception as e:
        # Log error
        log = ResumeOptimizationLog(
            resume_id=resume_id,
            user_id=user_id,
            job_description=job_description,
            job_title=job_title,
            ai_provider=ai_provider,
            status='failed',
            error_message=str(e)
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            "meta": {
                "success": False,
                "message": f"AI optimization failed: {str(e)}"
            }
        }), 500

    # Create new version or update existing
    if create_new_version:
        new_resume = Resume(
            user_id=user_id,
            title=f"{resume.title} - Optimized",
            is_primary=False,
            version=resume.version + 1,
            parent_resume_id=resume.id,
            personal_info=optimized_data.get('personal_info', {}),
            experiences=optimized_data.get('experiences', []),
            education=optimized_data.get('education', []),
            skills=optimized_data.get('skills', {}),
            projects=optimized_data.get('projects', []),
            certifications=optimized_data.get('certifications', []),
            last_optimized_at=datetime.datetime.utcnow(),
            optimization_count=1,
            ai_provider_used=ai_provider
        )
        db.session.add(new_resume)
        db.session.flush()
        target_resume = new_resume
    else:
        resume.personal_info = optimized_data.get('personal_info', resume.personal_info)
        resume.experiences = optimized_data.get('experiences', resume.experiences)
        resume.education = optimized_data.get('education', resume.education)
        resume.skills = optimized_data.get('skills', resume.skills)
        resume.projects = optimized_data.get('projects', resume.projects)
        resume.certifications = optimized_data.get('certifications', resume.certifications)
        resume.last_optimized_at = datetime.datetime.utcnow()
        resume.optimization_count += 1
        resume.ai_provider_used = ai_provider
        resume.version += 1
        target_resume = resume

    # Log optimization
    log = ResumeOptimizationLog(
        resume_id=target_resume.id,
        user_id=user_id,
        job_description=job_description,
        job_title=job_title,
        ai_provider=ai_provider,
        model_used=result.get('model_used'),
        changes_made={"optimization_notes": result.get('optimization_notes', '')},
        tokens_used=result.get('tokens_used'),
        processing_time_ms=result.get('processing_time_ms'),
        status='success'
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "data": {
            "resume_id": target_resume.id,
            "resume": target_resume.to_dict(),
            "optimization_log": {
                "id": log.id,
                "ai_provider": ai_provider,
                "processing_time_ms": result.get('processing_time_ms'),
                "optimization_notes": result.get('optimization_notes', '')
            }
        },
        "meta": {
            "success": True,
            "message": "Resume optimized successfully"
        }
    }), 200


@resume_bp.route("/resume/all", methods=["GET"])
@jwt_required()
def get_all_resumes():
    """Get all resumes for authenticated user."""
    user_id = int(get_jwt_identity())
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.updated_at.desc()).all()

    return jsonify({
        "data": {
            "resumes": [resume.to_dict() for resume in resumes]
        },
        "meta": {
            "success": True,
            "message": "Resumes retrieved successfully"
        }
    }), 200


@resume_bp.route("/resume/<int:resume_id>", methods=["GET"])
@jwt_required()
def get_resume(resume_id):
    """Get single resume."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    return jsonify({
        "data": {
            "resume": resume.to_dict()
        },
        "meta": {
            "success": True,
            "message": "Resume retrieved successfully"
        }
    }), 200


@resume_bp.route("/resume/<int:resume_id>", methods=["DELETE"])
@jwt_required()
def delete_resume(resume_id):
    """Delete resume and associated file."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    # Delete file if exists
    if resume.file_path:
        try:
            delete_resume_file(resume.file_path)
        except Exception as e:
            # Log error but continue with deletion
            pass

    db.session.delete(resume)
    db.session.commit()

    return jsonify({
        "meta": {
            "success": True,
            "message": "Resume deleted successfully"
        }
    }), 200


@resume_bp.route("/resume/download/<int:resume_id>", methods=["GET"])
@jwt_required()
def download_resume(resume_id):
    """Download or view resume file (PDF/DOCX)."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    # Check if resume has an associated file
    if not resume.file_path:
        return jsonify({
            "meta": {
                "success": False,
                "message": "This resume has no uploaded file. It was created using manual JSON entry."
            }
        }), 404

    # Verify file exists on filesystem
    if not os.path.exists(resume.file_path):
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume file not found on server"
            }
        }), 404

    # Determine if inline viewing (for browser) or download
    inline = request.args.get('inline', 'false').lower() == 'true'

    # Set MIME type based on file type
    mimetype_map = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword'
    }
    mimetype = mimetype_map.get(resume.file_type, 'application/octet-stream')

    # Send file
    return send_file(
        resume.file_path,
        mimetype=mimetype,
        as_attachment=not inline,  # False = inline viewing, True = download
        download_name=resume.original_filename
    )


@resume_bp.route("/resume/<int:resume_id>/optimization-history", methods=["GET"])
@jwt_required()
def get_optimization_history(resume_id):
    """Get optimization history for a resume."""
    user_id = int(get_jwt_identity())

    # Verify resume ownership
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    logs = ResumeOptimizationLog.query.filter_by(
        resume_id=resume_id,
        user_id=user_id
    ).order_by(ResumeOptimizationLog.created_at.desc()).all()

    return jsonify({
        "data": {
            "optimization_history": [log.to_dict() for log in logs]
        },
        "meta": {
            "success": True,
            "message": "Optimization history retrieved successfully"
        }
    }), 200

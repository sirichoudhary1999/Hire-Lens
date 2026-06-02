from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Resume, ResumeOptimizationLog
from app.extensions import db
from app.utils.file_handler import (
    validate_file_upload, save_uploaded_file, extract_text_from_file, delete_resume_file
)
from app.services.ai_service import get_optimizer
import datetime
import io
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

resume_bp = Blueprint("resume", __name__)


def _mark_resume_as_primary(user_id, resume_id):
    """Ensure only one resume remains primary for a user."""
    Resume.query.filter(
        Resume.user_id == user_id,
        Resume.id != resume_id,
        Resume.is_primary.is_(True)
    ).update({"is_primary": False}, synchronize_session=False)


def _delete_resume_by_id(user_id, resume_id):
    """Delete a user's resume, associated file, and related optimization logs."""
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return None, ({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }, 404)

    # Delete related optimization history first to avoid FK conflicts.
    ResumeOptimizationLog.query.filter_by(resume_id=resume.id, user_id=user_id).delete()

    # Delete file if present; continue even if file cleanup fails.
    if resume.file_path:
        try:
            delete_resume_file(resume.file_path)
        except Exception:
            pass

    db.session.delete(resume)
    db.session.commit()

    return resume, ({
        "meta": {
            "success": True,
            "message": "Resume deleted successfully"
        }
    }, 200)

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
    "with", "or", "you", "your", "we", "our", "this", "their", "they", "them", "can",
    "should", "must", "have", "had", "into", "within", "using", "use", "required",
    "requirements", "experience", "years", "year", "work", "role", "job", "candidate"
}

ACTION_VERBS = {
    "achieved", "built", "created", "designed", "developed", "drove", "implemented", "improved",
    "increased", "launched", "led", "managed", "optimized", "reduced", "scaled", "streamlined",
    "delivered", "engineered", "generated", "resolved", "owned", "spearheaded", "automated"
}


def _collect_resume_text(resume):
    chunks = [resume.title or ""]

    if isinstance(resume.personal_info, dict):
        for value in resume.personal_info.values():
            if isinstance(value, str):
                chunks.append(value)

    if isinstance(resume.skills, dict):
        for skill_values in resume.skills.values():
            if isinstance(skill_values, list):
                chunks.extend([str(v) for v in skill_values if v])
            elif isinstance(skill_values, str):
                chunks.append(skill_values)

    for section in [resume.experiences, resume.education, resume.projects, resume.certifications]:
        if isinstance(section, list):
            for item in section:
                if isinstance(item, dict):
                    for value in item.values():
                        if isinstance(value, str):
                            chunks.append(value)
                        elif isinstance(value, list):
                            chunks.extend([str(v) for v in value if isinstance(v, str)])
                elif isinstance(item, str):
                    chunks.append(item)

    return "\n".join([c for c in chunks if c]).lower()


def _extract_keywords(job_description):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", (job_description or "").lower())
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]

    keyword_counts = {}
    for word in filtered:
        keyword_counts[word] = keyword_counts.get(word, 0) + 1

    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in sorted_keywords[:20]]


def _extract_experience_bullets(experiences):
    bullets = []
    if not isinstance(experiences, list):
        return bullets

    candidate_fields = [
        "description", "responsibilities", "achievements", "highlights", "summary", "points", "details"
    ]

    for exp in experiences:
        if not isinstance(exp, dict):
            continue

        for field in candidate_fields:
            value = exp.get(field)
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, str) and entry.strip():
                        bullets.append(entry.strip())
            elif isinstance(value, str) and value.strip():
                parts = re.split(r"\n|•|- ", value)
                for part in parts:
                    text = part.strip()
                    if text:
                        bullets.append(text)

    return bullets


def _analyze_resume_content(resume, job_description):
    resume_text = _collect_resume_text(resume)
    keywords = _extract_keywords(job_description)

    present_keywords = [k for k in keywords if re.search(rf"\b{re.escape(k)}\b", resume_text)]
    missing_keywords = [k for k in keywords if k not in present_keywords]

    bullets = _extract_experience_bullets(resume.experiences)
    weak_bullets = []
    quantification_issues = []

    for bullet in bullets:
        words = bullet.split()
        starts_with_action_verb = words and words[0].strip(".,").lower() in ACTION_VERBS
        has_metric = bool(re.search(r"\d", bullet))

        if len(words) < 8 or not starts_with_action_verb:
            weak_bullets.append(bullet)
        if not has_metric:
            quantification_issues.append(bullet)

    passive_patterns = [
        r"\b(was|were|is|are|been|being)\s+\w+ed\b",
        r"\b(has been|have been|had been)\s+\w+ed\b"
    ]
    passive_hits = []
    for sentence in re.split(r"[.!?\n]", resume_text):
        normalized = sentence.strip()
        if not normalized:
            continue
        if any(re.search(pattern, normalized) for pattern in passive_patterns):
            passive_hits.append(normalized)

    keyword_coverage_score = int((len(present_keywords) / max(len(keywords), 1)) * 50)
    missing_penalty = min(len(missing_keywords) * 3, 20)
    weak_penalty = min(len(weak_bullets) * 2, 15)
    passive_penalty = min(len(passive_hits) * 2, 10)
    quant_penalty = min(len(quantification_issues) * 2, 10)
    ats_score = max(0, min(100, 90 + keyword_coverage_score - missing_penalty - weak_penalty - passive_penalty - quant_penalty))

    recommended_keywords = missing_keywords[:8] if missing_keywords else keywords[:8]

    return {
        "ats_score": ats_score,
        "missing_skills": [skill.title() for skill in missing_keywords[:10]],
        "weak_bullet_points": weak_bullets[:5],
        "too_much_passive_language": passive_hits[:5],
        "improve_quantification": quantification_issues[:5],
        "recommended_keywords": [k.title() for k in recommended_keywords],
        "keywords_present": [k.title() for k in present_keywords[:10]],
        "extracted_text_characters": len(resume_text)
    }


def _build_auto_improvements(resume, analysis):
    updated_personal_info = dict(resume.personal_info or {})
    updated_skills = dict(resume.skills or {})

    technical_skills = updated_skills.get("technical")
    if not isinstance(technical_skills, list):
        technical_skills = []

    technical_lower = {str(skill).lower() for skill in technical_skills}
    for missing in analysis.get("missing_skills", [])[:6]:
        if missing.lower() not in technical_lower:
            technical_skills.append(missing)

    updated_skills["technical"] = technical_skills

    summary = updated_personal_info.get("summary", "")
    if isinstance(summary, str):
        keyword_tail = ", ".join(analysis.get("recommended_keywords", [])[:4])
        improvement_note = f" Skilled in {keyword_tail}." if keyword_tail else ""
        if improvement_note and improvement_note.lower() not in summary.lower():
            updated_personal_info["summary"] = (summary.strip() + improvement_note).strip()

    return {
        "personal_info": updated_personal_info,
        "skills": updated_skills
    }


def _safe_text(value):
    return str(value).strip() if value is not None else ""


def _resume_to_lines(resume):
    lines = []
    personal_info = resume.personal_info or {}
    skills = resume.skills or {}

    lines.append(_safe_text(resume.title) or "Resume")

    name = _safe_text(personal_info.get("name"))
    email = _safe_text(personal_info.get("email"))
    phone = _safe_text(personal_info.get("phone"))
    header_bits = [bit for bit in [name, email, phone] if bit]
    if header_bits:
        lines.append(" | ".join(header_bits))

    summary = _safe_text(personal_info.get("summary") or personal_info.get("raw_text"))
    if summary:
        lines.extend(["", "Summary"])
        lines.extend([f"- {line.strip()}" for line in summary.splitlines() if line.strip()])

    if isinstance(skills, dict):
        skill_rows = []
        for key, value in skills.items():
            if isinstance(value, list) and value:
                skill_rows.append(f"{key.title()}: {', '.join([_safe_text(v) for v in value if _safe_text(v)])}")
            elif isinstance(value, str) and value.strip():
                skill_rows.append(f"{key.title()}: {value.strip()}")

        if skill_rows:
            lines.extend(["", "Skills"])
            lines.extend([f"- {row}" for row in skill_rows])

    section_map = [
        ("Experience", resume.experiences),
        ("Education", resume.education),
        ("Projects", resume.projects),
        ("Certifications", resume.certifications)
    ]

    for heading, entries in section_map:
        if not isinstance(entries, list) or not entries:
            continue

        lines.extend(["", heading])
        for entry in entries:
            if isinstance(entry, str) and entry.strip():
                lines.append(f"- {entry.strip()}")
                continue

            if isinstance(entry, dict):
                values = [
                    _safe_text(v) for v in entry.values()
                    if isinstance(v, (str, int, float)) and _safe_text(v)
                ]
                if values:
                    lines.append(f"- {' | '.join(values)}")

    return lines


def _generate_preview_pdf(resume):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    page_width, page_height = letter
    left_margin = 40
    top_margin = 50
    line_height = 14
    y = page_height - top_margin

    lines = _resume_to_lines(resume)
    for raw_line in lines:
        text_line = _safe_text(raw_line)

        wrapped_chunks = [text_line[i:i + 110] for i in range(0, max(len(text_line), 1), 110)]
        if not wrapped_chunks:
            wrapped_chunks = [""]

        for chunk in wrapped_chunks:
            if y <= 40:
                pdf.showPage()
                y = page_height - top_margin

            pdf.drawString(left_margin, y, chunk)
            y -= line_height

    pdf.save()
    buffer.seek(0)
    return buffer


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

        if is_primary:
            _mark_resume_as_primary(user_id, resume.id)

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
        db.session.flush()

        if resume.is_primary:
            _mark_resume_as_primary(user_id, resume.id)

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

    if data.get('is_primary', False):
        _mark_resume_as_primary(user_id, resume.id)

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


@resume_bp.route("/resume/analyze/<int:resume_id>", methods=["POST"])
@jwt_required()
def analyze_resume(resume_id):
    """Analyze resume against a job description and optionally auto-apply improvements."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    data = request.get_json() or {}
    job_description = data.get("job_description", "")
    permission_mode = (data.get("permission_mode", "manual") or "manual").lower()
    apply_changes = bool(data.get("apply_changes", False))

    if not job_description.strip():
        return jsonify({
            "meta": {
                "success": False,
                "message": "Job description is required for resume analysis"
            }
        }), 400

    if permission_mode not in ["manual", "auto"]:
        return jsonify({
            "meta": {
                "success": False,
                "message": "permission_mode must be 'manual' or 'auto'"
            }
        }), 400

    if apply_changes and permission_mode != "auto":
        return jsonify({
            "meta": {
                "success": False,
                "message": "Automatic changes require permission_mode='auto'"
            }
        }), 400

    analysis = _analyze_resume_content(resume, job_description)
    suggestions = _build_auto_improvements(resume, analysis)

    updated = False
    if apply_changes and permission_mode == "auto":
        resume.personal_info = suggestions["personal_info"]
        resume.skills = suggestions["skills"]
        resume.version += 1
        resume.last_optimized_at = datetime.datetime.utcnow()
        resume.optimization_count += 1
        resume.ai_provider_used = "rule-based-analyzer"
        db.session.commit()
        updated = True

    return jsonify({
        "data": {
            "resume_id": resume.id,
            "analysis": analysis,
            "permission_mode": permission_mode,
            "applied_changes": updated,
            "suggested_updates": suggestions,
            "resume": resume.to_dict() if updated else None
        },
        "meta": {
            "success": True,
            "message": "Resume analyzed successfully"
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
    _, (payload, status_code) = _delete_resume_by_id(user_id, resume_id)
    return jsonify(payload), status_code


@resume_bp.route("/resume/deleteResume/<int:resume_id>", methods=["DELETE"])
@jwt_required()
def delete_resume_by_id(resume_id):
    """Delete resume by ID (compatibility endpoint)."""
    user_id = int(get_jwt_identity())
    _, (payload, status_code) = _delete_resume_by_id(user_id, resume_id)
    return jsonify(payload), status_code


@resume_bp.route("/resume/set-primary/<int:resume_id>", methods=["PUT"])
@jwt_required()
def set_primary_resume(resume_id):
    """Mark a resume as the primary one for the current user."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    _mark_resume_as_primary(user_id, resume.id)
    resume.is_primary = True
    db.session.commit()

    return jsonify({
        "data": {
            "resume": resume.to_dict()
        },
        "meta": {
            "success": True,
            "message": "Primary resume updated successfully"
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


@resume_bp.route("/resume/preview/<int:resume_id>", methods=["GET"])
@jwt_required()
def preview_resume_pdf(resume_id):
    """Return a PDF preview; generates one from JSON data when no uploaded file exists."""
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()

    if not resume:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Resume not found or unauthorized"
            }
        }), 404

    # For uploaded PDF files, stream original file for best fidelity.
    if resume.file_path and resume.file_type == 'pdf' and os.path.exists(resume.file_path):
        return send_file(
            resume.file_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=resume.original_filename or f"resume_{resume.id}.pdf"
        )

    generated_pdf = _generate_preview_pdf(resume)
    return send_file(
        generated_pdf,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f"resume_preview_{resume.id}.pdf"
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

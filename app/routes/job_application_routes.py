from app.extensions import db
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.job_application import JobApplication
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import re

job_application_bp = Blueprint("job_application", __name__)


SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

INDIA_LOCATION_OPTIONS = {
    "Bengaluru", "Hyderabad", "Chennai", "Pune", "Mumbai", "Delhi NCR",
    "Kolkata", "Ahmedabad", "Noida", "Gurugram", "Kochi", "Coimbatore",
    "Jaipur", "Indore", "Visakhapatnam", "Remote India"
}


def _safe_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_provider_jobs(raw_jobs, provider, limit):
    normalized = []
    seen = set()

    for item in raw_jobs:
        url = _safe_text(item.get("url"))
        title = _safe_text(item.get("title"))
        if not url or not title:
            continue

        if url in seen:
            continue
        seen.add(url)

        normalized.append({
            "provider": provider,
            "title": title,
            "company": _safe_text(item.get("company")) or "Not specified",
            "location": _safe_text(item.get("location")) or "Not specified",
            "experience": _safe_text(item.get("experience")) or "",
            "posted": _safe_text(item.get("posted")) or "",
            "url": url
        })

        if len(normalized) >= limit:
            break

    return normalized


def _search_naukri_jobs(query, location, limit):
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("Missing dependencies: install requests and beautifulsoup4") from exc

    encoded_query = quote_plus(query)
    encoded_location = quote_plus(location)
    search_url = f"https://www.naukri.com/{encoded_query}-jobs?k={encoded_query}&l={encoded_location}"

    response = requests.get(search_url, headers=SCRAPE_HEADERS, timeout=12)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    cards = soup.select("article.jobTuple")
    for card in cards:
        title_node = card.select_one("a.title")
        company_node = card.select_one("a.comp-name")
        location_node = card.select_one("span.locWdth")
        experience_node = card.select_one("span.expwdth")

        jobs.append({
            "title": _safe_text(title_node.get_text()) if title_node else "",
            "company": _safe_text(company_node.get_text()) if company_node else "",
            "location": _safe_text(location_node.get_text()) if location_node else "",
            "experience": _safe_text(experience_node.get_text()) if experience_node else "",
            "url": title_node.get("href") if title_node else ""
        })

    if not jobs:
        for link in soup.select("a"):
            href = link.get("href") or ""
            text = _safe_text(link.get_text())
            if "/job-listings-" in href and text:
                jobs.append({
                    "title": text,
                    "company": "",
                    "location": "",
                    "experience": "",
                    "url": href
                })
            if len(jobs) >= limit:
                break

    return _normalize_provider_jobs(jobs, "Naukri", limit)


def _search_linkedin_jobs(query, location, limit):
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("Missing dependencies: install requests and beautifulsoup4") from exc

    search_url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(query)}&location={quote_plus(location)}"
    )

    response = requests.get(search_url, headers=SCRAPE_HEADERS, timeout=12)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    cards = soup.select("div.base-card")
    for card in cards:
        title_node = card.select_one("h3.base-search-card__title")
        company_node = card.select_one("h4.base-search-card__subtitle a")
        location_node = card.select_one("span.job-search-card__location")
        posted_node = card.select_one("time")
        link_node = card.select_one("a.base-card__full-link")

        jobs.append({
            "title": _safe_text(title_node.get_text()) if title_node else "",
            "company": _safe_text(company_node.get_text()) if company_node else "",
            "location": _safe_text(location_node.get_text()) if location_node else "",
            "posted": _safe_text(posted_node.get_text()) if posted_node else "",
            "url": link_node.get("href") if link_node else ""
        })

    if not jobs:
        for link in soup.select("a"):
            href = link.get("href") or ""
            text = _safe_text(link.get_text())
            if "/jobs/view/" in href and text:
                jobs.append({
                    "title": text,
                    "company": "",
                    "location": "",
                    "posted": "",
                    "url": href
                })
            if len(jobs) >= limit:
                break

    return _normalize_provider_jobs(jobs, "LinkedIn", limit)

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


# JOB ANALYTICS
@job_application_bp.route("/jobs/analytics", methods=["GET"])
@jwt_required()
def get_job_analytics():
    user_id = int(get_jwt_identity())
    jobs = JobApplication.query.filter_by(user_id=user_id).all()

    status_labels = ["applied", "interview", "waiting for response", "rejected", "offer", "other"]
    status_counts = {label: 0 for label in status_labels}

    now = datetime.utcnow()
    last_30_cutoff = now - timedelta(days=30)
    recent_30_days = 0

    # Prepare month buckets for last 6 months (oldest -> newest)
    month_buckets = []
    for offset in range(5, -1, -1):
        target_month = now.month - offset
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_buckets.append((target_year, target_month))

    monthly_counts = {f"{year}-{month:02d}": 0 for year, month in month_buckets}
    company_counts = {}

    for job in jobs:
        normalized_status = (job.status or "").strip().lower()
        if normalized_status not in status_counts:
            normalized_status = "other"
        status_counts[normalized_status] += 1

        if job.applied_at and job.applied_at >= last_30_cutoff:
            recent_30_days += 1

        if job.applied_at:
            month_key = f"{job.applied_at.year}-{job.applied_at.month:02d}"
            if month_key in monthly_counts:
                monthly_counts[month_key] += 1

        company_key = (job.company or "Unknown").strip() or "Unknown"
        company_counts[company_key] = company_counts.get(company_key, 0) + 1

    total_jobs = len(jobs)
    interviews = status_counts.get("interview", 0)
    offers = status_counts.get("offer", 0)
    rejected = status_counts.get("rejected", 0)

    monthly_trend = []
    for year, month in month_buckets:
        key = f"{year}-{month:02d}"
        label = datetime(year, month, 1).strftime("%b %Y")
        monthly_trend.append({
            "key": key,
            "label": label,
            "count": monthly_counts[key]
        })

    top_companies = sorted(
        [{"company": company, "count": count} for company, count in company_counts.items()],
        key=lambda item: item["count"],
        reverse=True
    )[:5]

    return jsonify({
        "data": {
            "summary": {
                "total_jobs": total_jobs,
                "recent_30_days": recent_30_days,
                "interviews": interviews,
                "offers": offers,
                "rejected": rejected,
                "interview_rate": round((interviews / total_jobs) * 100, 2) if total_jobs else 0,
                "offer_rate": round((offers / total_jobs) * 100, 2) if total_jobs else 0
            },
            "status_breakdown": [
                {"status": status, "count": count}
                for status, count in status_counts.items()
            ],
            "monthly_trend": monthly_trend,
            "top_companies": top_companies
        },
        "meta": {
            "success": True,
            "message": "Job analytics retrieved successfully"
        }
    }), 200


@job_application_bp.route("/jobs/search-external", methods=["GET"])
@jwt_required()
def search_external_jobs():
    role = (request.args.get("role") or "").strip()
    company = (request.args.get("company") or "").strip()
    skills = (request.args.get("skills") or "").strip()
    keywords = (request.args.get("keywords") or "").strip()
    fallback_query = (request.args.get("q") or "").strip()

    query_parts = [part for part in [role, company, skills, keywords] if part]
    query = " ".join(query_parts).strip() or fallback_query

    raw_locations = (request.args.get("locations") or "").strip()
    requested_locations = [
        _safe_text(loc) for loc in raw_locations.split(",")
        if _safe_text(loc)
    ]

    if not requested_locations:
        requested_locations = ["Bengaluru"]

    valid_locations = [loc for loc in requested_locations if loc in INDIA_LOCATION_OPTIONS]

    if not valid_locations:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Please select valid India locations"
            }
        }), 400

    # Cap number of locations to keep response time manageable.
    valid_locations = valid_locations[:6]
    limit = min(max(int(request.args.get("limit", 20)), 1), 50)

    if len(query) < 2:
        return jsonify({
            "meta": {
                "success": False,
                "message": "Search query must be at least 2 characters"
            }
        }), 400

    provider_results = {
        "naukri": {
            "jobs": [],
            "error": ""
        },
        "linkedin": {
            "jobs": [],
            "error": ""
        }
    }

    naukri_errors = []
    linkedin_errors = []
    naukri_jobs = []
    linkedin_jobs = []

    per_location_limit = max(5, min(limit, 20))

    for location in valid_locations:
        try:
            naukri_jobs.extend(_search_naukri_jobs(query, location, per_location_limit))
        except Exception as exc:
            naukri_errors.append(f"{location}: {str(exc)}")

        try:
            linkedin_jobs.extend(_search_linkedin_jobs(query, location, per_location_limit))
        except Exception as exc:
            linkedin_errors.append(f"{location}: {str(exc)}")

    provider_results["naukri"]["jobs"] = _normalize_provider_jobs(naukri_jobs, "Naukri", limit)
    provider_results["linkedin"]["jobs"] = _normalize_provider_jobs(linkedin_jobs, "LinkedIn", limit)
    provider_results["naukri"]["error"] = "; ".join(naukri_errors)
    provider_results["linkedin"]["error"] = "; ".join(linkedin_errors)

    combined = _normalize_provider_jobs(
        provider_results["naukri"]["jobs"] + provider_results["linkedin"]["jobs"],
        "Mixed",
        limit * 2
    )

    return jsonify({
        "data": {
            "query": query,
            "filters": {
                "role": role,
                "company": company,
                "skills": skills,
                "keywords": keywords,
                "locations": valid_locations
            },
            "providers": provider_results,
            "jobs": combined,
            "total": len(combined)
        },
        "meta": {
            "success": True,
            "message": "External job search completed"
        }
    }), 200
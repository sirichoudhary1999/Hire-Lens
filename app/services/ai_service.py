import json
import time
import re
from abc import ABC, abstractmethod
from flask import current_app
from openai import OpenAI
from anthropic import Anthropic

class AIResumeOptimizer(ABC):
    """Base class for AI resume optimization."""

    @abstractmethod
    def optimize_resume(self, resume_data: dict, job_description: str, job_title: str = None) -> dict:
        """
        Optimize resume based on job description.
        Returns: dict with keys: optimized_resume, processing_time_ms, tokens_used, model_used, optimization_notes
        """
        pass

    def _build_prompt(self, resume_data: dict, job_description: str, job_title: str = None) -> str:
        """Build optimization prompt."""
        job_title_str = f" for the role: {job_title}" if job_title else ""

        prompt = f"""You are a professional resume optimization expert. Your task is to restructure and enhance a resume to align with a specific job description{job_title_str}.

**Job Description:**
{job_description}

**Current Resume Data:**
{json.dumps(resume_data, indent=2)}

**Instructions:**
1. Analyze the job description to identify key skills, requirements, and keywords
2. Restructure the resume to emphasize relevant experience and skills
3. Rewrite bullet points to use action verbs and quantifiable achievements
4. Ensure ATS (Applicant Tracking System) compatibility by including relevant keywords
5. Maintain truthfulness - do not add false information or fabricate experiences
6. Keep the resume concise and impactful
7. Prioritize the most relevant experiences and skills

**Output Format:**
Respond with ONLY a valid JSON object matching this EXACT structure (no additional text before or after):
{{
  "personal_info": {{"name": "...", "email": "...", "phone": "...", "location": "...", "linkedin": "...", "summary": "..."}},
  "experiences": [{{"company": "...", "role": "...", "start_date": "...", "end_date": "...", "bullets": ["..."]}}],
  "education": [{{"institution": "...", "degree": "...", "field": "...", "start_date": "...", "end_date": "...", "gpa": "..."}}],
  "skills": {{"technical": ["..."], "soft": ["..."], "languages": ["..."], "tools": ["..."]}},
  "projects": [{{"name": "...", "description": "...", "technologies": ["..."], "url": "..."}}],
  "certifications": [{{"name": "...", "issuer": "...", "date": "...", "url": "..."}}],
  "optimization_notes": "Brief summary of key changes made (2-3 sentences)"
}}

Ensure the JSON is properly formatted and valid."""
        return prompt

    def _parse_ai_response(self, response_text: str) -> dict:
        """Parse AI response to extract JSON."""
        try:
            # Try to find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start:end]
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")


class OpenAIResumeOptimizer(AIResumeOptimizer):
    """OpenAI GPT implementation for resume optimization."""

    def __init__(self):
        api_key = current_app.config.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = OpenAI(api_key=api_key)
        self.model = current_app.config.get('OPENAI_MODEL', 'gpt-4-turbo-preview')

    def optimize_resume(self, resume_data: dict, job_description: str, job_title: str = None) -> dict:
        """Optimize resume using OpenAI."""
        start_time = time.time()

        prompt = self._build_prompt(resume_data, job_description, job_title)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional resume optimization expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                timeout=current_app.config.get('AI_TIMEOUT_SECONDS', 60)
            )

            response_text = response.choices[0].message.content
            optimized_resume = self._parse_ai_response(response_text)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "optimized_resume": optimized_resume,
                "processing_time_ms": processing_time_ms,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None,
                "model_used": self.model,
                "optimization_notes": optimized_resume.get("optimization_notes", "")
            }

        except Exception as e:
            raise Exception(f"OpenAI optimization failed: {str(e)}")


class AnthropicResumeOptimizer(AIResumeOptimizer):
    """Anthropic Claude implementation for resume optimization."""

    def __init__(self):
        api_key = current_app.config.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        self.client = Anthropic(api_key=api_key)
        self.model = current_app.config.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

    def optimize_resume(self, resume_data: dict, job_description: str, job_title: str = None) -> dict:
        """Optimize resume using Anthropic Claude."""
        start_time = time.time()

        prompt = self._build_prompt(resume_data, job_description, job_title)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=current_app.config.get('AI_TIMEOUT_SECONDS', 60)
            )

            response_text = response.content[0].text
            optimized_resume = self._parse_ai_response(response_text)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "optimized_resume": optimized_resume,
                "processing_time_ms": processing_time_ms,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else None,
                "model_used": self.model,
                "optimization_notes": optimized_resume.get("optimization_notes", "")
            }

        except Exception as e:
            raise Exception(f"Anthropic optimization failed: {str(e)}")


class DemoResumeOptimizer(AIResumeOptimizer):
    """Demo/Mock AI optimizer - works without API keys for testing."""

    def optimize_resume(self, resume_data: dict, job_description: str, job_title: str = None) -> dict:
        """Simulate AI optimization without calling external APIs."""
        start_time = time.time()

        # Simulate processing time (1-2 seconds)
        time.sleep(1.5)

        # Extract keywords from job description
        keywords = self._extract_keywords(job_description)

        # Create optimized resume by enhancing the original
        optimized_resume = self._enhance_resume(resume_data, keywords, job_title)

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "optimized_resume": optimized_resume,
            "processing_time_ms": processing_time_ms,
            "tokens_used": None,
            "model_used": "demo-optimizer-v1",
            "optimization_notes": f"Demo mode: Enhanced resume with {len(keywords)} keywords from job description. Added action verbs and quantifiable achievements. This is a simulated optimization - use OpenAI or Anthropic for real AI optimization."
        }

    def _extract_keywords(self, job_description: str) -> list:
        """Extract important keywords from job description."""
        # Simple keyword extraction (would be much better with real AI)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being'}
        words = re.findall(r'\b[a-zA-Z]{4,}\b', job_description.lower())
        keywords = [w for w in words if w not in common_words]
        # Return unique keywords, limited to top 10
        return list(set(keywords))[:10]

    def _enhance_resume(self, resume_data: dict, keywords: list, job_title: str = None) -> dict:
        """Enhance resume with keywords and improvements."""
        optimized = resume_data.copy()

        # Handle raw text parsing (for file uploads)
        if 'personal_info' in optimized and isinstance(optimized['personal_info'], dict):
            if 'raw_text' in optimized['personal_info'] and len(optimized['personal_info']) == 1:
                # This is a raw text resume that needs parsing
                raw_text = optimized['personal_info']['raw_text']
                optimized = self._parse_raw_text(raw_text)
                # Add keywords to the parsed data
                if 'skills' in optimized and 'technical' in optimized['skills']:
                    existing_skills = [s.lower() for s in optimized['skills']['technical']]
                    new_skills = [k for k in keywords[:5] if k.lower() not in existing_skills]
                    optimized['skills']['technical'].extend(new_skills)
                return optimized

        # Original enhancement logic for structured data
        # Enhance personal info summary
        if 'personal_info' in optimized and isinstance(optimized['personal_info'], dict):
            current_summary = optimized['personal_info'].get('summary', '')
            if current_summary:
                # Add some keywords to summary
                keyword_str = ', '.join(keywords[:3])
                optimized['personal_info']['summary'] = f"{current_summary} Experienced with {keyword_str} and related technologies."
            elif job_title:
                optimized['personal_info']['summary'] = f"Professional seeking {job_title} role with expertise in {', '.join(keywords[:3])}."

        # Enhance skills by adding job description keywords
        if 'skills' in optimized and isinstance(optimized['skills'], dict):
            if 'technical' not in optimized['skills'] or not optimized['skills']['technical']:
                optimized['skills']['technical'] = []
            # Add keywords as skills (if not already there)
            existing_skills = [s.lower() for s in optimized['skills']['technical']]
            new_skills = [k for k in keywords[:5] if k.lower() not in existing_skills]
            optimized['skills']['technical'].extend(new_skills)

        # Add optimization note to each experience (if exists)
        if 'experiences' in optimized and isinstance(optimized['experiences'], list):
            action_verbs = ['Led', 'Developed', 'Implemented', 'Designed', 'Managed', 'Improved', 'Achieved', 'Delivered']
            for i, exp in enumerate(optimized['experiences']):
                if isinstance(exp, dict) and 'bullets' in exp and isinstance(exp['bullets'], list):
                    # Enhance first bullet point with action verb
                    if exp['bullets'] and len(exp['bullets']) > 0:
                        first_bullet = exp['bullets'][0]
                        if not any(first_bullet.startswith(verb) for verb in action_verbs):
                            verb = action_verbs[i % len(action_verbs)]
                            exp['bullets'][0] = f"{verb} {first_bullet.lower()}"

        # Ensure all required fields exist
        if 'education' not in optimized:
            optimized['education'] = []
        if 'projects' not in optimized:
            optimized['projects'] = []
        if 'certifications' not in optimized:
            optimized['certifications'] = []

        return optimized

    def _parse_raw_text(self, raw_text: str) -> dict:
        """Simple parsing of raw resume text (demo mode only)."""
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

        # Try to extract basic information using simple patterns
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', raw_text)
        phone_match = re.search(r'\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', raw_text)

        # Assume first non-empty line is name
        name = lines[0] if lines else "Unknown"

        # Extract skills (look for common skill keywords)
        skill_keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker',
                         'typescript', 'angular', 'vue', 'mongodb', 'postgresql', 'git', 'kubernetes',
                         'html', 'css', 'api', 'rest', 'graphql', 'agile', 'scrum', 'ci/cd']

        found_skills = []
        text_lower = raw_text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())

        # Look for education keywords
        education_keywords = ['university', 'college', 'bachelor', 'master', 'phd', 'degree', 'b.s.', 'm.s.', 'b.a.', 'm.a.']
        has_education = any(keyword in text_lower for keyword in education_keywords)

        return {
            "personal_info": {
                "name": name,
                "email": email_match.group(0) if email_match else "",
                "phone": phone_match.group(0) if phone_match else "",
                "location": "",
                "linkedin": "",
                "summary": f"Extracted from uploaded resume. Contains {len(lines)} lines of text."
            },
            "experiences": [],
            "education": [{"institution": "See extracted text", "degree": "", "field": "", "start_date": "", "end_date": "", "gpa": ""}] if has_education else [],
            "skills": {
                "technical": found_skills if found_skills else ["Skill extraction available with OpenAI/Anthropic"],
                "soft": [],
                "languages": [],
                "tools": []
            },
            "projects": [],
            "certifications": []
        }


def get_optimizer(provider: str) -> AIResumeOptimizer:
    """
    Factory function to get the appropriate AI optimizer.
    Args:
        provider: 'openai', 'anthropic', or 'demo'
    Returns:
        AIResumeOptimizer instance
    """
    if provider.lower() == 'openai':
        return OpenAIResumeOptimizer()
    elif provider.lower() == 'anthropic':
        return AnthropicResumeOptimizer()
    elif provider.lower() == 'demo':
        return DemoResumeOptimizer()
    else:
        raise ValueError(f"Unknown AI provider: {provider}. Supported providers: openai, anthropic, demo")

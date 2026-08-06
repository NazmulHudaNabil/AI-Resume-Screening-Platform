"""
labeled_test_set.py — Phase 7 Labeled Test Data
=================================================

Contains 3 realistic job descriptions, each with 6 candidates.
Every candidate has a hand-crafted human ranking (1 = best fit)
and a simulated semantic score.

This data is the ground truth for the evaluation harness.
No database, no LLM, no API calls needed — everything is inline.

Structure:
  TEST_SCENARIOS = [
      {
          "job": { title, description, required_skills, ... },
          "candidates": [
              {
                  "id": "jd1_candidate_1",
                  "profile": { name, skills, experience_years, ... },
                  "human_rank": 1,                    ← gold label
                  "simulated_semantic_score": 0.92,   ← approximates embedding similarity
                  "expected_skill_score_range": (0.8, 1.0),  ← for extraction accuracy check
              },
              ...
          ]
      },
      ...
  ]
"""


# ─────────────────────────────────────────────────────────────────────
# TEST SCENARIO 1: Senior Backend Python Developer
# ─────────────────────────────────────────────────────────────────────

_JD1 = {
    "title": "Senior Backend Python Developer",
    "description": (
        "We are looking for a Senior Backend Python Developer to join our "
        "engineering team. You will design and build RESTful APIs, work with "
        "PostgreSQL databases, and develop microservices using FastAPI. "
        "Experience with containerization and caching is a plus. "
        "You will collaborate with frontend engineers and DevOps to ship "
        "features to production on a weekly cadence."
    ),
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "REST APIs", "Git"],
    "nice_to_have_skills": ["Docker", "Redis", "AWS"],
    "min_experience_years": 4.0,
}

_JD1_CANDIDATES = [
    {
        "id": "jd1_candidate_1",
        "profile": {
            "name": "Alice Chen",
            "skills": [
                "Python", "FastAPI", "PostgreSQL", "REST APIs", "Git",
                "Docker", "Redis", "SQLAlchemy", "Pytest", "Linux",
            ],
            "experience_years": 5.5,
            "education": ["B.Sc. Computer Science — Stanford University"],
            "roles": ["Senior Backend Developer", "Software Engineer"],
            "certifications": ["AWS Certified Developer – Associate"],
        },
        "human_rank": 1,
        "simulated_semantic_score": 0.94,
        "expected_skill_score_range": (0.85, 1.0),
    },
    {
        "id": "jd1_candidate_2",
        "profile": {
            "name": "Bob Martinez",
            "skills": [
                "Python", "Django", "PostgreSQL", "REST APIs", "Git",
                "Docker", "Celery", "Linux",
            ],
            "experience_years": 6.0,
            "education": ["M.Sc. Software Engineering — MIT"],
            "roles": ["Backend Developer", "Tech Lead"],
            "certifications": [],
        },
        "human_rank": 2,
        "simulated_semantic_score": 0.88,
        "expected_skill_score_range": (0.55, 0.85),
    },
    {
        "id": "jd1_candidate_3",
        "profile": {
            "name": "Charlie Kim",
            "skills": [
                "Python", "FastAPI", "Git", "SQLAlchemy",
                "Pytest", "GitHub Actions",
            ],
            "experience_years": 3.0,
            "education": ["B.Sc. Computer Engineering — Georgia Tech"],
            "roles": ["Junior Backend Developer", "Software Engineer Intern"],
            "certifications": [],
        },
        "human_rank": 3,
        "simulated_semantic_score": 0.82,
        "expected_skill_score_range": (0.40, 0.65),
    },
    {
        "id": "jd1_candidate_4",
        "profile": {
            "name": "Diana Patel",
            "skills": [
                "Python", "Flask", "MySQL", "REST APIs", "Git",
                "Heroku",
            ],
            "experience_years": 4.0,
            "education": ["B.Tech Information Technology — IIT Bombay"],
            "roles": ["Full-Stack Developer", "Backend Developer"],
            "certifications": [],
        },
        "human_rank": 4,
        "simulated_semantic_score": 0.76,
        "expected_skill_score_range": (0.35, 0.60),
    },
    {
        "id": "jd1_candidate_5",
        "profile": {
            "name": "Eve Johnson",
            "skills": [
                "JavaScript", "Node.js", "Express.js", "MongoDB",
                "React", "Git", "Docker",
            ],
            "experience_years": 7.0,
            "education": ["B.A. Computer Science — UC Berkeley"],
            "roles": ["Full-Stack Engineer", "Senior Node.js Developer"],
            "certifications": ["MongoDB Certified Developer"],
        },
        "human_rank": 5,
        "simulated_semantic_score": 0.55,
        "expected_skill_score_range": (0.10, 0.35),
    },
    {
        "id": "jd1_candidate_6",
        "profile": {
            "name": "Frank Lee",
            "skills": [
                "Python", "Pandas", "Jupyter",
            ],
            "experience_years": 1.0,
            "education": ["B.Sc. Data Science — University of Michigan"],
            "roles": ["Data Analyst Intern"],
            "certifications": [],
        },
        "human_rank": 6,
        "simulated_semantic_score": 0.42,
        "expected_skill_score_range": (0.05, 0.30),
    },
]


# ─────────────────────────────────────────────────────────────────────
# TEST SCENARIO 2: Frontend React Developer
# ─────────────────────────────────────────────────────────────────────

_JD2 = {
    "title": "Frontend React Developer",
    "description": (
        "We need a Frontend React Developer to build modern, responsive "
        "user interfaces. You will work closely with designers to translate "
        "Figma mockups into pixel-perfect React components. Strong TypeScript "
        "skills are required. Experience with server-side rendering and "
        "testing frameworks is valued."
    ),
    "required_skills": ["React", "TypeScript", "CSS", "HTML", "Git"],
    "nice_to_have_skills": ["Next.js", "Jest", "Figma"],
    "min_experience_years": 2.0,
}

_JD2_CANDIDATES = [
    {
        "id": "jd2_candidate_1",
        "profile": {
            "name": "Grace Wang",
            "skills": [
                "React", "TypeScript", "CSS", "HTML", "Git",
                "Next.js", "Jest", "Tailwind CSS", "Storybook",
            ],
            "experience_years": 3.5,
            "education": ["B.Sc. Computer Science — Carnegie Mellon"],
            "roles": ["Frontend Developer", "UI Engineer"],
            "certifications": [],
        },
        "human_rank": 1,
        "simulated_semantic_score": 0.95,
        "expected_skill_score_range": (0.85, 1.0),
    },
    {
        "id": "jd2_candidate_2",
        "profile": {
            "name": "Henry Adams",
            "skills": [
                "React", "JavaScript", "CSS", "HTML", "Git",
                "Sass", "Webpack", "Figma",
            ],
            "experience_years": 4.0,
            "education": ["B.A. Design & Computer Science — NYU"],
            "roles": ["Senior Frontend Developer", "UI/UX Developer"],
            "certifications": [],
        },
        "human_rank": 2,
        "simulated_semantic_score": 0.87,
        "expected_skill_score_range": (0.55, 0.80),
    },
    {
        "id": "jd2_candidate_3",
        "profile": {
            "name": "Ivy Thompson",
            "skills": [
                "React", "TypeScript", "Git", "Redux",
                "Material UI", "REST APIs",
            ],
            "experience_years": 2.0,
            "education": ["B.Sc. Software Engineering — Waterloo"],
            "roles": ["Frontend Developer"],
            "certifications": [],
        },
        "human_rank": 3,
        "simulated_semantic_score": 0.80,
        "expected_skill_score_range": (0.35, 0.60),
    },
    {
        "id": "jd2_candidate_4",
        "profile": {
            "name": "Jack Wilson",
            "skills": [
                "Vue.js", "TypeScript", "CSS", "HTML", "Git",
                "Nuxt.js", "Vuex",
            ],
            "experience_years": 3.0,
            "education": ["Bootcamp — Le Wagon"],
            "roles": ["Frontend Developer"],
            "certifications": [],
        },
        "human_rank": 4,
        "simulated_semantic_score": 0.68,
        "expected_skill_score_range": (0.35, 0.65),
    },
    {
        "id": "jd2_candidate_5",
        "profile": {
            "name": "Kate Brown",
            "skills": [
                "Angular", "JavaScript", "CSS", "HTML",
                "RxJS", "NgRx",
            ],
            "experience_years": 5.0,
            "education": ["B.Sc. Computer Science — University of Toronto"],
            "roles": ["Senior Angular Developer", "Frontend Lead"],
            "certifications": [],
        },
        "human_rank": 5,
        "simulated_semantic_score": 0.58,
        "expected_skill_score_range": (0.20, 0.50),
    },
    {
        "id": "jd2_candidate_6",
        "profile": {
            "name": "Liam Davis",
            "skills": [
                "Python", "Django", "PostgreSQL", "Docker",
                "Linux", "Bash",
            ],
            "experience_years": 4.0,
            "education": ["B.Sc. Information Systems — UC San Diego"],
            "roles": ["Backend Developer"],
            "certifications": [],
        },
        "human_rank": 6,
        "simulated_semantic_score": 0.32,
        "expected_skill_score_range": (0.0, 0.20),
    },
]


# ─────────────────────────────────────────────────────────────────────
# TEST SCENARIO 3: DevOps / Cloud Engineer
# ─────────────────────────────────────────────────────────────────────

_JD3 = {
    "title": "DevOps / Cloud Engineer",
    "description": (
        "We are hiring a DevOps / Cloud Engineer to manage our AWS "
        "infrastructure, build CI/CD pipelines, and maintain Kubernetes "
        "clusters. You will automate infrastructure provisioning with "
        "Terraform and ensure high availability of our production systems. "
        "Scripting ability and monitoring experience are a plus."
    ),
    "required_skills": [
        "AWS", "Docker", "Kubernetes", "CI/CD", "Linux", "Terraform",
    ],
    "nice_to_have_skills": ["Python scripting", "Prometheus", "Ansible"],
    "min_experience_years": 3.0,
}

_JD3_CANDIDATES = [
    {
        "id": "jd3_candidate_1",
        "profile": {
            "name": "Maya Singh",
            "skills": [
                "AWS", "Docker", "Kubernetes", "CI/CD", "Linux",
                "Terraform", "Python", "Prometheus", "Grafana",
                "Jenkins", "Ansible",
            ],
            "experience_years": 5.0,
            "education": ["M.Sc. Cloud Computing — Arizona State University"],
            "roles": ["Senior DevOps Engineer", "Cloud Architect"],
            "certifications": [
                "AWS Solutions Architect – Professional",
                "Certified Kubernetes Administrator",
            ],
        },
        "human_rank": 1,
        "simulated_semantic_score": 0.96,
        "expected_skill_score_range": (0.90, 1.0),
    },
    {
        "id": "jd3_candidate_2",
        "profile": {
            "name": "Noah Garcia",
            "skills": [
                "AWS", "Docker", "Kubernetes", "Jenkins", "Linux",
                "CloudFormation", "Bash", "Git",
            ],
            "experience_years": 4.0,
            "education": ["B.Sc. Computer Science — UCLA"],
            "roles": ["DevOps Engineer", "Site Reliability Engineer"],
            "certifications": ["AWS Certified DevOps Engineer"],
        },
        "human_rank": 2,
        "simulated_semantic_score": 0.85,
        "expected_skill_score_range": (0.45, 0.70),
    },
    {
        "id": "jd3_candidate_3",
        "profile": {
            "name": "Olivia Chen",
            "skills": [
                "Azure", "Docker", "Kubernetes", "Terraform",
                "CI/CD", "Linux", "Python",
            ],
            "experience_years": 3.0,
            "education": ["B.Sc. Information Technology — University of Melbourne"],
            "roles": ["Cloud Engineer", "Infrastructure Engineer"],
            "certifications": ["Azure Administrator Associate"],
        },
        "human_rank": 3,
        "simulated_semantic_score": 0.78,
        "expected_skill_score_range": (0.50, 0.75),
    },
    {
        "id": "jd3_candidate_4",
        "profile": {
            "name": "Peter Jones",
            "skills": [
                "AWS", "Docker", "Linux", "Bash", "Git",
                "CloudWatch",
            ],
            "experience_years": 2.0,
            "education": ["A.S. Network Administration — Community College"],
            "roles": ["Junior DevOps Engineer", "System Administrator"],
            "certifications": ["AWS Certified Cloud Practitioner"],
        },
        "human_rank": 4,
        "simulated_semantic_score": 0.65,
        "expected_skill_score_range": (0.20, 0.45),
    },
    {
        "id": "jd3_candidate_5",
        "profile": {
            "name": "Quinn Taylor",
            "skills": [
                "Linux", "Bash", "Nagios", "VMware",
                "Networking", "Docker",
            ],
            "experience_years": 6.0,
            "education": ["B.Sc. Electrical Engineering — Texas A&M"],
            "roles": ["Senior System Administrator", "IT Operations Manager"],
            "certifications": ["CompTIA Linux+", "RHCE"],
        },
        "human_rank": 5,
        "simulated_semantic_score": 0.52,
        "expected_skill_score_range": (0.15, 0.40),
    },
    {
        "id": "jd3_candidate_6",
        "profile": {
            "name": "Rachel White",
            "skills": [
                "Java", "Spring Boot", "MySQL", "Docker",
                "Maven", "JUnit",
            ],
            "experience_years": 3.0,
            "education": ["B.Sc. Computer Science — University of British Columbia"],
            "roles": ["Java Developer", "Software Engineer"],
            "certifications": [],
        },
        "human_rank": 6,
        "simulated_semantic_score": 0.38,
        "expected_skill_score_range": (0.05, 0.25),
    },
]


# ─────────────────────────────────────────────────────────────────────
# PUBLIC API — the eval script imports this
# ─────────────────────────────────────────────────────────────────────

TEST_SCENARIOS = [
    {"job": _JD1, "candidates": _JD1_CANDIDATES},
    {"job": _JD2, "candidates": _JD2_CANDIDATES},
    {"job": _JD3, "candidates": _JD3_CANDIDATES},
]

# Quick stats
TOTAL_SCENARIOS = len(TEST_SCENARIOS)
TOTAL_CANDIDATES = sum(len(s["candidates"]) for s in TEST_SCENARIOS)

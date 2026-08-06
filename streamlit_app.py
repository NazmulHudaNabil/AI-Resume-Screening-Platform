import streamlit as st
import requests
import time
import json

API_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="AI Resume Screener", layout="wide")

st.title("AI Resume Screening Platform")

# --- Authentication ---
if "access_token" not in st.session_state:
    st.session_state.access_token = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

def check_unauthorized(resp):
    if resp.status_code == 401:
        st.session_state.access_token = None
        st.error("Session expired or invalid token. Please log in again.")
        time.sleep(1.5)
        st.rerun()

if st.session_state.access_token is None:
    # Inject custom CSS for a premium login card look
    st.markdown("""
    <style>
        /* Hide sidebar while logged out */
        [data-testid="stSidebar"] {
            display: none;
        }
        
        /* Premium Form Styling */
        [data-testid="stForm"] {
            border-radius: 20px;
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.15);
            border: 1px solid rgba(200, 200, 200, 0.2);
            padding: 40px 30px;
            background: linear-gradient(to bottom right, #ffffff, #f8f9fa);
        }
        
        /* Premium Button Styling */
        [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%);
            color: #111 !important;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            transition: all 0.3s ease;
        }
        
        [data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 201, 255, 0.3);
            border: none;
        }
        
        /* Dark mode compatibility */
        @media (prefers-color-scheme: dark) {
            [data-testid="stForm"] {
                background: linear-gradient(to bottom right, #1a1a1a, #2d2d2d);
                border: 1px solid #444;
            }
        }
        
        /* Center text */
        .login-header {
            text-align: center;
            font-family: 'Inter', sans-serif;
            margin-bottom: -10px;
        }
        .login-subtitle {
            text-align: center;
            color: #888;
            font-size: 14px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<h2 class='login-header'>Welcome Back</h2>", unsafe_allow_html=True)
            st.markdown("<p class='login-subtitle'>Please sign in to the Recruiter Dashboard</p>", unsafe_allow_html=True)
            
            username = st.text_input("Username", placeholder="e.g. Nabil")
            password = st.text_input("Password", type="password", placeholder="e.g. 123456")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Authenticate Securely", use_container_width=True):
                resp = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
                if resp.status_code == 200:
                    st.session_state.access_token = resp.json().get("access_token")
                    st.success("✅ Logged in successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials (use admin/admin)")
    st.stop() # Do not render the rest of the app if not logged in

# User is logged in:
st.sidebar.success("✅ Logged in securely")
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.access_token = None
    st.rerun()


# --- Sidebar: Job Management ---
st.sidebar.header("Job Management")

def fetch_jobs():
    try:
        resp = requests.get(f"{API_URL}/jobs")
        check_unauthorized(resp)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.sidebar.error(f"Failed to fetch jobs: {e}")
        return []

jobs = fetch_jobs()
job_options = {job["title"]: job["id"] for job in jobs}
job_options["-- Create New Job --"] = "new"

selected_job_title = st.sidebar.selectbox("Select a Job", options=list(job_options.keys()))

if selected_job_title == "-- Create New Job --":
    st.header("Create a New Job Posting")
    with st.form("create_job_form"):
        title = st.text_input("Job Title")
        description = st.text_area("Job Description")
        req_skills = st.text_input("Required Skills (comma separated)")
        nice_skills = st.text_input("Nice to Have Skills (comma separated)")
        min_exp = st.number_input("Minimum Experience (Years)", min_value=0.0, step=0.5, value=0.0)
        
        submit = st.form_submit_button("Create Job")
        if submit:
            payload = {
                "title": title,
                "description": description,
                "required_skills": [s.strip() for s in req_skills.split(",") if s.strip()],
                "nice_to_have_skills": [s.strip() for s in nice_skills.split(",") if s.strip()],
                "min_experience_years": float(min_exp)
            }
            resp = requests.post(f"{API_URL}/jobs", json=payload, headers=get_auth_headers())
            check_unauthorized(resp)
            if resp.status_code == 201:
                st.success("Job created successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error creating job: {resp.text}")
else:
    job_id = job_options[selected_job_title]
    st.header(f"Job: {selected_job_title}")
    
    tab1, tab2 = st.tabs(["Upload & Process Resumes", "View Rankings"])
    
    with tab1:
        st.subheader("Upload Resumes")
        uploaded_files = st.file_uploader("Upload PDF or DOCX", accept_multiple_files=True, type=["pdf", "docx"])
        if st.button("Upload and Process"):
            if not uploaded_files:
                st.warning("Please upload at least one file.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Upload
                status_text.text("Uploading resumes...")
                files = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
                resp = requests.post(f"{API_URL}/jobs/{job_id}/resumes", files=files, headers=get_auth_headers())
                check_unauthorized(resp)
                
                if resp.status_code != 200:
                    st.error(f"Failed to upload: {resp.text}")
                else:
                    uploaded_resumes = resp.json()
                    st.success(f"Uploaded {len(uploaded_resumes)} resumes.")
                    
                    # Step 2: Extract
                    for i, res in enumerate(uploaded_resumes):
                        file_name = res.get('file_path', f"Resume {i+1}").split('/')[-1]
                        status_text.text(f"Extracting profile for {file_name} ({i+1}/{len(uploaded_resumes)})...")
                        ext_resp = requests.post(f"{API_URL}/jobs/{job_id}/resumes/{res['id']}/extract")
                        if ext_resp.status_code not in (200, 201):
                            st.error(f"Failed to extract {file_name}: {ext_resp.text}")
                        progress_bar.progress((i + 1) / (len(uploaded_resumes) + 3))
                    
                    # Step 3: Embed all
                    status_text.text("Embedding candidates in Qdrant (Phase 3)...")
                    emb_resp = requests.post(f"{API_URL}/jobs/{job_id}/embed-all")
                    expected_count = len(uploaded_resumes)
                    if emb_resp.status_code == 202:
                        expected_count = emb_resp.json().get("scheduled", expected_count)
                    else:
                        st.warning(f"Embedding issue: {emb_resp.text}")
                    progress_bar.progress((len(uploaded_resumes) + 1) / (len(uploaded_resumes) + 3))
                    
                    # We need to wait for all background embeddings to finish before ranking.
                    status_text.text(f"Waiting for {expected_count} vector embeddings to finish in background...")
                    
                    # Poll rankings until Qdrant indexes all background tasks
                    max_attempts = 30
                    rank_resp = None
                    current_rankings = []
                    for attempt in range(max_attempts):
                        rank_resp = requests.get(f"{API_URL}/jobs/{job_id}/rankings")
                        if rank_resp.status_code == 200:
                            current_rankings = rank_resp.json()
                            if len(current_rankings) >= expected_count:
                                break
                        time.sleep(2)
                    
                    if rank_resp is None or rank_resp.status_code != 200:
                        st.error(f"Failed to fetch initial rankings: {rank_resp.text if rank_resp else 'Timeout'}")
                    elif len(current_rankings) < expected_count:
                        st.warning(f"Vector embeddings timed out. Found {len(current_rankings)} out of {expected_count}.")
                    
                    # Step 5: Rank (Phase 4)
                    status_text.text("Computing hybrid ranking scores (Phase 4)...")
                    hyb_resp = requests.post(f"{API_URL}/jobs/{job_id}/rank")
                    if hyb_resp.status_code not in (200, 201):
                        st.error(f"Failed to compute final rankings: {hyb_resp.text}")
                    progress_bar.progress((len(uploaded_resumes) + 2) / (len(uploaded_resumes) + 3))
                    
                    # Step 6: Explain all
                    status_text.text("Generating AI explanations (Phase 5)...")
                    exp_resp = requests.post(f"{API_URL}/jobs/{job_id}/explain-all")
                    if exp_resp.status_code != 202:
                        st.warning(f"Explanation issue: {exp_resp.text}")
                    progress_bar.progress(1.0)
                    
                    status_text.text("Done! Go to 'View Rankings' tab to see results.")
                    time.sleep(2)
    
    with tab2:
        st.subheader("Candidate Rankings")
        if st.button("Refresh Rankings"):
            st.rerun()
            
        try:
            resp = requests.get(f"{API_URL}/jobs/{job_id}/rankings", headers=get_auth_headers())
            check_unauthorized(resp)
            if resp.status_code == 200:
                rankings = resp.json()
                if not rankings:
                    st.info("No rankings found. Please upload and process resumes.")
                else:
                    for i, rank in enumerate(rankings):
                        candidate_id = rank["candidate_id"]
                        
                        # Fetch candidate profile to get the name
                        prof_resp = requests.get(f"{API_URL}/candidates/{candidate_id}")
                        name = "Unknown Candidate"
                        if prof_resp.status_code == 200:
                            name = prof_resp.json().get("profile", {}).get("name", "Unknown Candidate")
                            
                        final_score = float(rank.get('final_score')) if rank.get('final_score') is not None else None
                        score_display = f"{final_score * 100:.1f}%" if final_score is not None else "N/A"
                        
                        with st.expander(f"#{i+1}: {name} - Final Score: {score_display}", expanded=(i==0)):
                            st.write(f"**Semantic Match:** {float(rank.get('semantic_score') or 0) * 100:.1f}%")
                            st.write(f"**Skill Overlap:** {float(rank.get('skill_overlap_score') or 0) * 100:.1f}%")
                            st.write(f"**Experience Fit:** {float(rank.get('experience_fit_score') or 0) * 100:.1f}%")
                            
                            st.markdown("### AI Explanation")
                            explanation = rank.get("explanation")
                            if explanation:
                                if explanation.startswith("Error:"):
                                    st.error(explanation)
                                else:
                                    st.info(explanation)
                            else:
                                st.info("Explanation is still generating in the background... Refresh to view.")
                                
                            # Display Original Resume Text
                            resume_id = prof_resp.json().get("resume_id") if prof_resp.status_code == 200 else None
                            if resume_id:
                                with st.expander("📄 View Original Resume"):
                                    res_resp = requests.get(f"{API_URL}/resumes/{resume_id}")
                                    if res_resp.status_code == 200:
                                        raw_text = res_resp.json().get("raw_text", "No text available.")
                                        st.text(raw_text)
                                    else:
                                        st.error("Could not load original resume text.")
                        
            else:
                st.error(f"Failed to fetch rankings: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the API. Is it running?")

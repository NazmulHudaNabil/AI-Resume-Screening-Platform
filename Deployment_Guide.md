# Deployment Guide: AI Resume Screening Platform

This guide will walk you through deploying the platform into a production environment. We will use a fully serverless, highly-scalable stack:

- **Database:** Neon (Serverless Postgres)
- **Vector Store:** Qdrant Cloud
- **Cache/Rate Limiting:** Upstash (Serverless Redis)
- **Backend API:** FastAPI Cloud (or Render)
- **Frontend UI:** Streamlit Community Cloud

> **Where does `docker-compose` fit into this?**
> You do **not** use `docker-compose up` when deploying to this serverless cloud architecture. Docker Compose is used exclusively on your local computer to easily spin up a local database and cache for development. In the cloud, Neon, Qdrant, and Upstash manage the databases for you automatically—your API just connects to them over the internet using URLs.

---

## 1. Setup External Services

Before deploying any code, you need to provision your databases and get the connection strings.

### A. Postgres Database (Neon)
1. Go to [Neon.tech](https://neon.tech/) and create a free account.
2. Create a new project and database.
3. Copy the **Connection String** (it starts with `postgresql://`). 
   - *This will be your `DATABASE_URL`.*

### B. Vector Database (Qdrant)
1. Go to [Qdrant Cloud](https://cloud.qdrant.io/) and create a free account.
2. Create a new free cluster.
3. Once provisioned, get the **Cluster URL** and generate an **API Key**.
   - *These will be your `QDRANT_URL` and `QDRANT_API_KEY`.*

### C. Redis Cache (Upstash)
1. Go to [Upstash](https://upstash.com/) and create a free account.
2. Create a new Redis database (leave TLS/SSL enabled).
3. Copy the **Redis URL** (it starts with `rediss://`).
   - *This will be your `REDIS_URL`.*

### D. LLM Provider (Groq / Gemini)
Ensure you have active API keys for:
- **Groq:** Get an API key from [console.groq.com](https://console.groq.com/).
- **Gemini:** Get an API key from [Google AI Studio](https://aistudio.google.com/).

---

## 2. Deploying the Backend API

You have two excellent choices for hosting your FastAPI backend: **FastAPI Cloud** or **Render**. 

### Option A: FastAPI Cloud (Recommended for Ease)
[FastAPI Cloud](https://fastapicloud.com/) is the official platform built by the creator of FastAPI. It is specifically designed to be the "Vercel of FastAPI".
- **Why it's great:** You don't need a Dockerfile. You just run a single command like `fastapi deploy` in your terminal. It automatically handles HTTPS, load balancing, and scaling without you writing any configuration.
- **How to deploy:** Install their CLI, log in, run the deploy command, and securely paste in your `DATABASE_URL`, `QDRANT_URL`, `REDIS_URL`, and API keys in their web dashboard.

### Option B: Render (Recommended if you already use it)
If you already host multiple applications on [Render](https://render.com/), it makes perfect sense to stick with it to keep all your billing and apps in one place!
1. Go to Render and click **New → Web Service**.
2. Connect your GitHub repository.
3. In the setup screen:
   - **Environment:** Docker
   - **Build Command:** *(leave blank, Render uses the `docker/Dockerfile.prod` file)*
   - **Start Command:** *(leave blank)*
4. Scroll down to **Environment Variables** and add:
   - `DATABASE_URL`: *(your Neon URL)*
   - `QDRANT_URL`: *(your Qdrant URL)*
   - `QDRANT_API_KEY`: *(your Qdrant API Key)*
   - `REDIS_URL`: *(your Upstash URL)*
   - `GROQ_API_KEY`: *(your Groq API Key)*
   - `GEMINI_API_KEY`: *(your Gemini API Key)*
   - `JWT_SECRET`: *(generate a random secure string)*
5. Click **Create Web Service**. 
6. Once deployment finishes, copy the URL (e.g., `https://ai-resume-api.onrender.com`).

---

## 3. Deploying the Frontend (Streamlit Cloud)

Now that your API is running in the cloud, you can deploy the frontend interface.

1. First, update `streamlit_app.py` in your code. Change the `API_URL` to point to your new backend URL:
   ```python
   # Change this line at the top of streamlit_app.py:
   API_URL = "https://ai-resume-api.onrender.com/api/v1"
   ```
2. Commit and push this change to your GitHub repository.
3. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and log in with GitHub.
4. Click **New App**.
5. Select your repository, branch (`main`), and main file path (`streamlit_app.py`).
6. Click **Deploy**.

Streamlit will automatically build the app and provide you with a public URL!

---

## 4. Final Smoke Test

1. Visit your Streamlit Cloud URL.
2. Log in using the default credentials (`admin` / `admin`).
3. Click **Create New Job** and fill out the details.
4. Go to **Upload Resumes**, attach a few test PDFs, and run the pipeline.
5. If the rankings appear successfully, your entire production stack is communicating perfectly! 🎉

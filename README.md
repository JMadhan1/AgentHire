# AgentHire — How It Works

## The Problem

Job seekers today spend **hours every week** manually applying to jobs. Each application requires:
- Navigating to a company's career portal (Lever, Greenhouse, Workday, etc.)
- Creating an account or logging in
- Filling out the same information over and over — name, email, phone, work history, education
- Uploading a resume
- Answering portal-specific screening questions
- Clicking through multi-step forms
- Submitting and confirming

Multiply this by 10, 20, or 50 job applications and it becomes a **full-time job in itself**.

---

## The Solution — AgentHire

AgentHire is an **AI-powered autonomous job application engine**. Instead of you navigating each career portal manually, an AI agent does it for you — in real time, on real websites, just like a human would.

---

## How It Works — Step by Step

### Step 1 — You Set Up Your Profile Once

When you first sign up, you fill out your candidate profile:

- **Personal details** — Full name, email address, phone number, location
- **Professional summary** — A short bio or objective statement
- **Work experience** — Job titles, companies, dates, responsibilities
- **Education** — Degrees, institutions, graduation year
- **Skills** — Technical and soft skills
- **Resume PDF** — Your formatted resume file

**Resume Auto-Fill:** When you upload your PDF resume, AgentHire's built-in parser automatically reads the document and fills in your profile fields for you — extracting your name, contact details, work history, skills, and more using intelligent text analysis. You just review and confirm.

This profile is stored securely and reused for every application. **You fill it out once — ever.**

---

### Step 2 — You Paste Job URLs

On the Apply page, you paste the URLs of job postings you want to apply to. These are direct links from:

- **Lever** (jobs.lever.co/...)
- **Greenhouse** (boards.greenhouse.io/...)
- **Workday** (company.wd1.myworkdayjobs.com/...)
- **BambooHR**, **iCIMS**, **SmartRecruiters**, **AshbyHQ**, **Taleo**, and more
- Direct company career pages

You can paste up to **5 URLs at once** per batch. AgentHire validates each URL and queues them for the agent.

---

### Step 3 — The AI Agent Takes Over

This is where the magic happens. AgentHire calls the **TinyFish Web Agent API** — a powerful autonomous browser AI — with:

1. **A natural language goal prompt** — written by AgentHire, describing exactly what the agent needs to do:
   > *"Navigate to [job URL]. Find and click the Apply button. Fill in all form fields using the candidate's information: name, email, phone, resume... Handle any screening questions intelligently. Upload the resume PDF. Submit the application. Confirm submission was successful."*

2. **All your profile data** — name, email, phone, skills, experience — passed as structured context so the agent knows what to fill in everywhere

The TinyFish agent then:

- **Opens a real browser** — a stealth browser session that navigates the actual career portal website, just like a human using Chrome
- **Finds the Apply button** — locates and clicks the correct call-to-action on the job posting page
- **Fills every form field** — reads each field label, understands what's being asked, and types the correct value from your profile
- **Handles multi-step flows** — moves through page 1 → page 2 → page 3 of multi-stage application forms
- **Uploads your resume** — finds the file upload input and attaches your PDF
- **Answers screening questions** — uses AI reasoning to respond to custom questions like "Why do you want to work here?" or "What is your expected salary?"
- **Deals with dropdowns and checkboxes** — selects the right options for fields like employment type, work authorization, experience level
- **Submits the application** — clicks the final Submit button
- **Confirms completion** — checks for a success/confirmation message to verify the application was received

---

### Step 4 — You Watch It Live (Real-Time Streaming)

You don't have to wait and wonder. AgentHire streams the agent's progress **live to your browser** using Server-Sent Events (SSE):

- 🚀 **STARTED** — Agent launched, session ID assigned
- 📺 **Live Browser Link** — A clickable URL to watch the actual browser session in real time (you can literally watch the AI filling the form)
- ▶ **PROGRESS updates** — Each step the agent takes: "Navigating to job page", "Clicking Apply", "Filling name field", "Uploading resume"
- 💓 **Heartbeat** — Every 15 seconds, confirming the agent is still active
- ✅ **COMPLETED** — Application submitted successfully
- ❌ **ERROR** — If something goes wrong (CAPTCHA, page changed, login required), you get an immediate explanation

---

### Step 5 — Your Dashboard Tracks Everything

Every application gets logged in your **Application Dashboard**:

| Field | What it shows |
|---|---|
| **Job URL** | The posting you applied to |
| **Company** | Extracted from the job page |
| **Role** | The position title |
| **Status** | Submitted ✅ / In Progress 🔄 / Failed ❌ |
| **Applied at** | Timestamp |
| **Agent Log** | Full transcript of every action the agent took |

You can view the full agent log for any application, see exactly what the AI did on each site, and re-apply to any job with one click if needed.

---

## The Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **Web Framework** | Flask (Python) | Serves the application, handles routes and auth |
| **AI Agent** | TinyFish Web Agent API | Autonomous browser that navigates and applies on real sites |
| **Real-Time Streaming** | Server-Sent Events (SSE) | Streams agent progress live to the browser |
| **Resume Parsing** | pypdf + regex | Extracts structured data from uploaded PDF resumes |
| **Database** | SQLite / SQLAlchemy | Stores users, profiles, and application history |
| **Authentication** | Flask-Login + bcrypt | Secure user sessions and hashed passwords |
| **Frontend** | Vanilla JS + Tailwind CSS | Responsive UI with real-time progress display |

---

## What Makes It Different

### vs. Browser Extensions
Most "autofill" tools are browser extensions that only fill standard fields using saved data. They fail on non-standard portals, multi-step flows, file uploads, and dynamic forms. AgentHire's AI agent reasons about each page and adapts in real time.

### vs. Easy Apply (LinkedIn)
LinkedIn Easy Apply only works on LinkedIn-listed jobs that support it. The vast majority of real job applications happen on company-specific portals that Easy Apply never touches. AgentHire works on any URL.

### vs. Manual Applying
Manual applying takes 10–30 minutes per job. AgentHire completes a full application in **under 3 minutes**, while you do nothing.

### vs. Hiring a VA
Virtual assistants to apply to jobs cost $5–15/hour and require trust with your personal data. AgentHire is automated, instant, and your data stays on your own server.

---

## Security & Privacy

- Your profile data is stored only in your local database — never sent to third parties except as part of the goal prompt to TinyFish for the specific application
- Your resume PDF stays on your server
- No passwords are ever stored in plain text — bcrypt hashing is used
- API keys are stored in `.env` files, not in code
- All file uploads are validated for type and signature before being saved

---

## The Vision

The average job seeker sends out 100–200 applications before landing a role. That's 50–100 hours of repetitive form-filling. AgentHire compresses that into a **click**. The goal is to democratize access to job opportunities by removing the mechanical barrier of application logistics — so candidates can focus on what actually matters: preparing for interviews, building skills, and telling their story.

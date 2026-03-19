# AgentHire — Demo Script
# TinyFish $2M Pre-Accelerator Hackathon

---

## PRE-RECORDING CHECKLIST

- [ ] `.env` has real `TINYFISH_API_KEY` set
- [ ] `python app.py` running without errors
- [ ] Browser at `http://localhost:5000`
- [ ] Test user account created (register first)
- [ ] Profile filled with realistic fake persona (see below)
- [ ] Resume PDF uploaded (any PDF works for demo)
- [ ] 2-3 real job URLs ready (see below)
- [ ] DB cleared of old test applications (or fresh install)
- [ ] Browser dev tools closed, clean window, zoom 100%
- [ ] Screen recording software ready (OBS / Loom)

---

## DEMO PERSONA (copy-paste into profile)

```
Full Name:   Alex Rivera
Email:       alexrivera.dev@gmail.com
Phone:       +1 (415) 555-0192
Location:    San Francisco, CA, USA
Title:       Senior Software Engineer
Experience:  6 years
Skills:      Python, JavaScript, React, Node.js, AWS, Docker, PostgreSQL, TypeScript
Desired:     Staff Engineer / Senior Full Stack Engineer
LinkedIn:    https://linkedin.com/in/alexrivera-dev
Portfolio:   https://alexrivera.dev
Salary:      $150k+
```

Cover letter template:
```
I am excited to apply for this position. With 6 years of experience building scalable 
software systems using Python, React, and AWS, I believe I can make an immediate impact. 
I thrive in fast-paced environments and have a track record of shipping products that 
users love. I look forward to the opportunity to contribute to your team.
```

---

## SUGGESTED JOB URLS FOR DEMO

Find fresh ones from:
- **Lever**: https://jobs.lever.co → find any active posting
- **Greenhouse**: https://boards.greenhouse.io → find any company
- **Direct company**: Any /careers or /jobs page

Example types to look for:
- Lever: `https://jobs.lever.co/{company}/{job-uuid}`
- Greenhouse: `https://boards.greenhouse.io/{company}/jobs/{id}`

Test the URLs open in browser before recording.

---

## RECORDING SCRIPT — 2:30

### 0:00 — Landing Page
- Open browser to `http://localhost:5000`
- **SAY**: "This is AgentHire — it applies to jobs for you using AI agents, without you having to click a single button."

### 0:15 — Flash Profile
- Click "Profile" in nav (already filled)
- **SAY**: "I've already set up my profile and uploaded my resume. One setup, unlimited applications."
- Show the completeness bar at 100%

### 0:25 — Apply Page
- Click "Apply" in nav
- **SAY**: "Now I paste 2 or 3 real job URLs..."
- Paste URL 1 (Lever job)
- Click "Add Another URL", paste URL 2 (Greenhouse job)
- Optionally add URL 3

### 0:40 — Launch
- **SAY**: "And I click Launch Agent. Watch the AI navigate real career portals in real time."
- Click "🤖 Launch Agent"
- Let the cards appear and logs start streaming

### 0:50 → 1:50 — Live Streaming (60–90 seconds)
- Watch the terminal-style logs scroll
- **NARRATE**:
  - When navigation events appear: "The agent is opening the job page..."
  - When action events appear: "It found the Apply button and clicked it..."
  - "Now it's filling in the name, email, phone fields..."
  - "It found a dropdown for years of experience..."
  - "Handling a multi-step form — clicking Next..."
  - "Answering screening questions..."
  - If CAPTCHA: "This one hit a CAPTCHA — it's reporting that as a blocker."
  - When ✅ appears: "Submitted! Confirmation received."

### 1:50 — Results
- **SAY**: "2 out of 3 submitted. 1 was blocked by a CAPTCHA — the agent correctly reported that."

### 2:00 — Dashboard
- Click "View Dashboard"
- **SAY**: "Every application is tracked here — status, company, role, date."
- Show the green "Submitted" and red "Failed" badges

### 2:10 — Application Detail
- Click "View Details" on a submitted application
- **SAY**: "I can drill into the full agent log — every step it took."
- Expand the log section, show the steps

### 2:20 — Architecture mention
- **SAY**: "This is built with Flask on the backend, powered by the TinyFish Web Agent API for the autonomous browser agent. SSE streaming shows live progress in the terminal."
- Point to the "Powered by TinyFish" badge in the footer

### 2:35 — Close
- Go back to landing page
- **SAY**: "AgentHire — stop applying manually. Built for the TinyFish $2M Pre-Accelerator Hackathon."
- *End recording*

---

## SUBMISSION CHECKLIST

### Code
- [ ] All code committed to GitHub (public repo)
- [ ] README.md with setup instructions included
- [ ] .env NOT committed (in .gitignore)

### Video
- [ ] 2–3 min demo video recorded (OBS / Loom / QuickTime)
- [ ] Video shows: landing → profile → apply → live streaming → dashboard → detail
- [ ] Upload to YouTube (unlisted ok) or Loom

### Submission
- [ ] Video posted on X (Twitter) tagging @Tiny_fish with #TinyFishAccelerator
- [ ] Submitted on HackerEarth with:
  - GitHub repository link
  - Demo video link
  - Project description

---

## QUICK COMMANDS

```bash
# Start app
cd agenthire
venv\Scripts\activate
python app.py

# Test TinyFish API directly
curl -N -X POST "https://agent.tinyfish.ai/v1/automation/run-sse" ^
  -H "X-API-Key: YOUR_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://scrapeme.live/shop\", \"goal\": \"Extract first 2 products as JSON\"}"

# Share via tunnel
npx tinyfi.sh 5000
# or
ngrok http 5000
```

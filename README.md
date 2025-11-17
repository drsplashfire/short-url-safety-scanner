How to Build an AI-Powered URL Title & Safety Scanner Using Cloud Run and Firestore
Introduction / Overview

Shortened or unfamiliar URLs appear everywhere — in emails, chats, documents, and social media. While convenient, they often hide the real destination, making users vulnerable to phishing, credential theft, and malicious redirects.

This project demonstrates how to build a lightweight, serverless, AI-powered URL Safety Scanner using:

Python Flask

Google Cloud Run

Firestore

Optional Gemini-based safety scoring

Audience

This guide is intended for developers with beginner-to-intermediate experience in Python, REST APIs, and cloud-native workflows.

Outcome

By following this guide, you will:

Build a working Flask microservice

Containerize and deploy it to Cloud Run

Integrate Firestore as a managed database

Plug in a hybrid AI safety engine (local heuristics + optional Gemini API)

Successfully scan URLs and retrieve safety scores

Design

This system is designed to be simple, fast, and cloud-native, while solving a real security problem.

The architecture consists of four major layers:

1. Application Layer (Cloud Run)

Handles:

Incoming HTTP requests

Fetching webpage HTML

Extracting <title>

Routing to AI scoring engine

2. AI Safety Engine

Hybrid intelligence:

Local heuristic scoring (default)

Optional Generative AI (Gemini) for deeper content understanding

3. Database Layer

Firestore (Native Mode) for production

SQLite for local development

4. Observability

Cloud Logging

Cloud Monitoring

The CI/CD flow uses Cloud Build + Artifact Registry. Cloud Run deploys new revisions automatically.

A color-coded architecture diagram visually separates these layers.

Prerequisites
Software

Python 3.10+

Docker

Google Cloud CLI

Code editor (VS Code, PyCharm, Cloud Shell Editor)

Setup Links

Python: https://www.python.org/downloads

Docker: https://www.docker.com/get-started

Google Cloud CLI: https://cloud.google.com/sdk/docs/install

Firestore Quickstart: https://cloud.google.com/firestore/docs/quickstart

Assumed Knowledge

Basic Python programming

JSON & REST APIs

Docker fundamentals

Basic cloud deployment concepts

Step-by-step instructions
Step 1: Create the project structure
shorturl_scanner/
  app/
  tests/
  requirements.txt
  Dockerfile
  run.ps1

Step 2: Implement the Flask microservice

Core responsibilities:

Accept a URL

Fetch webpage HTML

Extract the <title> tag or fallback snippet

Invoke the safety engine

Store results (Firestore or SQLite)

(Full code intentionally omitted here per Saadhna blog template.)

Step 3: Add Firestore integration

Enable Firestore → Create a Service Account → Download JSON → Set environment variable:

$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\key.json"


Toggle Firestore mode:

$env:USE_FIRESTORE="1"

Step 4: Containerize with Docker
docker build -t url-scanner:v1 .
docker run -p 8080:8080 url-scanner:v1

Step 5: Deploy to Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/url-scanner
gcloud run deploy url-scanner --image gcr.io/PROJECT_ID/url-scanner --allow-unauthenticated

Step 6: Test using PowerShell
Invoke-RestMethod -Method Post -Uri "https://SERVICE_URL/scan" `
  -ContentType "application/json" `
  -Body '{"url":"http://example.com"}'

Invoke-RestMethod -Method Get -Uri "https://SERVICE_URL/scans"


These responses form part of your functional demo.

Result / Demo

Once deployed, the system can:

Scan any URL (short or long)

Extract webpage titles

Run safety evaluation (heuristic or Gemini)

Store results in Firestore

Provide explanations and safety labels

Produce logs through Cloud Logging

Allow browsing historical scans via /scans

Suggested Visual Artifacts

Include screenshots of:

Cloud Run service endpoint

Firestore documents

Architecture diagram (color-coded)

Sample JSON API output

Why these visuals matter

Improve clarity and readability

Reinforce key concepts

Align with the system design described above

What’s next?

Ways to extend this project:

Add Gemini Pro Safety Tools

Add a frontend dashboard

Enable real-time log streaming

Add batch URL scanning using Cloud Tasks or Pub/Sub

Integrate Slack/Gmail notifications

Add Google Safe Browsing API

Trace redirect chains to show final landing URL

These enhancements would turn the tool into a production-grade security microservice.

Call to action

To learn more about Google Cloud services and to create impact for the work you do, get around to these steps right away:

Register for Code Vipassana sessions

Join the meetup group Datapreneur Social

Sign up to become Google Cloud Innovator
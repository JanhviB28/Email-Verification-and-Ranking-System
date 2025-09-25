# Email Verification and Ranking System

A full-stack web application designed to intelligently find and verify professional email addresses. This project provides a powerful solution for data enrichment and list cleaning by combining a predictive AI scoring model with real-time API validation. Users can find the most probable email address for an individual using just their name and company domain.

# Features

  * **Hybrid Verification:** Leverages a custom, rule-based AI model and a third-party email verification API (MailTester Ninja) for definitive deliverability checks.
  * **Intelligent Ranking:** Ranks potential email variations based on a composite probability score, giving priority to addresses confirmed as "valid" by the API.
  * **Web Interface:** A clean, user-friendly interface for quick single-entry lookups.
  * **Bulk Processing:** Supports CSV file uploads for efficient batch verification, returning an enriched CSV file with ranked results.
  * **Parallel Processing:** Utilizes multi-threading to handle multiple API requests concurrently, ensuring fast and responsive performance.
  * **API Token Management:** Includes a token caching system to manage API key access and reduce redundant calls.


# How It Works

The system operates on a powerful, two-step process:

1.  *Generation & AI Scoring:* The application first generates a comprehensive list of all common email formats (e.g., `first.last`, `f.last`, `firstl`) based on the provided name and domain. Each of these variations is then assigned an **AI confidence score** based on its pattern, name complexity, and domain professionalism.

2.  *API Validation & Final Ranking:* Each email variation is sent to a real-time verification API for a definitive check (MX record lookup, SMTP connection). The API's result is then combined with the AI score to calculate a final, highly-reliable **probability score**. The results are then sorted and presented to the user, with the most probable email address ranked at the top.

# Project Structure

├── demo.py             # Main Python backend script with all logic
├── index.html          # Frontend HTML file for the web interface
├── style.css           # CSS for styling the web interface
├── README.md           # This file


# Screenshots
<img width="930" height="783" alt="Screenshot 2025-09-25 204807" src="https://github.com/user-attachments/assets/d1490b9b-8dfa-40c8-8f0f-a01b017edc61" />
<img width="918" height="789" alt="Screenshot 2025-09-25 204843" src="https://github.com/user-attachments/assets/ec2c8db2-47a2-4370-b5a2-50111491051b" />
<img width="731" height="220" alt="Screenshot 2025-09-25 203606" src="https://github.com/user-attachments/assets/4315c93c-41de-41a8-b87d-749949f9de80" />

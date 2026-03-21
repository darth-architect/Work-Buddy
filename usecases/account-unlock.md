# Account Unlock Automation (Proactive + Security Question-Based | Okta)

## Overview

This solution enables users to unlock their locked accounts using an AI-driven chatbot integrated with Okta.
It enhances traditional reactive workflows by introducing **proactive notifications**, allowing users to resolve account lockouts instantly without contacting the service desk.

---

## Problem Statement

Account lockouts commonly occur due to:

* Multiple failed login attempts
* Credential sync issues
* Expired sessions

Challenges:

* Users are often unaware of the lockout cause
* Delays in resolution due to manual support
* Increased service desk workload

---

## Solution

A proactive, AI-driven solution that:

* Detects account lockout events in real-time
* Sends proactive notification to the user
* Allows user to initiate unlock via chatbot interaction
* Verifies identity using security questions
* Unlocks account using Okta APIs

---

## High-Level Workflow

1. User account gets locked in Okta
2. System detects lockout event
3. Proactive notification sent to user
4. User clicks **"Unlock My Account"**
5. Bot initiates identity verification
6. User answers security questions
7. System validates responses
8. If valid → account unlock executed
9. Bot confirms successful unlock

---

## Detailed Workflow

### Step 1: Lockout Detection

* Account lockout event is captured via:

  * Okta event hooks / system logs
* Automation workflow is triggered

---

### Step 2: Proactive Notification

* User receives notification via:

  * Chatbot (Teams / Web / App)
  * Email / Notification channel

**Message Example:**

> Your account has been locked due to multiple failed login attempts.
> Click below to unlock your account.

**Action Button:**

* **Unlock My Account**

---

### Step 3: Bot Initiation

* User clicks "Unlock My Account"
* Chatbot session is initiated automatically
* Context (user identity) is passed to bot

---

### Step 4: Identity Verification (Security Questions)

* Bot presents predefined security questions
* User submits answers
* System retrieves user profile from Okta

**Validation Logic:**

* Answers matched against stored attributes
* Case-insensitive comparison

**Failure Handling:**

* Incorrect answers → retry allowed
* Max attempts enforced → escalation

---

### Step 5: Account Unlock Execution

* Upon successful validation:

  * Okta API is triggered to unlock account

---

## Architecture

User ← Proactive Notification System ← Okta Event Hook
↓
Chatbot → Identity Verification → Okta API → Okta Directory

---

## Technology Stack

* Okta Identity Platform
* Okta Event Hooks / System Logs
* Okta User Management APIs
* AI Chatbot Platform (Aisera)
* Notification Channels (Teams / Email)
* REST APIs / Middleware

---

## Sample API Logic

### Get User Details

```id="okta11"
GET https://{yourOktaDomain}/api/v1/users/{userId}
```

---

### Unlock User Account

```id="okta12"
POST https://{yourOktaDomain}/api/v1/users/{userId}/lifecycle/unlock
```

---

## Key Features

* Proactive issue detection and resolution
* Zero-touch self-service unlock
* Security question-based identity verification
* Reduced service desk dependency
* Improved user experience

---

## Security Considerations

* Sensitive answers must not be logged
* Retry limits to prevent brute-force attacks
* Secure API token management
* Context validation for proactive sessions

---

## Failure & Escalation Handling

* Max retry attempts exceeded → escalate to live agent
* Notification delivery failure → fallback channel
* API failure → retry + user notification

---

## Reusability

This solution supports multiple entry points:

* Proactive notification (primary)
* Chatbot interaction
* Self-service portal
* REST API triggers

---

## Future Enhancements

* Add OTP as secondary verification
* Risk-based adaptive authentication
* Integration with SIEM for anomaly detection
* Smart retry/backoff mechanisms

---

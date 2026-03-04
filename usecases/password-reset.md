# Password Reset Automation

## Problem
Users frequently contact the service desk to reset their passwords.

## Solution
Automate password reset using a chatbot integrated with Azure AD via Microsoft Graph API.

## Workflow

1. User initiates password reset through chatbot
2. Bot verifies user identity
3. Bot calls automation API
4. API triggers Microsoft Graph password reset
5. Bot confirms reset to the user

## Technologies

- Azure AD
- Microsoft Graph API
- PowerShell automation
- Chatbot platform (Aisera)
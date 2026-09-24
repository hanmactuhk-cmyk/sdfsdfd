# G-Labs Studio

Windows desktop workspace for authorized G-Labs Webhook API and Workflow JSON automation.

## Build

GitHub Actions builds `G-Labs-Studio.exe` with PyInstaller on Windows.

The desktop UI uses Python's built-in Tkinter instead of PySide6 so the Windows build has fewer third-party packaging dependencies.

## Webhook

Default server URL: `http://127.0.0.1:8765`

Configure the API key from the authorized G-Labs Webhook server. The application does not collect browser cookies, session tokens, or CAPTCHA tokens.

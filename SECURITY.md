# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within Offline Chat, please send an email to the maintainers via GitHub Security Advisories. All security vulnerabilities will be promptly addressed.

**Please do not report security vulnerabilities through public GitHub issues.**

### What to Include

When reporting a vulnerability, please include:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will provide a more detailed response within 7 days indicating the next steps
- We will keep you informed of the progress towards a fix and announcement
- We may ask for additional information or guidance

## Security Best Practices

When using Offline Chat:

1. **Database Credentials**: Store database credentials securely using environment variables or secure credential managers
2. **Local Models**: Ensure Ollama is configured to only accept local connections
3. **Web Search**: Be cautious when enabling web search capabilities, as agents will fetch external content
4. **MCP Servers**: Only connect to trusted MCP servers
5. **File Permissions**: Ensure agent configuration files have appropriate permissions (readable only by your user)

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release new versions as soon as possible

## Comments on this Policy

If you have suggestions on how this process could be improved, please submit a pull request.

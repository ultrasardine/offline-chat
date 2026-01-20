# Quick Fix Guide

## Problem
Agent outputs JSON instead of using tools properly.

## Solution (3 Steps)

### 1. Pull Better Model
```bash
ollama pull qwen2.5:latest
```

### 2. Update Agent
```bash
python main.py
```
- Select: **6. Update agent**
- Select: **db-analyst**
- Select: **1. Update base model**
- Enter: **qwen2.5:latest**
- Confirm: **y**

### 3. Test
Chat with agent:
```
You: Can you tell me what's the most sold product?
```

Should work without JSON output!

## Alternative Models
- `llama3.2:latest` - Good balance
- `mistral:latest` - Fast alternative

## Why?
`llama3.1:latest` has weak tool calling support. Better models = better results.

## Done!
Your agent should now work reliably with database tools.

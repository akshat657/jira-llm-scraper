# 🚀 Jira LLM Scraper - Minimal Prototype

A simple web scraper that extracts public issue data from Apache's Jira instance and converts it to JSONL format for LLM training.

**Author:** akshat657  
**Created:** 2025-11-01  
**Status:** Minimal Prototype (v0.1)

---

## 📋 Overview

This prototype demonstrates:
- ✅ Connecting to Apache Jira's public API
- ✅ Fetching issues using JQL (Jira Query Language)
- ✅ Transforming raw Jira data to clean JSONL format
- ✅ Basic error handling

**Current Scope:** Fetch 10 issues from 1 project (KAFKA) for testing

---

## 🎯 Quick Start (5 Minutes)

### Prerequisites
- Python 3.8+
- Internet connection

### Step 1: Clone Repository
```bash
git clone https://github.com/akshat657/jira-llm-scraper.git
cd jira-llm-scraper
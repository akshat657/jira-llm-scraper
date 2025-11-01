# Apache Jira LLM Data Scraper

A production-grade web scraper that extracts issue data from Apache's public Jira instance and transforms it into JSONL format for LLM training.

**Author:** [@akshat657](https://github.com/akshat657)  
**Assignment:** Web Scraping for LLM Training Data  
**Submitted:** 2025-11-01

---

## Results

**Data Collected:**
- **3,000 issues** from 3 Apache projects (KAFKA, SPARK, HADOOP)
- **14,278 comments** extracted
- **84.6 issues/sec** average speed
- **21.4 MB** JSONL output

| Project | Issues | Comments | Speed |
|---------|--------|----------|-------|
| KAFKA   | 1,000  | 1,372    | 89.0/s |
| SPARK   | 1,000  | 884      | 82.5/s |
| HADOOP  | 1,000  | 12,022   | 82.3/s |

---

## Features

**Core Functionality:**
- Multi-project scraping with pagination
- Comment and metadata extraction
- JSONL transformation with LLM training tasks
- HTML/ADF format parsing

**Fault Tolerance:**
- SQLite checkpointing (resume on failure)
- Rate limiting (50 requests/min)
- Retry logic with exponential backoff
- Comprehensive error logging

**Edge Cases Handled:**
- HTTP 429/5xx responses
- Network timeouts
- Malformed/missing data
- Unicode encoding (UTF-8)

---

## Quick Start

### Installation

```bash
# Clone and setup
git clone https://github.com/akshat657/jira-llm-scraper.git
cd jira-llm-scraper
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Usage

```bash
# Run scraper
python main.py

# View statistics
python main.py --stats

# Reset project checkpoint
python main.py --reset KAFKA
```

---

## Architecture

```
src/
├── scraper/
│   ├── jira_client.py      # API client with retry logic
│   ├── fetcher.py          # Multi-project orchestrator
│   ├── checkpoint.py       # SQLite progress tracking
│   └── rate_limiter.py     # Token bucket rate limiter
├── transformer/
│   ├── cleaner.py          # HTML/ADF parser
│   └── formatter.py        # JSONL transformation
└── utils/
    └── logger.py           # UTF-8 logging

data/
├── checkpoints/
│   └── progress.db         # Resume state
└── output/
    ├── kafka_issues.jsonl
    ├── spark_issues.jsonl
    └── hadoop_issues.jsonl
```

**Data Flow:**
```
Apache Jira API → JiraClient → JiraFetcher → Transformer → JSONL
                     ↓              ↓
              Rate Limiter   Checkpoint DB
```

---

## Output Format

Each JSONL file contains one issue per line:

```json
{
  "issue_id": "HADOOP-19736",
  "project": "HADOOP",
  "url": "https://issues.apache.org/jira/browse/HADOOP-19736",
  "metadata": {
    "status": "Open",
    "priority": "Major",
    "type": "Task",
    "assignee": "Manika Joshi",
    "labels": ["pull-request-available"],
    "components": ["fs/azure"]
  },
  "content": {
    "title": "ABFS: Support for new auth type: User-bound SAS",
    "description": "Adding support for new authentication...",
    "comments": [...],
    "comment_count": 16
  },
  "training_tasks": [
    {
      "task_type": "summarization",
      "instruction": "Summarize the following software issue:",
      "input": "Title: ABFS...",
      "output": "ABFS: Support for new auth type"
    },
    {
      "task_type": "classification",
      "instruction": "Classify this issue type:",
      "input": "ABFS: Support...",
      "output": "task"
    }
  ]
}
```

---

## Configuration

Edit `config/config.yaml`:

```yaml
jira:
  projects:
    - name: "KAFKA"
      max_issues: 1000

scraping:
  batch_size: 100
  rate_limit:
    requests_per_minute: 50
    retry_attempts: 3

checkpointing:
  enabled: true
  checkpoint_every: 50
```

---

## Implementation Highlights

**Checkpointing System:**
- SQLite database tracks progress per project
- Resume from last successful state after interruption
- Checkpoint saved every 50 issues

**Rate Limiting:**
- Token bucket algorithm (50 requests/min)
- Respects server `Retry-After` headers
- Exponential backoff on failures (1s, 2s, 4s)

**LLM Task Generation:**
1. **Summarization** - Title from description
2. **Classification** - Bug/Feature/Task/Improvement
3. **Q&A Generation** - From issue comments
4. **Code Extraction** - Code blocks from descriptions

---

## Testing

```bash
# Full run (3,000 issues)
python main.py

# Quick test (10 issues)
# Edit config.yaml: max_issues: 10
python main.py

# Test resume capability
# Kill mid-run (Ctrl+C), then run again
python main.py
```

---

## Performance

- **Speed:** 84.6 issues/sec average
- **Runtime:** 35.5 seconds (3,000 issues)
- **Memory:** <100MB (streaming write)
- **API Efficiency:** 100 issues per batch

---

## Dependencies

```
requests==2.31.0
jsonlines==4.0.0
pyyaml==6.0.1
```

---

## Assignment Requirements

| Requirement | Implementation |
|------------|----------------|
| 3 Apache projects | ✅ KAFKA, SPARK, HADOOP |
| Pagination | ✅ 100 issues/batch |
| Rate limiting | ✅ Token bucket (50/min) |
| Resume capability | ✅ SQLite checkpoints |
| Edge cases | ✅ 429, 5xx, timeouts |
| JSONL format | ✅ Structured output |
| Metadata extraction | ✅ All fields |
| Comments | ✅ 14,278 extracted |
| LLM tasks | ✅ 4 task types |
| Documentation | ✅ This README |

---

**Submitted to:** [@Naman-Bhalla](https://github.com/Naman-Bhalla) • [@raun](https://github.com/raun)

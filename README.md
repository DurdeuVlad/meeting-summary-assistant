# Meeting Summary Assistant

## Introduction

I built this project during university after sitting through one too many meetings where no one remembered what was said or who had to do what. The goal was simple: take a raw meeting transcript and turn it into something useful. Something you could actually refer back to.

This was also one of my first real uses of NLP in a project, and it ended up being more than just a summary tool. I wired it up to automatically generate Trello tasks based on action items it finds in the meeting. No more forgetting who was supposed to follow up.

## What It Does

Feed it a `.txt` or audio file  
It extracts key points, filters the noise, and generates a clean summary  
Then it pushes any identified tasks directly to a Trello board using the API  
It can also generate a PDF summary and attach it to Trello  
Designed to help teams stay aligned without manually writing notes or TODOs

## Tech Stack

Python  
spaCy and NLTK for NLP  
Trello API for task generation  
OpenAI Whisper and GPT-4  
Command-line interface for simplicity

## How to Use It

Make sure your transcript is saved as `.txt` or audio like `.mp3`  
Then run the script:

```bash
python main.py
```

By default, it will:
- Transcribe the audio (if provided)
- Summarize the content
- Extract tasks and create Trello cards
- Generate and attach a summary PDF (optional)

## Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/DurdeuVlad/meeting-summary-assistant.git
cd meeting-summary-assistant
```

### 2. Install the requirements

Python 3.9 or newer:

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file with:

```
OPENAI_API_KEY=your_openai_api_key
TRELLO_API_KEY=your_trello_api_key
TRELLO_API_SECRET=your_trello_token
```

### 4. Drop your audio file

Put your `.mp3` in the root folder or update the path in the `main()` function inside `main.py`.

### 5. Run it

Adjust your Trello board name and list names in `main()` at the bottom of the file:

```python
main(
    audio_file="test-meeting.mp3",
    trello_board="Your Trello Board",
    task_list_name="Tasks",
    summary_list_name="Meeting Summaries",
    generate_pdf=True,
    generate_trello=True
)
```

Then just:

```bash
python main.py
```




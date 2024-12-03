import os

import requests
from dateutil.utils import today
from dotenv import load_dotenv
from openai import OpenAI
from trello import TrelloClient
import openai
import json
from datetime import datetime, timedelta
from dateutil import parser

from pdf_generator import generate_meeting_brief

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_API_SECRET = os.getenv("TRELLO_API_SECRET")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio_with_whisper(audio_path):
    """Transcribe audio using OpenAI's Whisper API."""
    print("[transcribe_audio_with_whisper]: Starting transcription...")
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {"file": (audio_path, open(audio_path, "rb")), "model": (None, "whisper-1")}
    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        print("[transcribe_audio_with_whisper]: Transcription successful.")
        result = response.json()
        return result["text"], result.get("language", "en")
    else:
        print(f"[transcribe_audio_with_whisper]: Error - {response.status_code} {response.text}")
        raise Exception(f"Failed to transcribe audio: {response.status_code}")


def generate_meeting_minutes_and_tasks(transcript, language, num_tasks, participant_names=None):
    """Generate meeting minutes and tasks using ChatGPT."""
    print("[generate_meeting_minutes_and_tasks]: Generating summary and tasks...")

    prompt = (
        f"Here is a transcript of a meeting in {language}:\n{transcript}\n\n"
        f"There are {num_tasks} tasks discussed in the meeting. Please summarize the meeting into minutes using bullet points and tasks. "
        f"Add details for each task, including the task description, assignee (if any), and due date (if any). "
        f"Please ensure the tasks are clear and actionable and task descriptions are detailed enough for the assignee to understand. You may also assign tasks to specific participants if mentioned. "
        f"Assign only to the participants who are present on this list: {participant_names}.\n"
        f"Assign deadlines if mentioned, if they are not mentioned assign reasonable deadlines for each task, ensuring they are distributed appropriately over time. Today is {datetime.now()}, so assign them from this starting date. Respond in the following JSON format:\n"
        "{\n"
        "  \"meeting_minutes\": \"<summary_of_meeting_bullet_points>\",\n"
        "  \"tasks\": [\n"
        "    {\n"
        "      \"task\": \"<task_name>\",\n"
        "      \"description\": \"<task_description_details>\",\n"
        "      \"assignee\": \"<assignee_if_any>\",\n"
        "      \"due_date\": \"<due_date_if_any>\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]
    )

    print("[generate_meeting_minutes_and_tasks]: Response received.")
    return response.choices[0].message.content


def parse_response(response):
    """Parse the JSON response from ChatGPT."""
    print("[parse_response]: Parsing ChatGPT response...")
    try:
        data = json.loads(response)
        return data["meeting_minutes"], data["tasks"]
    except json.JSONDecodeError:
        print("[parse_response]: Failed to parse JSON.")
        return None, None


def fix_invalid_json(original_response):
    """Ask ChatGPT to fix invalid JSON."""
    print("[fix_invalid_json]: Requesting JSON correction...")

    prompt = (
        f"The following response is not valid JSON:\n{original_response}\n\n"
        "Please correct it and ensure it follows the specified JSON format, DO NOT WRITE ANYTHING ELSE:"
        "{\n"
        "  \"meeting_minutes\": \"<summary_of_meeting_bullet_points>\",\n"
        "  \"tasks\": [\n"
        "    {\n"
        "      \"task\": \"<task_name>\",\n"
        "      \"description\": \"<task_description_details>\",\n"
        "      \"assignee\": \"<assignee_if_any>\",\n"
        "      \"due_date\": \"<due_date_if_any>\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    # Use the new client-based API
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a JSON validation and correction assistant. You respond with only valid JSON."},
            {"role": "user", "content": prompt},
        ]
    )

    print("[fix_invalid_json]: Corrected JSON response received.")
    print(f"[fix_invalid_json]: {response.choices[0].message.content}")
    return response.choices[0].message.content


def get_trello_members(board_name):
    """Retrieve all members of a specific Trello board."""
    print(f"[get_trello_members]: Fetching members for board '{board_name}'...")
    client = TrelloClient(
        api_key=TRELLO_API_KEY,
        token=TRELLO_API_SECRET,
    )
    board = next((board for board in client.list_boards() if board.name == board_name), None)
    if not board:
        print(f"[get_trello_members]: Board '{board_name}' not found.")
        raise ValueError(f"Board '{board_name}' not found.")
    print(f"[get_trello_members]: Members fetched successfully.")
    return {member.full_name: member.id for member in board.get_members()}



def add_to_trello(task_list, meeting_summary, board_name, task_list_name, summary_list_name, pdf_file=None):
    """Add tasks and meeting summary to separate Trello lists."""
    print("[add_to_trello]: Adding data to Trello...")
    client = TrelloClient(
        api_key=TRELLO_API_KEY,
        token=TRELLO_API_SECRET,
    )
    board = next((board for board in client.list_boards() if board.name == board_name), None)
    if not board:
        print(f"[add_to_trello]: Board '{board_name}' not found.")
        raise ValueError(f"Board '{board_name}' not found.")

    task_list_obj = next((lst for lst in board.list_lists() if lst.name == task_list_name), None)
    if not task_list_obj:
        task_list_obj = board.add_list(task_list_name)

    summary_list_obj = next((lst for lst in board.list_lists() if lst.name == summary_list_name), None)
    if not summary_list_obj:
        summary_list_obj = board.add_list(summary_list_name)

    for task in task_list:
        task_name = task["task"]
        task_description = task.get("description", "No description provided.")  # Add task description
        assignee_name = task.get("assignee", None)
        due_date = task.get("due_date", None)

        if due_date:
            try:
                print(f"[add_to_trello]: Raw due_date for task '{task_name}': {due_date}")
                # Attempt to parse and format the due date
                due_date = parser.parse(due_date).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, TypeError):
                print(f"[add_to_trello]: Invalid date format for task '{task_name}'. Skipping due date.")
                due_date = None

        card = task_list_obj.add_card(name=task_name, desc=task_description, due=due_date)
        if assignee_name:
            print(f"[add_to_trello]: Task '{task_name}' assigned to '{assignee_name}'.")
        else:
            print(f"[add_to_trello]: Task '{task_name}' left unassigned.")

    today = datetime.now().strftime("%Y-%m-%d")
    summary_title = f"Meeting Summary - {today}"
    # if pdf_file is not none add the pdf file to the card
    summary_card = summary_list_obj.add_card(name=summary_title, desc=meeting_summary)
    if pdf_file:
        summary_card.attach(name=summary_title, file=open(pdf_file, 'rb'))
        print(f"Attached PDF '{pdf_file}' to card '{summary_title}'.")
    print(f"[add_to_trello]: Meeting summary added with title '{summary_title}'.")


def main(audio_file, trello_board, task_list_name, summary_list_name, generate_pdf=False, generate_trello=False):
    """Main function to process audio, generate tasks, and add them to Trello."""
    print("[main]: Starting process...")
    try:
        transcript, language = transcribe_audio_with_whisper(audio_file)
        task_count = transcript.count("task")  
        print(f"[main]: Estimated number of tasks: {task_count}")

        response = generate_meeting_minutes_and_tasks(transcript, language, task_count, get_trello_members(trello_board))
        meeting_minutes, tasks = parse_response(response)

        if meeting_minutes is None or tasks is None:
            response = fix_invalid_json(response)
            meeting_minutes, tasks = parse_response(response)
            if meeting_minutes is None or tasks is None:
                print("[main]: Failed to parse corrected JSON. Exiting.")
                return
        pdf_path = None
        if generate_pdf:
            # Generate PDF
            pdf_path = generate_meeting_brief(json.dumps({"meeting_minutes": meeting_minutes, "tasks": tasks}), trello_board, datetime.now().strftime("%Y-%m-%d"))
        if generate_trello:
            # Add to Trello
            add_to_trello(tasks, meeting_minutes, trello_board, task_list_name, summary_list_name, pdf_path)
        print("[main]: Process completed successfully.")
    except Exception as e:
        print(f"[main]: Error occurred - {e}")



if __name__ == "__main__":
    # for testing
    # main(
    #     audio_file="test-meeting.mp3",
    #     trello_board="Leftsilon Games",
    #     task_list_name="In Lucru",
    #     summary_list_name="Meeting Summaries"
    # )

    main(
        audio_file="test-meeting.mp3",
        trello_board="Leftsilon Games",
        task_list_name="In Lucru",
        summary_list_name="Meeting Summaries",
        generate_pdf=True,
        generate_trello=True
    )


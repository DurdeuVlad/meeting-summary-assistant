import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from textwrap import wrap


def generate_meeting_brief(json_data, team_name, date):
    """
    Generates a PDF for a meeting brief based on the provided JSON data.

    Args:
        json_data (str): JSON string containing the meeting summary and tasks.
        team_name (str): The name of the team.
        date (str): The date of the meeting in 'YYYY-MM-DD' format.
    """
    # Parse the JSON data
    data = json.loads(json_data)
    meeting_minutes = data.get("meeting_minutes", "")
    tasks = data.get("tasks", [])

    # Generate the file name and title
    file_name = f"{date}_meeting_summary_{team_name}.pdf"
    title = f"Meeting Summary - {team_name} ({date})"

    # Create a PDF
    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    # Margins and content width
    margin = 1 * inch
    content_width = width - 2 * margin

    # Function to draw wrapped text
    def draw_wrapped_text(c, text, x, y, max_width, line_height):
        lines = wrap(text, width=int(max_width / 6))  # Approximation of characters per line
        for line in lines:
            c.drawString(x, y, line)
            y -= line_height
        return y

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - margin, title)

    # Add Summary Section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, height - margin - 0.5 * inch, "Summary:")
    c.setFont("Helvetica", 12)
    y_position = height - margin - 1 * inch
    y_position = draw_wrapped_text(c, meeting_minutes, margin, y_position, content_width, 14)

    # Add Tasks Section
    c.setFont("Helvetica-Bold", 14)
    y_position -= 0.5 * inch
    c.drawString(margin, y_position, "Tasks:")
    y_position -= 0.3 * inch

    c.setFont("Helvetica", 12)
    for task in tasks:
        task_name = task.get("task", "No Task Name")
        description = task.get("description", "No Description")
        assignee = task.get("assignee", "Unassigned")
        due_date = task.get("due_date", "No Due Date")

        task_details = (
            f"Task: {task_name}\n"
            f"Description: {description}\n"
            f"Assignee: {assignee}\n"
            f"Due Date: {due_date}\n"
        )
        for line in task_details.split("\n"):
            y_position = draw_wrapped_text(c, line, margin, y_position, content_width, 14)
            y_position -= 0.1 * inch  # Add spacing between tasks
            if y_position < margin:  # Create a new page if space is insufficient
                c.showPage()
                y_position = height - margin
                c.setFont("Helvetica", 12)

    # Save the PDF
    c.save()
    print(f"PDF generated: {file_name}")
    return file_name

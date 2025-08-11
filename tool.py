from textwrap import dedent
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Annotated
from bson import ObjectId
import subprocess
import glob
import re
import os

TOKEN = ""
MY_NUMBER = ""

# MongoDB setup
try:
    client = MongoClient('')
    db = client['tasksDB']
    collection = db['tasks']
except Exception as e:
    print(f"MongoDB server error: {e}")

# Models
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# Auth Provider
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="unknown", scopes=[], expires_at=None)
        return None

mcp = FastMCP("Task Manager MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

def get_all_tasks():
    tasks = []
    for task in collection.find():
        tasks.append({
            "taskID": str(task.get('_id')),
            "title": task.get('title', 'No Title'),
            "dueDate": task.get('dueDate', 'No Due Date'),
            "status": task.get('status', 'No Status')
        })
    return tasks

def to_markdown_table(tasks):
    if not tasks:
        return "No tasks available."
    headers = tasks[0].keys()
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    rows = ["| " + " | ".join(str(task[h]) for h in headers) + " |" for task in tasks]
    return "\n".join([header_line, separator_line] + rows)

ListTasksDescription = RichToolDescription(
    description="Retrieve all current tasks from the database as JSON (for AI) and markdown (for human display).",
    use_when="When you need to see all tasks, or before deleting/updating a task to find the task ID."
)

CreateTasksDescription = RichToolDescription(
    description="""Create a new task with title, due date, and status. Always follow up with listing tasks to confirm creation.

        You have to return the title of the task, the due date and the status of the task in the following format strictly of JSON object without any markdown or any other formatting example is show below:

        {
            "title": "Task Title",
            "dueDate": "Due date mentioned by the user",
            "status": "Pending"
        }
    """,
    use_when="When a user asks to add or create a task."
)

DeleteTasksDescription = RichToolDescription(
    description="Delete a task by its ID. If you don't have the ID, first call list_tasks to retrieve it. If user wants you to delete all the tasks, then delete them one by one. Do not ask user to proceed further. Just do what is necessary to server user's query. If the user wants to delete all the tasks at once then fetch taks IDs of all the tasks and then delete one-by-one.",
    use_when="When a user asks to remove a task."
)

UpdateTaskDescription = RichToolDescription(
    description="Update the status of a task by its ID. If you don't have the ID, first call list_tasks to retrieve it. Do not ask user to proceed further. Just do what is necessary to server user's query. If you get any task ID related errors just call the list_task tool and then proceed further. At first you will not be given the task ID, you will be given all the data from the database and based on that data you have to find the task ID and then pass that task ID to the tool's argument. Then the task will be deleted.",
    use_when="When a user asks to mark a task as done, pending, or change its status."
)


SummarizeYoutubeVideo = RichToolDescription(
    description="Summarize YouTube video using the link provided by the user.You have to summarize the video transcript in detail.",
    use_when="When the user asks to summarize a YouTube video given a video link."
)

RedirectToYouTube = RichToolDescription(
    description="Redirect user to YouTube based on user's query.",
    use_when="When you need to redirect user to YouTube based on user's query."
)

@mcp.tool
async def about() -> dict[str, str]:
    server_name = "Job Finder MCP"
    server_description = dedent("""
    This MCP server contains two powerful tools:
                                
    1. Simple but worthy task manager.
    
    -> Task creation: Ask puch to create a task for you. Eg: "Hey Puch please create a task for me named Schedule Meeting with a due date of 20 August 2025".
    -> Task listing: List all the created tasks. Eg: "Hey Puch please list all the tasks for me".
    -> Task updation: Update the status of task(pending, started or completed). Eg: Hey Puch please update the status of Schedule Meeting task to started.
    ->Task deletion: Delete unnecessary or complete tasks. Eg: Hey Puch please delete Schedule Meeting task.
                                
    2. Powerful YouTube summarizer.
                                
    -> Drop a YouTube video link and you will get the whole summary of it. Eg: Hey Puch can you summarize this video <video_url>.
    """)

    return {
        "name": server_name,
        "description": server_description
    }

@mcp.tool
async def validate() -> str:
    """Validation tool to confirm the MCP server is reachable."""
    return MY_NUMBER

@mcp.tool(description=ListTasksDescription.model_dump_json())
def list_tasks():
    tasks = get_all_tasks()
    print(f'Tasks: {tasks}')
    return {
        "tasks_json": tasks,
        "tasks_markdown": to_markdown_table(tasks)
    }

@mcp.tool(description=CreateTasksDescription.model_dump_json())
def create_task(task: dict):
    collection.insert_one({
        "title": task.get('title', 'No Title'),
        "dueDate": task.get('dueDate', 'No Due Date'),
        "status": task.get('status', 'Pending')
    })
    tasks = get_all_tasks()
    return {
        "message": "Task created successfully.",
        "tasks_json": tasks,
        "tasks_markdown": to_markdown_table(tasks)
    }

@mcp.tool(description=DeleteTasksDescription.model_dump_json())
def delete_task(task_id: Annotated[str | None, "MongoDB ObjectId of the task to delete"] = None):
    if task_id:
        collection.delete_one({"_id": ObjectId(task_id)})
        message = "Task deleted successfully."
    else:
        message = "No task ID provided. Returning task list instead."
    tasks = get_all_tasks()
    return {
        "message": message,
        "tasks_json": tasks,
        "tasks_markdown": to_markdown_table(tasks)
    }

@mcp.tool(description=UpdateTaskDescription.model_dump_json())
def update_task(task_id: Annotated[str | None, "MongoDB ObjectId of the task to update"] = None,
                status: Annotated[str | None, "New status for the task"] = None):
    if task_id and status:
        collection.update_one({"_id": ObjectId(task_id)}, {'$set': {"status": status}})
        message = "Task updated successfully."
    else:
        message = "Missing task ID or status. Returning task list instead."
    tasks = get_all_tasks()
    return {
        "message": message,
        "tasks_json": tasks,
        "tasks_markdown": to_markdown_table(tasks)
    }

def download_vtt_subtitles(url, language):
    print("⬇️ Downloading subtitles with yt-dlp...")

    command = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", language[1:],
        "--convert-subs", "vtt",
        url
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ yt-dlp error:")
        print(result.stderr)
        return None

    
    vtt_files = glob.glob(f"*{language[1:]}.vtt")
    if not vtt_files:
        print("❌ No .vtt subtitle file found.")
        return None

    return vtt_files[0]

def extract_transcript_from_vtt(vtt_file):
    print("🧼 Cleaning .vtt transcript...")

    with open(vtt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    text_lines = []
    skip_line = False
    last_line = None

    for line in lines:
        line = line.strip()

        if not line or line.startswith("WEBVTT") or re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} -->', line):
            skip_line = True
            continue

        if re.match(r'align:', line) or re.match(r'position:', line):
            continue

        cleaned_line = re.sub(r'<.*?>', '', line)

        if cleaned_line != last_line:
            text_lines.append(cleaned_line)
            last_line = cleaned_line

    full_text = " ".join(text_lines)
    full_text = re.sub(r'\s{2,}', ' ', full_text).strip()

    return full_text


@mcp.tool(description=SummarizeYoutubeVideo.model_dump_json())
def summarize_youtube_video(video_link):

    vtt_file = download_vtt_subtitles(video_link.strip())
    if not vtt_file:
        return

    transcript_text = extract_transcript_from_vtt(vtt_file)

    os.remove(vtt_file)

    print("\n📄 Full Transcript:\n")
    print(transcript_text)

    return transcript_text


async def main():
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8080)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

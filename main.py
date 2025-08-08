from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from pydantic import BaseModel
from pymongo import MongoClient
import markdownify
from typing import Annotated
from bson import ObjectId

TOKEN = ""
MY_NUMBER = ""

try:
    client = MongoClient('connection uri')
    db = client['tasksDB']
    collection = db['tasks']
except Exception as e:
        print(f"mongodb server error due to: {e}")

class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None

class SimpleBearerAuthProvider(BearerAuthProvider):
    """
    A simple BearerAuthProvider that does not require any specific configuration.
    It allows any valid bearer token to access the MCP server.
    For a more complete implementation that can authenticate dynamically generated tokens,
    please use `BearerAuthProvider` with your public key or JWKS URI.
    """

    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(
            public_key=k.public_key, jwks_uri=None, issuer=None, audience=None
        )
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="unknown",
                scopes=[],
                expires_at=None,
            )
        return None


mcp = FastMCP(
    "My MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)
print("line 55 hello mcp")

@mcp.tool
async def validate() -> str:
    """
    NOTE: This tool must be present in an MCP server used by puch.
    """
    return MY_NUMBER

ListTasksDescription = RichToolDescription(
    description="""List example tasks for the user.
    """,
    use_when="When user wants to see all his/her tasks.",
    side_effects=None,
)

CreateTasksDescription = RichToolDescription(
    description="""Tool for creating a task.

        User will query to you by asking "Create a new task" or similar.

        You have to return the title of the task, the due date and the status of the task in the following format strictly of JSON object without any markdown or any other formatting example is show below:

        {
            "title": "Task Title",
            "dueDate": "Due date mentioned by the user",
            "status": "Pending"
        }
    """,
    use_when="When user wants to see all his/her tasks.",
    side_effects=None,
)

DeleteTasksDescription = RichToolDescription(
    description="""Tool for deleting a task.

        User will query to you by asking "Delete a task" or similar.
    """,
    use_when="When user wants to delete a task.",
    side_effects=None,
)

UpdateTaskDescripiton = RichToolDescription(
    description="""Tool for updating a task.

        User will query to you by asking "Update a task" or similar.
    """,
    use_when="When user wants to update a task.",
    side_effects=None,
)

def json_list_to_markdown_table(data):
    if not data:
        return "No data available."

    headers = data[0].keys()
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    rows = []
    for item in data:
        row = "| " + " | ".join(str(item.get(header, "")) for header in headers) + " |"
        rows.append(row)

    return "\n".join([header_line, separator_line] + rows)


@mcp.tool(description=ListTasksDescription.model_dump_json())
def list_tasks():
    """
    This tool is used to list all the tasks of a user.

    Args: No arguments required.

    Returns a markdown table with the list of tasks.
    """
    
    tasks = []

    for task in collection.find():

        tasks.append({
        "taskID": f"{task.get('_id')}",
        "taskTitle": f"{task.get('title', 'No Title')}",
        "dueData": f"{task.get('dueDate', 'No Due Date')}",
        "taskStatus": f"{task.get('status', 'No Status')}"
    })

    content = markdownify.markdownify(json_list_to_markdown_table(tasks))
    print(f"Tasks: {tasks}")
    return f"""List of all the tasks: {tasks}"""

@mcp.tool(description=CreateTasksDescription.model_dump_json())
def create_task(task: dict):
    """
    This tool is used to create a new task.

    Args: Task object with title, due date and status.

    User will query to you by asking "Create a new task" or similar.

    You have to return the title of the task, the due date and the status of the task in the following format strictly of JSON object without any markdown or any other formatting example is show below:

    {
        "title": "Task Title",
        "dueDate": "Due date mentioned by the user",
        "status": "Pending"
    }  
    """

    collection.insert_one({"title": task.get('title', 'No Title'),
                           "dueDate": task.get('dueDate', 'No Due Date'),
                           "status": task.get('status', 'Not Started')})
    
    tasks = []

    for task in collection.find():

        tasks.append({
        "taskID": f"{task.get('_id')}",
        "taskTitle": f"{task.get('title', 'No Title')}",
        "dueData": f"{task.get('dueDate', 'No Due Date')}",
        "taskStatus": f"{task.get('status', 'No Status')}"
    })
        
    print(tasks)

    content = markdownify.markdownify(json_list_to_markdown_table(tasks)) 

    return f"Task created successfully and here are all the created tasks: {content}"
     

@mcp.tool(description=DeleteTasksDescription.model_dump_json())
def delete_task(task_id: Annotated[str | None, "The ID of the task to delete which is not the task title. The task ID is in the form of: 68727fd9eb91baafc3996f62. If the task ID is not in the desired form please pass task_id = None."]= None):
    """
    This tool is used to delete a task.

    Args: Task ID to be deleted. The task ID is in the form of: 687d36d8766c89d1de50bb85. If the task ID is not in the desired form please pass task_id = None.

    User will query to you by asking "Delete a task" or similar.
     
    At first you will not be given the task ID, you will be given all the data from the database and based on that data you have to find the task ID and then pass that task ID to the tool's argument. Then the task will be deleted. 
    """


    if(task_id):
        print(f"task_id: {task_id}")
        collection.delete_one({"_id": ObjectId(task_id)})

        tasks = []

        for task in collection.find():

            tasks.append({
            "taskID": f"{task.get('_id')}",
            "taskTitle": f"{task.get('title', 'No Title')}",
            "dueData": f"{task.get('dueDate', 'No Due Date')}",
            "taskStatus": f"{task.get('status', 'No Status')}"
        })

        content = markdownify.markdownify(json_list_to_markdown_table(tasks))
        return f"""Task deleted successfully. Here is the updated list of tasks: {content}"""
    else:
        tasks = []

        for task in collection.find():

            tasks.append({
            "taskID": f"{task.get('_id')}",
            "taskTitle": f"{task.get('title', 'No Title')}",
            "dueData": f"{task.get('dueDate', 'No Due Date')}",
            "taskStatus": f"{task.get('status', 'No Status')}"
        })
            
        print(tasks)

        content = markdownify.markdownify(json_list_to_markdown_table(tasks))
        return f"""List of all the tasks: {content}"""

@mcp.tool(description=UpdateTaskDescripiton.model_dump_json())
def update_task(task_id: Annotated[str | None, "The ID of the task to delete which is not the task title. The task ID is in the form of: 68727fd9eb91baafc3996f62. If the task ID is not in the desired form please pass task_id = None."]= None, status: Annotated[str | None, "The new status of the task. If not provided, the task will not be updated."]= None):
    """
    This tool is used to update a task.

    Args: Task ID to be updated. The task ID is in the form of: 68727fd9eb91baafcxxxxxxx. If the task ID is not in the desired form please pass task_id = None.

    User will query to you by asking "Update a task" or similar.
     
    At first you will not be given the task ID, you will be given all the data from the database and based on that data you have to find the task ID and then pass that task ID to the tool's argument. Then the task will be updated. 
    """


    if(task_id):
        print(f"task_id: {task_id}")
        collection.update_one({"_id": ObjectId(task_id)}, {'$set': {"status": status}})

        tasks = []

        for task in collection.find():

            tasks.append({
            "taskID": f"{task.get('_id')}",
            "taskTitle": f"{task.get('title', 'No Title')}",
            "dueData": f"{task.get('dueDate', 'No Due Date')}",
            "taskStatus": f"{task.get('status', 'No Status')}"
        })

        content = markdownify.markdownify(json_list_to_markdown_table(tasks))
        return f"""Task updated successfully. Here is the updated list of tasks: {content}"""
    else:
        tasks = []

        for task in collection.find():

            tasks.append({
            "taskID": f"{task.get('_id')}",
            "taskTitle": f"{task.get('title', 'No Title')}",
            "dueData": f"{task.get('dueDate', 'No Due Date')}",
            "taskStatus": f"{task.get('status', 'No Status')}"
        })
            
        print(tasks)

        content = markdownify.markdownify(json_list_to_markdown_table(tasks))
        return f"""List of all the tasks: {content}"""

async def main():
    await mcp.run_async(
        "streamable-http",
        host="0.0.0.0",
        port=8080
    )

if __name__ == "__main__":
    print("hello mcp")
    import asyncio

    asyncio.run(main())
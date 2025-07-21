from pymongo import MongoClient

tasks = []

client = MongoClient('mongodb://localhost:27017/')
db = client['tasksDB']
collection = db['tasks']

for task in collection.find():
    # tasks += f"""
    #         [
    #             {{
    #                 "taskTitle": "{task.get('title', 'No Title')}",
    #                 "dueData": "{task.get('dueDate', 'No Due Date')}",
    #                 "taskStatus": "{task.get('status', 'No Status')}"
    #             }}
    #         ]
    #     """

    tasks.append(task)

# print(tasks)
    
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


markdown = json_list_to_markdown_table(tasks)
print(markdown)
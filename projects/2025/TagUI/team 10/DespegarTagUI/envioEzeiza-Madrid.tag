//This script sends images to a Discord channel using a webhook URL using Python within a TagUI script.
// Update the file path; it currently uses an absolute reference.
py begin
import requests
import json
import os # This is a built-in Python library for interacting with the operating system

# Define the Discord webhook URL
webhook_url = "https://discord.com/api/webhooks/1420131501483491501/z-Hdgn5SIQ-4id5jkWvKb98r2-RxKyiOobjE0X7uc441p3MkwR4PPk13mJN2Gyu6-DPh"

# Define the image file paths
file_path = "C:\\Users\\Emma\\AutomatizacionTP2RPA\\DespegarTagUI\\out\\Ezeiza-Madrid\\TablaPrecios.png"
path_vuelo1 = "C:\\Users\\Emma\\AutomatizacionTP2RPA\\DespegarTagUI\\out\\Ezeiza-Madrid\\Vuelo1.png"
path_vuelo2 = "C:\\Users\\Emma\\AutomatizacionTP2RPA\\DespegarTagUI\\out\\Ezeiza-Madrid\\Vuelo2.png"
path_vuelo3 = "C:\\Users\\Emma\\AutomatizacionTP2RPA\\DespegarTagUI\\out\\Ezeiza-Madrid\\Vuelo3.png"

# Define the JSON content for the message
payload_data = {
    "content": "Tabla de precios de vuelos Ezeiza - Madrid"
}

# Prepare the files dictionary
# The key (e.g., "file1") is not important, but must be unique for each file
files = {
    "file1": (os.path.basename(file_path), open(file_path, "rb"), "image/png"),
    "file2": (os.path.basename(path_vuelo1), open(path_vuelo1, "rb"), "image/png"),
    "file3": (os.path.basename(path_vuelo2), open(path_vuelo2, "rb"), "image/png"),
    "file4": (os.path.basename(path_vuelo3), open(path_vuelo3, "rb"), "image/png")
}

# Prepare the JSON payload
data = {
    "payload_json": (None, json.dumps(payload_data), "application/json")
}

try:
    # Send the POST request to the webhook
    response = requests.post(webhook_url, data=data, files=files)

    # Check the response status
    if response.status_code == 204:
        print("Files uploaded successfully to Discord.")
    else:
        print(f"Error uploading files. Status code: {response.status_code}")
        print(response.text)

finally:
    # It is crucial to close all open files to release resources
    for file_tuple in files.values():
        file_object = file_tuple[1]
        file_object.close()
py finish
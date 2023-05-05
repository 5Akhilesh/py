import datetime
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import csv
import io
import os
import json
from google.cloud import storage
from google.cloud import secretmanager


# Set the ID of the folder in your Google Drive where you want to create the sheet
FOLDER_ID = "1U78iI1deHrsr5AEllJ8STJ2RCLGEzZ0a40"

# Set the name of the sheet you want to create
SHEET_NAME = "VM-inventory"

# Set the scopes for the service account
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/spreadsheets"]

#################################################################
# Using Secret Manager
client = secretmanager.SecretManagerServiceClient()
name = f"projects/project_id/secrets/secret_name/versions/latest"
#################################################################

response = client.access_secret_version(name=name)
creds_json = response.payload.data.decode('UTF-8')
creds_dict = json.loads(creds_json)

creds = service_account.Credentials.from_service_account_info(info=creds_dict, scopes=SCOPES)

# Get the current month and year
now = datetime.datetime.now()
month_year = now.strftime("%B_%Y")

# Rename the old sheet to "VM-inventory-current month"
drive_service = build("drive", "v3", credentials=creds)
query = "name='VM-inventory'"
response = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
file_id = response['files'][0]['id']
file_metadata = {"name": "VM-inventory-" + month_year}
drive_service.files().update(fileId=file_id, body=file_metadata).execute()
print("Old sheet renamed to:", file_metadata["name"])

# Create the new Google Sheet in the specified folder
file_metadata = {
    "name": SHEET_NAME,
    "parents": [FOLDER_ID],
    "mimeType": "application/vnd.google-apps.spreadsheet"
}
sheet = drive_service.files().create(body=file_metadata).execute()

# Get the ID of the new sheet
sheet_id = sheet["id"]

# Print the URL of the new sheet
print("Created sheet:", sheet.get("webViewLink"))

# Open the CSV file from the GCS bucket
#bucket_name = "nms-inventory"
#blob_name = "instances.csv"
#storage_client = storage.Client.from_service_account_json("/home/harieshkumar_r/service-account.json")
#bucket = storage_client.get_bucket(bucket_name)
#blob = bucket.blob(blob_name)
#csv_data = blob.download_as_string().decode('utf-8')
with open("instances.csv", "r") as f:
    csv_data = f.read()
# Convert the CSV data to a list
data = csv_data.split('\n')
values = []
for row in data:
    values.append(row.split(','))

# Add the data from the CSV file to the new sheet
sheet_service = build("sheets", "v4", credentials=creds)
range_name = "Sheet1!A1"
value_input_option = "USER_ENTERED"
request_body = {
    "range": range_name,
    "values": values,
    "majorDimension": "ROWS"
}
try:
    response = sheet_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption=value_input_option,
        body=request_body
    ).execute()
    print("CSV data added to the sheet.")
except HttpError as error:
    print(f"An error occurred: {error}")
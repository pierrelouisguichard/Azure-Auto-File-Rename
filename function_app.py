import logging
import azure.functions as func
import dropbox
import os
import requests
from datetime import datetime

app = func.FunctionApp()

@app.schedule(schedule="*/1 9-17 * * 1-5", arg_name="myTimer", run_on_startup=True, use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    # Retrieve Dropbox credentials from environment variables
    DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
    DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
    DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
    DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')

    if not DROPBOX_ACCESS_TOKEN or not DROPBOX_REFRESH_TOKEN or not DROPBOX_APP_KEY or not DROPBOX_APP_SECRET:
        logging.error('Dropbox credentials are not set properly.')
        return

    # Initialize Dropbox client
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

    # Folder path in Dropbox to list files from
    dropbox_folder_path = '/cloud script test'  # Update to match your folder path
    logging.info(f'Listing files in Dropbox folder: {dropbox_folder_path}')

    try:
        # List files in the specified Dropbox folder
        result = dbx.files_list_folder(dropbox_folder_path)
        
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                original_filename = entry.name
                
                if not original_filename.startswith('20') or len(original_filename) < 13:
                    creation_date = entry.client_modified
                    formatted_date = creation_date.strftime('%Y_%m_%d')
                    new_filename = f'{formatted_date}_{original_filename}'
                    existing_files = [file.name for file in result.entries if isinstance(file, dropbox.files.FileMetadata)]
                    
                    unique_filename = new_filename
                    count = 1
                    while unique_filename in existing_files:
                        unique_filename = f'{formatted_date}_{count}_{original_filename}'
                        count += 1
                    
                    new_path = f'{dropbox_folder_path}/{unique_filename}'
                    dbx.files_move(entry.path_lower, new_path, autorename=False)
                    
                    logging.info(f'Renamed file: {original_filename} to {unique_filename}')
                else:
                    logging.info(f'Skipped renaming file: {original_filename} (already renamed)')
                
            elif isinstance(entry, dropbox.files.FolderMetadata):
                logging.info(f'Folder found: {entry.name}')
                
    except dropbox.exceptions.AuthError as err:
        if 'expired_access_token' in str(err):
            logging.info('Access token expired, attempting to refresh token...')
            if refresh_access_token():
                # Retry listing files after refreshing the token
                dbx = dropbox.Dropbox(os.getenv('DROPBOX_ACCESS_TOKEN'))
                result = dbx.files_list_folder(dropbox_folder_path)
                logging.info('Retrying with refreshed token...')
            else:
                logging.error('Failed to refresh access token.')
        else:
            logging.error(f'Dropbox API error: {err}')
    except Exception as ex:
        logging.error(f'Unexpected error: {ex}')

    logging.info('Python function execution completed.')

def refresh_access_token() -> bool:
    try:
        DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
        DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
        DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')

        response = requests.post('https://api.dropbox.com/oauth2/token', data={
            'grant_type': 'refresh_token',
            'refresh_token': DROPBOX_REFRESH_TOKEN
        }, auth=(DROPBOX_APP_KEY, DROPBOX_APP_SECRET))

        if response.status_code == 200:
            new_tokens = response.json()
            new_access_token = new_tokens['access_token']
            os.environ['DROPBOX_ACCESS_TOKEN'] = new_access_token
            logging.info('Access token refreshed successfully.')
            return True
        else:
            logging.error(f'Failed to refresh access token: {response.content}')
            return False
    except Exception as ex:
        logging.error(f'Unexpected error while refreshing token: {ex}')
        return False
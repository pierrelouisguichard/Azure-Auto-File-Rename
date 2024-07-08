import logging
import azure.functions as func
import dropbox
import os
from datetime import datetime

app = func.FunctionApp()

@app.schedule(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    # Retrieve Dropbox access token from environment variables
    DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
    if not DROPBOX_ACCESS_TOKEN:
        logging.error('Dropbox access token is not set.')
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
                # Original file name
                original_filename = entry.name
                
                # Check if file already follows the naming convention
                if not original_filename.startswith('20') or len(original_filename) < 13:
                    # Retrieve creation date
                    creation_date = entry.client_modified
                    formatted_date = creation_date.strftime('%Y_%m_%d')
                    
                    # New file name with creation date
                    new_filename = f'{formatted_date}_{original_filename}'
                    
                    # Check if the new filename already exists in Dropbox
                    existing_files = [file.name for file in result.entries if isinstance(file, dropbox.files.FileMetadata)]
                    
                    # Make the new filename unique if it already exists
                    unique_filename = new_filename
                    count = 1
                    while unique_filename in existing_files:
                        unique_filename = f'{formatted_date}_{count}_{original_filename}'
                        count += 1
                    
                    # Perform file rename operation
                    new_path = f'{dropbox_folder_path}/{unique_filename}'
                    dbx.files_move(entry.path_lower, new_path, autorename=False)
                    
                    logging.info(f'Renamed file: {original_filename} to {unique_filename}')
                    
                else:
                    logging.info(f'Skipped renaming file: {original_filename} (already renamed)')
                
            elif isinstance(entry, dropbox.files.FolderMetadata):
                logging.info(f'Folder found: {entry.name}')
                
    except dropbox.exceptions.ApiError as err:
        logging.error(f'Dropbox API error: {err}')
    except Exception as ex:
        logging.error(f'Unexpected error: {ex}')

    logging.info('Python function execution completed.')
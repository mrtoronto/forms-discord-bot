import json
import os
from google.cloud import storage
from local_settings import firestore_creds
bucket_id = "forms-bot"
import logging

logger = logging.getLogger('FORMS_BOT')

def _init_creds():
	creds_filename = '/tmp/creds.json'
	try:
		os.unlink(creds_filename)
	except:
		pass

	with open(creds_filename, 'w') as f:
		json.dump(firestore_creds, f, indent=4, default=str)

_init_creds()
storage_client = storage.Client.from_service_account_json('/tmp/creds.json')
bucket = storage_client.bucket(bucket_id)

def upload_blob(
	source_filename, 
	remote_filename):
	"""
	Uploads a file to Google Cloud Storage
	"""

	### Upload the file
	blob = bucket.blob(remote_filename)
	if blob.exists():
		logger.info(f"File {remote_filename} already exists. Deleting it.")
		blob.delete()
		
	blob.upload_from_filename(source_filename)
	blob.make_public()
	logger.info(f"File {source_filename} uploaded to {remote_filename}.")
	
	return blob.public_url


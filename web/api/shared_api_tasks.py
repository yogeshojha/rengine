# include all the celery tasks to be used in the API, do not put in tasks.py
import requests

from reNgine.common_func import create_inappnotification, get_hackerone_key_username
from reNgine.definitions import PROJECT_LEVEL_NOTIFICATION, HACKERONE_ALLOWED_ASSET_TYPES
from reNgine.celery import app
from reNgine.database_utils import bulk_import_targets

@app.task(name='import_hackerone_programs_task', bind=False, queue='api_queue')
def import_hackerone_programs_task(handles, project_slug):
	"""
	Runs in the background to import programs from HackerOne

	Args:
		handles (list): List of handles to import
		project_slug (str): Slug of the project
	Returns:
		None
		rather creates inapp notifications
	"""
	def fetch_program_details_from_hackerone(program_handle):
		url = f'https://api.hackerone.com/v1/hackers/programs/{program_handle}'
		headers = {'Accept': 'application/json'}
		username, api_key = get_hackerone_key_username()

		response = requests.get(
			url,
			headers=headers,
			auth=(username, api_key)
		)

		if response.status_code == 200:
			return response.json()
		else:
			return None

	for handle in handles:
		program_details = fetch_program_details_from_hackerone(handle)
		if program_details:
			# Thanks, some parts of this logics were originally written by @null-ref-0000
			# via PR https://github.com/yogeshojha/rengine/pull/1410
			try:
				program_name = program_details['attributes']['name']

				assets = []
				scopes = program_details['relationships']['structured_scopes']['data']
				for scope in scopes:
					asset_type = scope['attributes']['asset_type']
					asset_identifier = scope['attributes']['asset_identifier']

					# we need to filter the scope that are supported by reNgine now
					if asset_type in HACKERONE_ALLOWED_ASSET_TYPES:
						assets.append(asset_identifier)
					
					# in some cases asset_type is OTHER and may contain the asset
					elif asset_type == 'OTHER' and ('.' in asset_identifier or asset_identifier.startswith('http')):
						assets.append(asset_identifier)

				# cleanup assets
				assets = list(set(assets))

				# convert assets to list of dict with name and description
				assets = [{'name': asset, 'description': None} for asset in assets]
				bulk_import_targets(
					targets=assets,
					project_slug=project_slug,
					organization_name=program_name,
					org_description=None,
					h1_team_handle=handle
				)
			
				create_inappnotification(
					title=f"HackerOne Program Imported: {handle}",
					description=f"The program '{program_name}' from hackerone has been successfully imported.",
					notification_type=PROJECT_LEVEL_NOTIFICATION,
					project_slug=project_slug,
					icon="mdi-check-circle",
					status='success'
				)

			except Exception as e:
				create_inappnotification(
				title=f"HackerOne Program Import Failed: {handle}",
				description=f"Failed to import program from hackerone with handle '{handle}'. {str(e)}",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				project_slug=project_slug,
				icon="mdi-alert-circle",
				status='error'
			)
		else:
			create_inappnotification(
				title=f"HackerOne Program Import Failed: {handle}",
				description=f"Failed to import program from hackerone with handle '{handle}'. Program details could not be fetched.",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				project_slug=project_slug,
				icon="mdi-alert-circle",
				status='error'
			)

	create_inappnotification(
		title="HackerOne Program Import Completed",
		description=f"Import process for {len(handles)} program(s) has completed.",
		notification_type=PROJECT_LEVEL_NOTIFICATION,
		project_slug=project_slug,
		icon="mdi-check-all",
		status='success'
	)
# include all the celery tasks to be used in the API, do not put in tasks.py
import requests

from reNgine.common_func import create_inappnotification, get_hackerone_key_username
from reNgine.definitions import PROJECT_LEVEL_NOTIFICATION, HACKERONE_ALLOWED_ASSET_TYPES
from reNgine.celery import app
from reNgine.database_utils import bulk_import_targets

@app.task(name='import_hackerone_programs_task', bind=False, queue='api_queue')
def import_hackerone_programs_task(handles, project_slug, is_sync = False):
	"""
	Runs in the background to import programs from HackerOne

	Args:
		handles (list): List of handles to import
		project_slug (str): Slug of the project
		is_sync (bool): If the import is a sync operation
	Returns:
		None
		rather creates inapp notifications
	"""
	def fetch_program_details_from_hackerone(program_handle):
		url = f'https://api.hackerone.com/v1/hackers/programs/{program_handle}'
		headers = {'Accept': 'application/json'}
		creds = get_hackerone_key_username()

		if not creds:
			raise Exception("HackerOne API credentials not configured")
		
		username, api_key = creds

		response = requests.get(
			url,
			headers=headers,
			auth=(username, api_key)
		)

		if response.status_code == 401:
			raise Exception("HackerOne API credentials are invalid")

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
					eligible_for_submission = scope['attributes']['eligible_for_submission']

					# for now we should ignore the scope that are not eligible for submission
					# in future release we will add this in target out_of_scope

					# we need to filter the scope that are supported by reNgine now
					if asset_type in HACKERONE_ALLOWED_ASSET_TYPES and eligible_for_submission:
						assets.append(asset_identifier)
					
					# in some cases asset_type is OTHER and may contain the asset
					elif asset_type == 'OTHER' and ('.' in asset_identifier or asset_identifier.startswith('http')):
						assets.append(asset_identifier)

				# cleanup assets
				assets = list(set(assets))

				# convert assets to list of dict with name and description
				assets = [{'name': asset, 'description': None} for asset in assets]
				new_targets_added = bulk_import_targets(
					targets=assets,
					project_slug=project_slug,
					organization_name=program_name,
					org_description='Imported from Hackerone',
					h1_team_handle=handle
				)

				if new_targets_added:
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

	if is_sync:
		title = "HackerOne Program Sync Completed"
		description = f"Sync process for {len(handles)} program(s) has completed."
	else:
		title = "HackerOne Program Import Completed"
		description = f"Import process for {len(handles)} program(s) has completed."

	create_inappnotification(
		title=title,
		description=description,
		notification_type=PROJECT_LEVEL_NOTIFICATION,
		project_slug=project_slug,
		icon="mdi-check-all",
		status='success'
	)


@app.task(name='sync_bookmarked_programs_task', bind=False, queue='api_queue')
def sync_bookmarked_programs_task(project_slug):
	"""
		Runs in the background to sync bookmarked programs from HackerOne

		Args:
			project_slug (str): Slug of the project
		Returns:
			None
			Creates in-app notifications for progress and results
	"""

	def fetch_bookmarked_programs():
		url = f'https://api.hackerone.com/v1/hackers/programs?&page[size]=100'
		headers = {'Accept': 'application/json'}
		bookmarked_programs = []
		
		credentials = get_hackerone_key_username()
		if not credentials:
			raise Exception("HackerOne API credentials not configured")
		
		username, api_key = credentials

		while url:
			response = requests.get(
				url,
				headers=headers,
				auth=(username, api_key)
			)

			if response.status_code == 401:
				raise Exception("HackerOne API credentials are invalid")
			elif response.status_code != 200:
				raise Exception(f"HackerOne API request failed with status code {response.status_code}")

			data = response.json()
			programs = data['data']
			bookmarked = [p for p in programs if p['attributes']['bookmarked']]
			bookmarked_programs.extend(bookmarked)
			
			url = data['links'].get('next')

		return bookmarked_programs

	try:
		bookmarked_programs = fetch_bookmarked_programs()
		handles = [program['attributes']['handle'] for program in bookmarked_programs]

		if not handles:
			create_inappnotification(
				title="HackerOne Bookmarked Programs Sync Completed",
				description="No bookmarked programs found.",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				project_slug=project_slug,
				icon="mdi-information",
				status='info'
			)
			return

		import_hackerone_programs_task.delay(handles, project_slug, is_sync=True)

		create_inappnotification(
			title="HackerOne Bookmarked Programs Sync Progress",
			description=f"Found {len(handles)} bookmarked program(s). Starting import process.",
			notification_type=PROJECT_LEVEL_NOTIFICATION,
			project_slug=project_slug,
			icon="mdi-progress-check",
			status='info'
		)

	except Exception as e:
		create_inappnotification(
			title="HackerOne Bookmarked Programs Sync Failed",
			description=f"Failed to sync bookmarked programs: {str(e)}",
			notification_type=PROJECT_LEVEL_NOTIFICATION,
			project_slug=project_slug,
			icon="mdi-alert-circle",
			status='error'
		)

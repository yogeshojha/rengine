// Mirrors shared/definitions/oast.py
export enum OastMode {
	OFF = 'off',
	SELF_HOSTED = 'self_hosted',
	PUBLIC = 'public'
}

export const OAST_MODES: OastMode[] = [OastMode.OFF, OastMode.SELF_HOSTED, OastMode.PUBLIC];

export const CALLBACK_SERVER = 'Callback server';

export const OAST_MODE_LABELS: Record<OastMode, string> = {
	[OastMode.OFF]: 'Off',
	[OastMode.SELF_HOSTED]: 'Self-hosted',
	[OastMode.PUBLIC]: 'Public'
};

export const OAST_MODE_HELP: Record<OastMode, string> = {
	[OastMode.OFF]: 'Checks that need a callback are skipped.',
	[OastMode.SELF_HOSTED]:
		'An interactsh server this instance operates. Callbacks reach that server.',
	[OastMode.PUBLIC]:
		'The interact.sh servers ProjectDiscovery operates. A callback reaches a third party.'
};

export const PUBLIC_ACK =
	'Callbacks reach interact.sh, operated by ProjectDiscovery. A payload can make a target send environment variables, instance metadata or credentials with the callback.';

export const DEFAULT_WAIT_SECONDS = 60;
export const MIN_WAIT_SECONDS = 0;
export const MAX_WAIT_SECONDS = 900;
export const WAIT_STEPS = [0, 15, 30, 60, 120, 300, 600, 900];

// the callback a finding carries
export const INTERACTION_LABELS: Record<string, string> = {
	protocol: 'Channel',
	'remote-address': 'Source',
	timestamp: 'Received',
	'full-id': 'Callback host',
	'unique-id': 'Callback host',
	'q-type': 'Record'
};

export const INTERACTION_RAW_LABELS: Record<string, string> = {
	'raw-request': 'Callback request',
	'raw-response': 'Callback response'
};

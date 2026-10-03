// mirrors shared/definitions/launch.py
export const CONTEXT_NOUN = 'Context';
export const ENGINE_NOUN = 'Engine';

export function credentialLaunchRefusal(noun: string, name: string): string {
	return `${noun} ${name} carries credentials. Its creator or an administrator can launch with it.`;
}

interface CredentialHolder {
	carries_credentials: boolean;
	created_by: string;
}

interface Viewer {
	id: string;
	is_superuser: boolean;
}

/** The viewer may not launch with this context or engine. */
export function launchLocked(row: CredentialHolder, user: Viewer | null): boolean {
	return row.carries_credentials && !user?.is_superuser && row.created_by !== user?.id;
}

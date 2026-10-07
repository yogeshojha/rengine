import Boxes from '@lucide/svelte/icons/boxes';
import FolderOpen from '@lucide/svelte/icons/folder-open';
import FileSearch from '@lucide/svelte/icons/file-search';
import Lock from '@lucide/svelte/icons/lock';
import CircleHelp from '@lucide/svelte/icons/circle-help';
import type { IconComponent } from '$lib/config/icons';
import { Severity } from '$lib/config/vulnerabilities';

export const CLOUD_STORAGE_STAGE = 'cloud_storage';
export const CLOUD_STORAGE_TAB = 'cloud-storage';
export const CLOUD_STORAGE_TAB_LABEL = 'Cloud storage';
export const CLOUD_STORAGE_TAB_ICON: IconComponent = Boxes;

export enum Provider {
	AWS_S3 = 'aws_s3',
	GCS = 'gcs',
	AZURE_BLOB = 'azure_blob',
	FIREBASE_RTDB = 'firebase_rtdb',
	DO_SPACES = 'do_spaces',
	R2 = 'r2'
}

export const PROVIDER_ORDER: readonly Provider[] = [
	Provider.AWS_S3,
	Provider.GCS,
	Provider.AZURE_BLOB,
	Provider.FIREBASE_RTDB,
	Provider.DO_SPACES,
	Provider.R2
];

export const PROVIDER_LABELS: Record<string, string> = {
	[Provider.AWS_S3]: 'AWS S3',
	[Provider.GCS]: 'Google Cloud Storage',
	[Provider.AZURE_BLOB]: 'Azure Blob',
	[Provider.FIREBASE_RTDB]: 'Firebase',
	[Provider.DO_SPACES]: 'DigitalOcean Spaces',
	[Provider.R2]: 'Cloudflare R2'
};

export enum Source {
	REFERENCED = 'referenced',
	HOSTNAME = 'hostname',
	GUESSED = 'guessed'
}

export const SOURCE_ORDER: readonly Source[] = [Source.REFERENCED, Source.HOSTNAME, Source.GUESSED];

export const SOURCE_LABELS: Record<string, string> = {
	[Source.REFERENCED]: 'Referenced',
	[Source.HOSTNAME]: 'Named after a host',
	[Source.GUESSED]: 'Guessed'
};

export const SOURCE_HELP: Record<string, string> = {
	[Source.REFERENCED]: 'A CNAME, page or script the scan read points at this bucket.',
	[Source.HOSTNAME]: 'A discovered hostname is also the bucket name.',
	[Source.GUESSED]: "The bucket name is the target's name joined with a common word."
};

export const OWNED_SOURCES: ReadonlySet<string> = new Set([Source.REFERENCED, Source.HOSTNAME]);

export enum Access {
	READABLE = 'readable',
	LISTABLE = 'listable',
	PROTECTED = 'protected',
	MISSING = 'missing'
}

export interface AccessSpec {
	key: Access;
	label: string;
	help: string;
	icon: IconComponent;
	severity: Severity;
}

export const ACCESS: AccessSpec[] = [
	{
		key: Access.LISTABLE,
		label: 'Listable',
		help: 'Anyone can list the objects in the bucket.',
		icon: FolderOpen,
		severity: Severity.HIGH
	},
	{
		key: Access.READABLE,
		label: 'Readable',
		help: "Anyone can read the bucket's contents.",
		icon: FileSearch,
		severity: Severity.HIGH
	},
	{
		key: Access.PROTECTED,
		label: 'Protected',
		help: 'The bucket exists and refuses anonymous access.',
		icon: Lock,
		severity: Severity.INFO
	},
	{
		key: Access.MISSING,
		label: 'Not found',
		help: 'No bucket answers to this name.',
		icon: CircleHelp,
		severity: Severity.INFO
	}
];

export const ACCESS_ORDER: readonly Access[] = ACCESS.map((a) => a.key);
export const ACCESS_BY_KEY: Record<string, AccessSpec> = Object.fromEntries(
	ACCESS.map((a) => [a.key, a])
);
export const OPEN_ACCESS: ReadonlySet<string> = new Set([Access.LISTABLE, Access.READABLE]);

export enum ReviewState {
	OPEN = 'open',
	CONFIRMED = 'confirmed',
	IGNORED = 'ignored'
}

export const STATE_LABELS: Record<string, string> = {
	[ReviewState.OPEN]: 'Open',
	[ReviewState.CONFIRMED]: 'Confirmed',
	[ReviewState.IGNORED]: 'Ignored'
};

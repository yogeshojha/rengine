import FileText from '@lucide/svelte/icons/file-text';
import Braces from '@lucide/svelte/icons/braces';
import FileCode from '@lucide/svelte/icons/file-code';
import Palette from '@lucide/svelte/icons/palette';
import FileType from '@lucide/svelte/icons/file-type';
import Image from '@lucide/svelte/icons/image';
import Film from '@lucide/svelte/icons/film';
import Database from '@lucide/svelte/icons/database';
import FileArchive from '@lucide/svelte/icons/file-archive';
import CircleHelp from '@lucide/svelte/icons/circle-help';
import Spider from '@lucide/svelte/icons/bug';
import Archive from '@lucide/svelte/icons/archive';
import FileSearch from '@lucide/svelte/icons/file-search';
import Map from '@lucide/svelte/icons/map';
import BotIcon from '@lucide/svelte/icons/bot';
import Home from '@lucide/svelte/icons/home';
import Braces2 from '@lucide/svelte/icons/file-json';
import Crosshair from '@lucide/svelte/icons/crosshair';
import Upload from '@lucide/svelte/icons/upload';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import Folder from '@lucide/svelte/icons/folder';
import FolderOpen from '@lucide/svelte/icons/folder-open';
import FolderCog from '@lucide/svelte/icons/folder-cog';
import FolderLock from '@lucide/svelte/icons/folder-lock';
import FolderCode from '@lucide/svelte/icons/folder-code';
import FolderKey from '@lucide/svelte/icons/folder-key';
import Folders from '@lucide/svelte/icons/folders';
import type { IconComponent } from './icons';

// mirrors shared/definitions/endpoints.py EndpointClass
export enum EndpointClass {
	PAGE = 'page',
	API = 'api',
	SCRIPT = 'script',
	STYLE = 'style',
	DOCUMENT = 'document',
	IMAGE = 'image',
	MEDIA = 'media',
	DATA = 'data',
	ARCHIVE_FILE = 'archive_file',
	OTHER = 'other'
}

export const ENDPOINT_CLASS_ORDER: EndpointClass[] = [
	EndpointClass.PAGE,
	EndpointClass.API,
	EndpointClass.SCRIPT,
	EndpointClass.DATA,
	EndpointClass.DOCUMENT,
	EndpointClass.ARCHIVE_FILE,
	EndpointClass.STYLE,
	EndpointClass.IMAGE,
	EndpointClass.MEDIA,
	EndpointClass.OTHER
];

export const ENDPOINT_CLASS_LABELS: Record<string, string> = {
	[EndpointClass.PAGE]: 'Pages',
	[EndpointClass.API]: 'API',
	[EndpointClass.SCRIPT]: 'Scripts',
	[EndpointClass.STYLE]: 'Styles',
	[EndpointClass.DOCUMENT]: 'Documents',
	[EndpointClass.IMAGE]: 'Images',
	[EndpointClass.MEDIA]: 'Media',
	[EndpointClass.DATA]: 'Data',
	[EndpointClass.ARCHIVE_FILE]: 'Archives',
	[EndpointClass.OTHER]: 'Other'
};

export const ENDPOINT_CLASS_ICONS: Record<string, IconComponent> = {
	[EndpointClass.PAGE]: FileText,
	[EndpointClass.API]: Braces,
	[EndpointClass.SCRIPT]: FileCode,
	[EndpointClass.STYLE]: Palette,
	[EndpointClass.DOCUMENT]: FileType,
	[EndpointClass.IMAGE]: Image,
	[EndpointClass.MEDIA]: Film,
	[EndpointClass.DATA]: Database,
	[EndpointClass.ARCHIVE_FILE]: FileArchive,
	[EndpointClass.OTHER]: CircleHelp
};

export const ENDPOINT_CLASS_FILL: Record<string, string> = {
	[EndpointClass.PAGE]: 'var(--chart-1)',
	[EndpointClass.API]: 'var(--chart-2)',
	[EndpointClass.SCRIPT]: 'var(--chart-3)',
	[EndpointClass.DATA]: 'var(--chart-4)',
	[EndpointClass.DOCUMENT]: 'var(--chart-5)',
	[EndpointClass.ARCHIVE_FILE]: 'color-mix(in oklch, var(--chart-4) 60%, transparent)',
	[EndpointClass.STYLE]: 'color-mix(in oklch, var(--chart-3) 50%, transparent)',
	[EndpointClass.IMAGE]: 'color-mix(in oklch, var(--muted-foreground) 45%, transparent)',
	[EndpointClass.MEDIA]: 'color-mix(in oklch, var(--muted-foreground) 35%, transparent)',
	[EndpointClass.OTHER]: 'color-mix(in oklch, var(--muted-foreground) 25%, transparent)'
};

// mirrors shared/definitions/endpoints.py STATIC_CLASSES + STATIC_EXTENSIONS
export const STATIC_CLASSES: ReadonlySet<string> = new Set([
	EndpointClass.STYLE,
	EndpointClass.IMAGE,
	EndpointClass.MEDIA
]);

// mirrors shared/definitions/endpoints.py FolderGlyph
export enum FolderGlyph {
	FOLDER = 'folder',
	ADMIN = 'admin',
	SENSITIVE = 'sensitive',
	API = 'api',
	AUTH = 'auth'
}

export const FOLDER_GLYPH_ICONS: Record<string, IconComponent> = {
	[FolderGlyph.FOLDER]: Folder,
	[FolderGlyph.ADMIN]: FolderCog,
	[FolderGlyph.SENSITIVE]: FolderLock,
	[FolderGlyph.API]: FolderCode,
	[FolderGlyph.AUTH]: FolderKey,
	group: Folders
};

export const FOLDER_OPEN_ICON: IconComponent = FolderOpen;

export const FOLDER_GLYPH_TONE: Record<string, string> = {
	[FolderGlyph.FOLDER]: 'text-muted-foreground',
	[FolderGlyph.ADMIN]: 'text-warning',
	[FolderGlyph.SENSITIVE]: 'text-destructive',
	[FolderGlyph.API]: 'text-chart-2',
	[FolderGlyph.AUTH]: 'text-warning',
	group: 'text-muted-foreground'
};

export const FOLDER_GLYPH_LABELS: Record<string, string> = {
	[FolderGlyph.FOLDER]: 'Folder',
	[FolderGlyph.ADMIN]: 'Holds an administrative or diagnostic interface',
	[FolderGlyph.SENSITIVE]: 'Holds a credential, backup or version control file',
	[FolderGlyph.API]: 'Mostly API routes',
	[FolderGlyph.AUTH]: 'Holds an authentication boundary',
	group: 'Folders that share one layout'
};

export const ENDPOINT_CLASS_TONE: Record<string, string> = {
	[EndpointClass.API]: 'text-chart-2'
};

// mirrors shared/definitions/endpoints.py EndpointSource
export enum EndpointSource {
	SEED = 'seed',
	RESPONSE_MINING = 'response_mining',
	CRAWL = 'crawl',
	ROBOTS = 'robots',
	SITEMAP = 'sitemap',
	ARCHIVE = 'archive',
	DEEP_ARCHIVE = 'deep_archive',
	JS = 'js',
	FUZZ = 'fuzz',
	PARAM_MINING = 'param_mining',
	VULN_SCAN = 'vuln_scan',
	IMPORT = 'import',
	OTHER = 'other'
}

// mirrors shared/definitions/endpoints.py: the verification pass reports coverage
// but never discovers, so it is not an EndpointSource
export const PROBE_COVERAGE_SOURCE = 'probe';

export const SOURCE_LABELS: Record<string, string> = {
	[EndpointSource.SEED]: 'Site root',
	[EndpointSource.RESPONSE_MINING]: 'Response mining',
	[EndpointSource.CRAWL]: 'Crawl',
	[EndpointSource.ROBOTS]: 'robots.txt',
	[EndpointSource.SITEMAP]: 'sitemap.xml',
	[EndpointSource.ARCHIVE]: 'Archive',
	[EndpointSource.DEEP_ARCHIVE]: 'Deep archive',
	[EndpointSource.JS]: 'JavaScript',
	[EndpointSource.FUZZ]: 'Content discovery',
	[EndpointSource.PARAM_MINING]: 'Parameter mining',
	[EndpointSource.VULN_SCAN]: 'Vulnerability scan',
	[EndpointSource.IMPORT]: 'Imported',
	[EndpointSource.OTHER]: 'Other'
};

export const COVERAGE_SOURCE_LABELS: Record<string, string> = {
	...SOURCE_LABELS,
	[PROBE_COVERAGE_SOURCE]: 'Verification'
};

export const SOURCE_ICONS: Record<string, IconComponent> = {
	[EndpointSource.SEED]: Home,
	[EndpointSource.RESPONSE_MINING]: FileSearch,
	[EndpointSource.CRAWL]: Spider,
	[EndpointSource.ROBOTS]: BotIcon,
	[EndpointSource.SITEMAP]: Map,
	[EndpointSource.ARCHIVE]: Archive,
	[EndpointSource.DEEP_ARCHIVE]: Archive,
	[EndpointSource.JS]: Braces2,
	[EndpointSource.FUZZ]: Crosshair,
	[EndpointSource.PARAM_MINING]: Crosshair,
	[EndpointSource.VULN_SCAN]: ShieldAlert,
	[EndpointSource.IMPORT]: Upload,
	[EndpointSource.OTHER]: CircleHelp
};

// a source that never contacts the target reads differently from one that does
export const PASSIVE_SOURCES: ReadonlySet<string> = new Set([
	EndpointSource.SEED,
	EndpointSource.RESPONSE_MINING,
	EndpointSource.ARCHIVE,
	EndpointSource.DEEP_ARCHIVE,
	EndpointSource.VULN_SCAN,
	EndpointSource.IMPORT,
	EndpointSource.OTHER
]);

export const ARCHIVE_SOURCES: ReadonlySet<string> = new Set([
	EndpointSource.ARCHIVE,
	EndpointSource.DEEP_ARCHIVE
]);

// mirrors ParamInterest + PathInterest
export const INTEREST_LABELS: Record<string, string> = {
	idor: 'Object reference',
	open_redirect: 'Open redirect',
	ssrf: 'Server-side request',
	traversal: 'Path traversal',
	sqli: 'SQL injection',
	xss: 'Cross-site scripting',
	rce: 'Command execution',
	ssti: 'Template injection',
	upload: 'File upload',
	debug: 'Debug switch',
	vcs: 'Version control',
	secrets: 'Credential file',
	backup: 'Backup or temporary file',
	admin: 'Administrative interface',
	api_doc: 'API documentation',
	debug_endpoint: 'Diagnostic endpoint',
	auth: 'Authentication',
	infra: 'Infrastructure service'
};

// the interests that describe an exposed file rather than an input to test
export const SENSITIVE_INTEREST: ReadonlySet<string> = new Set(['vcs', 'secrets', 'backup']);

export const STATUS_CLASS_LABELS: Record<string, string> = {
	'2xx': 'OK',
	'3xx': 'Redirect',
	'4xx': 'Client error',
	'5xx': 'Server error',
	none: 'Not checked'
};

export const STATUS_CLASS_FILL: Record<string, string> = {
	'2xx': 'var(--success)',
	'3xx': 'var(--info)',
	'4xx': 'var(--warning)',
	'5xx': 'var(--destructive)',
	none: 'color-mix(in oklch, var(--muted-foreground) 30%, transparent)'
};

export function statusClassOf(status: number | null | undefined): string {
	if (status == null) return 'none';
	if (status < 300) return '2xx';
	if (status < 400) return '3xx';
	if (status < 500) return '4xx';
	return '5xx';
}

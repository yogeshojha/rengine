import Network from '@lucide/svelte/icons/network';
import Link2 from '@lucide/svelte/icons/link-2';
import Heading from '@lucide/svelte/icons/heading';
import Image from '@lucide/svelte/icons/image';
import FileDigit from '@lucide/svelte/icons/file-digit';
import Fingerprint from '@lucide/svelte/icons/fingerprint';
import FileBadge from '@lucide/svelte/icons/file-badge';
import Layers from '@lucide/svelte/icons/layers';
import Server from '@lucide/svelte/icons/server';
import Cloud from '@lucide/svelte/icons/cloud';
import type { IconComponent } from './icons';

export const CORRELATION_TAB = 'correlation';

// mirrors shared/definitions/correlation.py CorrelationKind
export enum CorrelationKind {
	IP = 'ip',
	CNAME = 'cname',
	TITLE = 'title',
	FAVICON = 'favicon',
	BODY = 'content_hash',
	JARM = 'jarm',
	CERT_ISSUER = 'cert.issuer',
	TECH = 'tech',
	SERVER = 'server',
	CDN = 'cdn'
}

export const KIND_ICONS: Record<string, IconComponent> = {
	[CorrelationKind.IP]: Network,
	[CorrelationKind.CNAME]: Link2,
	[CorrelationKind.TITLE]: Heading,
	[CorrelationKind.FAVICON]: Image,
	[CorrelationKind.BODY]: FileDigit,
	[CorrelationKind.JARM]: Fingerprint,
	[CorrelationKind.CERT_ISSUER]: FileBadge,
	[CorrelationKind.TECH]: Layers,
	[CorrelationKind.SERVER]: Server,
	[CorrelationKind.CDN]: Cloud
};

// the strong identities take the chart scale; the infrastructure kinds share the neutral ink
export const KIND_COLOR_VAR: Record<string, string> = {
	[CorrelationKind.IP]: '--chart-1',
	[CorrelationKind.CNAME]: '--chart-5',
	[CorrelationKind.TITLE]: '--chart-2',
	[CorrelationKind.FAVICON]: '--chart-4',
	[CorrelationKind.BODY]: '--chart-3',
	[CorrelationKind.JARM]: '--chart-3',
	[CorrelationKind.CERT_ISSUER]: '--chart-4',
	[CorrelationKind.TECH]: '--muted-foreground',
	[CorrelationKind.SERVER]: '--muted-foreground',
	[CorrelationKind.CDN]: '--muted-foreground'
};

// two kinds share a hue only when one of them is drawn with a dashed ring
export const KIND_DASHED: ReadonlySet<string> = new Set([
	CorrelationKind.JARM,
	CorrelationKind.CERT_ISSUER
]);

export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 5;

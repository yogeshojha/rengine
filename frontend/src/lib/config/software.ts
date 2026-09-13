export enum VersionSource {
	BANNER = 'banner',
	FINGERPRINT = 'fingerprint'
}

export const VERSION_SOURCE_LABELS: Record<string, string> = {
	[VersionSource.BANNER]: 'Server header',
	[VersionSource.FINGERPRINT]: 'Fingerprint'
};

export const VERSION_SOURCE_HELP: Record<string, string> = {
	[VersionSource.BANNER]: 'Version stated in a server response header.',
	[VersionSource.FINGERPRINT]: 'Version read from the page body.'
};

export enum Caveat {
	BACKPORT = 'backport',
	CONDITIONAL = 'conditional',
	FINGERPRINT = 'fingerprint',
	COARSE = 'coarse'
}

export const CAVEAT_LABELS: Record<string, string> = {
	[Caveat.BACKPORT]: 'Distribution build',
	[Caveat.CONDITIONAL]: 'Conditional',
	[Caveat.FINGERPRINT]: 'Fingerprinted version',
	[Caveat.COARSE]: 'Major version only'
};

export const CAVEAT_HELP: Record<string, string> = {
	[Caveat.BACKPORT]:
		'The banner names a distribution build. Fixes may land without a version change.',
	[Caveat.CONDITIONAL]: 'NVD ties this CVE to a further component this scan did not identify.',
	[Caveat.FINGERPRINT]: 'The version was read from the page body.',
	[Caveat.COARSE]:
		'Only a major version was reported. The match covers every release in that series.'
};

export const CAVEAT_ORDER: string[] = [
	Caveat.BACKPORT,
	Caveat.CONDITIONAL,
	Caveat.FINGERPRINT,
	Caveat.COARSE
];

export enum Confidence {
	HIGH = 'high',
	MEDIUM = 'medium',
	LOW = 'low'
}

export const CONFIDENCE_LABELS: Record<string, string> = {
	[Confidence.HIGH]: 'High',
	[Confidence.MEDIUM]: 'Medium',
	[Confidence.LOW]: 'Low'
};

export const CONFIDENCE_HELP: Record<string, string> = {
	[Confidence.HIGH]: 'The server stated the version and NVD names no further condition.',
	[Confidence.MEDIUM]: 'One part of the match is unverified.',
	[Confidence.LOW]: 'Two or more parts of the match are unverified.'
};

export const CONFIDENCE_ORDER: string[] = [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW];

export const CONFIDENCE_VARIANT: Record<string, 'default' | 'secondary' | 'outline'> = {
	[Confidence.HIGH]: 'default',
	[Confidence.MEDIUM]: 'secondary',
	[Confidence.LOW]: 'outline'
};

export const CONFIDENCE_TEXT: Record<string, string> = {
	[Confidence.HIGH]: 'text-foreground',
	[Confidence.MEDIUM]: 'text-muted-foreground',
	[Confidence.LOW]: 'text-muted-foreground/70'
};

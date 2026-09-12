export enum VersionSource {
	BANNER = 'banner',
	FINGERPRINT = 'fingerprint'
}

export const VERSION_SOURCE_LABELS: Record<string, string> = {
	[VersionSource.BANNER]: 'Server header',
	[VersionSource.FINGERPRINT]: 'Fingerprint'
};

export const VERSION_SOURCE_HELP: Record<string, string> = {
	[VersionSource.BANNER]: 'The server stated this version in its own response headers.',
	[VersionSource.FINGERPRINT]: 'Read from the page, not stated by the server.'
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
		'The banner names a distribution that patches without changing the version number, so the version alone does not settle it.',
	[Caveat.CONDITIONAL]:
		'NVD records this CVE against a further component, such as an operating system, that this scan did not identify.',
	[Caveat.FINGERPRINT]: 'The version was read from the page rather than stated by the server.',
	[Caveat.COARSE]:
		'Only a major version was reported, so the match covers every release in that series.'
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
	[Confidence.MEDIUM]: 'One thing about this match is unverified.',
	[Confidence.LOW]: 'More than one thing about this match is unverified.'
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

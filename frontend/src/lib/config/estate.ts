// mirrors shared/definitions/estate.py
export enum EstateStrength {
	DIRECT = 'direct',
	SHARED = 'shared'
}

export enum EstateTriageState {
	OPEN = 'open',
	DISMISSED = 'dismissed'
}

export enum ProviderKind {
	EDGE = 'edge',
	HOSTING = 'hosting',
	DNS = 'dns',
	MAIL = 'mail'
}

export const ESTATE_STRENGTH_LABELS: Record<string, string> = {
	[EstateStrength.DIRECT]: 'Direct',
	[EstateStrength.SHARED]: 'Shared'
};

export const PROVIDER_KIND_LABELS: Record<string, string> = {
	[ProviderKind.EDGE]: 'Edge',
	[ProviderKind.HOSTING]: 'Hosting',
	[ProviderKind.DNS]: 'Nameservers',
	[ProviderKind.MAIL]: 'Mail'
};

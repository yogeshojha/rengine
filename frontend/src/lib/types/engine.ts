export type {
	Intensity,
	DiscoveryConfig,
	ExpansionConfig,
	DepthConfig,
	ScanEngine,
	ScanEngineCreate,
	ScanEngineUpdate
} from './scan-engine';

export {
	DEFAULT_DISCOVERY_CONFIG,
	DEFAULT_EXPANSION_CONFIG,
	DEFAULT_DEPTH_CONFIG,
	INTENSITIES,
	INTENSITY_LABELS,
	INTENSITY_HELP,
	DEFAULT_INTENSITY,
	DEFAULT_GLOBAL_THREADS
} from './scan-engine';

export type ArtifactType =
	| 'seed'
	| 'hosts'
	| 'domains'
	| 'subdomains'
	| 'ports'
	| 'live-hosts'
	| 'screenshots'
	| 'endpoints'
	| 'findings'
	| 'buckets'
	| 'report'
	| 'results';

export const ARTIFACT_LABEL: Record<ArtifactType, string> = {
	seed: 'target',
	hosts: 'hosts',
	domains: 'domains',
	subdomains: 'subdomains',
	ports: 'open ports',
	'live-hosts': 'live hosts',
	screenshots: 'screenshots',
	endpoints: 'endpoints',
	findings: 'findings',
	buckets: 'cloud assets',
	report: 'report',
	results: 'results'
};

export const SEED_TYPES = ['domain', 'ip', 'cidr', 'url', 'org', 'asn'] as const;

export interface PhaseColor {
	header: string;
	accent: string;
	text: string;
	bgLight: string;
}

export const PHASE_COLORS: Record<'discovery' | 'expansion' | 'depth', PhaseColor> = {
	discovery: {
		header: '#AFA9EC',
		accent: '#7F77DD',
		text: '#3C3489',
		bgLight: '#EDE9FF'
	},
	expansion: {
		header: '#5DCAA5',
		accent: '#1D9E75',
		text: '#085041',
		bgLight: '#E0F7F1'
	},
	depth: {
		header: '#F0997B',
		accent: '#D85A30',
		text: '#712B13',
		bgLight: '#FEF0EB'
	}
};

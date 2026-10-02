// mirrors shared/definitions/issue_trackers.py

export const MAX_TRACKERS = 20;
export const MAX_FILE_SELECTION = 500;
export const MAX_FILE_CHECKS = 100;
export const MAX_GROUP_LOCATIONS = 50;
export const SHEET_REFRESH_SECONDS = 300;
export const MAX_LISTED = 500;

export enum TrackerKind {
	JIRA_CLOUD = 'jira_cloud',
	JIRA_DC = 'jira_dc',
	GITHUB = 'github',
	GITLAB = 'gitlab'
}

export interface TrackerField {
	key: string;
	label: string;
	secret: boolean;
	placeholder: string;
	help: string;
}

export interface TrackerSpec {
	kind: TrackerKind;
	label: string;
	urlLabel: string;
	urlPlaceholder: string;
	defaultUrl: string | null;
	destinationLabel: string;
	destinationPlaceholder: string;
	hasIssueType: boolean;
	fields: TrackerField[];
	docsUrl: string;
}

const field = (key: string, label: string, secret = false, help = ''): TrackerField => ({
	key,
	label,
	secret,
	placeholder: '',
	help
});

export const TRACKERS: TrackerSpec[] = [
	{
		kind: TrackerKind.JIRA_CLOUD,
		label: 'Jira Cloud',
		urlLabel: 'Site URL',
		urlPlaceholder: 'https://acme.atlassian.net',
		defaultUrl: null,
		destinationLabel: 'Project',
		destinationPlaceholder: 'SEC',
		hasIssueType: true,
		fields: [
			field('email', 'Account email'),
			field('token', 'API token', true, 'id.atlassian.com > Security > API tokens.')
		],
		docsUrl:
			'https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/'
	},
	{
		kind: TrackerKind.JIRA_DC,
		label: 'Jira Data Center',
		urlLabel: 'Base URL',
		urlPlaceholder: 'https://jira.acme.com',
		defaultUrl: null,
		destinationLabel: 'Project',
		destinationPlaceholder: 'SEC',
		hasIssueType: true,
		fields: [field('token', 'Personal access token', true, 'Profile > Personal Access Tokens.')],
		docsUrl:
			'https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html'
	},
	{
		kind: TrackerKind.GITHUB,
		label: 'GitHub Issues',
		urlLabel: 'API URL',
		urlPlaceholder: 'https://api.github.com',
		defaultUrl: 'https://api.github.com',
		destinationLabel: 'Repository',
		destinationPlaceholder: 'acme/security',
		hasIssueType: false,
		fields: [
			field('token', 'Fine-grained token', true, 'Repository permissions > Issues: Read and write.')
		],
		docsUrl:
			'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens'
	},
	{
		kind: TrackerKind.GITLAB,
		label: 'GitLab Issues',
		urlLabel: 'Instance URL',
		urlPlaceholder: 'https://gitlab.com',
		defaultUrl: 'https://gitlab.com',
		destinationLabel: 'Project',
		destinationPlaceholder: 'acme/security',
		hasIssueType: false,
		fields: [field('token', 'Access token', true, 'Project or personal token. Scope: api.')],
		docsUrl: 'https://docs.gitlab.com/user/profile/personal_access_tokens/'
	}
];

export const TRACKERS_BY_KIND: Record<string, TrackerSpec> = Object.fromEntries(
	TRACKERS.map((spec) => [spec.kind, spec])
);

export const trackerLabel = (kind: string): string => TRACKERS_BY_KIND[kind]?.label ?? kind;

/** `#12` for a repository key, the key itself otherwise. */
export const shortKey = (key: string): string =>
	key.includes('#') ? `#${key.split('#').pop()}` : key;

export enum FilingState {
	PENDING = 'pending',
	FILED = 'filed',
	FAILED = 'failed'
}

export const FILING_STATE_LABELS: Record<FilingState, string> = {
	[FilingState.PENDING]: 'Filing',
	[FilingState.FILED]: 'Filed',
	[FilingState.FAILED]: 'Not filed'
};

export enum RemoteCategory {
	TODO = 'todo',
	IN_PROGRESS = 'in_progress',
	DONE = 'done'
}

export const REMOTE_CATEGORY_LABELS: Record<RemoteCategory, string> = {
	[RemoteCategory.TODO]: 'To do',
	[RemoteCategory.IN_PROGRESS]: 'In progress',
	[RemoteCategory.DONE]: 'Done'
};

export const REMOTE_CATEGORY_DOT: Record<RemoteCategory, string> = {
	[RemoteCategory.TODO]: 'bg-muted-foreground/60',
	[RemoteCategory.IN_PROGRESS]: 'bg-info',
	[RemoteCategory.DONE]: 'bg-success'
};

export enum Grouping {
	AUTO = 'auto',
	SEPARATE = 'separate'
}

export const GROUPING_LABELS: Record<Grouping, string> = {
	[Grouping.AUTO]: 'Group by check',
	[Grouping.SEPARATE]: 'One issue per finding'
};

const TECH_ICON_BASE = '/tech-icons';

const ICON_ALIASES: Record<string, string> = {
	amazon: 'amazon-web-services',
	aws: 'amazon-web-services',
	'aws-elb': 'amazon-elb',
	'aws-s3': 'amazon-s3',
	'aws-global-accelerator': 'amazon-web-services',
	'elastic-beanstalk': 'amazon-web-services',
	cloudfront: 'amazon-cloudfront',
	'azure-app-service': 'azure',
	'azure-api-management': 'azure',
	'azure-traffic-manager': 'azure',
	'azure-blob': 'azure',
	'bunny-cdn': 'bunny',
	'alibaba-cdn': 'alibaba-cloud',
	'oracle-cloud': 'oracle',
	'cloud-run': 'google-cloud',
	statuspage: 'atlassian-statuspage',
	'bitbucket-pages': 'atlassian-bitbucket',
	incapsula: 'imperva',
	office365: 'microsoft-365',
	// service names from shared/definitions/ports.py that spell a brand differently
	mssql: 'microsoft',
	'ms-sql-s': 'microsoft',
	weblogic: 'weblogic-server'
};

export function techIconSlug(name: string): string {
	const slug = name
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');
	return ICON_ALIASES[slug] ?? slug;
}

export function techIconUrl(name: string): string | null {
	const slug = techIconSlug(name.split(':')[0]);
	return slug ? `${TECH_ICON_BASE}/${slug}.svg` : null;
}

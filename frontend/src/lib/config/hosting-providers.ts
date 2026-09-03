import Cloud from '@lucide/svelte/icons/cloud';
import Globe from '@lucide/svelte/icons/globe';
import Network from '@lucide/svelte/icons/network';
import HardDrive from '@lucide/svelte/icons/hard-drive';
import ShoppingBag from '@lucide/svelte/icons/shopping-bag';
import FileCode from '@lucide/svelte/icons/file-code';
import AppWindow from '@lucide/svelte/icons/app-window';
import Mail from '@lucide/svelte/icons/mail';
import Waypoints from '@lucide/svelte/icons/waypoints';
import type { IconComponent } from './icons';

export type ProviderKind =
	| 'cloud'
	| 'cdn'
	| 'lb'
	| 'storage'
	| 'shop'
	| 'pages'
	| 'saas'
	| 'mail'
	| 'dns';

export interface HostingProvider {
	suffix: string;
	label: string;
	kind: ProviderKind;
}

export const PROVIDER_KIND_LABELS: Record<ProviderKind, string> = {
	cloud: 'Cloud hosting',
	cdn: 'CDN edge',
	lb: 'Load balancer',
	storage: 'Object storage',
	shop: 'Commerce platform',
	pages: 'Static hosting',
	saas: 'SaaS platform',
	mail: 'Email service',
	dns: 'Traffic manager'
};

export const PROVIDER_KIND_ICONS: Record<ProviderKind, IconComponent> = {
	cloud: Cloud,
	cdn: Globe,
	lb: Network,
	storage: HardDrive,
	shop: ShoppingBag,
	pages: FileCode,
	saas: AppWindow,
	mail: Mail,
	dns: Waypoints
};

const LIST: HostingProvider[] = [
	{ suffix: 'elb.amazonaws.com', label: 'AWS ELB', kind: 'lb' },
	{ suffix: 'cloudfront.net', label: 'CloudFront', kind: 'cdn' },
	{ suffix: 's3.amazonaws.com', label: 'AWS S3', kind: 'storage' },
	{ suffix: 'awsglobalaccelerator.com', label: 'AWS Global Accelerator', kind: 'lb' },
	{ suffix: 'elasticbeanstalk.com', label: 'Elastic Beanstalk', kind: 'cloud' },
	{ suffix: 'amazonaws.com', label: 'AWS', kind: 'cloud' },
	{ suffix: 'myshopify.com', label: 'Shopify', kind: 'shop' },
	{ suffix: 'azurewebsites.net', label: 'Azure App Service', kind: 'cloud' },
	{ suffix: 'azureedge.net', label: 'Azure CDN', kind: 'cdn' },
	{ suffix: 'azurefd.net', label: 'Azure Front Door', kind: 'lb' },
	{ suffix: 'trafficmanager.net', label: 'Azure Traffic Manager', kind: 'dns' },
	{ suffix: 'cloudapp.azure.com', label: 'Azure', kind: 'cloud' },
	{ suffix: 'blob.core.windows.net', label: 'Azure Blob', kind: 'storage' },
	{ suffix: 'azure-api.net', label: 'Azure API Management', kind: 'cloud' },
	{ suffix: 'github.io', label: 'GitHub Pages', kind: 'pages' },
	{ suffix: 'herokuapp.com', label: 'Heroku', kind: 'cloud' },
	{ suffix: 'herokudns.com', label: 'Heroku', kind: 'cloud' },
	{ suffix: 'netlify.app', label: 'Netlify', kind: 'pages' },
	{ suffix: 'netlify.com', label: 'Netlify', kind: 'pages' },
	{ suffix: 'vercel.app', label: 'Vercel', kind: 'pages' },
	{ suffix: 'vercel-dns.com', label: 'Vercel', kind: 'pages' },
	{ suffix: 'fastly.net', label: 'Fastly', kind: 'cdn' },
	{ suffix: 'fastlylb.net', label: 'Fastly', kind: 'cdn' },
	{ suffix: 'akamaiedge.net', label: 'Akamai', kind: 'cdn' },
	{ suffix: 'akamai.net', label: 'Akamai', kind: 'cdn' },
	{ suffix: 'edgekey.net', label: 'Akamai', kind: 'cdn' },
	{ suffix: 'edgesuite.net', label: 'Akamai', kind: 'cdn' },
	{ suffix: 'cloudflare.net', label: 'Cloudflare', kind: 'cdn' },
	{ suffix: 'incapdns.net', label: 'Imperva', kind: 'cdn' },
	{ suffix: 'sucuri.net', label: 'Sucuri', kind: 'cdn' },
	{ suffix: 'llnwd.net', label: 'Limelight', kind: 'cdn' },
	{ suffix: 'cdn77.org', label: 'CDN77', kind: 'cdn' },
	{ suffix: 'b-cdn.net', label: 'Bunny CDN', kind: 'cdn' },
	{ suffix: 'cachefly.net', label: 'CacheFly', kind: 'cdn' },
	{ suffix: 'alicdn.com', label: 'Alibaba CDN', kind: 'cdn' },
	{ suffix: 'aliyuncs.com', label: 'Alibaba Cloud', kind: 'cloud' },
	{ suffix: 'myqcloud.com', label: 'Tencent Cloud', kind: 'cloud' },
	{ suffix: 'qcloud.com', label: 'Tencent Cloud', kind: 'cloud' },
	{ suffix: 'oraclecloud.com', label: 'Oracle Cloud', kind: 'cloud' },
	{ suffix: 'googlehosted.com', label: 'Google', kind: 'cloud' },
	{ suffix: 'googleusercontent.com', label: 'Google Cloud', kind: 'cloud' },
	{ suffix: 'appspot.com', label: 'Google App Engine', kind: 'cloud' },
	{ suffix: 'run.app', label: 'Cloud Run', kind: 'cloud' },
	{ suffix: 'web.app', label: 'Firebase', kind: 'pages' },
	{ suffix: 'firebaseapp.com', label: 'Firebase', kind: 'pages' },
	{ suffix: 'storage.googleapis.com', label: 'Google Cloud Storage', kind: 'storage' },
	{ suffix: 'ondigitalocean.app', label: 'DigitalOcean', kind: 'cloud' },
	{ suffix: 'digitaloceanspaces.com', label: 'DigitalOcean Spaces', kind: 'storage' },
	{ suffix: 'sealos.io', label: 'Sealos', kind: 'cloud' },
	{ suffix: 'ngrok.io', label: 'ngrok', kind: 'cloud' },
	{ suffix: 'ngrok.app', label: 'ngrok', kind: 'cloud' },
	{ suffix: 'wpengine.com', label: 'WP Engine', kind: 'cloud' },
	{ suffix: 'wordpress.com', label: 'WordPress.com', kind: 'pages' },
	{ suffix: 'kinsta.cloud', label: 'Kinsta', kind: 'cloud' },
	{ suffix: 'pantheonsite.io', label: 'Pantheon', kind: 'cloud' },
	{ suffix: 'hubspot.net', label: 'HubSpot', kind: 'saas' },
	{ suffix: 'hs-sites.com', label: 'HubSpot', kind: 'saas' },
	{ suffix: 'zendesk.com', label: 'Zendesk', kind: 'saas' },
	{ suffix: 'freshdesk.com', label: 'Freshdesk', kind: 'saas' },
	{ suffix: 'intercom.help', label: 'Intercom', kind: 'saas' },
	{ suffix: 'readme.io', label: 'ReadMe', kind: 'saas' },
	{ suffix: 'statuspage.io', label: 'Statuspage', kind: 'saas' },
	{ suffix: 'uservoice.com', label: 'UserVoice', kind: 'saas' },
	{ suffix: 'helpscoutdocs.com', label: 'Help Scout', kind: 'saas' },
	{ suffix: 'force.com', label: 'Salesforce', kind: 'saas' },
	{ suffix: 'siteforce.com', label: 'Salesforce', kind: 'saas' },
	{ suffix: 'salesforce.com', label: 'Salesforce', kind: 'saas' },
	{ suffix: 'okta.com', label: 'Okta', kind: 'saas' },
	{ suffix: 'auth0.com', label: 'Auth0', kind: 'saas' },
	{ suffix: 'atlassian.net', label: 'Atlassian', kind: 'saas' },
	{ suffix: 'sharepoint.com', label: 'Microsoft 365', kind: 'saas' },
	{ suffix: 'squarespace.com', label: 'Squarespace', kind: 'pages' },
	{ suffix: 'wixdns.net', label: 'Wix', kind: 'pages' },
	{ suffix: 'webflow.io', label: 'Webflow', kind: 'pages' },
	{ suffix: 'ghost.io', label: 'Ghost', kind: 'pages' },
	{ suffix: 'surge.sh', label: 'Surge', kind: 'pages' },
	{ suffix: 'unbounce.com', label: 'Unbounce', kind: 'pages' },
	{ suffix: 'tumblr.com', label: 'Tumblr', kind: 'pages' },
	{ suffix: 'bitbucket.io', label: 'Bitbucket Pages', kind: 'pages' },
	{ suffix: 'cargo.site', label: 'Cargo', kind: 'pages' },
	{ suffix: 'gitbook.io', label: 'GitBook', kind: 'pages' },
	{ suffix: 'notion.site', label: 'Notion', kind: 'pages' },
	{ suffix: 'launchrock.com', label: 'Launchrock', kind: 'pages' },
	{ suffix: 'strikingly.com', label: 'Strikingly', kind: 'pages' },
	{ suffix: 'tilda.ws', label: 'Tilda', kind: 'pages' },
	{ suffix: 'sendgrid.net', label: 'SendGrid', kind: 'mail' },
	{ suffix: 'mailgun.org', label: 'Mailgun', kind: 'mail' },
	{ suffix: 'list-manage.com', label: 'Mailchimp', kind: 'mail' },
	{ suffix: 'mailchimp.com', label: 'Mailchimp', kind: 'mail' }
];
const PROVIDERS = [...LIST].sort((a, b) => b.suffix.length - a.suffix.length);

export function providerFor(cname: string | null | undefined): HostingProvider | null {
	if (!cname) return null;
	const host = cname.toLowerCase().replace(/\.$/, '');
	return PROVIDERS.find((p) => host === p.suffix || host.endsWith(`.${p.suffix}`)) ?? null;
}

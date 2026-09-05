export interface Provider {
	name: string;
	icon: string | null;
}

const NS_PROVIDERS: ReadonlyArray<readonly [RegExp, Provider]> = [
	[/cloudflare/i, { name: 'Cloudflare', icon: 'cloudflare' }],
	[/(awsdns|route53|amazonaws)/i, { name: 'AWS Route 53', icon: 'amazon-route-53' }],
	[/(domaincontrol|godaddy)/i, { name: 'GoDaddy', icon: 'godaddy' }],
	[
		/(googledomains|ns[.-]google|google\.com)/i,
		{ name: 'Google Cloud DNS', icon: 'google-cloud-dns' }
	],
	[/(azure-dns|azuredns)/i, { name: 'Azure DNS', icon: 'azure' }],
	[/(akam\.net|akamai)/i, { name: 'Akamai', icon: 'akamai' }],
	[/dnsmadeeasy/i, { name: 'DNS Made Easy', icon: null }],
	[/(\bns1\b|nsone\.net)/i, { name: 'NS1', icon: null }],
	[/dyn(ect)?\.(com|net)/i, { name: 'Dyn', icon: null }],
	[/digitalocean/i, { name: 'DigitalOcean', icon: 'digitalocean' }],
	[/(registrar-servers|namecheap|name-services)/i, { name: 'Namecheap', icon: null }],
	[/cloudns/i, { name: 'ClouDNS', icon: null }],
	[/buddyns/i, { name: 'BuddyNS', icon: null }],
	[/vercel-dns/i, { name: 'Vercel', icon: 'vercel' }],
	[/fastly/i, { name: 'Fastly', icon: 'fastly' }],
	[/(hover|tucows)/i, { name: 'Tucows', icon: null }],
	[/wordpress|wpengine/i, { name: 'WordPress', icon: 'wordpress' }],
	[/gandi/i, { name: 'Gandi', icon: null }],
	[/ultradns/i, { name: 'UltraDNS', icon: null }],
	[/(hetzner|your-server\.de)/i, { name: 'Hetzner', icon: 'hetzner' }],
	[/ovh\.net/i, { name: 'OVH', icon: 'ovhcloud' }],
	[/linode/i, { name: 'Linode', icon: null }],
	[/he\.net/i, { name: 'Hurricane Electric', icon: null }],
	[/netlify/i, { name: 'Netlify', icon: 'netlify' }]
];

const MX_PROVIDERS: ReadonlyArray<readonly [RegExp, Provider]> = [
	[
		/(aspmx.*google|googlemail|google\.com)/i,
		{ name: 'Google Workspace', icon: 'google-workspace' }
	],
	[
		/(outlook\.com|protection\.outlook|office365)/i,
		{ name: 'Microsoft 365', icon: 'microsoft-365' }
	],
	[/pphosted\.com/i, { name: 'Proofpoint', icon: null }],
	[/mimecast/i, { name: 'Mimecast', icon: null }],
	[/(zoho|zohomail)/i, { name: 'Zoho Mail', icon: 'zoho-mail' }],
	[/(amazonaws|inbound-smtp)/i, { name: 'Amazon SES', icon: 'amazon-ses' }],
	[/(mail\.protonmail|protonmail\.ch)/i, { name: 'Proton Mail', icon: null }],
	[/fastmail|messagingengine/i, { name: 'Fastmail', icon: null }],
	[/secureserver\.net/i, { name: 'GoDaddy', icon: 'godaddy' }],
	[/mailgun/i, { name: 'Mailgun', icon: 'mailgun' }],
	[/sendgrid/i, { name: 'SendGrid', icon: 'sendgrid' }],
	[/barracuda/i, { name: 'Barracuda', icon: null }],
	[/yandex/i, { name: 'Yandex', icon: 'yandex' }],
	[/mail\.ru/i, { name: 'Mail.ru', icon: null }],
	[/(icloud|apple)/i, { name: 'iCloud Mail', icon: 'apple-icloud-mail' }],
	[/(hostinger|titan\.email)/i, { name: 'Titan', icon: null }],
	[/mailchannels/i, { name: 'MailChannels', icon: null }],
	[/cloudflare/i, { name: 'Cloudflare Email Routing', icon: 'cloudflare' }]
];

const REGISTRARS: ReadonlyArray<readonly [RegExp, string]> = [
	[/godaddy/i, 'godaddy'],
	[/cloudflare/i, 'cloudflare'],
	[/amazon/i, 'amazon-web-services'],
	[/google/i, 'google'],
	[/squarespace/i, 'squarespace'],
	[/wix/i, 'wix'],
	[/shopify/i, 'shopify'],
	[/ovh/i, 'ovhcloud'],
	[/hetzner/i, 'hetzner'],
	[/microsoft/i, 'microsoft']
];

function match(table: ReadonlyArray<readonly [RegExp, Provider]>, hosts: readonly string[]) {
	for (const host of hosts) {
		for (const [re, provider] of table) if (re.test(host)) return provider;
	}
	return null;
}

export function nameserverProvider(hosts: readonly string[]): Provider | null {
	return match(NS_PROVIDERS, hosts);
}

export function mailProvider(hosts: readonly string[]): Provider | null {
	return match(MX_PROVIDERS, hosts);
}

export function registrarIcon(name: string | null | undefined): string | null {
	if (!name) return null;
	for (const [re, icon] of REGISTRARS) if (re.test(name)) return icon;
	return null;
}

export type TxtPurposeKind = 'spf' | 'dmarc' | 'dkim' | 'bimi' | 'verification' | 'other';

export interface TxtPurpose {
	kind: TxtPurposeKind;
	label: string;
	detail?: string;
	icon?: string | null;
}

const VERIFICATION_VENDORS: ReadonlyArray<readonly [RegExp, string, string | null]> = [
	[/^google-site-verification=/i, 'Google', 'google'],
	[/^MS=/i, 'Microsoft 365', 'microsoft-365'],
	[/^apple-domain-verification=/i, 'Apple', 'apple'],
	[/^facebook-domain-verification=/i, 'Meta', 'meta'],
	[/^workplace-domain-verification=/i, 'Meta Workplace', 'meta'],
	[/^atlassian-(domain|sending-domain)-verification=/i, 'Atlassian', 'atlassian'],
	[/^docusign=/i, 'DocuSign', 'docusign'],
	[/^stripe-verification=/i, 'Stripe', 'stripe'],
	[/^adobe-(idp-)?(site|domain)-verification=/i, 'Adobe', 'adobe'],
	[/^amazonses:/i, 'Amazon SES', 'amazon-ses'],
	[/^zoom-domain-verification=/i, 'Zoom', null],
	[/^miro-verification=/i, 'Miro', null],
	[/^notion-domain-verification=/i, 'Notion', 'notion'],
	[/^mgverify=/i, 'Mailgun', 'mailgun'],
	[/^mailru-verification:/i, 'Mail.ru', null],
	[/^dropbox-domain-verification=/i, 'Dropbox', 'dropbox'],
	[/^canva-site-verification=/i, 'Canva', 'canva'],
	[/^openai-domain-verification=/i, 'OpenAI', 'openai'],
	[/^anthropic-domain-verification/i, 'Anthropic', 'anthropic'],
	[/^cursor-domain-verification/i, 'Cursor', null],
	[/^perplexity-ai-domain-verification/i, 'Perplexity', null],
	[/^resend-domain-verification=/i, 'Resend', null],
	[/^twilio-domain-verification=/i, 'Twilio', 'twilio'],
	[/^slack-domain-verification=/i, 'Slack', 'slack'],
	[/^hubspot-developer-verification=/i, 'HubSpot', 'hubspot'],
	[/^_?globalsign-domain-verification=/i, 'GlobalSign', null],
	[/^digicert-/i, 'DigiCert', null],
	[/^(sendinblue|brevo)-code:/i, 'Brevo', 'brevo'],
	[/^have-i-been-pwned-verification=/i, 'Have I Been Pwned', null],
	[/^onetrust-domain-verification=/i, 'OneTrust', null],
	[/^logmein-verification-code=/i, 'LogMeIn', null],
	[/^pardot_/i, 'Salesforce Pardot', 'salesforce'],
	[/^status-page-domain-verification=/i, 'Statuspage', 'atlassian-statuspage'],
	[/^webexdomainverification/i, 'Webex', 'cisco'],
	[/^cisco-ci-domain-verification=/i, 'Cisco', 'cisco'],
	[/^yandex-verification:/i, 'Yandex', 'yandex'],
	[/^wrike-verification=/i, 'Wrike', null],
	[/^intacct-esk=/i, 'Sage Intacct', null],
	[/^shopify-verification-code=/i, 'Shopify', 'shopify'],
	[/^square-verification=/i, 'Square', 'square'],
	[/^loaderio=/i, 'Loader.io', null],
	[/^bugcrowd-verification=/i, 'Bugcrowd', null],
	[/^hackerone-verification=/i, 'HackerOne', null]
];

const GENERIC_VERIFICATION = /^([a-z0-9]+(?:-[a-z0-9]+)*?)[-_](?:domain|site)[-_]verification/i;

export type SpfPolicy = 'strict' | 'soft fail' | 'neutral' | 'permissive' | 'no all mechanism';

export function spfPolicy(value: string): SpfPolicy {
	if (/[\s-]-all\b/.test(value)) return 'strict';
	if (/~all\b/.test(value)) return 'soft fail';
	if (/\?all\b/.test(value)) return 'neutral';
	if (/\+all\b/.test(value)) return 'permissive';
	return 'no all mechanism';
}

function dmarcPolicy(value: string): string {
	const m = /(?:^|;)\s*p=([a-z]+)/i.exec(value);
	return m ? `p=${m[1].toLowerCase()}` : 'no policy';
}

export function txtPurpose(value: string): TxtPurpose {
	const v = value.trim();
	if (/^v=spf1\b/i.test(v)) return { kind: 'spf', label: 'SPF', detail: spfPolicy(v) };
	if (/^v=DMARC1\b/i.test(v)) return { kind: 'dmarc', label: 'DMARC', detail: dmarcPolicy(v) };
	if (/^v=DKIM1\b/i.test(v)) return { kind: 'dkim', label: 'DKIM' };
	if (/^v=BIMI1\b/i.test(v)) return { kind: 'bimi', label: 'BIMI' };
	for (const [re, vendor, icon] of VERIFICATION_VENDORS) {
		if (re.test(v)) return { kind: 'verification', label: vendor, detail: 'verification', icon };
	}
	const generic = GENERIC_VERIFICATION.exec(v);
	if (generic) {
		const vendor = generic[1]
			.split('-')
			.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
			.join(' ');
		return { kind: 'verification', label: vendor, detail: 'verification', icon: null };
	}
	return { kind: 'other', label: 'TXT' };
}

export function verificationVendors(values: readonly string[]): string[] {
	const out = new Set<string>();
	for (const v of values) {
		const p = txtPurpose(v);
		if (p.kind === 'verification') out.add(p.label);
	}
	return [...out];
}

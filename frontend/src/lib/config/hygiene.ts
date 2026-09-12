import Lock from '@lucide/svelte/icons/lock';
import FileCode from '@lucide/svelte/icons/file-code';
import Cookie from '@lucide/svelte/icons/cookie';
import Globe from '@lucide/svelte/icons/globe';
import Eye from '@lucide/svelte/icons/eye';
import type { IconComponent } from './icons';

// mirrors shared/definitions/hygiene.py
export const HygieneCheck = {
	NO_HSTS: 'no_hsts',
	HSTS_SHORT: 'hsts_short',
	NO_HTTPS_REDIRECT: 'no_https_redirect',
	NO_FRAME_PROTECTION: 'no_frame_protection',
	NO_NOSNIFF: 'no_nosniff',
	NO_CSP: 'no_csp',
	CSP_REPORT_ONLY: 'csp_report_only',
	CSP_UNSAFE_INLINE: 'csp_unsafe_inline',
	CSP_WILDCARD_SCRIPT: 'csp_wildcard_script',
	COOKIE_NO_SECURE: 'cookie_no_secure',
	COOKIE_NO_HTTPONLY: 'cookie_no_httponly',
	CACHEABLE_SESSION: 'cacheable_session',
	CORS_CREDENTIALS: 'cors_credentials',
	CORS_ANY_ORIGIN: 'cors_any_origin',
	SERVER_VERSION: 'server_version',
	RUNTIME_DISCLOSED: 'runtime_disclosed',
	NO_REFERRER_POLICY: 'no_referrer_policy'
} as const;
export type HygieneCheck = (typeof HygieneCheck)[keyof typeof HygieneCheck];

export const HygieneGroup = {
	TRANSPORT: 'transport',
	CONTENT: 'content',
	COOKIES: 'cookies',
	CROSS_ORIGIN: 'cross_origin',
	DISCLOSURE: 'disclosure'
} as const;
export type HygieneGroup = (typeof HygieneGroup)[keyof typeof HygieneGroup];

export const HygieneTone = { WARNING: 'warning', INFO: 'info' } as const;
export type HygieneTone = (typeof HygieneTone)[keyof typeof HygieneTone];

export const HYGIENE_FIELD = 'hygiene';
export const HYGIENE_ANY = 'any';
export const HYGIENE_NONE = 'none';

export const GROUP_LABELS: Record<HygieneGroup, string> = {
	transport: 'Transport',
	content: 'Content',
	cookies: 'Cookies',
	cross_origin: 'Cross-origin',
	disclosure: 'Disclosure'
};

export const GROUP_ICONS: Record<HygieneGroup, IconComponent> = {
	transport: Lock,
	content: FileCode,
	cookies: Cookie,
	cross_origin: Globe,
	disclosure: Eye
};

export interface CheckSpec {
	key: HygieneCheck;
	label: string;
	control: string;
	help: string;
	applies: string;
	fix: string;
	header: string;
	group: HygieneGroup;
	tone: HygieneTone;
}

export const CHECKS: CheckSpec[] = [
	{
		key: 'no_https_redirect',
		label: 'Plaintext without redirect',
		control: 'HTTPS redirect',
		help: 'An http response that does not redirect to https.',
		applies: 'Every http response.',
		fix: 'Answer http with a 301 to the https URL.',
		header: 'Location',
		group: 'transport',
		tone: 'warning'
	},
	{
		key: 'cookie_no_secure',
		label: 'Cookie without Secure',
		control: 'Cookie Secure',
		help: 'A cookie set over https without the Secure attribute.',
		applies: 'Every https response that sets a cookie.',
		fix: 'Add Secure to every Set-Cookie on https.',
		header: 'Set-Cookie',
		group: 'cookies',
		tone: 'warning'
	},
	{
		key: 'cookie_no_httponly',
		label: 'Session cookie without HttpOnly',
		control: 'Cookie HttpOnly',
		help: 'A session or authentication cookie without the HttpOnly attribute.',
		applies: 'Every response that sets a session-named cookie.',
		fix: 'Add HttpOnly to session and authentication cookies.',
		header: 'Set-Cookie',
		group: 'cookies',
		tone: 'warning'
	},
	{
		key: 'cacheable_session',
		label: 'Session cookie in a cacheable response',
		control: 'Session cache control',
		help: 'A response that sets a session cookie without Cache-Control: no-store or private.',
		applies: 'Every response that sets a session-named cookie.',
		fix: 'Send Cache-Control: no-store on responses that set session cookies.',
		header: 'Cache-Control',
		group: 'cookies',
		tone: 'warning'
	},
	{
		key: 'cors_credentials',
		label: 'CORS credentials with wildcard origin',
		control: 'CORS credentials',
		help: 'Access-Control-Allow-Origin is * or null while Access-Control-Allow-Credentials is true.',
		applies: 'Every response with Access-Control-Allow-Origin.',
		fix: 'Name the allowed origin exactly, or drop Access-Control-Allow-Credentials.',
		header: 'Access-Control-Allow-Origin',
		group: 'cross_origin',
		tone: 'warning'
	},
	{
		key: 'no_frame_protection',
		label: 'No framing protection',
		control: 'Framing protection',
		help: 'An HTML page without X-Frame-Options or a CSP frame-ancestors directive.',
		applies: 'Every 2xx HTML response.',
		fix: "Send Content-Security-Policy: frame-ancestors 'self' or X-Frame-Options: DENY.",
		header: 'X-Frame-Options',
		group: 'content',
		tone: 'warning'
	},
	{
		key: 'csp_unsafe_inline',
		label: 'CSP allows inline scripts',
		control: 'CSP inline scripts',
		help: "script-src permits 'unsafe-inline' with no nonce, hash or 'strict-dynamic'.",
		applies: 'Every response with an enforcing Content-Security-Policy that governs scripts.',
		fix: "Replace 'unsafe-inline' with nonces or hashes.",
		header: 'Content-Security-Policy',
		group: 'content',
		tone: 'warning'
	},
	{
		key: 'csp_wildcard_script',
		label: 'CSP allows any script origin',
		control: 'CSP script origins',
		help: 'script-src includes *, https:, http: or data:.',
		applies: 'Every response with an enforcing Content-Security-Policy that governs scripts.',
		fix: 'List the script origins the page uses.',
		header: 'Content-Security-Policy',
		group: 'content',
		tone: 'warning'
	},
	{
		key: 'no_hsts',
		label: 'No HSTS',
		control: 'HSTS',
		help: 'An https response without Strict-Transport-Security.',
		applies: 'Every https response.',
		fix: 'Send Strict-Transport-Security: max-age=31536000; includeSubDomains.',
		header: 'Strict-Transport-Security',
		group: 'transport',
		tone: 'info'
	},
	{
		key: 'hsts_short',
		label: 'HSTS under a year',
		control: 'HSTS max-age',
		help: 'Strict-Transport-Security max-age below 31536000 seconds.',
		applies: 'Every response with Strict-Transport-Security.',
		fix: 'Raise max-age to 31536000 or more.',
		header: 'Strict-Transport-Security',
		group: 'transport',
		tone: 'info'
	},
	{
		key: 'no_csp',
		label: 'No Content-Security-Policy',
		control: 'Content-Security-Policy',
		help: 'An HTML page without a Content-Security-Policy header.',
		applies: 'Every 2xx HTML response.',
		fix: 'Send a Content-Security-Policy header.',
		header: 'Content-Security-Policy',
		group: 'content',
		tone: 'info'
	},
	{
		key: 'csp_report_only',
		label: 'CSP report-only',
		control: 'Enforcing CSP',
		help: 'Content-Security-Policy-Report-Only without an enforcing policy.',
		applies: 'Every 2xx HTML response.',
		fix: 'Promote the report-only policy to Content-Security-Policy.',
		header: 'Content-Security-Policy-Report-Only',
		group: 'content',
		tone: 'info'
	},
	{
		key: 'no_nosniff',
		label: 'No nosniff',
		control: 'nosniff',
		help: 'X-Content-Type-Options: nosniff is absent.',
		applies: 'Every 2xx response with a content type.',
		fix: 'Send X-Content-Type-Options: nosniff.',
		header: 'X-Content-Type-Options',
		group: 'content',
		tone: 'info'
	},
	{
		key: 'no_referrer_policy',
		label: 'No Referrer-Policy',
		control: 'Referrer-Policy',
		help: 'An HTML page without a Referrer-Policy header.',
		applies: 'Every 2xx HTML response.',
		fix: 'Send Referrer-Policy: strict-origin-when-cross-origin.',
		header: 'Referrer-Policy',
		group: 'content',
		tone: 'info'
	},
	{
		key: 'cors_any_origin',
		label: 'CORS allows any origin',
		control: 'CORS origin',
		help: 'Access-Control-Allow-Origin: *.',
		applies: 'Every response with Access-Control-Allow-Origin.',
		fix: 'Name the allowed origins if the resource is not public.',
		header: 'Access-Control-Allow-Origin',
		group: 'cross_origin',
		tone: 'info'
	},
	{
		key: 'server_version',
		label: 'Server version disclosed',
		control: 'Server banner',
		help: 'The Server header carries a version number.',
		applies: 'Every response with a Server header.',
		fix: 'Strip the version from the Server header.',
		header: 'Server',
		group: 'disclosure',
		tone: 'info'
	},
	{
		key: 'runtime_disclosed',
		label: 'Runtime disclosed',
		control: 'Runtime headers',
		help: 'X-Powered-By, X-AspNet-Version or X-Generator names the platform.',
		applies: 'Every response.',
		fix: 'Remove X-Powered-By and related headers.',
		header: 'X-Powered-By',
		group: 'disclosure',
		tone: 'info'
	}
];

export const CHECK_BY_KEY: Record<string, CheckSpec> = Object.fromEntries(
	CHECKS.map((c) => [c.key, c])
);
export const CHECK_ORDER: Record<string, number> = Object.fromEntries(
	CHECKS.map((c, i) => [c.key, i])
);

export function checkSpec(key: string): CheckSpec | null {
	return CHECK_BY_KEY[key] ?? null;
}

export function checkLabel(key: string): string {
	return CHECK_BY_KEY[key]?.label ?? key;
}

export function hygieneQuery(value: string): string {
	return `${HYGIENE_FIELD}:${value}`;
}

export function sortChecks(keys: string[]): string[] {
	return [...keys].sort(
		(a, b) => (CHECK_ORDER[a] ?? CHECKS.length) - (CHECK_ORDER[b] ?? CHECKS.length)
	);
}

export function worstTone(keys: string[]): HygieneTone | null {
	if (!keys.length) return null;
	return keys.some((k) => CHECK_BY_KEY[k]?.tone === 'warning') ? 'warning' : 'info';
}

export function toneCounts(keys: string[]): { warning: number; info: number } {
	let warning = 0;
	let info = 0;
	for (const k of keys) {
		if (CHECK_BY_KEY[k]?.tone === 'warning') warning += 1;
		else if (CHECK_BY_KEY[k]) info += 1;
	}
	return { warning, info };
}

export const TONE_CHIP: Record<HygieneTone, string> = {
	warning: 'border-warning/30 bg-warning/10 text-warning',
	info: 'border-info/25 bg-info/10 text-info'
};

export const TONE_TEXT: Record<HygieneTone, string> = {
	warning: 'text-warning',
	info: 'text-info'
};

export const TONE_DOT: Record<HygieneTone, string> = {
	warning: 'bg-warning',
	info: 'bg-info'
};

export const TONE_LABEL: Record<HygieneTone, string> = {
	warning: 'Warning',
	info: 'Info'
};

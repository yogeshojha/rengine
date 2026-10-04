import BriefcaseBusiness from '@lucide/svelte/icons/briefcase-business';
import CircleDashed from '@lucide/svelte/icons/circle-dashed';
import CircleMinus from '@lucide/svelte/icons/circle-minus';
import CircleOff from '@lucide/svelte/icons/circle-off';
import Globe from '@lucide/svelte/icons/globe';
import UsersRound from '@lucide/svelte/icons/users-round';
import type { IconComponent } from '$lib/config/icons';

export const SOURCE_NAME = 'Hudson Rock';
export const SOURCE_URL = 'https://www.hudsonrock.com/free-tools';

export enum Audience {
	EMPLOYEE = 'employee',
	USER = 'user'
}

export const AUDIENCE_ORDER: readonly Audience[] = [Audience.EMPLOYEE, Audience.USER];

export const AUDIENCE: Record<Audience, { label: string; icon: IconComponent }> = {
	[Audience.EMPLOYEE]: { label: 'Employees', icon: BriefcaseBusiness },
	[Audience.USER]: { label: 'Users', icon: UsersRound }
};

export enum PasswordStrength {
	TOO_WEAK = 'too_weak',
	WEAK = 'weak',
	MEDIUM = 'medium',
	STRONG = 'strong'
}

export const STRENGTH_ORDER: readonly PasswordStrength[] = [
	PasswordStrength.TOO_WEAK,
	PasswordStrength.WEAK,
	PasswordStrength.MEDIUM,
	PasswordStrength.STRONG
];

export const STRENGTH: Record<PasswordStrength, { label: string; fill: string }> = {
	[PasswordStrength.TOO_WEAK]: { label: 'Too weak', fill: 'bg-destructive' },
	[PasswordStrength.WEAK]: { label: 'Weak', fill: 'bg-warning' },
	[PasswordStrength.MEDIUM]: { label: 'Medium', fill: 'bg-muted-foreground/40' },
	[PasswordStrength.STRONG]: { label: 'Strong', fill: 'bg-success' }
};

export enum HostStanding {
	WEB_ASSET = 'web_asset',
	RESOLVED = 'resolved',
	UNRESOLVED = 'unresolved',
	ABSENT = 'absent'
}

export const STANDING: Record<HostStanding, { label: string; icon: IconComponent; tone: string }> =
	{
		[HostStanding.WEB_ASSET]: { label: 'Web asset', icon: Globe, tone: 'text-foreground' },
		[HostStanding.RESOLVED]: {
			label: 'No web response',
			icon: CircleDashed,
			tone: 'text-muted-foreground'
		},
		[HostStanding.UNRESOLVED]: {
			label: 'Not resolved',
			icon: CircleOff,
			tone: 'text-muted-foreground'
		},
		[HostStanding.ABSENT]: {
			label: 'Not in scan',
			icon: CircleMinus,
			tone: 'text-muted-foreground/70'
		}
	};

export const QUERY_FIELD = 'infostealer';

export const hostQuery = (host: string) => `host=${host}`;

export function loginLabel(
	host: string,
	login: { scheme: string | null; port: number | null; path: string | null }
) {
	const prefix = login.scheme ? `${login.scheme}://` : '';
	const port = login.port != null ? `:${login.port}` : '';
	return `${prefix}${host}${port}${login.path ?? ''}`;
}

export const ROLE_LABELS = {
	admin: 'Administrator',
	member: 'Standard user'
} as const;

export function roleLabel(isSuperuser: boolean): string {
	return isSuperuser ? ROLE_LABELS.admin : ROLE_LABELS.member;
}

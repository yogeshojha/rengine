export const getInitials = (name: string): string => {
	return name
		.split(' ')
		.map((n) => n[0])
		.join('')
		.toUpperCase()
		.slice(0, 2);
};

const COMPACT = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });

export const compactCount = (value: number): string =>
	value < 1000 ? String(value) : COMPACT.format(value);

export const getInitials = (name: string): string => {
	return name
		.split(' ')
		.map((n) => n[0])
		.join('')
		.toUpperCase()
		.slice(0, 2);
};

/** `3 findings`, `1 finding`. The plural defaults to the singular with an s. */
export const plural = (n: number, one: string, many = `${one}s`): string =>
	`${n.toLocaleString()} ${n === 1 ? one : many}`;

/** `10,000+` when the count stopped at its cap. */
export const cappedCount = (n: number, capped = false): string =>
	`${n.toLocaleString()}${capped ? '+' : ''}`;

export const cappedPlural = (n: number, capped: boolean, one: string, many = `${one}s`): string =>
	`${cappedCount(n, capped)} ${n === 1 && !capped ? one : many}`;

/** The noun alone, without the count. */
export const pluralWord = (n: number, one: string, many = `${one}s`): string =>
	n === 1 ? one : many;

/** `Email address` becomes `Email addresses`; a label built round a preposition is left alone. */
export const pluralLabel = (label: string): string => {
	if (/\s(in|with|of|for)\s/i.test(label)) return label;
	const parts = label.split(' ');
	const last = parts[parts.length - 1];
	if (/(s|x|z|ch|sh)$/i.test(last)) parts[parts.length - 1] = `${last}es`;
	else if (/[^aeiou]y$/i.test(last)) parts[parts.length - 1] = `${last.slice(0, -1)}ies`;
	else parts[parts.length - 1] = `${last}s`;
	return parts.join(' ');
};

/** `a web asset`, `an address`. */
export const withArticle = (noun: string): string =>
	`${/^[aeiou]/i.test(noun) ? 'an' : 'a'} ${noun}`;

export const percentLabel = (p: number): string => (p > 0 && p < 1 ? '<1%' : `${Math.round(p)}%`);

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

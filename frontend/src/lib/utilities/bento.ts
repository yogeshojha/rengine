const XL: Record<number, string> = {
	3: 'xl:col-span-3',
	4: 'xl:col-span-4',
	6: 'xl:col-span-6',
	8: 'xl:col-span-8',
	12: 'xl:col-span-12'
};
const LG_HALF = 'lg:col-span-6';

/** Column spans for `n` cells of a 12-column bento that fill every row. */
export function packedSpans(n: number, wide = -1): string[] {
	if (wide >= 0 && wide < n && n <= 3) return widePacked(n, wide);
	const rows = Math.ceil(n / 3);
	const base = Math.floor(n / rows);
	const extra = n % rows;
	const out: string[] = [];
	for (let r = 0; r < rows; r++) {
		const k = base + (r < extra ? 1 : 0);
		for (let i = 0; i < k; i++) {
			const lgTail = n % 2 === 1 && out.length === n - 1;
			out.push(span(k > 1 && !lgTail ? LG_HALF : '', XL[12 / k]));
		}
	}
	return out;
}

function widePacked(n: number, wide: number): string[] {
	const others = n - 1;
	const wideXl = others === 2 ? 6 : others === 1 ? 8 : 12;
	const restXl = others ? (12 - wideXl) / others : 12;
	return Array.from({ length: n }, (_, i) =>
		i === wide ? span('', XL[wideXl]) : span(others === 2 ? LG_HALF : '', XL[restXl])
	);
}

function span(lg: string, xl: string): string {
	return ['col-span-12', lg, xl].filter(Boolean).join(' ');
}

interface ClippedOptions {
	value: string | null | undefined;
	onChange: (clipped: boolean) => void;
}

export function clipped(node: HTMLElement, options: ClippedOptions) {
	let current = options;
	const measure = () => current.onChange(node.scrollWidth > node.clientWidth + 1);
	const observer = new ResizeObserver(measure);

	observer.observe(node);
	measure();
	return {
		update(next: ClippedOptions) {
			current = next;
			measure();
		},
		destroy: () => observer.disconnect()
	};
}

interface VisibleOptions {
	root?: HTMLElement | null;
	margin?: string;
	onChange: (visible: boolean) => void;
}

export function visible(node: HTMLElement, options: VisibleOptions) {
	let observer: IntersectionObserver | null = null;

	function attach(next: VisibleOptions) {
		observer?.disconnect();
		observer = new IntersectionObserver(
			(entries) => next.onChange(entries[entries.length - 1].isIntersecting),
			{ root: next.root ?? null, rootMargin: next.margin ?? '0px' }
		);
		observer.observe(node);
	}

	attach(options);
	return {
		update: attach,
		destroy: () => observer?.disconnect()
	};
}

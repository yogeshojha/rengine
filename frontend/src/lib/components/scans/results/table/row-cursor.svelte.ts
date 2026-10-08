function inLayer(target: EventTarget | null): boolean {
	return target instanceof Element && target.closest('[role=dialog], [role=alertdialog]') !== null;
}

/**
 * The keyboard row cursor the results tables share. The cursor is real focus: j/k move focus
 * between rows, focusing a row (Tab or click) moves the cursor, and a closing detail sheet
 * hands focus back to the row it last showed.
 */
export class RowCursor {
	index = $state(-1);
	readonly #attr: string;
	#root: HTMLElement | null = null;

	/** `attr` is the attribute carrying each row's index, e.g. `data-row-index`. */
	constructor(attr: string) {
		this.#attr = attr;
	}

	/** The focusable element of row `i`: the row itself, or the first focusable inside it. */
	row(i = this.index): HTMLElement | null {
		if (i < 0 || typeof document === 'undefined') return null;
		const scope = this.#root?.isConnected ? this.#root : document;
		const el = scope.querySelector<HTMLElement>(`[${this.#attr}="${i}"]`);
		if (!el || el.hasAttribute('tabindex')) return el;
		return el.querySelector<HTMLElement>('[tabindex]') ?? el;
	}

	/** Moves the cursor and focus to row `i`. */
	focus(i: number) {
		this.index = i;
		const el = this.row(i);
		if (!el) return;
		el.focus({ preventScroll: true });
		el.scrollIntoView({ block: 'nearest' });
	}

	/** One row down or up, clamped to the `count` rows on the page. */
	move(dir: 1 | -1, count: number) {
		if (count <= 0) return;
		this.focus(Math.min(Math.max(this.index + dir, 0), count - 1));
	}

	/** Drops the cursor, and focus with it when focus sits on the cursor row. */
	clear() {
		const el = this.row();
		this.index = -1;
		if (el && document.activeElement === el) el.blur();
	}

	/** Keeps the cursor on the row a detail sheet shows as it steps. */
	follow(i: number) {
		if (i >= 0) this.index = i;
	}

	/**
	 * j/k and the arrows move, Enter opens the cursor row, Esc clears.
	 * Returns true when it handled the key.
	 */
	keys(e: KeyboardEvent, count: number, open: (i: number) => void): boolean {
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			this.move(1, count);
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			this.move(-1, count);
		} else if (e.key === 'Enter' && this.index >= 0 && this.index < count) {
			open(this.index);
		} else if (e.key === 'Escape') {
			// an Esc that closed a sheet or dialog has already handed focus back to the cursor row
			if (!inLayer(e.target)) this.clear();
		} else {
			return false;
		}
		return true;
	}

	/** Attach to the rows' container: focus landing in a row moves the cursor there. */
	track = (node: HTMLElement) => {
		this.#root = node;
		const onFocus = (e: FocusEvent) => {
			const row = e.target instanceof Element ? e.target.closest(`[${this.#attr}]`) : null;
			if (!row) return;
			const i = Number(row.getAttribute(this.#attr));
			if (Number.isInteger(i)) this.index = i;
		};
		node.addEventListener('focusin', onFocus);
		return () => {
			node.removeEventListener('focusin', onFocus);
			if (this.#root === node) this.#root = null;
		};
	};

	/** A detail sheet's onCloseAutoFocus: focus returns to the cursor row, not the opener. */
	restore = (e: Event) => {
		const el = this.row();
		if (!el || !el.getClientRects().length) return;
		e.preventDefault();
		el.focus({ preventScroll: true });
		el.scrollIntoView({ block: 'nearest' });
	};
}

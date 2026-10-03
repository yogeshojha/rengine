/** Holds a dialog or sheet open while its form has unsaved changes. */
export class DiscardGuard {
	asking = $state(false);
	#dirty: () => boolean;
	#close: () => void;

	constructor(dirty: () => boolean, close: () => void) {
		this.#dirty = dirty;
		this.#close = close;
	}

	close = (): void => {
		if (this.#dirty()) this.asking = true;
		else this.#close();
	};

	discard = (): void => {
		this.asking = false;
		this.#close();
	};
}

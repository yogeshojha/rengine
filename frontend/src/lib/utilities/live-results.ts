export const LIVE_REFRESH_MS = 5000;
export const LIVE_OVERVIEW_MS = 12000;
export const LIVE_AGGREGATE_MS = 20000;

/** Runs at most once per `every` ms. A declined call still lands on a trailing timer,
 *  so the last tick of a scan is never the one that gets dropped. */
export class Throttled {
	#run: () => unknown;
	#every: number;
	#last = 0;
	#timer: ReturnType<typeof setTimeout> | null = null;

	constructor(run: () => unknown, every = LIVE_AGGREGATE_MS) {
		this.#run = run;
		this.#every = every;
	}

	call(): unknown {
		const wait = this.#every - (Date.now() - this.#last);
		if (wait <= 0) {
			this.#last = Date.now();
			return this.#run();
		}
		if (this.#timer === null) {
			this.#timer = setTimeout(() => {
				this.#timer = null;
				this.#last = Date.now();
				void this.#run();
			}, wait);
		}
		return undefined;
	}

	stop() {
		if (this.#timer) clearTimeout(this.#timer);
		this.#timer = null;
	}
}

/** Re-runs a results view while its scan is still writing rows, at most once per LIVE_REFRESH_MS. */
export class LiveRefresh {
	#run: () => unknown;
	#every: number;
	#seen = 0;
	#latest = 0;
	#timer: ReturnType<typeof setTimeout> | null = null;

	constructor(run: () => unknown, every = LIVE_REFRESH_MS) {
		this.#run = run;
		this.#every = every;
	}

	notify(revision: number, active: boolean) {
		this.#latest = revision;
		if (!active || revision === this.#seen || this.#timer) return;
		this.#arm();
	}

	#arm() {
		this.#timer = setTimeout(() => {
			this.#timer = null;
			// table frozen at the counts from when you left
			if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
				this.#arm();
				return;
			}
			this.#seen = this.#latest;
			void this.#run();
		}, this.#every);
	}

	stop() {
		if (this.#timer) clearTimeout(this.#timer);
		this.#timer = null;
	}
}

export const LIVE_REFRESH_MS = 5000;
// the overview reloads seven panels, so it watches at a slower cadence than one table
export const LIVE_OVERVIEW_MS = 12000;

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
			// a background tab keeps receiving events; refreshing it fetches nobody's screen.
			// wait rather than drop it, or a scan that finishes while you are away leaves the
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

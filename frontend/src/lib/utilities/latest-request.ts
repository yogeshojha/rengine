export interface RequestHandlers<R> {
	/** The response, when no newer request started while it was in flight. */
	done: (res: R) => void;
	/** The error, under the same condition. */
	failed?: (err: unknown) => void;
	/** Runs after either, under the same condition. */
	settled?: () => void;
}

/** Latest-request-wins guard: a response lands only when no newer request started after it. */
export class LatestRequest {
	#seq = 0;

	/** Starts a request. The returned check stays true until a newer one starts or `cancel` runs. */
	begin(): () => boolean {
		const mine = ++this.#seq;
		return () => mine === this.#seq;
	}

	/** Retires the request in flight, so its response is dropped. */
	cancel(): void {
		this.#seq++;
	}

	/** Runs `fetch` and hands its outcome to `on` only while this call is still the newest. */
	async run<R>(fetch: () => Promise<R>, on: RequestHandlers<R>): Promise<void> {
		const current = this.begin();
		try {
			const res = await fetch();
			if (current()) on.done(res);
		} catch (err) {
			if (current()) on.failed?.(err);
		} finally {
			if (current()) on.settled?.();
		}
	}
}

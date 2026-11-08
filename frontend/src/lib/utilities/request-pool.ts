export const PAGE_REQUEST_LIMIT = 4;

export type RequestPool = <T>(task: () => Promise<T>) => Promise<T>;

/** Run tasks with at most `limit` in flight, in the order queued. */
export function requestPool(limit: number = PAGE_REQUEST_LIMIT): RequestPool {
	let active = 0;
	const queue: (() => void)[] = [];
	const next = () => {
		active--;
		queue.shift()?.();
	};
	return <T>(task: () => Promise<T>) =>
		new Promise<T>((resolve, reject) => {
			const start = () => {
				active++;
				task().then(resolve, reject).finally(next);
			};
			if (active < limit) start();
			else queue.push(start);
		});
}

import { whatsNewApi } from '$lib/api/whats-new';

function createWhatsNewStore() {
	let unseen = $state(0);
	let fetchedProjectId = $state<string | null>(null);
	let pending: Promise<void> | null = null;
	let pendingId: string | null = null;
	let wanted: string | null = null;
	let seq = 0;

	return {
		get unseen() {
			return unseen;
		},

		async fetch(projectId: string, force = false) {
			wanted = projectId;
			if (!force && fetchedProjectId === projectId) return;
			if (!force && pending && pendingId === projectId) return pending;
			const my = ++seq;
			const current = () => my === seq && wanted === projectId;
			const request: Promise<void> = whatsNewApi
				.unseen(projectId)
				.then(
					(res) => {
						if (!current()) return;
						unseen = res.count;
						fetchedProjectId = projectId;
					},
					() => {
						if (current()) unseen = 0;
					}
				)
				.finally(() => {
					if (pending !== request) return;
					pending = null;
					pendingId = null;
				});
			pending = request;
			pendingId = projectId;
			return request;
		},

		async caughtUp(projectId: string): Promise<void> {
			await whatsNewApi.caughtUp(projectId);
			unseen = 0;
			fetchedProjectId = projectId;
		},

		clear() {
			seq++;
			unseen = 0;
			fetchedProjectId = null;
			pending = null;
			pendingId = null;
			wanted = null;
		}
	};
}

export const whatsNewStore = createWhatsNewStore();

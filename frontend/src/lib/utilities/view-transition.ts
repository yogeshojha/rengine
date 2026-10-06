import { tick } from 'svelte';

export async function morph(update: () => unknown): Promise<void> {
	const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	if (still || !document.startViewTransition) {
		await update();
		return;
	}
	await document.startViewTransition(async () => {
		await update();
		await tick();
	}).updateCallbackDone;
}

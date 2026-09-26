<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import EstateTray from '$lib/components/targets/estate-tray.svelte';
	import { targetsApi } from '$lib/api/targets';
	import type { ProjectEstate } from '$lib/types/estate';

	interface Props {
		projectId: string;
		onAdded: () => void;
	}

	let { projectId, onAdded }: Props = $props();

	let estate = $state<ProjectEstate | null>(null);
	let loadedFor: string | null = null;

	$effect(() => {
		const pid = projectId;
		if (!pid || loadedFor === pid) return;
		loadedFor = pid;
		untrack(() => {
			targetsApi
				.projectEstate(pid)
				.then((e) => (estate = e))
				.catch(() => (estate = null));
		});
	});

	let bySource = $derived.by(() => {
		const tally = new SvelteMap<string, number>();
		for (const d of estate?.domains ?? [])
			for (const s of d.sources) tally.set(s.target_value, (tally.get(s.target_value) ?? 0) + 1);
		return [...tally.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
	});
</script>

{#if estate}
	<EstateTray
		count={estate.untracked}
		subject="the project's targets"
		detail={bySource.map(([t, n]) => `${n} from ${t}`).join(' · ')}
		domains={estate.domains}
		sheetDescription="{estate.untracked} domains named by {estate.targets_examined} targets{estate
			.domains.length < estate.untracked
			? ` · strongest ${estate.domains.length} shown`
			: ''}"
		{onAdded}
	/>
{/if}

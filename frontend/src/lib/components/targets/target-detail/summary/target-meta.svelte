<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { usersApi } from '$lib/api/users';
	import CopyButton from '$lib/components/copy-button.svelte';

	let { target }: { target: Target } = $props();

	const projectName = $derived(
		projectsStore.projects.find((p) => p.id === target.project_id)?.name ??
			projectsStore.activeProject?.name ??
			null
	);

	let creator = $state<string | null>(null);
	$effect(() => {
		const id = target.created_by;
		creator = null;
		if (!id) return;
		usersApi
			.getSummary(id)
			.then((u) => {
				if (target.created_by === id) creator = u.username;
			})
			.catch(() => {});
	});

	const lastEnriched = $derived.by(() => {
		const ts = [
			target.whois_status === TaskStatus.SUCCESS ? target.whois?.queried_at : null,
			target.dns_status === TaskStatus.SUCCESS ? target.dns?.queried_at : null,
			target.bgp_status === TaskStatus.SUCCESS ? target.bgp?.queried_at : null
		]
			.filter((x): x is string => Boolean(x))
			.map((x) => new Date(x).getTime());
		return ts.length ? new Date(Math.max(...ts)).toISOString() : null;
	});
</script>

<div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-1 text-[11px] text-muted-foreground/55">
	{#if projectName}
		<span>Project <span class="text-foreground/65">{projectName}</span></span>
		<span class="text-muted-foreground/25">·</span>
	{/if}
	<span
		>Added <span class="text-foreground/65">{formatShortDate(target.created_at)}</span>{#if creator}
			by <span class="text-foreground/65">{creator}</span>{/if}</span
	>
	{#if target.updated_at !== target.created_at}
		<span class="text-muted-foreground/25">·</span>
		<span>Updated <span class="text-foreground/65">{relativeTime(target.updated_at)}</span></span>
	{/if}
	<span class="text-muted-foreground/25">·</span>
	<span>
		Last enriched
		<span class="text-foreground/65">{lastEnriched ? relativeTime(lastEnriched) : 'never'}</span>
	</span>
	<span class="ml-auto flex items-center gap-1 group/id">
		<span class="font-mono text-[10px] text-muted-foreground/40">{target.id}</span>
		<span
			class="opacity-100 sm:opacity-0 sm:group-hover/id:opacity-100 group-focus-within/id:opacity-100 transition-opacity"
		>
			<CopyButton value={target.id} />
		</span>
	</span>
</div>

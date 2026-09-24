<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { TCOL } from './columns';
	import { targetPrefs } from './prefs.svelte';

	const NAME = ['w-44', 'w-36', 'w-52', 'w-40', 'w-32', 'w-48'];

	interface Props {
		rows?: number;
	}

	let { rows = 8 }: Props = $props();
</script>

<div class="@container/targets w-full" aria-busy="true">
	<div
		class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
	>
		<div class={TCOL.select}></div>
		<div class={TCOL.target}>Target</div>
		{#if targetPrefs.shows('run')}<div class={TCOL.run}>Last run</div>{/if}
		{#if targetPrefs.shows('findings')}<div class={TCOL.findings}>Findings</div>{/if}
		{#if targetPrefs.shows('assets')}<div class={TCOL.assets}>Assets</div>{/if}
		{#if targetPrefs.shows('change')}<div class={TCOL.change}>Change</div>{/if}
		{#if targetPrefs.shows('organizations')}<div class={TCOL.organizations}>Organizations</div>{/if}
		{#if targetPrefs.shows('tags')}<div class={TCOL.tags}>Tags</div>{/if}
		<div class={TCOL.actions}></div>
	</div>
	{#each { length: rows } as _, i (i)}
		<div class="flex items-center gap-3 border-b border-border/60 px-4 py-2.5">
			<div class="{TCOL.select} h-6"><Skeleton class="size-4 rounded-[4px]" /></div>
			<div class="{TCOL.target} flex flex-col gap-1.5">
				<Skeleton class="h-4 {NAME[i % NAME.length]}" />
				<div class="flex gap-1.5">
					<Skeleton class="h-3.5 w-12" />
					<Skeleton class="h-3.5 w-40" />
				</div>
			</div>
			{#if targetPrefs.shows('run')}
				<div class="{TCOL.run} flex-col gap-1">
					<Skeleton class="h-6 w-24 rounded-md" />
					<Skeleton class="h-3 w-12" />
				</div>
			{/if}
			{#if targetPrefs.shows('findings')}
				<div class={TCOL.findings}><Skeleton class="h-6 w-28 rounded-md" /></div>
			{/if}
			{#if targetPrefs.shows('assets')}
				<div class={TCOL.assets}><Skeleton class="h-6 w-40 rounded-md" /></div>
			{/if}
			{#if targetPrefs.shows('change')}
				<div class={TCOL.change}><Skeleton class="h-4 w-14" /></div>
			{/if}
			{#if targetPrefs.shows('organizations')}
				<div class={TCOL.organizations}><Skeleton class="h-6 w-16 rounded-md" /></div>
			{/if}
			{#if targetPrefs.shows('tags')}
				<div class={TCOL.tags}><Skeleton class="h-6 w-16 rounded-md" /></div>
			{/if}
			<div class="{TCOL.actions} gap-1"><Skeleton class="size-7 rounded-md" /></div>
		</div>
	{/each}
</div>

<script lang="ts">
	import { Building2, Play, RefreshCw, Tag, Trash2, X } from 'lucide-svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';

	interface Props {
		selectedCount: number;
		tags: { id: string; name: string; color: string }[];
		organizations: { id: string; name: string }[];
		onScan: () => void;
		onDelete: () => void;
		onClear: () => void;
		onEnrich: (kind: 'whois' | 'dns' | 'bgp') => void;
		onAddTag: (name: string) => void;
		onAddOrg: (name: string) => void;
	}

	let {
		selectedCount,
		tags,
		organizations,
		onScan,
		onDelete,
		onClear,
		onEnrich,
		onAddTag,
		onAddOrg
	}: Props = $props();

	const btn =
		'flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors text-sm text-gray-100 font-medium';
</script>

<div
	class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ease-out {selectedCount >
	0
		? 'translate-y-0 opacity-100'
		: 'translate-y-3 opacity-0 pointer-events-none'}"
>
	<div
		class="flex items-center gap-0.5 bg-gray-900/80 backdrop-blur-xl backdrop-saturate-180 border border-white/10 rounded-2xl shadow-xl shadow-black/30 p-1.5"
	>
		<div class="flex items-center px-2.5 py-1.5">
			<span class="text-xs font-medium text-gray-400 tabular-nums">
				{selectedCount}
				{selectedCount === 1 ? 'target' : 'targets'} selected
			</span>
		</div>

		<div class="w-px h-4 bg-white/10 self-center mx-0.5"></div>

		<button class={btn} onclick={onScan}>
			<Play class="h-3.5 w-3.5 text-blue-400" />
			Scan
		</button>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger class={btn}>
				<RefreshCw class="h-3.5 w-3.5 text-emerald-400" />
				Enrich
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="center" class="w-40">
				<DropdownMenu.Item onclick={() => onEnrich('whois')}>Re-run WHOIS</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => onEnrich('dns')}>Re-run DNS</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => onEnrich('bgp')}>Re-run BGP</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger class={btn}>
				<Tag class="h-3.5 w-3.5 text-violet-400" />
				Tag
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="center" class="max-h-72 w-48 overflow-y-auto">
				{#if tags.length === 0}
					<DropdownMenu.Item disabled>No tags</DropdownMenu.Item>
				{:else}
					{#each tags as tag (tag.id)}
						<DropdownMenu.Item onclick={() => onAddTag(tag.name)} class="gap-2">
							<span class="h-2.5 w-2.5 rounded-full shrink-0" style="background-color: {tag.color}"
							></span>
							<span class="truncate">{tag.name}</span>
						</DropdownMenu.Item>
					{/each}
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger class={btn}>
				<Building2 class="h-3.5 w-3.5 text-sky-400" />
				Org
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="center" class="max-h-72 w-48 overflow-y-auto">
				{#if organizations.length === 0}
					<DropdownMenu.Item disabled>No organizations</DropdownMenu.Item>
				{:else}
					{#each organizations as org (org.id)}
						<DropdownMenu.Item onclick={() => onAddOrg(org.name)} class="truncate">
							{org.name}
						</DropdownMenu.Item>
					{/each}
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<button
			class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
			onclick={onDelete}
		>
			<Trash2 class="h-3.5 w-3.5 text-red-400" />
			<span class="text-sm text-red-400 font-medium">Delete</span>
		</button>

		<div class="w-px h-4 bg-white/10 self-center mx-0.5"></div>
		<button
			class="flex items-center justify-center w-7 h-7 rounded-lg hover:bg-white/10 transition-colors"
			onclick={onClear}
		>
			<X class="h-3.5 w-3.5 text-gray-500" />
		</button>
	</div>
</div>

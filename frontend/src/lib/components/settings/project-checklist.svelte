<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import type { Project } from '$lib/types/project';

	interface Props {
		projects: readonly Project[];
		selected: string[];
		disabled?: boolean;
	}

	let { projects, selected = $bindable([]), disabled = false }: Props = $props();

	function toggle(id: string, on: boolean) {
		selected = on ? [...selected.filter((s) => s !== id), id] : selected.filter((s) => s !== id);
	}
</script>

{#if projects.length === 0}
	<p class="rounded-lg border px-3 py-2.5 text-sm text-muted-foreground">No projects</p>
{:else}
	<div class="overflow-hidden rounded-lg border">
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-64">
			<div class="divide-y" role="group" aria-label="Projects">
				{#each projects as project (project.id)}
					<Label
						class="flex cursor-pointer items-center gap-3 px-3 py-2.5 font-normal transition-colors hover:bg-muted/40"
					>
						<Checkbox
							checked={selected.includes(project.id)}
							onCheckedChange={(v) => toggle(project.id, v === true)}
							{disabled}
						/>
						<span class="min-w-0 flex-1 text-sm font-medium wrap-anywhere">{project.name}</span>
					</Label>
				{/each}
			</div>
		</ScrollArea>
	</div>
{/if}

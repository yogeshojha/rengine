<script lang="ts">
	import { projectsStore } from '$lib/stores/projects.svelte';
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-lg font-semibold">Dashboard</h1>
		<p class="text-sm text-muted-foreground">
			{projectsStore.activeProject?.name ?? 'Select a project'}
		</p>
	</div>

	{#if projectsStore.activeProject}
		<div class="grid grid-cols-4 gap-4">
			<!-- Activity feed — right column -->
			<div class="col-span-1">
				<div class="h-[600px]"></div>
			</div>

			<!-- Placeholder slots for future widgets -->
			<div class="col-span-3">
				<div class="grid grid-cols-3 gap-4">
					<div
						class="col-span-3 h-48 rounded-lg border border-dashed border-border flex items-center justify-center"
					>
						<span class="text-xs text-muted-foreground">Overview stats</span>
					</div>
					<div
						class="col-span-2 h-64 rounded-lg border border-dashed border-border flex items-center justify-center"
					>
						<span class="text-xs text-muted-foreground">Attack surface</span>
					</div>
					<div
						class="col-span-1 h-64 rounded-lg border border-dashed border-border flex items-center justify-center"
					>
						<span class="text-xs text-muted-foreground">Scan queue</span>
					</div>
				</div>
			</div>
		</div>
	{:else}
		<div
			class="flex items-center justify-center h-64 rounded-lg border border-dashed border-border"
		>
			<p class="text-sm text-muted-foreground">No project selected</p>
		</div>
	{/if}
</div>

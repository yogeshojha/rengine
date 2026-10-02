<script lang="ts">
	import type { IconComponent } from '$lib/config/icons';

	let { icon: Icon, title }: { icon: IconComponent; title: string } = $props();
</script>

<div class="space-y-3">
	<div class="flex size-9 items-center justify-center rounded-lg border bg-muted text-foreground">
		<Icon class="size-[18px]" />
	</div>
	<h2 class="text-xl font-semibold tracking-tight text-foreground">{title}</h2>
</div>

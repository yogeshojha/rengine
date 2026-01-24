<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import BookOpen from 'lucide-svelte/icons/book-open';
	import ExternalLink from 'lucide-svelte/icons/external-link';

	interface DocLink {
		title: string;
		url: string;
		icon: typeof BookOpen;
	}

	let { link }: { link: DocLink } = $props();
</script>

<Sidebar.Group class="mt-auto">
	<Sidebar.Menu>
		<Sidebar.MenuItem>
			<Sidebar.MenuButton tooltipContent={link.title}>
				{#snippet child({ props })}
					<a href={link.url} target="_blank" rel="noopener noreferrer" {...props}>
						<link.icon class="size-4" />
						<span>{link.title}</span>
						<ExternalLink class="ms-auto size-3 text-muted-foreground" />
					</a>
				{/snippet}
			</Sidebar.MenuButton>
		</Sidebar.MenuItem>
	</Sidebar.Menu>
</Sidebar.Group>
<script lang="ts">
	import { ExternalLink } from 'lucide-svelte';

	type ImportType = 'text' | 'json' | 'csv';
	export let type: ImportType;
</script>

<p class="text-xs text-muted-foreground">
	<span class="inline-flex flex-wrap items-center gap-1">
		{#if type === 'text'}
			Accepted targets: domain, IP, CIDR range, ASN (<code>AS123</code>), or URL.<a
				href="https://rengine.wiki/import/targets"
				target="_blank"
				rel="noopener noreferrer"
				class="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground"
			>
				Supported target types
				<ExternalLink class="h-3 w-3" />
			</a>
		{:else if type === 'json'}
			Each target supports <code>target_value</code>, <code>tags</code>,
			<code>organizations</code>, and <code>display_name</code>.
            <a
				href="https://rengine.wiki/import/json"
				target="_blank"
				rel="noopener noreferrer"
				class="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground"
			>
				Supported JSON import formats
				<ExternalLink class="h-3 w-3" />
			</a>
		{:else if type === 'csv'}
			Supported columns:
			<code>target_value</code>, <code>tags</code>,
			<code>organizations</code>, <code>display_name</code>. Headers are optional.
			<a
				href="https://rengine.wiki/import/csv"
				target="_blank"
				rel="noopener noreferrer"
				class="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground"
			>
				Supported CSV import formats
				<ExternalLink class="h-3 w-3" />
			</a>
		{/if}
	</span>
</p>

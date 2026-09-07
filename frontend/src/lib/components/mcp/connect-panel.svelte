<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import CodeBlock from '$lib/components/code-block.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import type { McpStatus } from '$lib/types/mcp';

	interface Props {
		status: McpStatus;
	}

	let { status }: Props = $props();

	type Transport = 'http' | 'stdio';
	const TRANSPORTS: { value: Transport; label: string; file: string }[] = [
		{ value: 'http', label: 'HTTP', file: 'mcp.json' },
		{ value: 'stdio', label: 'stdio', file: 'claude_desktop_config.json' }
	];
	const PLACEHOLDER = 'paste-a-service-token';

	let transport = $state<Transport>('http');

	const httpSnippet = $derived(
		JSON.stringify(
			{
				mcpServers: {
					rengine: {
						type: 'http',
						url: status.endpoint,
						headers: { Authorization: `Bearer ${PLACEHOLDER}` }
					}
				}
			},
			null,
			2
		)
	);

	const stdioSnippet = $derived.by(() => {
		const [command, ...args] = status.stdio_command.split(' ');
		return JSON.stringify(
			{ mcpServers: { rengine: { command, args, env: { RENGINE_MCP_TOKEN: PLACEHOLDER } } } },
			null,
			2
		);
	});

	const current = $derived(TRANSPORTS.find((t) => t.value === transport) ?? TRANSPORTS[0]);
</script>

<section class="flex flex-col gap-3 border-t py-5">
	<SectionHead title="Connect an agent">
		<ToggleGroup.Root
			type="single"
			size="sm"
			variant="outline"
			value={transport}
			onValueChange={(v) => v && (transport = v as Transport)}
		>
			{#each TRANSPORTS as t (t.value)}
				<ToggleGroup.Item value={t.value} class="h-7 px-2.5 text-xs">{t.label}</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
	</SectionHead>
	<p class="text-sm text-muted-foreground">
		{#if transport === 'http'}
			Add this block to the agent's MCP configuration and replace the placeholder with a service
			token. A reverse proxy owns TLS and any access from outside the host.
		{:else}
			The agent starts this process itself, so Start and Stop do not apply. Revoking the token cuts
			access.
		{/if}
	</p>
	<CodeBlock
		code={transport === 'http' ? httpSnippet : stdioSnippet}
		lang="json"
		label={current.file}
		numbers={false}
	/>
</section>

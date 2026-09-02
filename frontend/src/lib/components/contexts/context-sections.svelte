<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { SvelteSet } from 'svelte/reactivity';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Info from '@lucide/svelte/icons/info';
	import Check from '@lucide/svelte/icons/check';
	import Minus from '@lucide/svelte/icons/minus';

	import { Textarea } from '$lib/components/ui/textarea';
	import { Button } from '$lib/components/ui/button';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import * as Popover from '$lib/components/ui/popover';
	import { proxiesStore } from '$lib/stores/proxies.svelte';

	import AuthSection from './auth-section.svelte';
	import RateSection from './rate-section.svelte';
	import ScopeSection from './scope-section.svelte';
	import RuntimeSection from './runtime-section.svelte';
	import ProxySection from './proxy-section.svelte';
	import { markTouchedSecrets, type ContextFormSection } from './context-form';
	import { contextFacets } from './context-summary';
	import type { ScanContextCreate, AuthConfig, AuthHeader } from '$lib/types/scan-context';

	const ALL_SECTIONS: ContextFormSection[] = [
		'auth',
		'rate',
		'scope',
		'runtime',
		'proxy',
		'identity'
	];

	interface Props {
		draft: ScanContextCreate;
		open: Record<ContextFormSection, boolean>;
		touched: SvelteSet<string>;
		onPatch: (updates: Partial<ScanContextCreate>) => void;
		sections?: ContextFormSection[];
		seedKey?: number;
	}

	let {
		draft,
		open = $bindable(),
		touched,
		onPatch,
		sections = ALL_SECTIONS,
		seedKey = 0
	}: Props = $props();

	const META: Record<ContextFormSection, { title: string; subtitle: string }> = {
		identity: { title: 'Description', subtitle: 'Notes on when to use this context' },
		auth: { title: 'Authentication', subtitle: 'Credentials and headers sent with every request' },
		rate: { title: 'Rate limiting', subtitle: 'Request rate caps and concurrency multipliers' },
		scope: { title: 'Scope', subtitle: 'Assets to include in or exclude from scanning' },
		runtime: { title: 'Runtime', subtitle: 'Protocol and redirect behaviour' },
		proxy: { title: 'Proxy', subtitle: 'Route scan traffic through a proxy' }
	};

	const proxyName = $derived(
		draft.proxy_id
			? (proxiesStore.proxies.find((p) => p.id === draft.proxy_id)?.name ?? null)
			: null
	);
	const facets = $derived(contextFacets(draft, proxyName));

	function facetOf(key: ContextFormSection): { set: boolean; value: string } {
		if (key === 'identity') {
			const text = draft.description?.trim() ?? '';
			return { set: text.length > 0, value: text || 'No description' };
		}
		if (key === 'auth') {
			const auth = facets.find((f) => f.key === 'auth')!;
			const headers = facets.find((f) => f.key === 'headers')!;
			const parts = [auth.set ? auth.value : null, headers.set ? `+ ${headers.value}` : null];
			const value = parts.filter(Boolean).join(' ');
			return { set: auth.set || headers.set, value: value || 'None' };
		}
		const facet = facets.find((f) => f.key === key)!;
		return { set: facet.set, value: facet.value };
	}

	function handleAuthChange(next: { auth: AuthConfig; extraHeaders: AuthHeader[] }) {
		markTouchedSecrets(next.auth, touched);
		onPatch({
			auth_type: next.auth.auth_type as ScanContextCreate['auth_type'],
			auth: next.auth,
			extra_headers: next.extraHeaders
		});
	}
</script>

{#snippet section(key: ContextFormSection, content: Snippet, info?: Snippet)}
	{@const facet = facetOf(key)}
	<Collapsible.Root bind:open={open[key]} class="section" data-set={facet.set}>
		<div class="head">
			<span class="mark" aria-hidden="true">
				{#if facet.set}
					<Check size={13} class="text-primary" />
				{:else}
					<Minus size={13} class="opacity-60" />
				{/if}
			</span>
			<Collapsible.Trigger
				class="disclose"
				aria-label="{open[key] ? 'Collapse' : 'Expand'} {META[key].title}"
			>
				<span class="titles">
					<span class="title">{META[key].title}</span>
					<span class="subtitle">{META[key].subtitle}</span>
				</span>
				<span class="value" class:muted={!facet.set}>{facet.value}</span>
				<ChevronRight size={14} class="chev" />
			</Collapsible.Trigger>
			{#if info}
				<Popover.Root>
					<Popover.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="h-7 w-7 shrink-0 text-muted-foreground"
								aria-label="Precedence"
							>
								<Info size={13} />
							</Button>
						{/snippet}
					</Popover.Trigger>
					<Popover.Content class="w-72 text-xs text-muted-foreground">
						{@render info()}
					</Popover.Content>
				</Popover.Root>
			{/if}
		</div>
		<Collapsible.Content class="body">
			{@render content()}
		</Collapsible.Content>
	</Collapsible.Root>
{/snippet}

{#snippet authInfo()}
	<p class="mb-1 font-medium text-foreground">Precedence</p>
	<ul class="space-y-1 pl-3">
		<li class="list-disc">
			Context headers are added to the engine headers. On a conflict, the context value is used.
		</li>
		<li class="list-disc">A context cannot enable a stage the engine disabled.</li>
	</ul>
{/snippet}

{#snippet rateInfo()}
	<p class="mb-1 font-medium text-foreground">Precedence</p>
	<ul class="space-y-1 pl-3">
		<li class="list-disc">Context rate overrides replace the engine rate limits.</li>
		<li class="list-disc">The global limit is a ceiling. It lowers rates but never raises them.</li>
	</ul>
{/snippet}

{#snippet identityBody()}
	<Textarea
		value={draft.description ?? ''}
		placeholder="Describe when to use this context, such as the environment or program it applies to."
		class="min-h-20 text-sm"
		oninput={(e) => onPatch({ description: e.currentTarget.value || null })}
	/>
{/snippet}

{#snippet authBody()}
	{#key seedKey}
		<AuthSection
			auth={draft.auth as AuthConfig}
			extraHeaders={draft.extra_headers}
			onChange={handleAuthChange}
		/>
	{/key}
{/snippet}

{#snippet rateBody()}
	<RateSection context={draft} onChange={onPatch} />
{/snippet}

{#snippet scopeBody()}
	<ScopeSection context={draft} onChange={onPatch} />
{/snippet}

{#snippet runtimeBody()}
	<RuntimeSection context={draft} onChange={onPatch} />
{/snippet}

{#snippet proxyBody()}
	<ProxySection context={draft} onChange={onPatch} />
{/snippet}

{#snippet sectionFor(key: ContextFormSection)}
	{#if key === 'identity'}
		{@render section('identity', identityBody)}
	{:else if key === 'auth'}
		{@render section('auth', authBody, authInfo)}
	{:else if key === 'rate'}
		{@render section('rate', rateBody, rateInfo)}
	{:else if key === 'scope'}
		{@render section('scope', scopeBody)}
	{:else if key === 'runtime'}
		{@render section('runtime', runtimeBody)}
	{:else if key === 'proxy'}
		{@render section('proxy', proxyBody)}
	{/if}
{/snippet}

<div class="sections">
	{#each sections as key (key)}
		{@render sectionFor(key)}
	{/each}
</div>

<style>
	.sections {
		border: 1px solid var(--border);
		border-radius: 0.7rem;
		background: var(--card);
		overflow: hidden;
	}
	:global(.section) {
		border-bottom: 1px solid var(--border);
	}
	:global(.section:last-child) {
		border-bottom: none;
	}
	:global(.section[data-state='open']) {
		background: color-mix(in oklch, var(--primary) 3%, transparent);
	}

	.head {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 10px 0 14px;
		min-height: 52px;
	}
	.mark {
		display: inline-flex;
		flex-shrink: 0;
		width: 14px;
	}
	:global(.section .disclose) {
		display: flex;
		align-items: center;
		gap: 12px;
		flex: 1;
		min-width: 0;
		padding: 10px 0;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		color: inherit;
	}
	.titles {
		display: flex;
		flex-direction: column;
		gap: 1px;
		min-width: 0;
		flex: 0 0 auto;
		max-width: 46%;
	}
	.title {
		font-size: 13px;
		font-weight: 500;
	}
	.subtitle {
		font-size: 11px;
		color: var(--muted-foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.value {
		flex: 1;
		min-width: 0;
		text-align: right;
		font-size: 11.5px;
		color: var(--foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		font-variant-numeric: tabular-nums;
	}
	.value.muted {
		color: var(--muted-foreground);
	}
	:global(.section .disclose .chev) {
		flex-shrink: 0;
		color: var(--muted-foreground);
		transition: transform 0.15s ease;
	}
	:global(.section[data-state='open'] .disclose .chev) {
		transform: rotate(90deg);
	}
	:global(.section .body) {
		padding: 4px 16px 18px 38px;
	}

	@media (max-width: 640px) {
		.value {
			display: none;
		}
		.titles {
			max-width: none;
		}
		:global(.section .body) {
			padding-left: 16px;
		}
	}
</style>

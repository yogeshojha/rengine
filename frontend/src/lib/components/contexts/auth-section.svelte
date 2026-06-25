<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { Separator } from '$lib/components/ui/separator';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import X from '@lucide/svelte/icons/x';
	import {
		AUTH_TYPES,
		MASK,
		type AuthConfig,
		type AuthHeader,
		type AuthType
	} from '$lib/types/scan-context';

	interface Props {
		auth: AuthConfig;
		extraHeaders: AuthHeader[];
		onChange: (next: { auth: AuthConfig; extraHeaders: AuthHeader[] }) => void;
	}

	let { auth, extraHeaders, onChange }: Props = $props();

	const AUTH_LABELS: Record<AuthType, string> = {
		none: 'None',
		bearer: 'Bearer token',
		basic: 'Basic auth',
		header: 'Custom header',
		cookie: 'Cookie',
		api_key: 'API key'
	};

	type SecretField =
		| 'bearer_token'
		| 'basic_password'
		| 'header_value'
		| 'cookie_value'
		| 'api_key_value';

	// svelte-ignore state_referenced_locally
	const wasSet: Record<SecretField, boolean> = {
		bearer_token: auth.bearer_token === MASK,
		basic_password: auth.basic_password === MASK,
		header_value: auth.header_value === MASK,
		cookie_value: auth.cookie_value === MASK,
		api_key_value: auth.api_key_value === MASK
	};

	// svelte-ignore state_referenced_locally
	let local = $state<AuthConfig>({
		...auth,
		bearer_token: wasSet.bearer_token ? null : auth.bearer_token,
		basic_password: wasSet.basic_password ? null : auth.basic_password,
		header_value: wasSet.header_value ? null : auth.header_value,
		cookie_value: wasSet.cookie_value ? null : auth.cookie_value,
		api_key_value: wasSet.api_key_value ? null : auth.api_key_value
	});

	let show = $state<Record<SecretField, boolean>>({
		bearer_token: false,
		basic_password: false,
		header_value: false,
		cookie_value: false,
		api_key_value: false
	});

	// svelte-ignore state_referenced_locally
	const maskedNames = new Set(
		extraHeaders.filter((h) => h.value === MASK).map((h) => h.name.toLowerCase())
	);
	// svelte-ignore state_referenced_locally
	let headers = $state<AuthHeader[]>(
		extraHeaders.map((h) => ({ name: h.name, value: h.value === MASK ? '' : h.value }))
	);

	function emit() {
		const cleaned = headers
			.filter((h) => h.name.trim() !== '')
			.map((h) =>
				h.value === '' && maskedNames.has(h.name.toLowerCase())
					? { name: h.name, value: MASK }
					: { ...h }
			);
		onChange({ auth: { ...local }, extraHeaders: cleaned });
	}

	function setField(key: keyof AuthConfig, value: string | null) {
		local = { ...local, [key]: value };
		emit();
	}

	function setType(t: string) {
		local = { ...local, auth_type: t };
		emit();
	}

	function onSecretInput(field: SecretField, value: string) {
		local = { ...local, [field]: value };
		emit();
	}

	function clearSecret(field: SecretField) {
		wasSet[field] = false;
		local = { ...local, [field]: '' };
		emit();
	}

	function secretHint(field: SecretField): boolean {
		return wasSet[field] && local[field] == null;
	}

	let headerRows = $derived(
		headers.length === 0 ? [{ name: '', value: '' }] : [...headers, { name: '', value: '' }]
	);

	function commitHeaders(rows: AuthHeader[]) {
		headers = rows.filter((r) => r.name.trim() !== '' || r.value.trim() !== '');
		emit();
	}

	function updateHeader(i: number, key: 'name' | 'value', v: string) {
		const rows = headerRows.map((r) => ({ ...r }));
		rows[i][key] = v;
		commitHeaders(rows);
	}

	function removeHeader(i: number) {
		commitHeaders(headerRows.filter((_, idx) => idx !== i));
	}

	let previewLine = $derived.by(() => {
		switch (local.auth_type) {
			case 'bearer':
				return 'Authorization: Bearer ••••';
			case 'basic':
				return `Authorization: Basic •••• ${local.basic_username ? `(${local.basic_username})` : ''}`.trim();
			case 'header':
				return `${local.header_name || 'X-Header'}: ••••`;
			case 'cookie':
				return 'Cookie: ••••';
			case 'api_key':
				return `${local.api_key_name || 'X-API-Key'}: ••••`;
			default:
				return null;
		}
	});

	const SECRET_PLACEHOLDER = 'Enter value';
</script>

{#snippet secretInput(field: SecretField, label: string, ph: string)}
	<div class="space-y-1.5">
		<Label class="text-xs">{label}</Label>
		<div class="flex items-center gap-2">
			<Input
				type={show[field] ? 'text' : 'password'}
				value={local[field] ?? ''}
				placeholder={secretHint(field) ? 'Leave blank to keep current value' : ph}
				class="h-9 flex-1 font-mono text-xs"
				autocomplete="off"
				oninput={(e) => onSecretInput(field, e.currentTarget.value)}
			/>
			<Button
				variant="ghost"
				size="icon"
				class="h-9 w-9 shrink-0 text-muted-foreground"
				onclick={() => (show[field] = !show[field])}
				aria-label="Toggle visibility"
			>
				{#if show[field]}<EyeOff class="h-4 w-4" />{:else}<Eye class="h-4 w-4" />{/if}
			</Button>
		</div>
		{#if secretHint(field)}
			<div class="flex items-center gap-2">
				<p class="text-xs text-muted-foreground">
					Value set — leave blank to keep, or type to replace.
				</p>
				<Button
					variant="ghost"
					size="sm"
					class="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
					onclick={() => clearSecret(field)}
				>
					Clear
				</Button>
			</div>
		{/if}
	</div>
{/snippet}

<div class="space-y-5">
	<RadioGroup.Root
		value={local.auth_type}
		onValueChange={setType}
		class="grid grid-cols-2 gap-2 sm:grid-cols-3"
	>
		{#each AUTH_TYPES as t (t)}
			<Label
				class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm data-[active=true]:border-primary data-[active=true]:bg-muted"
				data-active={local.auth_type === t}
			>
				<RadioGroup.Item value={t} />
				<span>{AUTH_LABELS[t]}</span>
			</Label>
		{/each}
	</RadioGroup.Root>

	{#if local.auth_type === 'none'}
		<p class="text-sm text-muted-foreground">
			No authentication headers are injected. Requests are sent unauthenticated.
		</p>
	{:else if local.auth_type === 'bearer'}
		{@render secretInput('bearer_token', 'Bearer token', SECRET_PLACEHOLDER)}
	{:else if local.auth_type === 'basic'}
		<div class="space-y-1.5">
			<Label class="text-xs">Username</Label>
			<Input
				value={local.basic_username ?? ''}
				placeholder="username"
				class="h-9 font-mono text-xs"
				autocomplete="off"
				oninput={(e) => setField('basic_username', e.currentTarget.value || null)}
			/>
		</div>
		{@render secretInput('basic_password', 'Password', SECRET_PLACEHOLDER)}
	{:else if local.auth_type === 'header'}
		<div class="space-y-1.5">
			<Label class="text-xs">Header name</Label>
			<Input
				value={local.header_name ?? ''}
				placeholder="Authorization"
				class="h-9 font-mono text-xs"
				autocomplete="off"
				oninput={(e) => setField('header_name', e.currentTarget.value || null)}
			/>
		</div>
		{@render secretInput('header_value', 'Header value', SECRET_PLACEHOLDER)}
	{:else if local.auth_type === 'cookie'}
		{@render secretInput('cookie_value', 'Cookie value', 'session=abc123; token=...')}
	{:else if local.auth_type === 'api_key'}
		<div class="space-y-1.5">
			<Label class="text-xs">Key name</Label>
			<Input
				value={local.api_key_name ?? ''}
				placeholder="X-API-Key"
				class="h-9 font-mono text-xs"
				autocomplete="off"
				oninput={(e) => setField('api_key_name', e.currentTarget.value || null)}
			/>
		</div>
		{@render secretInput('api_key_value', 'Key value', SECRET_PLACEHOLDER)}
	{/if}

	{#if previewLine}
		<div class="rounded-md border border-dashed border-border bg-muted/40 px-3 py-2">
			<p class="text-[10px] uppercase tracking-wide text-muted-foreground">Injected header</p>
			<code class="text-xs text-foreground">{previewLine}</code>
		</div>
	{/if}

	<Separator />

	<div class="space-y-2">
		<div>
			<Label class="text-xs">Extra headers</Label>
			<p class="mt-0.5 text-xs text-muted-foreground">
				Merged into every request. On conflict, these win over the auth header above.
			</p>
		</div>
		{#each headerRows as row, i (i)}
			<div class="flex items-center gap-2">
				<Input
					value={row.name}
					placeholder="Header-Name"
					class="h-9 flex-1 font-mono text-xs"
					oninput={(e) => updateHeader(i, 'name', e.currentTarget.value)}
				/>
				<Input
					value={row.value}
					placeholder="value"
					class="h-9 flex-1 font-mono text-xs"
					oninput={(e) => updateHeader(i, 'value', e.currentTarget.value)}
				/>
				<Button
					variant="ghost"
					size="icon"
					class="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive"
					disabled={row.name === '' && row.value === '' && headerRows.length === 1}
					onclick={() => removeHeader(i)}
					aria-label="Remove header"
				>
					<X class="h-4 w-4" />
				</Button>
			</div>
		{/each}
		<p class="text-xs text-muted-foreground">Type in the empty row to add a header.</p>
	</div>
</div>

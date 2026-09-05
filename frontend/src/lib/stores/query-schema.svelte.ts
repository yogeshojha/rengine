import { SvelteMap } from 'svelte/reactivity';
import { api } from '$lib/api/client';
import { EMPTY_QUERY_SCHEMA, type QueryFieldSpec, type QuerySchema } from '$lib/types/asset-query';

class QuerySchemaStore {
	schema = $state<QuerySchema>(EMPTY_QUERY_SCHEMA);
	loaded = $state(false);
	private pending: Promise<void> | null = null;

	constructor(private readonly endpoint: string) {}

	byName = $derived.by(() => {
		const map = new SvelteMap<string, QueryFieldSpec>();
		for (const field of this.schema.fields) {
			map.set(field.name, field);
			for (const alias of field.aliases) map.set(alias, field);
		}
		return map;
	});

	names = $derived(this.schema.fields.flatMap((f) => [f.name, ...f.aliases]));

	async load(): Promise<void> {
		if (this.loaded) return;
		this.pending ??= api
			.get<QuerySchema>(this.endpoint)
			.then((schema) => {
				this.schema = schema;
				this.loaded = true;
			})
			.catch(() => {
				this.schema = EMPTY_QUERY_SCHEMA;
			})
			.finally(() => {
				this.pending = null;
			});
		return this.pending;
	}

	resolve(name: string): QueryFieldSpec | undefined {
		return this.byName.get(name.toLowerCase());
	}

	reset() {
		this.schema = EMPTY_QUERY_SCHEMA;
		this.loaded = false;
		this.pending = null;
	}
}

export type { QuerySchemaStore };

export const querySchema = new QuerySchemaStore('/subdomains/search/schema');
export const ipQuerySchema = new QuerySchemaStore('/ips/search/schema');
export const serviceQuerySchema = new QuerySchemaStore('/ports/search/schema');
export const vulnQuerySchema = new QuerySchemaStore('/vulnerabilities/search/schema');
export const endpointQuerySchema = new QuerySchemaStore('/endpoints/search/schema');

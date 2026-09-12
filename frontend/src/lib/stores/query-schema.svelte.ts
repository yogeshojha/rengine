import { SvelteMap } from 'svelte/reactivity';
import { api } from '$lib/api/client';
import { SurfaceDimension } from '$lib/config/surface';
import { EMPTY_QUERY_SCHEMA, type QueryFieldSpec, type QuerySchema } from '$lib/types/asset-query';

const SCHEMAS_ENDPOINT = '/surface/schemas';
let allPending: Promise<Record<string, QuerySchema>> | null = null;

function loadAll(): Promise<Record<string, QuerySchema>> {
	allPending ??= api.get<Record<string, QuerySchema>>(SCHEMAS_ENDPOINT).finally(() => {
		allPending = null;
	});
	return allPending;
}

class QuerySchemaStore {
	schema = $state<QuerySchema>(EMPTY_QUERY_SCHEMA);
	loaded = $state(false);
	private pending: Promise<void> | null = null;

	constructor(private readonly dimension: string) {}

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
		this.pending ??= loadAll()
			.then((schemas) => {
				this.schema = schemas[this.dimension] ?? EMPTY_QUERY_SCHEMA;
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

export const querySchema = new QuerySchemaStore(SurfaceDimension.WEB_ASSETS);
export const ipQuerySchema = new QuerySchemaStore(SurfaceDimension.IPS);
export const serviceQuerySchema = new QuerySchemaStore(SurfaceDimension.SERVICES);
export const vulnQuerySchema = new QuerySchemaStore(SurfaceDimension.VULNERABILITIES);
export const endpointQuerySchema = new QuerySchemaStore(SurfaceDimension.ENDPOINTS);

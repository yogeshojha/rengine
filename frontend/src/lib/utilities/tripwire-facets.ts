import { subdomainsApi } from '$lib/api/subdomains';
import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
import { endpointsApi, ipsApi, secretsApi, servicesApi, softwareApi } from '$lib/api/scan-results';
import { ScopeKind } from '$lib/config/tripwires';
import { SurfaceDimension } from '$lib/config/surface';
import type { TripwireScope } from '$lib/types/tripwire';
import type { Facet } from '$lib/utilities/scan-insights';
import type { TargetScope } from '$lib/utilities/surface-scope';
import { facetsAsRecord } from '$lib/utilities/vulns';

type Keyed = { key: string; label: string; count: number };

function keyed(rows: Keyed[]): Facet[] {
	return rows.map((f) => ({ value: f.key, label: f.label, count: f.count }));
}

export function targetScopeOf(scope: TripwireScope): TargetScope {
	if (scope.kind === ScopeKind.Targets) return { targetIds: scope.ids };
	if (scope.kind === ScopeKind.Organization) return { organizationId: scope.ids[0] };
	if (scope.kind === ScopeKind.Tag) return { tagId: scope.ids[0] };
	return {};
}

/** The values the scope's covering runs hold, for the query bar's value suggestions. */
export async function loadTripwireFacets(
	dimension: string,
	projectId: string,
	scope: TripwireScope
): Promise<Record<string, Facet[]>> {
	const target = targetScopeOf(scope);
	try {
		switch (dimension) {
			case SurfaceDimension.WEB_ASSETS:
				return (await subdomainsApi.facets(projectId, '', target)) as unknown as Record<
					string,
					Facet[]
				>;
			case SurfaceDimension.IPS:
				return (await ipsApi.facets(projectId, '', target)) as unknown as Record<string, Facet[]>;
			case SurfaceDimension.SERVICES:
				return (await servicesApi.facets(projectId, '')) as unknown as Record<string, Facet[]>;
			case SurfaceDimension.ENDPOINTS:
				return (await endpointsApi.facets(projectId, '')) as unknown as Record<string, Facet[]>;
			case SurfaceDimension.VULNERABILITIES:
				return facetsAsRecord(await vulnerabilitiesApi.facets(projectId, ''));
			case SurfaceDimension.SOFTWARE: {
				const f = await softwareApi.facets(projectId, '', target);
				return {
					severity: keyed(f.severity),
					confidence: keyed(f.confidence),
					source: keyed(f.source),
					caveat: keyed(f.caveat),
					evidence: keyed(f.evidence),
					product: keyed(f.product)
				};
			}
			case SurfaceDimension.SECRETS: {
				const f = await secretsApi.facets(projectId, '');
				return {
					state: keyed(f.state),
					group: keyed(f.group),
					secret: keyed(f.kind),
					kind: keyed(f.kind),
					vendor: keyed(f.vendor),
					source: keyed(f.source),
					subject: keyed(f.subject)
				};
			}
			default:
				return {};
		}
	} catch {
		return {};
	}
}

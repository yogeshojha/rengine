export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	size: number;
	pages: number;
}

export interface TargetCounts {
	all: number;
	domain: number;
	ip: number;
	ip_range: number;
	asn: number;
	url: number;
}

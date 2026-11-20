import type { Audience, HostStanding, PasswordStrength } from '$lib/config/infostealer';

export interface NamedCount {
	name: string;
	count: number | null;
}

export interface InfostealerSummary {
	domain: string;
	checked_at: string;
	total: number;
	employees: number;
	users: number;
	third_parties: number;
	host_count: number;
}

export interface InfostealerPath {
	audience: Audience;
	scheme: string | null;
	port: number | null;
	path: string | null;
	credentials: number;
}

export interface InfostealerHost {
	host: string;
	employee_credentials: number;
	user_credentials: number;
	standing: HostStanding;
	first_seen: string | null;
	paths: InfostealerPath[];
}

export interface InfostealerChangeHost {
	audience: Audience;
	host: string;
	credentials_from: number;
	credentials_to: number;
	new: boolean;
}

export interface InfostealerChange {
	id: string;
	checked_at: string;
	previous_checked_at: string | null;
	employees_from: number;
	employees_to: number;
	users_from: number;
	users_to: number;
	hosts: InfostealerChangeHost[];
}

export interface InfostealerWatcher {
	id: string;
	name: string;
}

export interface InfostealerReport extends InfostealerSummary {
	total_urls: number;
	last_employee_at: string | null;
	last_user_at: string | null;
	scan_id: string | null;
	in_scan: number;
	query: string;
	hosts: InfostealerHost[];
	families: NamedCount[];
	passwords: Partial<Record<Audience, Partial<Record<PasswordStrength, number>>>>;
	applications: NamedCount[];
	services: NamedCount[];
	changes: InfostealerChange[];
	watchers: InfostealerWatcher[];
}

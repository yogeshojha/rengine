export enum DnsRecordType {
	A = 'A',
	AAAA = 'AAAA',
	CNAME = 'CNAME',
	NS = 'NS',
	MX = 'MX',
	TXT = 'TXT',
	SOA = 'SOA',
	SRV = 'SRV',
	PTR = 'PTR',
	CAA = 'CAA',
	AXFR = 'AXFR',
	CDN = 'CDN'
}

export const DNS_RECORD_DISPLAY_ORDER: DnsRecordType[] = [
	DnsRecordType.A,
	DnsRecordType.AAAA,
	DnsRecordType.CNAME,
	DnsRecordType.NS,
	DnsRecordType.MX,
	DnsRecordType.TXT,
	DnsRecordType.SOA,
	DnsRecordType.CAA,
	DnsRecordType.SRV,
	DnsRecordType.PTR
];

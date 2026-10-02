import { describe, expect, it } from 'vitest';
import { curlFor } from './endpoints';

describe('curlFor', () => {
	it('names a non-GET method', () => {
		expect(curlFor({ url: 'https://a.example/x', methods: ['GET', 'POST'] })).toBe(
			"curl -sk -X POST 'https://a.example/x'"
		);
	});

	it('drops a method that is not plain letters', () => {
		expect(curlFor({ url: 'https://a.example/x', methods: ['POST;id', '$(id)', 'GET'] })).toBe(
			"curl -sk 'https://a.example/x'"
		);
	});

	it('quotes the URL', () => {
		expect(curlFor({ url: "https://a.example/'$(id)'", methods: [] })).toBe(
			"curl -sk 'https://a.example/'\\''$(id)'\\'''"
		);
	});
});

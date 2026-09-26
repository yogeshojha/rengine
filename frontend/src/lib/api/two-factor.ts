import { api } from './client';
import type { LoginResponse } from './auth';

export const twoFactorApi = {
	status: (): Promise<{ enabled: boolean }> => {
		return api.get<{ enabled: boolean }>('/auth/2fa/status');
	},

	setup: (): Promise<{ secret: string; otpauth_uri: string; qr: string }> => {
		return api.post<{ secret: string; otpauth_uri: string; qr: string }>('/auth/2fa/setup');
	},

	verify: (code: string): Promise<{ enabled: boolean; backup_codes: string[] }> => {
		return api.post<{ enabled: boolean; backup_codes: string[] }>('/auth/2fa/verify', { code });
	},

	disable: (code: string): Promise<{ enabled: boolean }> => {
		return api.post<{ enabled: boolean }>('/auth/2fa/disable', { code });
	},

	loginVerify: (mfa_token: string, code: string): Promise<LoginResponse> => {
		return api.post<LoginResponse>('/auth/2fa/login', { mfa_token, code });
	}
};

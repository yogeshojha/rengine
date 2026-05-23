import { api } from './client';

export interface User {
	id: string;
	email: string;
	username: string;
	is_active: boolean;
	is_superuser: boolean;
	created_at: string;
	updated_at: string | null;
}

export interface LoginRequest {
	username: string;
	password: string;
}

export interface TokenResponse {
	access_token: string;
	refresh_token: string;
}

export interface ChangePasswordRequest {
	current_password: string;
	new_password: string;
	user_id?: string; // Optional, for admin changing other user's password
}

export interface ChangeUsernameRequest {
	new_username: string;
	user_id?: string; // Optional, for admin changing other user's username
}

export interface ChangePasswordResponse {
	message: string;
	user_id: string;
}

export interface ChangeUsernameResponse {
	message: string;
	user_id: string;
	new_username: string;
}

export interface RegisterRequest {
	email: string;
	username: string;
	password: string;
}

export const authApi = {
	me: (): Promise<User> => {
		return api.get<User>('/auth/me');
	},
	login: (credentials: LoginRequest): Promise<TokenResponse> => {
		return api.post<TokenResponse>('/auth/login', credentials);
	},
	refresh: (): Promise<TokenResponse> => {
		return api.post<TokenResponse>('/auth/refresh');
	},
	logout: (): Promise<{ message: string }> => {
		return api.post<{ message: string }>('/auth/logout');
	},
	register: (data: RegisterRequest): Promise<User> => {
		return api.post<User>('/auth/register', data);
	},
	changePassword: (data: ChangePasswordRequest): Promise<ChangePasswordResponse> => {
		return api.post<ChangePasswordResponse>('/auth/change-password', data);
	},
	changeUsername: (data: ChangeUsernameRequest): Promise<ChangeUsernameResponse> => {
		return api.post<ChangeUsernameResponse>('/auth/change-username', data);
	},
};

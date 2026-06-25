import "axios";

declare module "axios" {
	interface AxiosRequestConfig {
		skipAuth?: boolean;
	}

	interface InternalAxiosRequestConfig {
		skipAuth?: boolean;
	}
}

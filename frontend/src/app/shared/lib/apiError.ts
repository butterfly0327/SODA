import axios from "axios";

type ApiErrorBody = {
  message?: string;
};

export function getApiErrorInfo(error: unknown) {
  if (!axios.isAxiosError<ApiErrorBody>(error)) {
    return {
      status: undefined as number | undefined,
      message: undefined as string | undefined,
    };
  }

  return {
    status: error.response?.status,
    message: error.response?.data?.message,
  };
}

export function getApiErrorMessage(error: unknown, fallback: string) {
  const { message } = getApiErrorInfo(error);
  return message || fallback;
}

export function isApiErrorStatus(error: unknown, status: number) {
  const info = getApiErrorInfo(error);
  return info.status === status;
}

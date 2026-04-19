import type {
  ActionCatalogResponse,
  ActionInvocationResponse,
  BootstrapResponse,
  ConfigUpdateRequest,
  ConfigUpdateResponse,
  PersistResponse,
  SessionResponse,
  SnapshotResponse
} from "./types";

class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new ApiError(response.status, detail);
  }

  return readJson<T>(response);
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = error.detail as { detail?: string | { detail?: string } } | string;
    if (typeof detail === "string") {
      return detail;
    }
    if (detail && typeof detail === "object" && "detail" in detail) {
      const nested = detail.detail;
      if (typeof nested === "string") {
        return nested;
      }
      if (nested && typeof nested === "object" && "detail" in nested && typeof nested.detail === "string") {
        return nested.detail;
      }
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown request error";
}

export function getConflictDetail(error: unknown): Record<string, unknown> | null {
  if (!(error instanceof ApiError)) {
    return null;
  }
  if (error.status !== 409 || !error.detail || typeof error.detail !== "object") {
    return null;
  }
  const payload = error.detail as { detail?: Record<string, unknown> };
  if (payload.detail && typeof payload.detail === "object") {
    return payload.detail;
  }
  return error.detail as Record<string, unknown>;
}

export const api = {
  bootstrap(): Promise<BootstrapResponse> {
    return request<BootstrapResponse>("/ui/bootstrap");
  },

  createSession(payload: { client_name?: string; user_agent?: string }): Promise<SessionResponse> {
    return request<SessionResponse>("/ui/sessions", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  heartbeatSession(sessionId: string): Promise<SessionResponse> {
    return request<SessionResponse>(`/ui/sessions/${sessionId}/heartbeat`, {
      method: "POST"
    });
  },

  closeSession(sessionId: string): Promise<void> {
    return request<void>(`/ui/sessions/${sessionId}`, {
      method: "DELETE"
    });
  },

  snapshot(sinceRevision?: string): Promise<SnapshotResponse> {
    const suffix = sinceRevision ? `?since_revision=${encodeURIComponent(sinceRevision)}` : "";
    return request<SnapshotResponse>(`/ui/snapshot${suffix}`);
  },

  updateConfig(payload: ConfigUpdateRequest): Promise<ConfigUpdateResponse> {
    return request<ConfigUpdateResponse>("/config", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  persistConfig(payload: { revision: string; session_id?: string | null }): Promise<PersistResponse> {
    return request<PersistResponse>("/config/persist", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  actionCatalog(): Promise<ActionCatalogResponse> {
    return request<ActionCatalogResponse>("/actions/catalog");
  },

  invokeAction(action: string, value?: string): Promise<ActionInvocationResponse> {
    const params = new URLSearchParams({ action, source: "ui" });
    if (value && value.length > 0) {
      params.set("value", value);
    }
    return request<ActionInvocationResponse>(`/actions/semantic?${params.toString()}`, {
      method: "POST"
    });
  }
};

export { ApiError };

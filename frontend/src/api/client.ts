import type {
  ConversationDetail,
  ConversationSummary,
  FaqItem,
  MemoryClearResponse,
  MemoryListResponse,
  MemoryRecord,
  MemoryType,
  OrchestratorResponse,
  PersonalizationProfile,
  QuizEvaluationResponse,
  QuizQuestionItem,
  QuizSubmission,
  SendTurnResponse,
  SystemCapability,
  UpdateProfileRequest,
} from "./types";

const BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status?: number;
  data?: any;

  constructor(message: string, status?: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errDetail = `HTTP ${res.status} ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson?.detail) {
          errDetail = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to status text
      }
      throw new ApiError(errDetail, res.status);
    }
    return (await res.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      err?.message || "Failed to communicate with the Finova AI backend. Ensure the server is running at " + BASE_URL,
      0
    );
  }
}

export const apiClient = {
  async checkHealth(): Promise<{ status: string; env: string; ollama_model: string }> {
    return request<{ status: string; env: string; ollama_model: string }>("/health");
  },

  async askOrchestrator(
    query: string,
    userId?: string,
    history?: Array<{ role: string; content: string }>
  ): Promise<OrchestratorResponse> {
    return request<OrchestratorResponse>("/orchestrator/ask", {
      method: "POST",
      body: JSON.stringify({
        query,
        user_id: userId || null,
        conversation_history: history || [],
      }),
    });
  },

  async getMemories(userId: string, memoryType?: MemoryType): Promise<MemoryListResponse> {
    const params = new URLSearchParams({ user_id: userId });
    if (memoryType) params.append("memory_type", memoryType);
    return request<MemoryListResponse>(`/memory?${params.toString()}`);
  },

  async getPersonalizationProfile(userId: string): Promise<PersonalizationProfile> {
    const params = new URLSearchParams({ user_id: userId });
    return request<PersonalizationProfile>(`/memory/profile?${params.toString()}`);
  },

  async updatePersonalizationProfile(payload: UpdateProfileRequest): Promise<PersonalizationProfile> {
    return request<PersonalizationProfile>("/memory/profile", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async createMemory(
    userId: string,
    memoryType: MemoryType,
    key: string,
    value: string
  ): Promise<MemoryRecord> {
    return request<MemoryRecord>("/memory", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        memory_type: memoryType,
        key,
        value,
      }),
    });
  },

  async deleteMemory(userId: string, memoryId: string): Promise<{ status: string; memory_id: string }> {
    const params = new URLSearchParams({ user_id: userId });
    return request<{ status: string; memory_id: string }>(`/memory/${memoryId}?${params.toString()}`, {
      method: "DELETE",
    });
  },

  async clearMemories(userId: string): Promise<MemoryClearResponse> {
    const params = new URLSearchParams({ user_id: userId });
    return request<MemoryClearResponse>(`/memory?${params.toString()}`, {
      method: "DELETE",
    });
  },

  async submitQuiz(submissions: QuizSubmission[], userId?: string): Promise<QuizEvaluationResponse> {
    return request<QuizEvaluationResponse>("/agents/quiz/submit", {
      method: "POST",
      body: JSON.stringify({
        submissions,
        user_id: userId || null,
      }),
    });
  },

  async getQuizQuestions(topic?: string, limit: number = 5): Promise<QuizQuestionItem[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (topic) params.append("topic", topic);
    return request<QuizQuestionItem[]>(`/agents/quiz/questions?${params.toString()}`);
  },

  async getCapabilities(): Promise<SystemCapability[]> {
    return request<SystemCapability[]>("/agents/onboarding/capabilities");
  },

  async getFaqs(category?: string): Promise<FaqItem[]> {
    const params = category ? `?category=${encodeURIComponent(category)}` : "";
    return request<FaqItem[]>(`/agents/onboarding/faqs${params}`);
  },

  async listConversations(userId: string, domain?: string | null): Promise<ConversationSummary[]> {
    const params = new URLSearchParams({ user_id: userId });
    if (domain) {
      params.append("domain", domain);
    }
    return request<ConversationSummary[]>(`/conversations?${params.toString()}`);
  },

  async getConversation(conversationId: string, userId: string): Promise<ConversationDetail> {
    const params = new URLSearchParams({ user_id: userId });
    return request<ConversationDetail>(`/conversations/${conversationId}?${params.toString()}`);
  },

  async sendTurn(
    userId: string,
    query: string,
    conversationId?: string | null,
    domain?: string | null
  ): Promise<SendTurnResponse> {
    return request<SendTurnResponse>("/conversations/send", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        query,
        conversation_id: conversationId || null,
        domain: domain || null,
      }),
    });
  },

  async renameConversation(
    conversationId: string,
    userId: string,
    title: string
  ): Promise<any> {
    return request(`/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify({
        user_id: userId,
        title,
      }),
    });
  },

  async deleteConversation(
    conversationId: string,
    userId: string
  ): Promise<{ status: string; conversation_id: string }> {
    const params = new URLSearchParams({ user_id: userId });
    return request<{ status: string; conversation_id: string }>(
      `/conversations/${conversationId}?${params.toString()}`,
      { method: "DELETE" }
    );
  },

  async clearAllConversations(
    userId: string
  ): Promise<{ status: string; user_id: string; deleted_count: number }> {
    const params = new URLSearchParams({ user_id: userId });
    return request<{ status: string; user_id: string; deleted_count: number }>(
      `/conversations?${params.toString()}`,
      { method: "DELETE" }
    );
  },
};

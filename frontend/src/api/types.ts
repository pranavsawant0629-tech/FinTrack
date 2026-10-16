export type Domain =
  | "EQUITY"
  | "CRYPTO"
  | "PERSONAL_FINANCE"
  | "DERIVATIVES"
  | "PORTFOLIO"
  | "NEWS"
  | "QUIZ"
  | "ONBOARDING"
  | "GENERAL";

export type GroundingStatus = "fully_grounded" | "partially_grounded" | "ungrounded";

export interface Citation {
  citation_id: number;
  chunk_id: string;
  doc_id: string;
  title: string;
  source: string;
  authority_level: string;
  url: string;
  page_numbers: number[];
  similarity_score: number;
}

export interface MarketDataProvenance {
  symbol: string;
  company_name: string;
  exchange: string;
  currency: string;
  price: number;
  change: number;
  change_percent: number;
  previous_close?: number;
  open?: number;
  high?: number;
  low?: number;
  volume?: number;
  market_status: "pre_open" | "regular_trading" | "post_closing" | "closed";
  market_timestamp: string;
  retrieved_at: string;
  provider: string;
  source_url: string;
  freshness_status: "realtime" | "delayed" | "stale";
}

export interface SubTaskExecutionMetadata {
  task_id: string;
  domain: string;
  intent: string;
  target?: string | null;
  status: "success" | "fallback" | "filtered" | "error" | "failed";
  latency_ms: number;
}

export interface OrchestratorResponse {
  query: string;
  answer: string;
  grounding_status: GroundingStatus;
  citations: Citation[];
  market_data?: MarketDataProvenance | null;
  market_data_list: MarketDataProvenance[];
  crypto_data?: Record<string, any> | null;
  derivatives_data?: Record<string, any> | null;
  portfolio_data?: Record<string, any> | null;
  news_data?: Array<Record<string, any>> | null;
  quiz_data?: Record<string, any> | null;
  onboarding_data?: Array<Record<string, any>> | null;
  grounding_sources: string[];
  domain_detected: Domain;
  sub_tasks: SubTaskExecutionMetadata[];
  agent_name: string;
  disclaimer: string;
  model_used: string;
  latency_ms: number;
  topic?: string | null;
  related_concepts?: string[] | null;
  suggested_next?: string[] | null;
}

export type MemoryType =
  | "user_preference"
  | "portfolio_holding"
  | "watchlist"
  | "learning_progress"
  | "risk_profile"
  | "calculation_history";

export interface MemoryRecord {
  memory_id: string;
  user_id: string;
  memory_type: MemoryType;
  key: string;
  value: string;
  confidence: number;
  source: string;
  created_at: string;
  updated_at: string;
  ttl_seconds?: number | null;
}

export interface MemoryListResponse {
  user_id: string;
  memories: MemoryRecord[];
  count: number;
}

export interface MemoryClearResponse {
  status: string;
  user_id: string;
  deleted_count: number;
}

export interface PersonalizationProfile {
  user_id: string | null;
  learning_level: "beginner" | "intermediate" | "advanced" | null;
  learning_goals: string[];
  interests: string[];
  preferences: Record<string, string>;
  active_memories: MemoryRecord[];
}

export interface UpdateProfileRequest {
  user_id: string;
  learning_level?: "beginner" | "intermediate" | "advanced" | null;
  learning_goals?: string[];
  interests?: string[];
  preferences?: Record<string, string>;
}

export interface QuizSubmission {
  question_id: string;
  selected_option: string;
}

export interface QuizQuestionItem {
  question_id: string;
  topic: string;
  difficulty: string;
  question_text: string;
  options: Record<string, string>;
}

export interface QuizResultItem {
  question_id: string;
  selected_option: string;
  correct_option: string;
  is_correct: boolean;
  explanation: string;
}

export interface QuizEvaluationResponse {
  score: number;
  total: number;
  percentage: number;
  results: QuizResultItem[];
}

export interface SystemCapability {
  name: string;
  domain: string;
  description: string;
  example_queries: string[];
}

export interface FaqItem {
  category: string;
  question: string;
  answer: string;
}

export interface ConversationSummary {
  conversation_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  domain?: string | null;
  message_count: number;
}

export interface ConversationMessage {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  status: "complete" | "failed";
  metadata?: Record<string, any> | null;
}

export interface ConversationDetail {
  conversation: {
    conversation_id: string;
    user_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    domain?: string | null;
  };
  messages: ConversationMessage[];
}

export interface SendTurnResponse {
  conversation_id: string;
  user_message: ConversationMessage;
  assistant_message: ConversationMessage;
  orchestrator_response?: OrchestratorResponse | null;
}

export type TutorSectionId =
  | "general"
  | "equity"
  | "derivatives"
  | "personal_finance"
  | "crypto"
  | "portfolio"
  | "news"
  | "quiz"
  | "onboarding";

export interface SendTurnRequest {
  user_id: string;
  query: string;
  conversation_id?: string | null;
  domain?: string | null;
  top_k?: number | null;
  score_threshold?: number | null;
}


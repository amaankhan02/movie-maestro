export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  error?: boolean;
}

export interface Conversation {
  id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

// ChatResponse defines the structure of the response from the backend
// that we expect to receive from /chat endpoint
export interface ChatResponse {
  response: string; // the response from the backend
  conversation_id: string; // the conversation ID
  timestamp: string; // the timestamp of the response
} 
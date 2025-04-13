export interface Citation {
  text: string;
  url: string;
  title?: string;
}

export interface ImageData {
  url: string;
  alt: string;
  caption?: string;
}

export interface RelatedQuery {
  text: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  error?: boolean;
  citations?: Citation[];
  images?: ImageData[];
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
  citations?: Citation[]; // optional citations
  images?: ImageData[]; // optional images
  related_queries?: RelatedQuery[]; // optional related query suggestions
}
import { Message, ChatResponse } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Sends a message to the backend and returns a ChatResponse.
 * Makes a POST request to the /chat endpoint.
 *  
 * @param message - The message to send to the backend
 * @param conversationId - The conversation ID to send to the backend
 * @returns A promise that resolves to a ChatResponse object
 * @throws Error if the request fails or if there's an error sending the message
 */
export const sendMessage = async (
  message: string,
  conversationId?: string
): Promise<ChatResponse> => {
  try {
    // send a POST request to the /chat endpoint
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    // if the request fails, throw an error
    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    // return the response from the backend
    return await response.json();
  } catch (error) {
    // if there's an error, throw an error
    console.error('Error sending message:', error);
    throw error;
  }
};

/**
 * Retrieves the history of messages for a specific conversation.
 * 
 * @param conversationId - The unique identifier of the conversation to fetch
 * @returns A promise that resolves to an array of Message objects representing the conversation history
 * @throws Error if the request fails or if there's an error fetching the conversation history
 */
export const getConversationHistory = async (
  conversationId: string
): Promise<Message[]> => {
  try {
    // send a GET request to the /conversation/{conversationId} endpoint
    const response = await fetch(
      `${API_BASE_URL}/conversation/${conversationId}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch conversation history');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching conversation history:', error);
    throw error;
  }
}; 
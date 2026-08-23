export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const API_BASE = "/api/v1";

export const chatApi = {
  createSession: async (): Promise<string> => {
    // 1. Added trailing slash here!
    const res = await fetch(`${API_BASE}/sessions`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to initialize chat.');
    const data = await res.json();
    
    // 2. Print exactly what the backend gives us
    console.log("Session API Response:", data); 
    
    // If your backend returns "id" instead of "session_id", change this line!
    return data.session_id || data.id; 
  },

  sendMessage: async (sessionId: string, message: string) => {
    // Trailing slash is already here, but double-check it!
    const res = await fetch(`${API_BASE}/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message })
    });
    if (!res.ok) throw new Error('Network error. Please try again.');
    return await res.json();
  }
};
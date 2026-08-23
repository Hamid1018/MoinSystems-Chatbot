import React, { useState, useEffect, useRef } from 'react';
import { chatApi, type ChatMessage } from './chatapi';
import './chat.css';

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true); // Defaulting to true for testing
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem('moin_chat_session');
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) {
      chatApi.createSession().then(id => {
        setSessionId(id);
        localStorage.setItem('moin_chat_session', id);
      }).catch(() => setError("Failed to connect."));
    }
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    setError(null);
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const data = await chatApi.sendMessage(sessionId, userMsg);
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-widget-container">
      {!isOpen && (
        <button className="chat-launcher" onClick={() => setIsOpen(true)} aria-label="Open Chat">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      )}

      {isOpen && (
        <div className="chat-panel" role="dialog" aria-label="Chat support">
          <div className="chat-header">
          <div className="header-brand">
              {/* Exact 'M' style logo from screenshot */}
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
                 <path d="M4 18L10 6L14 14" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                 <path d="M10 18L16 6L20 14" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h3>MoinSystem AI</h3>
              <span className="online-indicator"></span>
            </div>
            <button className="close-btn" onClick={() => setIsOpen(false)} aria-label="Close Chat">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <div className="chat-messages" aria-live="polite">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message-wrapper ${msg.role}`}>
                <div className="message">{msg.content}</div>
              </div>
            ))}
            {isLoading && (
              <div className="message-wrapper assistant">
                <div className="message typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            {error && <div className="message-wrapper error"><div className="message">{error}</div></div>}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-composer">
            <div className="chat-composer-inner">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder="Ask a question..."
                disabled={isLoading}
                aria-label="Type your message"
              />
              <button onClick={handleSend} disabled={isLoading || !input.trim()} aria-label="Send Message">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
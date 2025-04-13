'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import { FiCopy, FiRefreshCw, FiSun, FiMoon } from 'react-icons/fi';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  error?: boolean;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Apply dark mode class to html element
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      document.body.style.backgroundColor = '#343541';
    } else {
      document.documentElement.classList.remove('dark');
      document.body.style.backgroundColor = '#ffffff';
    }
  }, [isDarkMode]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: "Here's a sample response with **markdown** support:\n\n```javascript\nconst hello = 'world';\n```\n\nAnd some *italic* and **bold** text.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleRetry = async (messageIndex: number) => {
    if (isLoading) return;
    
    setIsLoading(true);
    setIsTyping(true);
    
    try {
      // Remove the error message
      setMessages((prev) => prev.filter((_, index) => index !== messageIndex));
      
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: "This is a retry attempt with a successful response!",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: "Sorry, the retry attempt failed. Please try again later.",
        timestamp: new Date(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className={`flex flex-col h-screen max-w-4xl mx-auto p-4 ${isDarkMode ? 'bg-dark-bg' : 'bg-white'}`}>
      <header className={`py-4 border-b ${isDarkMode ? 'border-dark-border' : 'border-gray-200'} flex justify-between items-center`}>
        <h1 className={`text-2xl font-bold ${isDarkMode ? 'text-dark-text' : 'text-gray-900'}`}>AI Answer Engine</h1>
        <button
          onClick={() => setIsDarkMode(!isDarkMode)}
          className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-dark-bg-secondary' : 'hover:bg-gray-100'}`}
          title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDarkMode ? (
            <FiSun className="w-5 h-5 text-dark-text" />
          ) : (
            <FiMoon className="w-5 h-5 text-gray-900" />
          )}
        </button>
      </header>

      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : isDarkMode
                  ? 'bg-dark-bg-secondary text-dark-text'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className={`text-xs opacity-70 ${isDarkMode ? 'text-dark-text' : 'text-gray-600'}`}>
                  {format(message.timestamp, 'h:mm a')}
                </span>
                {message.role === 'assistant' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => copyToClipboard(message.content)}
                      className={`p-1 rounded ${
                        isDarkMode
                          ? 'hover:bg-dark-bg text-dark-text'
                          : 'hover:bg-gray-200 text-gray-900'
                      }`}
                      title="Copy message"
                    >
                      <FiCopy className="w-4 h-4" />
                    </button>
                    {message.error && (
                      <button
                        onClick={() => handleRetry(index)}
                        className={`p-1 rounded ${
                          isDarkMode
                            ? 'hover:bg-dark-bg text-dark-text'
                            : 'hover:bg-gray-200 text-gray-900'
                        }`}
                        title="Retry"
                      >
                        <FiRefreshCw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                )}
              </div>
              <div className={`prose ${isDarkMode ? 'prose-invert' : ''} max-w-none`}>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div
              className={`rounded-lg p-4 ${
                isDarkMode
                  ? 'bg-dark-bg-secondary text-dark-text'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex space-x-2">
                <div className={`w-2 h-2 rounded-full animate-bounce ${
                  isDarkMode ? 'bg-gray-400' : 'bg-gray-400'
                }`} />
                <div className={`w-2 h-2 rounded-full animate-bounce ${
                  isDarkMode ? 'bg-gray-400' : 'bg-gray-400'
                }`} style={{ animationDelay: '0.2s' }} />
                <div className={`w-2 h-2 rounded-full animate-bounce ${
                  isDarkMode ? 'bg-gray-400' : 'bg-gray-400'
                }`} style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="mt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className={`flex-1 p-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isDarkMode
                ? 'bg-dark-bg-secondary border-dark-border text-dark-text placeholder-gray-400'
                : 'bg-white border-gray-300 text-gray-900'
            }`}
            disabled={isLoading}
          />
          <button
            type="submit"
            className={`px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            }`}
            disabled={isLoading}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

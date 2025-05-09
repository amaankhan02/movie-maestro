'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import { FiCopy, FiRefreshCw, FiSun, FiMoon, FiArrowLeft } from 'react-icons/fi';
import { sendMessage } from '../services/api';
import { customScrollIntoView } from '../services/scrollUtils';
import { Message, RelatedQuery } from '../types';
import LandingPage from '../components/LandingPage';
import Citation from '../components/Citation';
import ImageGallery from '../components/ImageGallery';
import RelatedQueries from '../components/RelatedQueries';

export default function Home(): React.ReactElement {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);  // true when a request is in progress. prevents multiple submissions
  const [isTyping, setIsTyping] = useState(false);   // when the assistant is generating a response
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [conversationId, setConversationId] = useState<string>();
  const [showLanding, setShowLanding] = useState(true);
  const [relatedQueries, setRelatedQueries] = useState<RelatedQuery[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const relatedQueriesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      document.body.style.backgroundColor = '#343541';
    } else {
      document.documentElement.classList.remove('dark');
      document.body.style.backgroundColor = '#ffffff';
    }
  }, [isDarkMode]);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      customScrollIntoView(messagesEndRef.current, {
        behavior: 'smooth',
        block: 'end'
      }, 100);
    }
  };

  const scrollToRelatedQueries = () => {
    // Use a small timeout to ensure the element is fully rendered before scrolling
    setTimeout(() => {
      const element = document.getElementById('related-queries');
      if (element) {
        // Use a more reliable approach with simpler parameters
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Apply custom scroll speed through CSS
        document.documentElement.style.setProperty('--scroll-speed', '2000ms');
        
        // Reset the CSS property after scrolling completes
        setTimeout(() => {
          document.documentElement.style.removeProperty('--scroll-speed');
        }, 2500);
      } else {
        console.log('Related queries element not found');
      }
    }, 100);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input field when chat view is shown
  useEffect(() => {
    // Only when in the chat interface page (i.e, !showLanding)
    // focus on the input textbox
    if (!showLanding && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showLanding]);

  const handleSubmit = async (e?: React.FormEvent, initialQuery?: string) => {
    // optional initial query for direct function calls instead of a form submission
    if (e) e.preventDefault();
    
    // use initialQuery if provided, otherwise use the user input that they typed in
    const message = initialQuery || input;  
    if (!message.trim() || isLoading) return;

    // Clear related queries when a new question is asked
    setRelatedQueries([]);

    // If we're on the landing page, transition to chat view
    if (showLanding) {
      setShowLanding(false);
    }

    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      // send the message to the backend and get back the response
      const response = await sendMessage(message, conversationId);
      
      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        citations: response.citations,
        images: response.images,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      // Set related queries if we get it
      if (response.related_queries && response.related_queries.length > 0) {
        setRelatedQueries(response.related_queries);
      }
    } catch {
      const errorMessage: Message = {
        role: 'assistant',
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date().toISOString(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleRelatedQueryClick = (query: string) => {
    const cleanQuery = query.slice(1, -1);   // Remove the quotation marks
    handleSubmit(undefined, cleanQuery);
  };

  const handleLandingSearch = (query: string) => {
    handleSubmit(undefined, query);
  };

  const handleRetry = async (messageIndex: number) => {
    if (isLoading) return;
    
    // Clear related queries when retry is attempted
    setRelatedQueries([]);
    
    setIsLoading(true);
    setIsTyping(true);
    
    try {
      // Remove the error message
      setMessages((prev) => prev.filter((_, index) => index !== messageIndex));
      
      // Get the last user message
      const lastUserMessage = [...messages]
        .reverse()
        .find(message => message.role === 'user');
      
      if (lastUserMessage) {
        const response = await sendMessage(lastUserMessage.content, conversationId);
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.response,
          timestamp: response.timestamp,
          citations: response.citations,
          images: response.images,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        
        // Set related queries after response is displayed
        if (response.related_queries && response.related_queries.length > 0) {
          setRelatedQueries(response.related_queries);
        }
      }
    } catch {
      const errorMessage: Message = {
        role: 'assistant',
        content: "Sorry, the retry attempt failed. Please try again later.",
        timestamp: new Date().toISOString(),
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

  const resetConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    setRelatedQueries([]);
    setShowLanding(true);
  };

  // Landing Page
  if (showLanding) {
    return (
      <div className={`min-h-screen flex flex-col ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
        <header className="absolute top-0 right-0 p-4">
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-gray-800' : 'hover:bg-gray-100'}`}
            title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDarkMode ? (
              <FiSun className={`w-5 h-5 ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`} />
            ) : (
              <FiMoon className={`w-5 h-5 ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`} />
            )}
          </button>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <LandingPage onSearch={handleLandingSearch} isDarkMode={isDarkMode} />
        </div>
      </div>
    );
  }

  // Chat Interface Page
  return (
    <div className={`flex flex-col h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Top Navigation Header which has the back button and the title */}
      <header className={`py-4 px-4 border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-200'} flex justify-between items-center sticky top-0 z-10 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="flex items-center">
          {/* Back Button */}
          <button
            onClick={resetConversation}
            className={`p-3 mr-3 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-dark-bg-secondary text-dark-text' : 'hover:bg-gray-100 text-gray-700'}`}
            title="New conversation"
          >
            <FiArrowLeft className="w-6 h-6" />
          </button>

          {/* Title - "Movie Maestro" on the top */}
          <h1 className={`text-xl font-bold ${isDarkMode ? 'text-dark-text' : 'text-gray-900'}`}>
            Movie Maestro
          </h1>
        </div>

        {/* Dark Mode Toggle Button */}
        <button
          onClick={() => setIsDarkMode(!isDarkMode)}
          className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-dark-bg-secondary' : 'hover:bg-gray-100'}`}
          title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDarkMode ? (
            <FiSun className={`w-5 h-5 ${isDarkMode ? 'text-dark-text' : 'text-gray-900'}`} />
          ) : (
            <FiMoon className={`w-5 h-5 ${isDarkMode ? 'text-dark-text' : 'text-gray-900'}`} />
          )}
        </button>
      </header>
        
      {/* Main screen consisting of the chat messages */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.map((message, index) => (
          // Outer div: handles horizontal positining of the entire message bubble
          <div
            key={index}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            } ${index > 0 ? 'mt-6' : ''}`}
          >
            {/* Contains all the styling for the message bubble itself */}
            <div
              className={`${
                message.role === 'user'
                  ? isDarkMode
                    ? 'ml-12 md:ml-24 bg-gray-700 text-gray-100 rounded-2xl rounded-tr-none'
                    : 'ml-12 md:ml-24 bg-blue-100 text-gray-800 rounded-2xl rounded-tr-none'
                  : isDarkMode
                    ? 'mr-12 md:mr-24 bg-gray-800 border-gray-700 text-gray-200 shadow-sm rounded-2xl rounded-tl-none'
                    : 'mr-12 md:mr-24 bg-gray-100 border border-gray-200 text-gray-800 shadow-sm rounded-2xl rounded-tl-none'
              } overflow-hidden ${
                message.images && message.images.length > 0 ? 'max-w-full' : 'max-w-[65%]'
              }`}
            >
              <div className={`p-4 ${
                message.images && message.images.length > 0 ? 'md:max-w-[60%]' : 'max-w-full'
              }`}>
                <div className="flex items-center justify-between gap-2 mb-2">
                  {/* Date Text */}
                  <span className={`text-xs font-medium ${
                    message.role === 'user' 
                      ? isDarkMode ? 'text-gray-300' : 'text-gray-600'
                      : isDarkMode ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    {format(new Date(message.timestamp), 'h:mm a')}
                  </span>
                  
                  {/* Specific fields to the assistant message */}
                  {message.role === 'assistant' && (
                    <div className="flex gap-2">
                      {/* Copy Message Btn */}
                      <button
                        onClick={() => copyToClipboard(message.content)}
                        className={`p-1.5 rounded hover:bg-opacity-10 ${
                          isDarkMode
                            ? 'hover:bg-white text-gray-300'
                            : 'hover:bg-black text-gray-500'
                        }`}
                        title="Copy message"
                      >
                        <FiCopy className="w-4 h-4" />
                      </button>

                      {message.error && (
                        <button
                          onClick={() => handleRetry(index)}
                          className={`p-1.5 rounded hover:bg-opacity-10 ${
                            isDarkMode
                              ? 'hover:bg-white text-gray-300'
                              : 'hover:bg-black text-gray-500'
                          }`}
                          title="Retry"
                        >
                          <FiRefreshCw className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
                {/* Actual Message Body itself - using <ReactMarkdown> Component */}
                <div className={`prose text-lg font-medium ${
                  isDarkMode 
                    ? message.role === 'user' ? 'text-gray-100' : 'text-gray-200'
                    : 'text-gray-800'
                }`}>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
                
                {/* Citations */}
                {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                  <div className="mt-4 border-t pt-2 space-y-1">
                    <h4 className={`text-lg font-semibold mb-2 ${
                      isDarkMode ? 'text-gray-300 border-gray-700' : 'text-gray-700 border-gray-200'
                    }`}>
                      Sources
                    </h4>
                    {message.citations.map((citation, citIndex) => (
                      <Citation 
                        key={citIndex} 
                        citation={citation} 
                        index={citIndex} 
                        isDarkMode={isDarkMode} 
                      />
                    ))}
                  </div>
                )}
                
                {/* Related Queries Anchor Link */}
                {message.role === 'assistant' && relatedQueries.length > 0 && (
                  <div className="mt-3">
                    <button 
                      onClick={(e) => {
                        e.preventDefault();
                        scrollToRelatedQueries();
                      }}
                      className={`text-sm font-medium px-3 py-1.5 rounded-full ${
                        isDarkMode 
                          ? 'bg-gray-700 text-blue-300 hover:bg-gray-600' 
                          : 'bg-gray-50 text-blue-600 hover:bg-gray-100'
                      } transition-colors`}
                    >
                      View related queries
                    </button>
                  </div>
                )}
              </div>
              
              {/* Images */}
              {message.role === 'assistant' && message.images && message.images.length > 0 && (
                <div className="md:max-w-[40%] border-t md:border-t-0 md:border-l">
                  <ImageGallery images={message.images} isDarkMode={isDarkMode} />
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Three dots typing display when the assistant is generating an answer */}
        {isTyping && (
          <div className="flex justify-start">
            <div
              className={`rounded-2xl rounded-tl-none p-4 ${
                isDarkMode 
                  ? 'bg-gray-800 border-gray-700' 
                  : 'bg-white border-gray-200'
              } border shadow-sm`}
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
        
        {/* Related Queries - shown only when the assistant is not generating a response */}
        {!isTyping && relatedQueries.length > 0 && (
          <div ref={relatedQueriesRef} className="flex justify-end">
            <RelatedQueries 
              queries={relatedQueries} 
              isDarkMode={isDarkMode} 
              onQueryClick={handleRelatedQueryClick} 
            />
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Bottom footer -- contains the input text box and the submit button */}
      <div className={`p-4 border-t ${isDarkMode ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'} sticky bottom-0 z-10`}>
        {/* Form consists of the submit button and the input field textbox */}
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative">
            {/* Input Box to put the new query */}
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about movies..."
              className={`w-full p-3 pr-24 rounded-full border-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                isDarkMode
                  ? 'bg-dark-bg-secondary border-dark-border text-dark-text placeholder-gray-400'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
              disabled={isLoading}
            />
            {/* Submit button */}
            <button
              type="submit"
              className={`absolute right-2 top-1/2 transform -translate-y-1/2 px-4 py-1.5 rounded-full text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                isLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600'
              }`}
              disabled={isLoading}
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
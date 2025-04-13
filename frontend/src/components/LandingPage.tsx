// src/components/LandingPage.tsx
import { useState } from 'react';
import { FiSearch } from 'react-icons/fi';

interface LandingPageProps {
  onSearch: (query: string) => void;
  isDarkMode: boolean;
}

export default function LandingPage({ onSearch, isDarkMode }: LandingPageProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="max-w-3xl px-4">
        <h1 className={`text-4xl md:text-5xl font-bold mb-6 ${isDarkMode ? 'text-dark-text' : 'text-gray-900'}`}>
          Movie Answer Engine
        </h1>
        <p className={`text-lg md:text-xl mb-10 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Get intelligent answers about movies, actors, directors, and more. Ask about plots, reviews, or recommendations.
        </p>
        
        <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything about movies..."
              className={`w-full p-4 pr-12 text-lg rounded-full border-2 shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                isDarkMode
                  ? 'bg-dark-bg-secondary border-dark-border text-dark-text placeholder-gray-400'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-blue-500 hover:text-blue-600 focus:outline-none"
            >
              <FiSearch className="w-6 h-6" />
            </button>
          </div>
        </form>
        
        <div className="mt-12">
          <p className={`text-sm mb-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>Try asking:</p>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              "What's a good family movie to watch?",
              "Compare Inception and Interstellar",
              "Show me popular sci-fi movies from the last 5 years",
              "What are Christopher Nolan's best-rated films?"
            ].map((suggestion, index) => (
              <button
                key={index}
                onClick={() => {
                  setQuery(suggestion);
                  onSearch(suggestion);
                }}
                className={`px-4 py-2 rounded-full text-sm transition-colors ${
                  isDarkMode
                    ? 'bg-dark-bg-secondary hover:bg-gray-700 text-gray-300'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                }`}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
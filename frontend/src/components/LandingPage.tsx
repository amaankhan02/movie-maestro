// src/components/LandingPage.tsx
import { useState } from 'react';
import { FiSearch } from 'react-icons/fi';

interface LandingPageProps {
  onSearch: (query: string) => void;
  isDarkMode: boolean;
}

export default function LandingPage({ onSearch, isDarkMode }: LandingPageProps): React.ReactElement {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <div className="w-full">
      <div className="max-w-3xl px-4 mx-auto">
        <h1 className={`text-5xl md:text-6xl font-bold mb-8 leading-tight ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`}>
          Movie Maestro
        </h1>
        <p className={`text-xl md:text-2xl mb-12 leading-relaxed ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Get intelligent answers about movies, actors, directors, and more. Ask about plots, reviews, or recommendations.
        </p>
        
        <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything about movies..."
              className={`w-full p-5 pr-12 text-lg rounded-full border-2 shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                isDarkMode
                  ? 'bg-gray-800 border-gray-700 text-gray-100 placeholder-gray-400'
                  : 'bg-white border-gray-200 text-gray-900'
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
          <p className={`text-base mb-6 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>Try asking:</p>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              "What's a good family movie to watch?",
              "Compare the plot of Inception and Interstellar",
              "Where can I watch Toy Story?",
              "What are Christopher Nolan's best-rated films?",
              "How has Pulp Fiction impacted Cinema over the years?"
            ].map((suggestion, index) => (
              // Create a set of buttons for each suggestion from that list
              <button
                key={index}
                onClick={() => {
                  setQuery(suggestion);
                  onSearch(suggestion);
                }}
                className={`px-5 py-2.5 rounded-full text-base transition-colors ${
                  isDarkMode
                    ? 'bg-gray-800 hover:bg-gray-700 text-gray-300'
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
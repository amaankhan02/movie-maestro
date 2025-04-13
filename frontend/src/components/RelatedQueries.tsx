import { useState, useEffect } from 'react';
import { RelatedQuery } from '../types';

interface RelatedQueriesProps {
  queries: RelatedQuery[];
  isDarkMode: boolean;
  onQueryClick: (query: string) => void;
}

const RelatedQueries: React.FC<RelatedQueriesProps> = ({ 
  queries, 
  isDarkMode, 
  onQueryClick 
}) => {
  const [visible, setVisible] = useState(false);

  // Add animation effect - show queries after a small delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(true);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  if (!queries || queries.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col space-y-2 w-full md:max-w-[80%] mx-auto mt-4">
      <p className={`text-sm font-medium ${
        isDarkMode ? 'text-gray-300' : 'text-gray-600'
      }`}>
        Related queries:
      </p>
      <div className="flex flex-col md:flex-row gap-2 justify-between items-center">
        {queries.map((query, index) => (
          <button
            key={index}
            onClick={() => onQueryClick(query.text)}
            className={`
              px-4 py-2 rounded-lg w-full md:w-auto text-left
              transition-all duration-300 transform 
              ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
              ${isDarkMode 
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200' 
                : 'bg-gray-100 hover:bg-gray-200 text-gray-800'}
              border border-transparent
              hover:border-blue-400
              shadow-md hover:shadow-lg
              hover:scale-105
              delay-${index * 100}
            `}
            style={{ 
              fontStyle: 'italic'
            }}
          >
            {query.text}
          </button>
        ))}
      </div>
    </div>
  );
};

export default RelatedQueries; 
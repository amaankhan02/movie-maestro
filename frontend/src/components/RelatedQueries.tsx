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
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  if (!queries || queries.length === 0) {
    return null;
  }

  return (
    <div id="related-queries" className="flex flex-col space-y-6 w-full md:max-w-[80%] mx-auto mt-4 pt-4 pb-8 scroll-mt-8">
      <h2 className={`text-2xl font-bold text-center ${
        isDarkMode ? 'text-gray-200' : 'text-gray-800'
      }`}>
        Related queries
      </h2>
      <div className="flex flex-col gap-2">
        {queries.map((query, index) => (
          <button
            key={index}
            onClick={() => onQueryClick(query.text)}
            className={`
              px-4 py-3 rounded-lg w-full max-w-[600px] mx-auto text-center
              transition-all duration-2000 transform 
              ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
              ${isDarkMode 
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200' 
                : 'bg-gray-100 hover:bg-gray-200 text-gray-800'}
              border-l-4 border-transparent
              hover:border-l-4 hover:border-blue-400
              shadow-sm hover:shadow-md
              hover:scale-[1.02]
              delay-${index * 800}
              text-3xl
            `}
            style={{ 
              fontStyle: 'italic',
              fontSize: '20px',
              transitionTimingFunction: 'ease-in-out'
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
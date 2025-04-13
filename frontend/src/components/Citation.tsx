// src/components/Citation.tsx
import { useState } from 'react';
import { FiExternalLink, FiChevronUp, FiChevronDown } from 'react-icons/fi';
import { Citation as CitationType } from '../types';

interface CitationProps {
  citation: CitationType;
  index: number;
  isDarkMode: boolean;
}

export default function Citation({ citation, index, isDarkMode }: CitationProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div 
      className={`mt-1 text-sm rounded-md overflow-hidden ${
        isDarkMode ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
      }`}
    >
      <div 
        className="flex items-center cursor-pointer p-2"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className={`flex items-center justify-center w-5 h-5 rounded-full mr-2 text-xs ${
          isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
        }`}>
          {index + 1}
        </span>
        <span className="flex-1 truncate">{citation.title || citation.url}</span>
        {isExpanded ? 
          <FiChevronUp className="flex-shrink-0 ml-2" /> : 
          <FiChevronDown className="flex-shrink-0 ml-2" />
        }
      </div>
      
      {isExpanded && (
        <div className={`p-2 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <p className="mb-2">{citation.text}</p>
          <a 
            href={citation.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center text-blue-500 hover:underline"
          >
            Visit source <FiExternalLink className="ml-1" />
          </a>
        </div>
      )}
    </div>
  );
}
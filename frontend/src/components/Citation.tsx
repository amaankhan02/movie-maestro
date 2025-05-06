// src/components/Citation.tsx
import { useState, useRef, useEffect } from 'react';
import { FiExternalLink, FiChevronUp, FiChevronDown } from 'react-icons/fi';
import { Citation as CitationType } from '../types';

interface CitationProps {
  citation: CitationType;
  index: number;
  isDarkMode: boolean;
}

export default function Citation({ citation, index, isDarkMode }: CitationProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(false);
  const [needsTruncation, setNeedsTruncation] = useState(false);
  const textRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (textRef.current) {
      const lineHeight = parseInt(getComputedStyle(textRef.current).lineHeight);
      const maxHeight = lineHeight * 2; // 2 lines
      setNeedsTruncation(textRef.current.scrollHeight > maxHeight);
    }
  }, [citation.text]);

  return (
    <div 
      className={`mt-1 text-sm rounded-md overflow-hidden ${
        isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-200 text-gray-700'
      }`}
    >
      {/* Header button on top of each citation to minimize or maximize it */}
      <div 
        className={`flex items-center p-2 ${needsTruncation ? 'cursor-pointer' : ''}`}
        onClick={() => needsTruncation && setIsExpanded(!isExpanded)}
      >
        {/* Citation number */}
        <span className={`flex items-center justify-center w-5 h-5 rounded-full mr-2 text-xs ${
          isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
        }`}>
          {index + 1}
        </span>

        {/* Citation title or URL if the title doesn't exist */}
        <span className="flex-1 truncate">{citation.title || citation.url}</span>

        {/* Up/Down button for minimizing/expanding the citation */}
        {needsTruncation && (
          isExpanded ? 
            <FiChevronUp className="flex-shrink-0 ml-2" /> : 
            <FiChevronDown className="flex-shrink-0 ml-2" />
        )}
      </div>
      
      {/* Actual citation text */}
      <div className={`p-2 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        {/* Text */}
        <p 
          ref={textRef}
          className={`mb-2 ${!isExpanded && needsTruncation ? 'line-clamp-2' : ''}`}
        >
          {citation.text}
        </p>

        {/* Link */}
        <a 
          href={citation.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center text-blue-500 hover:underline"
        >
          Visit source <FiExternalLink className="ml-1" />
        </a>
      </div>
    </div>
  );
}
// src/components/ImageGallery.tsx
import { useState } from 'react';
import { FiX } from 'react-icons/fi';
import { ImageData } from '../types';
import Image from 'next/image';

interface ImageGalleryProps {
  images: ImageData[];
  isDarkMode: boolean;
}

export default function ImageGallery({ images, isDarkMode }: ImageGalleryProps): React.ReactElement | null {
  const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);

  if (!images || images.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      
      {/* Show the images in a gallery format inside this div container */}
      <div className="grid grid-cols-2 gap-2">
        {images.map((image, index) => (
          <div 
            key={index} 
            className="cursor-pointer rounded-md overflow-hidden"
            onClick={() => setSelectedImage(image)}
          >
            <Image 
              src={image.url} 
              alt={image.alt} 
              width={500}
              height={281}
              className="w-full h-auto object-cover"
              style={{ aspectRatio: '16/9' }}
            />
            {image.caption && (
              <p className={`text-xs p-1 ${
                isDarkMode ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
              }`}>
                {image.caption}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* When an image is selected, display it full screen */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
          <div className="relative max-w-4xl max-h-full">
            {/* X button on the top right */}
            <button 
              className="absolute top-2 right-2 text-white bg-black bg-opacity-50 rounded-full p-1"
              onClick={() => setSelectedImage(null)}
            >
              <FiX className="w-6 h-6" />
            </button>

            {/* Image Itself */}
            <Image 
              src={selectedImage.url} 
              alt={selectedImage.alt} 
              width={1200}
              height={675}
              className="w-full h-auto max-h-[90vh] object-contain" 
            />

            {/* Caption for the Image */}
            {selectedImage.caption && (
              <p className="text-white text-center mt-2">{selectedImage.caption}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
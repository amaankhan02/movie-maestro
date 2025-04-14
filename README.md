# Movie Maestro
Perplexity Take-Home Project for Amaan Khan

A specialized movie answer engine built for Perplexity's Residency Program. This application intelligently answers movie-related queries using data from multiple sources, providing detailed, accurate information with citations and visual content.

## Features

- **Multiple Data Sources**: Integrates TMDb and Wikipedia for comprehensive movie information
- **Intelligent API Selection**: Dynamically selects the appropriate TMDb API endpoint based on query context
- **Advanced LLM Integration**: Powered by GPT-4 for natural language understanding and response generation
- **Citations & Sources**: All information is properly attributed with citations to original sources
- **Related Queries**: Suggests related questions users might want to explore
- **Rich Media Support**: Includes relevant movie images, posters, and other visual content
- **Conversation History**: Supports multi-turn and follow-up queries by maintaining context
- **Responsive UI**: Modern, user-friendly interface that works across devices
- **Dark/Light Theme**: Users have the option to choose a Dark or Light theme.

## Tech Stack

- **Backend**:
  - Python with FastAPI
  - LangChain for LLM orchestration
  - TMDb and Wikipedia APIs

- **Frontend**:
  - TypeScript
  - Next.js with App Router
  - Tailwind CSS for styling

- **Deployment**:
  - Frontend: Vercel
  - Backend: Render

## Setup Instructions

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- TMDb API key

### Backend Setup

#### Using Conda
```bash
# Create and activate environment
conda create -n plex-env python=3.11
conda activate plex-env

# Install dependencies
conda env update -f backend/environment.yml

# Set up environment variables
cp backend/.env.example backend/.env
# Edit .env and add your API keys
```

#### Using Pip
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Set up environment variables
cp backend/.env.example backend/.env
# Edit .env and add your API keys
```

### Frontend Setup
```bash
# Install dependencies
cd frontend
npm install

# Create environment file
cp .env.example .env.local
# Configure environment variables
```

## Running the Application

### Backend
```bash
cd backend
python -m src.main
```

### Frontend
```bash
cd frontend
npm run dev
```

Visit `http://localhost:3000` to use the application.

## Architecture

The application follows a client-server architecture:

1. User queries are processed by the frontend and sent to the backend API
2. The backend identifies query intent and selects appropriate data sources
    * Decides if it should use TMDb, Wikipedia, or both
    * For TMDb, it decides which API endpoint to use. It uses an LLM call to determine type of information it requires: movie, person, rating, etc. And then makes the correct respective API call to retrieve that information.
    * For Wikipedia, it first determines 3 relevant keywords that it can use to search for in Wikipedia, and then gathers that information
3. Relevant data is fetched from TMDb and/or Wikipedia 
    * Due to Wikipedia having a lot of information, it retrieves only introduction paragraph and an additional 20 sentences. However, this can easily be changes to retrieve everything. Or if I had a vector DB of the Wikipedia snapshot available, then it could perform a more intelligent search/retreival to only retrieve relevant chunks of data from the Wikipedia article.
4. GPT-4 generates a comprehensive answer using retrieved information
5. The response, including citations and related queries, is returned to the frontend
6. The frontend presents the information in an engaging, accessible format
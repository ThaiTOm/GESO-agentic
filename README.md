# GESO-agentic: Policy-Aware Orchestrator with RAG and Data Analysis

## Project Overview

GESO-agentic is an advanced AI-powered system that combines Retrieval Augmented Generation (RAG), structured database querying, and data analysis capabilities within a policy-aware orchestration framework. The system is designed to provide intelligent responses to user queries while enforcing access control policies based on user roles.

### Key Features

- **Policy-Aware Orchestration**: Enforces security policies based on user roles before routing queries to appropriate services
- **Retrieval Augmented Generation (RAG)**: Answers questions about documents, policies, and general information
- **Structured Database Querying**: Retrieves specific information from structured databases
- **Business Data Analysis**: Analyzes financial reports, business segments, and trends
- **Chatbot Management**: Create and manage multiple chatbots with separate document collections
- **Document Management**: Upload, process, and index documents for RAG
- **Conversation History**: Maintains and summarizes conversation context

## System Architecture

The system is built with a modular architecture consisting of several key components:

### Backend Components

1. **Orchestrator Service**
   - Enforces access policies
   - Routes queries to appropriate tools
   - Manages conversation history and context

2. **RAG Service**
   - Processes and indexes documents
   - Retrieves relevant context for queries
   - Generates answers using LLM with retrieved context

3. **Database Query Service**
   - Queries structured data from Excel files
   - Analyzes data using a specialized data analyst agent

4. **Data Analysis Service**
   - Processes time series data
   - Performs trend analysis on business performance
   - Generates visualizations and textual summaries

### Frontend Components

1. **Chat Interface**
   - User-friendly chat UI
   - Chatbot selection
   - Message history display

2. **Admin Dashboard**
   - Chatbot management
   - Document upload and management
   - System monitoring

### Technology Stack

- **Backend**: FastAPI, LangGraph, LangChain
- **Database**: Typesense (vector database)
- **LLM Integration**: Google Gemini API
- **Frontend**: React, React Router
- **Data Visualization**: Plotly
- **Data Processing**: Pandas, NumPy

## Installation and Setup

### Prerequisites

- Python 3.9+
- Node.js 14+
- Typesense server
- Google Gemini API key

### Backend Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-org/GESO-agentic.git
   cd GESO-agentic
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `config.py` file with the following settings:
   ```python
   # API and Service Configuration
   API_URL = "http://localhost:8000"
   CORS_ORIGINS = ["http://localhost:3000"]
   UPLOAD_DIR = "uploads"
   
   # Typesense Configuration
   TYPESENSE_HOST = "localhost"
   TYPESENSE_PORT = 8108
   TYPESENSE_PROTOCOL = "http"
   TYPESENSE_API_KEY = "your_typesense_api_key"
   
   # LLM Configuration
   GEMINI_API_KEY = ["your_gemini_api_key"]
   GEMINI_MODEL_NAME = "gemini-pro"
   OPEN_ROUTER_KEY = "your_openrouter_key"
   SELF_HOST = False
   
   # Embedding Configuration
   EMBEDDING_MODEL = "all-MiniLM-L6-v2"
   EMBEDDING_DIMENSION = 384
   EMBEDDING_BATCH_SIZE = 32
   EMBEDDING_MAX_SEQ_LENGTH = 256
   MODEL_CACHE_DIR = ".model_cache"
   MODEL_URL = "http://localhost:8000"
   
   # LangSmith Configuration (optional)
   LANGSMITH_TRACING_V2 = "true"
   LANGSMITH_API_KEY = "your_langsmith_api_key"
   LANGSMITH_PROJECT = "geso-agentic"
   
   # Logging Configuration
   LOG_LEVEL = "INFO"
   LOG_DIR = "logs"
   LOG_TO_FILE = True
   LOG_FILE_MAX_SIZE_MB = 10
   LOG_FILE_BACKUP_COUNT = 5
   ENABLE_PERFORMANCE_MONITORING = True
   ENABLE_REQUEST_LOGGING = True
   
   # Data Analysis Configuration
   DA_CHUNK_SIZE = 1000
   ```

5. Start the Typesense server:
   ```
   docker run -p 8108:8108 -v ./typesense-data:/data typesense/typesense:0.24.1 --data-dir /data --api-key=your_typesense_api_key
   ```

6. Start the backend services:
   ```
   # Start the main API service
   uvicorn src.routes.main_routes:app --host 0.0.0.0 --port 8000 --reload
   
   # Start the orchestrator service
   uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd front-end
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. Access the application at `http://localhost:3000`

## Usage Guide

### Chatbot Management

1. **Creating a Chatbot**:
   - Navigate to the Admin page
   - Click "Create New Chatbot"
   - Enter a name and description
   - Save the API key for future use

2. **Uploading Documents**:
   - Select a chatbot from the admin dashboard
   - Click "Upload Document"
   - Select PDF files to upload
   - The system will process and index the documents automatically

### Using the Chat Interface

1. **Selecting a Chatbot**:
   - Choose a chatbot from the dropdown in the chat interface
   - Enter the API key if prompted

2. **Asking Questions**:
   - Type your question in the input field
   - The system will:
     - Check if you're authorized to ask the question
     - Route your query to the appropriate tool (RAG, database query, or analysis)
     - Return the answer with relevant context or visualizations

3. **Query Types**:
   - **Document Queries**: Questions about policies, procedures, or information in documents
   - **Database Queries**: Questions about specific data points, statistics, or structured information
   - **Analysis Queries**: Questions about trends, patterns, or business performance

## API Documentation

### Orchestrator API

- **POST /orchestrate**
  - Receives a natural language query and user info
  - Enforces security policy
  - Routes to the correct backend service
  - Returns the result

### RAG API

- **GET /api/v1/typesense/chatbot/all**
  - Retrieves all chatbots

- **POST /api/v1/typesense/chatbot/create**
  - Creates a new chatbot

- **DELETE /api/v1/typesense/chatbot/delete/{chatbot_name}**
  - Deletes a chatbot

- **GET /api/v1/typesense/document/{chatbot_name}**
  - Retrieves documents for a specific chatbot

- **POST /api/v1/typesense/document/upload/{chatbot_name}**
  - Uploads and processes a document

- **POST /api/v1/typesense/query_ver_thai**
  - Performs a RAG query and returns an answer

- **POST /api/v1/query_rag**
  - Analyzes Excel documents based on a query

### Analysis API

- **GET /api/v1/analysis**
  - Processes sales data and performs trend analysis
  - Returns text results and plot data

## Dependencies

### Backend Dependencies

- fastapi
- langchain
- langgraph
- typesense
- google-generativeai
- pandas
- numpy
- plotly
- pydantic
- aiofiles

### Frontend Dependencies

- react
- react-router-dom
- axios
- plotly.js
- react-icons

## Deployment

For production deployment, consider the following:

1. **Environment Variables**:
   - Store sensitive information in environment variables
   - Use a .env file or a secure secrets management system

2. **Docker Deployment**:
   - Containerize the application for consistent deployment
   - Use docker-compose for orchestrating multiple services

3. **Security Considerations**:
   - Secure the Typesense server with proper authentication
   - Use HTTPS for all API endpoints
   - Implement proper user authentication and authorization

4. **Scaling**:
   - Consider using a load balancer for the API services
   - Scale the Typesense server based on your indexing and query needs
   - Implement caching for frequently accessed data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
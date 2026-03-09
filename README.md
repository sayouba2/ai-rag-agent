# AI RAG Agent

A Retrieval-Augmented Generation application built with FastAPI, React, LangChain and ChromaDB.

## Features

- Upload PDF or TXT documents
- Index documents into a vector database
- Ask questions about the documents
- Generate AI answers using OpenAI

## Tech Stack

Backend
- Python
- FastAPI
- LangChain
- ChromaDB
- OpenAI API

Frontend
- React
- Vite

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
cd frontend
npm install
npm run dev 
```
Environment variables

Create a .env file in backend/:

OPENAI_API_KEY=your_api_key_here
Usage

1 Upload documents
2 Ask questions about them

Example question:

What is the internship duration mentioned in the document?
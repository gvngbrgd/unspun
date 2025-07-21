# Unspun

A small Flask application that analyzes article content using Firecrawl and OpenAI.

## Installation

Create a virtual environment and install dependencies using **pip**:

```bash
pip install -r requirements.txt
```

Alternatively, install the project as a package:

```bash
pip install .
```

## Environment Variables

Set the following environment variables so the application can access the required APIs:

- `FIRECRAWL_API_KEY` – API key for Firecrawl (required)
- `OPENAI_API_KEY` – API key for OpenAI (optional but required for summaries)

These can be exported in your shell or placed in an `.env` file loaded by your environment.

## Running the App

To start the Flask development server on port **10000** run:

```bash
python main.py
```

For production you can use **gunicorn**:

```bash
gunicorn -b 0.0.0.0:10000 main:app
```

## Example Usage

With the server running, send a `GET` request to `/analyze` with a `url` query parameter:

```bash
curl "http://localhost:10000/analyze?url=https://example.com/article"
```

The endpoint returns JSON containing the extracted text and an optional summary if an OpenAI key is configured.

# research_helper

A lightweight toolkit for automating and streamlining research workflows, aimed at academics and data scientists. This repository provides a set of scripts, utilities, and templates to assist with research project organization, literature management, data processing, and reproducible analysis.

## Features

- Project structure templates for reproducible research
- Tools for managing and formatting bibliographies
- Utilities for data cleaning and preprocessing
- Scripts for automating tasks such as scraping Google Scholar and formatting results with OpenAI LLMs

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/peterdunson/research_helper.git
   cd research_helper
   ```

2. **Set up your environment variables:**

   This project requires access to the OpenAI API.  
   You must create a `.env` file in the root directory with your OpenAI API key.

   Example `.env` file:
   ```
   OPENAI_API_KEY=sk-...your-key-here...
   ```

   The project uses [`python-dotenv`](https://pypi.org/project/python-dotenv/) to load environment variables.

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Using the scrapper:**

   The main scraping logic is in `app/scholar.py` (`search_scholar` function).  
   To run an end-to-end workflow that scrapes Google Scholar and formats results with an OpenAI LLM, use `llm_wrapper.py`:

   ```bash
   python llm_wrapper.py
   ```

   This will run a sample query and print formatted paper results.

   - You can modify the query or integrate the modules into your own scripts.
   - Make sure your `.env` file is present and your API key is valid.

## Requirements

- Python 3.7+
- See `requirements.txt` for dependencies.

## Contributing

Contributions, suggestions, and bug reports are welcome! Please submit pull requests or open issues as needed.

## License

This project is licensed under the MIT License.

---
*Created by Peter Dunson*

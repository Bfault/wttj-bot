# wttj-bot

Fetch all companies on welcometothejungle given a keyword and a language

Apply to all companies with a given cover letter is possible

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 bot.py -h
```
to see all options

```bash
python3 bot.py -k "python" -l "fr" -o "companies.txt"
```
to fetch all companies with keyword "python" and language "fr" and save them in "companies.txt"

```bash
python3 bot.py -k "python" -l "fr" -c "cover_letter.txt"
```
to send application to all companies with keyword "python" and language "fr" and use "cover_letter.txt" as cover letter

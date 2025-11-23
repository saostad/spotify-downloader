# Spotify Podcast Downloader

A Python script that downloads podcast episodes from Spotify URLs by finding them on alternative platforms like YouTube, Acast, and Podchaser.

## Features

- **Multi-Source Fallback System**: Tries multiple sources to find your podcast
  - YouTube search (primary)
  - Direct Acast URL construction
  - Apple Podcasts search (via iTunes API)
  - Web search for alternative platforms (Acast, Podchaser, SoundCloud)
  
- **Smart Validation**: Uses a scoring system to ensure the correct episode is downloaded
  - Duration matching (exact or approximate)
  - Channel/uploader verification
  - Title similarity checking
  
- **Automatic Audio Extraction**: Downloads and converts to MP3 format

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (required for audio conversion):
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Usage

### Basic Usage

```bash
python spotify_podcast_download.py <spotify_podcast_url>
```

### Examples

Download a podcast episode:
```bash
python spotify_podcast_download.py "https://open.spotify.com/episode/1InTLPWB1UCU7ktVN2pPe3"
```

## How It Works

1. **Metadata Extraction**: Scrapes the Spotify URL to extract:
   - Episode title
   - Show name
   - Duration (if available)

2. **YouTube Search**: Searches YouTube with multiple query variations:
   - Full show name + episode title
   - Show name + episode title (without episode number)
   - Show name + episode number
   - Episode title only

3. **Direct URL Construction**: Attempts to construct direct URLs to known platforms:
   - Acast (with multiple slug variations)

4. **Apple Podcasts Search**: Searches Apple Podcasts using the iTunes API:
   - Finds the podcast show by name
   - Retrieves recent episodes (up to 200)
   - Scores each episode based on title, duration, and show match
   - Downloads the best match if score ≥40

5. **Web Search Fallback**: If YouTube, direct URLs, and Apple Podcasts fail, searches the web for:
   - Acast episodes
   - Podchaser episodes
   - SoundCloud

6. **Validation**: Each candidate is scored based on:
   - **Duration match** (50 points for exact, 20 for approximate)
   - **Channel match** (40 points if uploader matches show name)
   - **Title similarity** (up to 30 points)
   - Minimum score threshold: 50 for YouTube, 40 for alternative sources

7. **Download**: Downloads the best match and converts to MP3

## Scoring System

The script validates each candidate to prevent downloading the wrong episode:

| Criteria | Points | Description |
|----------|--------|-------------|
| Exact duration match | 50 | Within 60 seconds |
| Approximate duration | 20 | Within 3 minutes |
| Channel match | 40 | Uploader name matches show |
| Title similarity | 0-30 | Based on fuzzy matching |

**Threshold**: 
- YouTube results: ≥50 points required
- Alternative sources: ≥40 points required

## Limitations

- **Music tracks**: This tool is designed for **podcasts only**. It will not download music tracks (as shown in the example with Drake's "One Dance")
- **DRM-protected platforms**: Cannot download from Amazon Music or Everand (DRM-protected)
- **Acast URL slugs**: Acast abbreviates episode slugs unpredictably, so direct URL construction may not always work
- **Availability**: Episodes must be available on at least one supported platform (YouTube, Acast, Podchaser, etc.)

## Supported Platforms

- ✅ YouTube
- ✅ Acast
- ✅ Podchaser
- ✅ Apple Podcasts (via iTunes API)
- ✅ SoundCloud
- ❌ Amazon Music (DRM-protected)
- ❌ Spotify (no direct download)
- ❌ Everand (DRM-protected)

## Output

Downloaded files are saved in the current directory with the format:
```
Episode Title [video_id].mp3
```

## Troubleshooting

### "No suitable match found"
- The episode may not be available on any supported platform
- Try searching manually on YouTube or Acast to verify availability

### "Duration tag not found"
- This is normal - not all Spotify pages include duration metadata
- The script will still work using title and channel matching

### "Failed to download podcast from all sources"
- Verify the Spotify URL is for a **podcast episode** (not a music track)
- Check if the episode is available on YouTube or other platforms
- Some podcasts are exclusive to Spotify and cannot be downloaded

## Requirements

- Python 3.7+
- FFmpeg
- Internet connection

## Dependencies

- `yt-dlp`: YouTube and media downloading
- `beautifulsoup4`: HTML parsing
- `requests`: HTTP requests
- `ddgs`: Web search functionality

## License

This tool is for personal use only. Respect copyright laws and podcast creators' rights.

## Disclaimer

This tool is intended for downloading podcasts that you have the right to access. Do not use it to download copyrighted content without permission. The authors are not responsible for any misuse of this tool.

import sys
import requests
from bs4 import BeautifulSoup
import yt_dlp
import difflib
import re

def get_spotify_metadata(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metadata = {}
        
        # Extract Title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            metadata['title'] = og_title['content']
        else:
            # Fallback to title tag
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().replace('| Podcast on Spotify', '').strip()

        # Extract Show Name
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            # Format is usually "Show Name · Episode"
            metadata['show'] = og_desc['content'].split(' · ')[0].strip()
        
        # Extract Duration
        duration_tag = soup.find('meta', property='music:duration')
        if duration_tag:
            print(f"Found duration tag: {duration_tag}")
            try:
                metadata['duration'] = int(duration_tag['content'])
            except ValueError:
                print(f"Could not parse duration: {duration_tag['content']}")
        else:
            print("Duration tag not found in Spotify page.")
                
        return metadata
    except Exception as e:
        print(f"Error fetching Spotify page: {e}")
        return None

def download_video(url, title):
    print(f"Downloading: {title}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return True
        except Exception as e:
            print(f"Error downloading: {e}")
            return False

def calculate_score(candidate, metadata):
    score = 0
    reasons = []
    
    # 1. Duration Check
    target_duration = metadata.get('duration')
    video_duration = candidate.get('duration')
    if target_duration and video_duration:
        diff = abs(target_duration - video_duration)
        if diff < 60:
            score += 50
            reasons.append("Exact duration match")
        elif diff < 180: # 3 mins tolerance
            score += 20
            reasons.append("Approx duration match")
            
    # 2. Channel/Uploader Check
    show_name = metadata.get('show', '').lower()
    uploader = candidate.get('uploader', '').lower()
    channel = candidate.get('channel', '').lower()
    
    # Check if significant parts of show name are in uploader/channel
    show_words = set(re.findall(r'\w+', show_name))
    # Filter out common words
    stop_words = {'with', 'podcast', 'the', 'show', 'episode', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'so', 'money'} 
    
    unique_show_words = show_words - stop_words
    
    uploader_words = set(re.findall(r'\w+', uploader + ' ' + channel))
    
    common = unique_show_words.intersection(uploader_words)
    
    if len(common) >= 1:
        score += 40
        reasons.append(f"Channel match ({common})")
        
    # 3. Title Similarity
    target_title = metadata.get('title', '').lower()
    video_title = candidate.get('title', '').lower()
    
    # Check against full title
    ratio = difflib.SequenceMatcher(None, target_title, video_title).ratio()
    
    # Check against title without episode number (if applicable)
    clean_target = re.sub(r'^\d+[:\s-]', '', target_title).strip()
    if clean_target != target_title:
        ratio2 = difflib.SequenceMatcher(None, clean_target, video_title).ratio()
        ratio = max(ratio, ratio2)
        
    score += ratio * 30
    reasons.append(f"Title similarity {ratio:.2f}")
    
    return score, reasons

from ddgs import DDGS

# ... (imports)

def try_direct_sources(metadata):
    """Try to construct direct URLs to known podcast platforms"""
    print("\nTrying direct URL construction for known platforms...")
    
    show = metadata.get('show', '')
    title = metadata.get('title', '')
    
    # Extract episode number
    episode_num = None
    match = re.match(r'^(\d+)', title)
    if match:
        episode_num = match.group(1)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    # Try Acast URL construction
    # Format: https://shows.acast.com/{show-slug}/episodes/{episode-slug}
    if show and title:
        # Create slug from show name
        show_base = show.lower().replace(' with ', '-').replace(' ', '-').replace(':', '')
        show_slugs = [show_base, f"{show_base}-1"]  # Try with and without -1 suffix
        
        # Create slug from title (simplified)
        title_clean = re.sub(r'^\d+:\s*', '', title)  # Remove episode number
        title_slug = title_clean.lower()[:80]  # Limit length
        title_slug = re.sub(r'[^\w\s-]', '', title_slug)  # Remove special chars
        title_slug = re.sub(r'\s+', '-', title_slug.strip())  # Replace spaces
        title_slug = re.sub(r'-+', '-', title_slug)  # Remove duplicate dashes
        
        # Try different URL variations
        acast_urls = []
        for show_slug in show_slugs:
            if episode_num:
                acast_urls.append(f"https://shows.acast.com/{show_slug}/episodes/{episode_num}-{title_slug}")
            acast_urls.append(f"https://shows.acast.com/{show_slug}/episodes/{title_slug}")
        
        for url in acast_urls:
            print(f"Trying direct URL: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    score, reasons = calculate_score(info, metadata)
                    print(f"Candidate: {info.get('title')} | Score: {score:.2f} | Reasons: {reasons}")
                    
                    if score >= 40:
                        print(f"Selected: {info['title']}")
                        return download_video(url, info['title'])
                except Exception as e:
                    # Don't print error for expected 404s
                    if "HTTP Error 404" not in str(e):
                        print(f"Failed: {e}")
                    continue
    
    return False

def search_web_and_download(metadata):
    print("\nSearching web for alternative sources...")
    
    show = metadata.get('show', '')
    title = metadata.get('title', '')
    
    # Extract episode number
    episode_num = None
    match = re.match(r'^(\d+)', title)
    if match:
        episode_num = match.group(1)
        
    queries = []
    # 1. Very specific query with episode number
    if episode_num:
        queries.append(f'"{show}" "{episode_num}" site:acast.com OR site:podchaser.com')
        
    # 2. Specific query with site restriction
    queries.append(f"{show} {title} site:acast.com OR site:podchaser.com")
    
    # 3. Just Show + Title (let search engine find best source)
    queries.append(f'"{show}" "{title}" podcast')

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    seen_urls = set()
    
    for query in queries:
        print(f"\nWeb Search Query: {query}")
        try:
            # DDGS().text returns a list of dicts
            results = DDGS().text(query, max_results=10)
        except Exception as e:
            print(f"Web search failed: {e}")
            continue
            
        if not results:
            print("No web results found.")
            continue
            
        for result in results:
            url = result['href']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Filter for likely audio sources
            if not any(domain in url for domain in ['acast.com', 'podchaser.com', 'podcasts.apple.com', 'soundcloud.com']):
                continue
            
            # Skip non-episode pages
            if any(skip in url for skip in ['/insights', '/creators/', '/podcasts/' + show.lower().replace(' ', '-') + '$']):
                continue
                
            print(f"\nChecking URL: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Extract info without downloading first
                    info = ydl.extract_info(url, download=False)
                    
                    # Check duration/title match
                    score, reasons = calculate_score(info, metadata)
                    print(f"Candidate: {info.get('title')} | Score: {score:.2f} | Reasons: {reasons}")
                    
                    # Lower threshold for web results as we are more confident in the source (Acast/Podchaser)
                    if score >= 40: 
                        print(f"Selected: {info['title']}")
                        return download_video(url, info['title'])
                        
                except Exception as e:
                    print(f"Error checking URL {url}: {e}")
                    continue
    
    return False

def search_and_download(metadata):
    show = metadata.get('show', '')
    title = metadata.get('title', '')
    
    queries = []
    
    # Extract episode number
    episode_num = None
    clean_title = title
    match = re.match(r'^(\d+)[:\s-](.*)', title)
    if match:
        episode_num = match.group(1)
        clean_title = match.group(2).strip()

    # 1. Full Query
    queries.append(f"{show} {title}")
    
    # 2. Show + Title without Episode Number
    if clean_title != title:
        queries.append(f"{show} {clean_title}")

    # 3. Show + Episode Number
    if episode_num:
        queries.append(f"{show} Episode {episode_num}")
        if "Farnoosh Torabi" in show:
            queries.append(f"Farnoosh Torabi {episode_num}")

    # 4. Just Title
    queries.append(title)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch5',
    }
    
    best_candidate = None
    best_score = 0
    
    seen_urls = set()
    
    for query in queries:
        print(f"\nTrying query: {query}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                
                if 'entries' not in info:
                    continue
                
                candidates = list(info['entries'])
                print(f"Found {len(candidates)} candidates.")
                
                for entry in candidates:
                    if not entry: continue
                    url = entry.get('webpage_url')
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    score, reasons = calculate_score(entry, metadata)
                    print(f"Candidate: {entry.get('title')} | Score: {score:.2f} | Reasons: {reasons}")
                    
                    if score > best_score:
                        best_score = score
                        best_candidate = entry
                        
            except Exception as e:
                print(f"Error searching: {e}")
                continue
                
    if best_candidate and best_score >= 50:
        print(f"\nSelected Best Match: {best_candidate['title']} (Score: {best_score:.2f})")
        return download_video(best_candidate['webpage_url'], best_candidate['title'])
    else:
        print(f"\nNo suitable match found on YouTube. Best score was {best_score:.2f}.")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python download_podcast.py <spotify_url>")
        sys.exit(1)

    spotify_url = sys.argv[1]
    print(f"Processing Spotify URL: {spotify_url}")

    metadata = get_spotify_metadata(spotify_url)
    if not metadata:
        print("Could not extract metadata from Spotify URL.")
        sys.exit(1)
        
    print(f"Metadata: {metadata}")
    
    # Try YouTube first
    success = search_and_download(metadata)
    
    if not success:
        # Try direct URL construction
        success = try_direct_sources(metadata)
        
    if not success:
        # Fallback to web search
        success = search_web_and_download(metadata)
        
    if not success:
        print("Failed to download podcast from all sources.")
        sys.exit(1)

if __name__ == "__main__":
    main()

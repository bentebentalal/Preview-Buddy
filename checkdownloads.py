import requests

OWNER = "bentebentalal"
REPO = "Preview-Buddy"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"

def fetch_download_counts():
    response = requests.get(API_URL)
    if response.status_code != 200:
        print(f"Error fetching releases: {response.status_code}")
        return

    releases = response.json()
    total_downloads = 0

    for release in releases:
        print(f"\nRelease: {release.get('name', 'Unnamed Release')}")
        for asset in release.get('assets', []):
            name = asset.get('name')
            count = asset.get('download_count', 0)
            print(f"  {name} — {count} downloads")
            total_downloads += count

    print(f"\nTotal downloads across all releases: {total_downloads}")

if __name__ == "__main__":
    fetch_download_counts()

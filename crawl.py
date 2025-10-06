import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

URL = "https://dict.variants.moe.edu.tw/appendix.jsp?ID=3"
OUTPUT_PATH = "E:\Benkyute Kudasai\Chinese\Building-a-dictionary-of-Chinese-variants\variants.html"

def fetch_and_save_insecure(url: str, output_path: str) -> None:
    try:
        resp = requests.get(url, timeout=30, verify=False)
        resp.raise_for_status()
        encoding = resp.encoding or resp.apparent_encoding or "utf-8"
        with open(output_path, "w", encoding=encoding) as f:
            f.write(resp.text)
        print(f"[INSECURE] Saved content to: {output_path}")
        print(f"Status Code: {resp.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

# def write_to_csv():
    
if __name__ == "__main__":
    fetch_and_save_insecure(URL, OUTPUT_PATH)

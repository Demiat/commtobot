import requests
import os

ca_bundle_path = r'C:\Users\Legion\Dropbox\PY\commtobot\russian_trusted_root_ca.cer'
os.environ['REQUESTS_CA_BUNDLE'] = ca_bundle_path
gigaurl = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'

payload = 'scope=GIGACHAT_API_PERS'
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'RqUID': '30ef1a13-3be9-475b-8d53-a789de49b1c5',
    'Authorization': 'Basic ODgyZDY5ZGUtYTk2OS00MTVmLWFmNzMtZmZiZjI4MDkzN2I1OjUwZjNkYTU1LTBlMjctNDAyMy05NDYxLWU3ZjRiYzc4NmFhYQ=='
}

response = requests.request("POST", gigaurl, headers=headers, data=payload)

print(response.text)

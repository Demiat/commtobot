import certifi
with open(certifi.where(), 'r') as f:
    lines = f.readlines()
    if 'russian_trusted_root_ca.cer' in ''.join(lines):
        print("Сертификат найден!")
    else:
        print("Сертификат не найден.")

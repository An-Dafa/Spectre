# Local HTTPS Certificates

This folder is for local development TLS certificates.

Generate certificates with OpenSSL:

```powershell
cd D:\Spectre\backend
openssl req -x509 -newkey rsa:2048 -nodes `
  -keyout certs\localhost-key.pem `
  -out certs\localhost-cert.pem `
  -days 365 `
  -subj "/CN=localhost" `
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

Run backend over HTTPS:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 `
  --ssl-keyfile .\certs\localhost-key.pem `
  --ssl-certfile .\certs\localhost-cert.pem
```

The certificate and private key are ignored by git.

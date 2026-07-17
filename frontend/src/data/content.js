export const tracks = {
  kyc: {
    label: 'Enterprise KYC',
    source: 'Customer uploads KTP, KK, SIM, passport, or identity proof.',
    engine: ['YOLO26n-ready detection', 'Guardrail validation', 'Redaction policy', 'Sovereign Vault'],
    destination: 'Operational server receives redacted evidence only.',
    endpoint: '/api/redact',
  },
  live: {
    label: 'LiveShield',
    source: 'Raw webcam, OBS, or mobile camera frame.',
    engine: ['Frame detection', 'Blur active classes', 'Ephemeral return', 'No frame storage'],
    destination: 'Public stream receives safe video frames.',
    endpoint: '/api/live/redact-frame',
  },
  screen: {
    label: 'Screen-Shield',
    source: 'Screen text, spreadsheet, meeting share, or screenshot.',
    engine: ['OCR or text parse', 'Sensitive regex detection', 'Blackout regions', 'Ephemeral return'],
    destination: 'Meeting transport receives redacted content.',
    endpoint: '/api/screen/ocr-redact',
  },
};

export const institutions = ['Banking', 'Government', 'Healthcare', 'Logistics', 'Telco', 'Campus', 'Fintech', 'Broadcast'];

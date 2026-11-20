# AFARM media on Amazon S3 + CloudFront

Uploads from the API are stored in **S3** and served via **CloudFront**. The database stores full HTTPS URLs (fast global delivery, no load on EC2).

Images are still **optimized to WebP** before upload (`app/storage/optimize.py`).

---

## 1. S3 bucket (Mumbai `ap-south-1` recommended)

1. **S3 → Create bucket**
   - Name: e.g. `afarm-media-prod` (globally unique)
   - Region: **ap-south-1** (same region as EC2 reduces upload latency)
   - **Block all public access**: ON (CloudFront will read objects; bucket stays private)
2. Optional: enable **Bucket versioning** for recovery.

---

## 2. CloudFront distribution

1. **CloudFront → Create distribution**
   - **Origin domain**: choose your S3 bucket (not the website endpoint)
   - **Origin access**: **Origin access control (OAC)** → create new OAC
   - **Viewer protocol policy**: Redirect HTTP to HTTPS
   - **Allowed HTTP methods**: GET, HEAD, OPTIONS (uploads go API → S3, not browser → S3)
   - **Compress objects automatically**: Yes (faster images)
   - **Price class**: Use all edge locations (or India/Europe if cost-sensitive)
2. After creation, apply the **bucket policy** CloudFront shows (allows `s3:GetObject` for the distribution only).
3. Note the distribution domain: `https://dxxxxxxxx.cloudfront.net` → `AWS_CLOUDFRONT_URL`

Optional: add **alternate domain** `cdn.afarm.khulega.online` (ACM cert in **us-east-1** for CloudFront, CNAME in Route 53).

---

## 3. IAM permissions (EC2 instance role — recommended)

Attach a policy to the **EC2 instance role** for khulega-online (no keys in `.env`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AfarmMediaUpload",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::afarm-media-prod/*"
    },
    {
      "Sid": "AfarmMediaListOptional",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::afarm-media-prod"
    }
  ]
}
```

Replace bucket name. **Do not** grant public `s3:*`.

**Alternative:** IAM user access key → set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in server `.env` (less ideal).

---

## 4. Server `.env`

```env
STORAGE_BACKEND=s3
AWS_S3_BUCKET=afarm-media-prod
AWS_S3_REGION=ap-south-1
AWS_S3_PREFIX=
AWS_CLOUDFRONT_URL=https://dxxxxxxxx.cloudfront.net
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

Restart API:

```bash
cd /srv/afarm/afarm-backend
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart afarm-backend
```

---

## 5. Frontend (optional)

In `afarm-frontend/.env.production` set the same CDN for any client-side absolute URLs:

```env
NEXT_PUBLIC_CDN_URL=https://dxxxxxxxx.cloudfront.net
```

Rebuild frontend after change. Product images returned by the API are already full CloudFront URLs when using S3.

---

## 6. Existing `/uploads/` on disk

- Old rows keep paths like `/uploads/products/...` (still served from EC2 via FastAPI).
- New uploads use CloudFront URLs.
- Re-upload important images in admin or run a one-off migration script if needed.

---

## 7. Verify

1. Admin → upload a product image.
2. API response / DB `url` should start with `https://dxxxx.cloudfront.net/`.
3. Open that URL in a browser (should load fast).
4. Storefront product page should show the same URL in DevTools → Network.

---

## Troubleshooting

| Symptom | Check |
|--------|--------|
| `S3 upload failed (AccessDenied)` | IAM policy on instance role or keys |
| 403 from CloudFront | OAC bucket policy applied; object exists in S3 |
| Still `/uploads/...` URLs | `STORAGE_BACKEND=s3` and both bucket + CloudFront URL set |
| Images broken in admin only | Full URL should work; check `resolveMediaUrl` / API URL for legacy paths |
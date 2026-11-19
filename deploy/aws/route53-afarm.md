# Route 53 — AFARM on khulega-online

Hosted zone: **khulega.online**

Point **only AFARM** at **khulega-online** if you deploy there (`i-0421a5b373773cd18`).

| Record name | Type | Value |
|-------------|------|--------|
| `afarm.khulega.online` | **A** | `13.207.119.202` |
| `api.afarm.khulega.online` | **A** | `13.207.119.202` |

Other subdomains (chairdekho, video, etc.) may use **other EC2 instances** — use each instance’s **Public IPv4**, not this IP unless that site really runs on khulega-online.

After DNS:

```bash
sudo certbot --nginx -d afarm.khulega.online -d api.afarm.khulega.online
```
# EC2: khulega-online (AFARM)

| Field | Value |
|--------|--------|
| Name | `khulega-online` |
| Instance ID | `i-0421a5b373773cd18` |
| Region | `ap-south-1` (Mumbai) |
| OS | Amazon Linux 2023 |
| SSH user | **`ec2-user`** |
| Key pair | `webserver1-key` |
| **Elastic IP (use in DNS)** | **`13.207.119.202`** |
| Allocation ID | `eipalloc-0f5a2226fa6e1a8ea` |
| Private IP | `172.31.3.143` |
| Type | `t3.nano` |

## Multiple EC2 instances

You have **more than one server**. In Route 53, **each hostname must point at the instance that actually runs that site** — do not set every `*.khulega.online` record to this IP.

| If the site runs on **khulega-online** (`i-0421a5b373773cd18`) | Set A record to |
|------------------------------------------------------------------|-----------------|
| All sites on this instance (khulega, afarm, etc.) | **`13.207.119.202`** |

For other hostnames, open each instance in EC2 and use **its** Public IPv4.

Records on **other EC2 instances** keep **those instances’** public IPs — only hostnames served by **khulega-online** use **`13.207.119.202`**.

## DNS on this instance (same IP for all)

| Name | Type | Value |
|------|------|--------|
| `khulega.online` | A | `13.207.119.202` |
| `www.khulega.online` | A | `13.207.119.202` |
| `afarm.khulega.online` | A | `13.207.119.202` |
| `api.afarm.khulega.online` | A | `13.207.119.202` |
| Other `*.khulega.online` **on this server** | A | `13.207.119.202` |

## SSH

```bash
ssh -i /path/to/webserver1-key.pem ec2-user@13.207.119.202
```

## GitHub Actions

| Secret | Value |
|--------|--------|
| `SSH_HOST` | `13.207.119.202` |
| `SSH_USER` | `ec2-user` |

## AFARM paths on this box

```text
/srv/afarm/afarm-backend/
/srv/afarm/afarm-frontend/
```
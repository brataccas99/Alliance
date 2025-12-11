# Quick Deploy - Cost-Optimized Setup

Deploy your backend to Azure in **5 minutes** for **~$5-7/month**!

## 🚀 One-Command Deploy

```powershell
# Windows PowerShell
cd cloud
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your API keys
./deploy.ps1
```

```bash
# Linux/Mac
cd cloud
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your API keys
chmod +x deploy.sh
./deploy.sh
```

## 💰 Cost Breakdown

**Total: ~$5-7/month**

| Resource | Tier | Cost/Month | Notes |
|----------|------|------------|-------|
| App Service | F1 (Free) | **$0** | Perfect for backend with minimal traffic |
| Cosmos DB | Serverless | ~$0-2 | Only pay for actual requests |
| Container Registry | Basic | ~$5 | Image storage |
| Bandwidth | First 100GB | **$0** | Plenty for API traffic |

## 🌍 Region: West Europe

Perfect for:
- 🇮🇹 Italy: ~25ms latency
- 🇶🇦 Qatar: ~100-120ms latency

## ⚠️ Free Tier Limitations

The F1 (Free) tier is perfect for a lightweight backend but has:
- 60 minutes/day compute limit
- Cold starts after 20 min idle (first request takes 10-20 sec)
- 1 GB RAM, 1 GB storage

**Need more?** Change `app_service_sku = "B1"` for ~$13/month with:
- Unlimited compute
- Always-on (no cold starts)
- 1.75 GB RAM, 10 GB storage

## 📋 Requirements

1. Azure account (free tier available)
2. Install: Azure CLI, Terraform, Docker
3. Your API keys: Google API, HuggingFace

## 🔑 Setup terraform.tfvars

```hcl
project_name = "gro-ai"
location = "West Europe"
app_service_sku = "F1"  # Change to "B1" if you need always-on
debug = "False"
google_api_key = "YOUR_KEY_HERE"
huggingface_token = "YOUR_TOKEN_HERE"
```

## ✅ What Gets Deployed

1. **Resource Group** - Container for all resources
2. **App Service (F1)** - Runs your FastAPI backend
3. **Cosmos DB (MongoDB API)** - Serverless database
4. **Container Registry** - Stores your Docker image
5. **All in West Europe** - Accessible from Italy & Qatar

## 🎯 After Deployment

Your API will be available at:
- `https://gro-ai-app.azurewebsites.net`
- Docs: `https://gro-ai-app.azurewebsites.net/docs`
- Health: `https://gro-ai-app.azurewebsites.net/health`

## 📊 Monitoring Costs

Set up billing alerts in Azure Portal:
1. Go to Cost Management + Billing
2. Set alerts at $10, $20, $50
3. Monitor daily usage

## 🔄 Update Your App

```bash
cd backend
docker build -t <acr-url>/gro-backend:latest .
docker push <acr-url>/gro-backend:latest
az webapp restart --name gro-ai-app --resource-group gro-ai-rg
```

## 🗑️ Cleanup

```bash
cd cloud
terraform destroy
```

Type `yes` to delete everything.

---

**Questions?** Check the full [README.md](./README.md) for detailed instructions!

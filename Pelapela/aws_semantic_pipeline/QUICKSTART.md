# 🚀 Quick Start Guide

Get your AWS Semantic Concept Pipeline up and running in 15 minutes!

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Terraform** installed (v1.0+)
4. **Python** 3.11+ with pip
5. **Git** for cloning the repository

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd aws_semantic_pipeline

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

## Step 2: Deploy Infrastructure

```bash
# Deploy to dev environment
python deploy.py --environment dev

# Or deploy with sample data
python deploy.py --environment dev --upload-data ../JLPT/
```

This will:
- ✅ Create S3 bucket for data storage
- ✅ Deploy OpenSearch Serverless collection
- ✅ Set up Lambda functions
- ✅ Configure API Gateway
- ✅ Set up EventBridge triggers

## Step 3: Test the Pipeline

```bash
# Run the demo (replace with your API URL)
python demo.py https://abc123.execute-api.us-east-1.amazonaws.com/prod

# Or test individual components
python -c "
from client.semantic_client import create_client
client = create_client('https://abc123.execute-api.us-east-1.amazonaws.com/prod')
print(client.get_statistics())
"
```

## Step 4: Upload Your Data

```bash
# Upload your Japanese learning data
aws s3 cp your_data.json s3://pelapela-semantic-raw-data-xxxxx/sample_data/

# The pipeline will automatically:
# 1. Trigger concept extraction
# 2. Process with Bedrock AI
# 3. Store in OpenSearch
# 4. Make available via API
```

## Step 5: Build Your Application

```python
from client.semantic_client import create_client, create_analyzer

# Initialize client
client = create_client('https://abc123.execute-api.us-east-1.amazonaws.com/prod')
analyzer = create_analyzer('https://abc123.execute-api.us-east-1.amazonaws.com/prod')

# Search for concepts
results = client.search_concepts("topic particles", limit=10)

# Generate learning paths
path = client.get_learning_path("は", target_level="N4")

# Analyze progress
analysis = analyzer.analyze_learning_progress(["jlpt_1", "jlpt_2"])
```

## 🎯 What You Get

### ✅ **Intelligent Concept Discovery**
- AI-powered concept extraction from raw data
- Automatic normalization and categorization
- JLPT level detection
- Related concept identification

### ✅ **Vector Similarity Search**
- Find similar concepts instantly
- Filter by category, level, or source
- Semantic understanding of Japanese grammar

### ✅ **Learning Path Generation**
- AI-generated study sequences
- Progressive difficulty levels
- Personalized recommendations

### ✅ **Advanced Analytics**
- Learning progress tracking
- Concept clustering
- Study time estimation
- Gap analysis

## 🔧 Configuration

### Environment Variables
```bash
export AWS_REGION=us-east-1
export PROJECT_NAME=pelapela-semantic
export ENVIRONMENT=dev
```

### Customization
Edit `infrastructure/variables.tf` to customize:
- AWS region
- Project name
- Resource limits
- Cost optimization settings

## 📊 Cost Estimation

| Component | Monthly Cost (1K concepts) |
|-----------|---------------------------|
| OpenSearch Serverless | ~$15-30 |
| Bedrock Agents | ~$20-50 |
| S3 Storage | ~$1-5 |
| Lambda/API Gateway | ~$5-15 |
| **Total** | **~$40-100** |

## 🚨 Troubleshooting

### Common Issues

**1. Terraform fails to apply**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify region access
aws opensearchserverless list-collections
```

**2. Lambda functions fail**
```bash
# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/pelapela-semantic"

# Verify IAM permissions
aws iam get-role --role-name pelapela-semantic-lambda-role
```

**3. API Gateway returns 500**
```bash
# Check Lambda function status
aws lambda get-function --function-name pelapela-semantic-concept-query

# Test OpenSearch connectivity
curl -X GET "https://your-opensearch-endpoint/_cluster/health" \
  -H "Authorization: AWS4-HMAC-SHA256 ..."
```

### Getting Help

1. **Check logs**: CloudWatch → Log groups → `/aws/lambda/pelapela-semantic-*`
2. **Monitor costs**: AWS Cost Explorer → Services → Filter by tags
3. **Test API**: Use the demo script or curl commands
4. **Review docs**: See `README.md` for detailed documentation

## 🎉 Next Steps

1. **Upload your data**: Start with a small dataset to test
2. **Explore the API**: Use the demo script to understand capabilities
3. **Build integrations**: Connect to your existing applications
4. **Scale up**: Add more data sources and users
5. **Optimize**: Monitor performance and costs

## 📞 Support

- **Documentation**: See `README.md` and `docs/` folder
- **Examples**: Check `demo.py` and `client/` folder
- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions

---

**Ready to revolutionize your Japanese learning concept network? Let's build something amazing! 🚀** 
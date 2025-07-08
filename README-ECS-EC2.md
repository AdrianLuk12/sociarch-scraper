# Movie Scraper ECS Deployment with EC2 (AWS Console Guide)

This guide covers deploying the movie scraper on **Amazon ECS with EC2 instances** using the **AWS Console** for daily scheduled runs.

## ECS EC2 vs Fargate Comparison

| Feature | ECS with EC2 | ECS with Fargate |
|---------|--------------|------------------|
| **Cost** | $10-15/month (t3.medium always running) | $3-5/month (pay per task run) |
| **Control** | Full EC2 control, can SSH, install tools | No server access |
| **Scaling** | Manual EC2 scaling | Automatic |
| **Maintenance** | OS updates, security patches | Fully managed |
| **Startup Time** | Faster (instances pre-warmed) | Slower (cold start) |
| **Best For** | Frequent runs, debugging needs | Infrequent runs, simplicity |

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Docker** installed locally to build the image
3. **Supabase** credentials ready

> 💡 **Console-Only Deployment**: This guide uses AWS Console exclusively. No AWS CLI required except for the ECR push commands (which are provided by the Console).

## Step-by-Step AWS Console Deployment

### Step 1: Create ECR Repository

1. Go to **Amazon ECR** in AWS Console
2. Click **"Create repository"**
3. Set **Repository name**: `sociarch/movie-scraper`
4. Leave other settings as default
5. Click **"Create repository"**
6. **Note the repository URI** (you'll need it later)

### Step 2: Build and Push Docker Image via Console

1. **Build the image locally** (Apple Silicon compatible):
   ```bash
   chmod +x build-local.sh
   ./build-local.sh
   ```
   
   This creates a local Docker image tagged as `sociarch/movie-scraper:latest`

2. **Get your ECR push commands from AWS Console**:
   - Go to **Amazon ECR** → **Repositories** → `sociarch/movie-scraper`
   - Click **"View push commands"** button
   - Copy and run the commands shown (they'll look like this):

3. **Example push commands** (replace with your actual values):
   ```bash
   # Login to ECR (from console)
   aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com
   
   # Tag your local image (note: use sociarch/movie-scraper as built by build-local.sh)
   docker tag sociarch/movie-scraper:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/sociarch/movie-scraper:latest
   
   # Push to ECR
   docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/sociarch/movie-scraper:latest
   ```

4. **Alternative: Manual upload via Console** (if you prefer not to use CLI at all):
   - Some AWS regions support direct console upload for smaller images
   - Check if "Push image" button is available in your ECR repository

### Step 3: Store Supabase Credentials in Systems Manager

1. Go to **AWS Systems Manager** → **Parameter Store**
2. Click **"Create parameter"**
3. Create first parameter:
   - **Name**: `/movie-scraper/supabase-url`
   - **Type**: `SecureString`
   - **Value**: Your Supabase URL
4. Create second parameter:
   - **Name**: `/movie-scraper/supabase-key`
   - **Type**: `SecureString`
   - **Value**: Your Supabase anon key

> 💡 **Note**: Keep the parameter names as `/movie-scraper/...` (without the "sociarch/" prefix) for consistency with the application code.

### Step 4: Create ECS Cluster with EC2

1. Go to **Amazon ECS** → **Clusters**
2. Click **"Create Cluster"**
3. Choose **"EC2 Linux + Networking"**
4. Configure cluster:
   - **Cluster name**: `movie-scraper-cluster`
   - **EC2 instance type**: `t3.medium` (2 vCPU, 4GB RAM)
   - **Number of instances**: `1`
   - **Key pair**: Select or create one (for SSH access)
   - **VPC**: Use default or select existing
   - **Subnets**: Select public subnets
   - **Security group**: Create new or use existing (allow outbound HTTPS)
   - **Auto assign public IP**: Enable
5. Click **"Create"**

### Step 5: Create IAM Roles

#### Task Execution Role
1. Go to **IAM** → **Roles** → **Create role**
2. Select **"AWS service"** → **"Elastic Container Service"** → **"Elastic Container Service Task"**
3. Attach policy: `AmazonECSTaskExecutionRolePolicy`
4. **Role name**: `movie-scraper-execution-role`

#### Task Role (for accessing SSM Parameters)
1. **Create the custom policy first**:
   - Go to **IAM** → **Policies** → **Create policy**
   - Click **"JSON"** tab
   - Replace the content with:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ssm:GetParameters",
           "ssm:GetParameter"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
   - Click **"Next: Tags"** (skip tags)
   - Click **"Next: Review"**
   - **Policy name**: `MovieScraperSSMAccess`
   - **Description**: `Allows access to SSM parameters for movie scraper`
   - Click **"Create policy"**

2. **Create the role**:
   - Go to **IAM** → **Roles** → **Create role**
   - Select **"AWS service"** → **"Elastic Container Service"** → **"Elastic Container Service Task"**
   - Click **"Next: Permissions"**
   - Search for and select: `MovieScraperSSMAccess` (the policy you just created)
   - Click **"Next: Tags"** (skip tags)
   - Click **"Next: Review"**
   - **Role name**: `movie-scraper-task-role`
   - **Description**: `Task role for movie scraper to access SSM parameters`
   - Click **"Create role"**

> 💡 **Note**: Using `"Resource": "*"` is simpler for console creation. For production, you can later edit the policy to restrict to specific parameter paths: `arn:aws:ssm:us-east-2:YOUR_ACCOUNT_ID:parameter/movie-scraper/*`

### Step 6: Create Task Definition

1. Go to **ECS** → **Task Definitions** → **Create new Task Definition**
2. Select **"EC2"** launch type
3. Configure task definition:
   - **Task Definition Name**: `movie-scraper-task`
   - **Task Role**: `movie-scraper-task-role`
   - **Task execution role**: `movie-scraper-execution-role`
   - **Network Mode**: `bridge`
   - **Task memory**: `2048` MiB (2GB recommended for reliable browser startup)
   - **Task CPU**: `1024` CPU units (1 vCPU recommended)

4. **Add Container**:
   - **Container name**: `movie-scraper`
   - **Image**: `YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/sociarch/movie-scraper:latest` (use your actual ECR URI from Step 2)
   - **Memory Limits**: Soft limit `2048` MiB
   - **Port mappings**: None needed
   - **Environment variables**:
     - `HEADLESS_MODE`: `true`
     - `NO_SANDBOX`: `true`
     - `SCRAPER_DELAY`: `2`
     - `SCRAPER_TIMEOUT`: `60`
     - `SUPABASE_SCHEMA`: `knowledge_base`
   - **Secrets** (from Parameter Store):
     - `SUPABASE_URL`: `arn:aws:ssm:us-east-2:YOUR_ACCOUNT_ID:parameter/movie-scraper/supabase-url`
     - `SUPABASE_KEY`: `arn:aws:ssm:us-east-2:YOUR_ACCOUNT_ID:parameter/movie-scraper/supabase-key`

5. **Log Configuration**:
   - **Log driver**: `awslogs`
   - **Log group**: `/ecs/movie-scraper` (create if doesn't exist)
   - **Log region**: `us-east-2`
   - **Log stream prefix**: `ecs`

6. Click **"Create"**

### Step 7: Create EventBridge Rule for Scheduling

1. Go to **Amazon EventBridge** → **Rules** → **Create rule**
2. Configure rule:
   - **Name**: `movie-scraper-daily-trigger`
   - **Description**: `Daily trigger for movie scraper`
   - **Event bus**: `default`
   - **Rule type**: `Schedule`
   - **Schedule expression**: `cron(0 22 * * ? *)` (6 AM HK time)

3. **Select target**:
   - **Target type**: `AWS service`
   - **Service**: `Amazon ECS`
   - **ECS cluster**: `movie-scraper-cluster`
   - **Task definition**: `movie-scraper-task`
   - **Launch type**: `EC2`
   - **Task count**: `1`
   - **Task role**: `movie-scraper-task-role`

4. **Create new role for EventBridge**:
   - Let AWS create the role automatically
   - Or create manually with ECS task execution permissions

5. Click **"Create"**

### Step 8: Test the Setup

1. **Manual test run**:
   - Go to **ECS** → **Clusters** → `movie-scraper-cluster` → **Tasks** tab
   - Click **"Run new task"**
   - **Launch type**: `EC2`
   - **Task definition**: `movie-scraper-task`
   - **Cluster**: `movie-scraper-cluster`
   - **Number of tasks**: `1`
   - Click **"Run task"**

2. **Monitor the task**:
   - Watch task status in ECS console
   - Check CloudWatch logs at `/ecs/movie-scraper`
   - Task should complete and stop automatically

### Step 9: Monitoring and Troubleshooting

#### CloudWatch Logs
- Go to **CloudWatch** → **Logs** → **Log groups** → `/ecs/movie-scraper`
- View real-time logs during task execution

#### ECS Task Monitoring
- Go to **ECS** → **Clusters** → `movie-scraper-cluster` → **Tasks**
- Check running and stopped tasks
- View task details and logs

#### Common Issues and Solutions

1. **Task fails to start**:
   - Check EC2 instances are running and healthy
   - Verify security groups allow outbound HTTPS
   - Check IAM roles have correct permissions

2. **Out of memory errors**:
   - Increase task memory limit (try 2048 MiB)
   - Consider upgrading EC2 instance type

3. **Browser timeout errors ("timed out during opening handshake")**:
   - **Most common issue**: Browser startup timeout in containerized environment
   - **Primary solution**: Increase ECS task resources:
     - **Memory**: Change from 1024 MiB to 2048 MiB (or higher)
     - **CPU**: Change from 512 to 1024 CPU units (or higher)
   - **Why this happens**: Chrome needs more time/resources to start in containers
   - **Automatic retry**: The scraper now includes 3 retry attempts with progressive timeouts
   - **Check logs**: Look for "Browser initialization attempt X/3" messages

4. **Browser connection failures ("Failed to connect to browser")**:
   - **Most common cause**: Container running as root
   - **Solution**: Rebuild image with latest Dockerfile (includes non-root user)
   - **Verify**: Check CloudWatch logs for "Starting browser with headless=true, no_sandbox=True"
   - **Environment**: Ensure `NO_SANDBOX=true` is set in task definition
   - **Memory**: Ensure minimum 2GB memory allocation for Chrome

5. **"no matching manifest for linux/amd64" error**:
   - **Cause**: Image built for wrong architecture (arm64 instead of amd64)
   - **Check**: Run `./check-image.sh` to verify image architecture
   - **Solution**: Rebuild with: `./build-local.sh` (uses docker buildx)
   - **Verify**: Image should show "Architecture: amd64" after rebuild
   - **Note**: Docker buildx is required for cross-platform builds on Apple Silicon

6. **SSM parameter access denied**:
   - Verify task role has SSM permissions
   - Check parameter names match exactly

### Step 10: Cost Optimization

#### Auto Scaling (Optional)
To reduce costs, set up auto scaling:

1. Go to **EC2** → **Auto Scaling Groups**
2. Find the ASG created by ECS
3. Set **Desired capacity**: `0` (during non-running hours)
4. Create scheduled scaling actions:
   - Scale up to 1 instance at 9:30 PM UTC (30 min before scraper)
   - Scale down to 0 instances at 11:30 PM UTC (30 min after scraper)

#### Spot Instances (Advanced)
For further cost savings:
1. Recreate cluster with Spot instances
2. Use mixed instance types
3. Accept potential interruptions

## Maintenance Tasks

### Updating the Application

#### After Code Changes (like browser fixes)
1. **Rebuild the Docker image**:
   ```bash
   ./build-local.sh
   ```

2. **Push to ECR** (get commands from AWS Console):
   ```bash
   # Example commands (replace with your actual values)
   aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com
   docker tag sociarch/movie-scraper:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/sociarch/movie-scraper:latest
   docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/sociarch/movie-scraper:latest
   ```

3. **Force new deployment** (no task definition changes needed):
   - Go to **ECS** → **Clusters** → `movie-scraper-cluster` → **Services**
   - If you have a service: Click **"Update Service"** → **"Force new deployment"**
   - For scheduled tasks: Next run will automatically use the new image

4. **Test manually**:
   - Run a manual ECS task to verify the browser connection works
   - Check CloudWatch logs for successful browser initialization

### Monitoring Cluster Health
1. Check EC2 instances in ECS console
2. Monitor CloudWatch metrics
3. Set up alarms for failures

### Security Updates
1. Regularly update EC2 instances (or use managed AMIs)
2. Update Docker base image
3. Rotate Supabase credentials in Parameter Store

## Cost Comparison Summary

**ECS with EC2**: ~$10-15/month
- t3.medium instance: ~$12/month
- ECS service: Free
- CloudWatch logs: ~$0.50/month
- ECR storage: ~$0.10/month

**ECS with Fargate**: ~$3-5/month
- Task execution (30 min daily): ~$2-3/month
- CloudWatch logs: ~$0.50/month
- ECR storage: ~$0.10/month

## When to Choose EC2 over Fargate

Choose **ECS with EC2** when:
- ✅ You need to debug by SSH'ing into instances
- ✅ You plan to run multiple applications on the same cluster
- ✅ You need specific EC2 features or instance types
- ✅ You want to optimize costs for frequent, predictable workloads
- ✅ You need faster startup times (no cold start)

Choose **ECS with Fargate** when:
- ✅ You want minimal operational overhead
- ✅ You have infrequent or unpredictable workloads
- ✅ You prefer pay-per-use pricing
- ✅ You don't need server-level access

Your movie scraper is now running on ECS with EC2 instances! 
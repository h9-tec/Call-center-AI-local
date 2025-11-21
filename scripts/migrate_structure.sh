#!/bin/bash
# Script to migrate existing code to new structure

set -e

echo "🚀 Migrating Call Center AI to production-ready structure..."

# Create backup
echo "📦 Creating backup..."
cp -r . ../call-center-ai-backup-$(date +%Y%m%d_%H%M%S)

# Update imports in Python files
echo "🔧 Updating imports..."

# Update imports from services.audio_processor to app.services.audio_processor
find . -name "*.py" -type f -exec sed -i 's/from services\./from app.services./g' {} \;
find . -name "*.py" -type f -exec sed -i 's/import services\./import app.services./g' {} \;

# Update imports for main app
find . -name "*.py" -type f -exec sed -i 's/from server import/from app.main import/g' {} \;
find . -name "*.py" -type f -exec sed -i 's/import server/import app.main/g' {} \;

# Update config imports
find . -name "*.py" -type f -exec sed -i 's/from config import/from app.core.config import/g' {} \;
find . -name "*.py" -type f -exec sed -i 's/import config/import app.core.config/g' {} \;

# Fix specific service imports
echo "🔄 Fixing service-specific imports..."

# Update twilio_voice_handler imports
if [ -f "app/services/telephony/twilio_handler.py" ]; then
    sed -i 's/from services.twilio_bridge/from app.services.telephony.twilio_bridge/g' \
        app/services/telephony/twilio_handler.py
fi

# Update audio processor location references
if [ -f "app/services/telephony/twilio_handler.py" ]; then
    sed -i 's/from services.audio_processor/from app.services.audio_processor/g' \
        app/services/telephony/twilio_handler.py
fi

# Clean up old directories
echo "🧹 Cleaning up old structure..."
if [ -d "services" ] && [ -z "$(ls -A services)" ]; then
    rmdir services
fi

# Update Docker and deployment files
echo "📋 Updating deployment configurations..."

# Update Dockerfile paths
if [ -f "deployments/docker/Dockerfile" ]; then
    sed -i 's|CMD \["python", "server.py"\]|CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]|g' \
        deployments/docker/Dockerfile
    sed -i 's|COPY server.py|COPY app/|g' deployments/docker/Dockerfile
fi

# Update docker-compose
for compose_file in deployments/docker/docker-compose*.yml; do
    if [ -f "$compose_file" ]; then
        sed -i 's|python server.py|uvicorn app.main:app --host 0.0.0.0 --port 8000|g' "$compose_file"
        sed -i 's|./server.py|./app/main.py|g' "$compose_file"
    fi
done

# Create .gitkeep files for empty directories
echo "📂 Ensuring directory structure..."
find . -type d -empty -not -path "./.git/*" -exec touch {}/.gitkeep \;

# Update relative paths in scripts
echo "📝 Updating script paths..."
find scripts -name "*.sh" -type f -exec sed -i 's|python server.py|python -m app.main|g' {} \;
find scripts -name "*.py" -type f -exec sed -i 's|sys.path.append(".")|sys.path.append("..")|g' {} \;

echo "✅ Migration complete!"
echo ""
echo "📌 Next steps:"
echo "1. Review the changes made to your codebase"
echo "2. Test the application: make run-dev"
echo "3. Run tests: make test"
echo "4. Update any hardcoded paths in configuration files"
echo "5. Commit the changes: git add . && git commit -m 'Migrate to production structure'"
echo ""
echo "🔍 Check for any remaining issues:"
echo "   grep -r 'from services\\.' --include='*.py' ."
echo "   grep -r 'server.py' --include='*.py' --include='*.sh' --include='*.yml' ."

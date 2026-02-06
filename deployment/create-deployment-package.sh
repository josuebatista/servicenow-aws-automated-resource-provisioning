#######################################
# chmod +x create-deployment-package.sh
#######################################

#!/bin/bash

# Create a distributable deployment package

PACKAGE_NAME="servicenow-aws-integration-v1.0"
PACKAGE_DIR="$PACKAGE_NAME"

echo "Creating deployment package: $PACKAGE_NAME"

# Create package directory
mkdir -p "$PACKAGE_DIR"

# Copy required files
cp deploy.sh "$PACKAGE_DIR/"
cp spa-creator-stack.yaml "$PACKAGE_DIR/"
cp spa-creator-policy.json "$PACKAGE_DIR/"
cp spa-creator-lambda.py "$PACKAGE_DIR/"
cp backend-list-bucket.py "$PACKAGE_DIR/"
cp backend-upload-url.py "$PACKAGE_DIR/"
cp backend-user-info.py "$PACKAGE_DIR/"
cp test-complete-flow.sh "$PACKAGE_DIR/"
cp cleanup-resources.sh "$PACKAGE_DIR/"
cp README.md "$PACKAGE_DIR/"
cp DEPLOYMENT-GUIDE.md "$PACKAGE_DIR/"
cp API-REFERENCE.md "$PACKAGE_DIR/"
cp SERVICENOW-INTEGRATION.md "$PACKAGE_DIR/"
cp DEMO-SCRIPT.md "$PACKAGE_DIR/"

# Make scripts executable
chmod +x "$PACKAGE_DIR/"*.sh

# Create archive
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_DIR"
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_DIR" > /dev/null

# Cleanup
rm -rf "$PACKAGE_DIR"

echo ""
echo "✅ Deployment packages created:"
echo "  - ${PACKAGE_NAME}.tar.gz"
echo "  - ${PACKAGE_NAME}.zip"
echo ""
echo "To deploy in a new AWS account:"
echo "  1. Extract the package"
echo "  2. cd $PACKAGE_NAME"
echo "  3. ./deploy.sh"

EOF

chmod +x create-deployment-package.sh
echo "✅ create-deployment-package.sh created"
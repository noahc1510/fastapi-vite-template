#!/bin/bash

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Project Initialization Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get project name
read -p "$(echo -e ${YELLOW}Enter project name \(e.g., my-awesome-app\): ${NC})" PROJECT_NAME

if [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}Error: Project name cannot be empty${NC}"
    exit 1
fi

# Validate project name (lowercase, alphanumeric, hyphens only)
if ! [[ "$PROJECT_NAME" =~ ^[a-z0-9-]+$ ]]; then
    echo -e "${RED}Error: Project name should only contain lowercase letters, numbers, and hyphens${NC}"
    exit 1
fi

# Get project description
read -p "$(echo -e ${YELLOW}Enter project description \(optional\): ${NC})" PROJECT_DESC

if [ -z "$PROJECT_DESC" ]; then
    PROJECT_DESC="A FastAPI + Vite project"
fi

# Convert project name to different formats
PROJECT_NAME_SNAKE=$(echo "$PROJECT_NAME" | tr '-' '_')  # my_awesome_app
PROJECT_NAME_TITLE=$(echo "$PROJECT_NAME" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')  # My Awesome App

echo ""
echo -e "${BLUE}Project Configuration:${NC}"
echo -e "  Name (kebab-case): ${GREEN}$PROJECT_NAME${NC}"
echo -e "  Name (snake_case): ${GREEN}$PROJECT_NAME_SNAKE${NC}"
echo -e "  Name (Title Case): ${GREEN}$PROJECT_NAME_TITLE${NC}"
echo -e "  Description: ${GREEN}$PROJECT_DESC${NC}"
echo ""

read -p "$(echo -e ${YELLOW}Proceed with these settings? \(y/N\): ${NC})" CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Initialization cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Updating project files...${NC}"

# Function to replace in file with backup
replace_in_file() {
    local file=$1
    local old=$2
    local new=$3

    if [ -f "$file" ]; then
        # Check if running on macOS or Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|$old|$new|g" "$file"
        else
            sed -i "s|$old|$new|g" "$file"
        fi
        echo -e "  ${GREEN}✓${NC} Updated: $file"
    else
        echo -e "  ${YELLOW}⚠${NC} Skipped (not found): $file"
    fi
}

# 1. Update pyproject.toml
replace_in_file "pyproject.toml" "name = \"fastapi-vite-template\"" "name = \"$PROJECT_NAME\""
replace_in_file "pyproject.toml" "description = \"Add your description here\"" "description = \"$PROJECT_DESC\""

# 2. Update frontend/package.json
replace_in_file "frontend/package.json" "\"name\": \"vite-project\"" "\"name\": \"$PROJECT_NAME-frontend\""

# 3. Update Makefile
replace_in_file "Makefile" "DOCKER_IMAGE := fastapi-vite-app" "DOCKER_IMAGE := $PROJECT_NAME"
replace_in_file "Makefile" "DOCKER_CONTAINER := fastapi-vite-container" "DOCKER_CONTAINER := $PROJECT_NAME-container"

# 4. Update app/api.py
replace_in_file "app/api.py" "title=\"FastAPI Vite Template API\"" "title=\"$PROJECT_NAME_TITLE API\""
replace_in_file "app/api.py" "description=\"基础 FastAPI 服务，内置 CORS 与 Swagger 文档\"" "description=\"$PROJECT_DESC\""

# 5. Update frontend/index.html
replace_in_file "frontend/index.html" "<title>vite-project</title>" "<title>$PROJECT_NAME_TITLE</title>"

# 6. Update README.md (create if not exists)
if [ ! -f "README.md" ] || [ ! -s "README.md" ]; then
    cat > README.md << EOF
# $PROJECT_NAME_TITLE

$PROJECT_DESC

## 🚀 Quick Start

\`\`\`bash
# Install dependencies
make install

# Run development server
make dev

# Or run backend and frontend separately
make backend-dev  # Terminal 1
make frontend-dev # Terminal 2
\`\`\`

## 📦 Available Commands

Run \`make help\` to see all available commands.

## 🛠 Tech Stack

- **Backend**: FastAPI + Python 3.13
- **Frontend**: React + Vite + TypeScript
- **Database**: PostgreSQL + SQLAlchemy
- **Package Manager**: uv (backend) + bun (frontend)

## 📝 License

MIT
EOF
    echo -e "  ${GREEN}✓${NC} Created: README.md"
else
    # Update existing README.md title
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "1s/.*/# $PROJECT_NAME_TITLE/" README.md
    else
        sed -i "1s/.*/# $PROJECT_NAME_TITLE/" README.md
    fi
    echo -e "  ${GREEN}✓${NC} Updated: README.md"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ✓ Initialization Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Review the changes in the files above"
echo -e "  2. Run ${GREEN}make install${NC} to install dependencies"
echo -e "  3. Run ${GREEN}make dev${NC} to start the server"
echo ""

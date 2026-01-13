#!/bin/bash
# Helper script to set ANTHROPIC_API_KEY

echo "Anthropic API Key Setup"
echo "======================"
echo ""
echo "Please enter your Anthropic API key (get it from https://console.anthropic.com/settings/keys):"
read -s API_KEY

if [ -z "$API_KEY" ]; then
    echo "Error: API key cannot be empty"
    exit 1
fi

echo ""
echo "Where would you like to store the API key?"
echo "1. Environment variable (export ANTHROPIC_API_KEY=...)"
echo "2. .env file in project root"
echo "3. ~/.anthropic_api_key file"
echo "4. .ralph/config.json"
read -p "Choice (1-4): " choice

case $choice in
    1)
        echo "export ANTHROPIC_API_KEY=$API_KEY" >> ~/.zshrc
        export ANTHROPIC_API_KEY=$API_KEY
        echo "✅ Added to ~/.zshrc and current session"
        echo "Run: source ~/.zshrc (or restart terminal)"
        ;;
    2)
        echo "ANTHROPIC_API_KEY=$API_KEY" > .env
        echo "✅ Created .env file"
        ;;
    3)
        echo "$API_KEY" > ~/.anthropic_api_key
        chmod 600 ~/.anthropic_api_key
        echo "✅ Created ~/.anthropic_api_key"
        ;;
    4)
        mkdir -p .ralph
        if [ -f .ralph/config.json ]; then
            # Update existing config
            python3 -c "
import json
with open('.ralph/config.json', 'r') as f:
    config = json.load(f)
if 'anthropic' not in config:
    config['anthropic'] = {}
config['anthropic']['apiKey'] = '$API_KEY'
with open('.ralph/config.json', 'w') as f:
    json.dump(config, f, indent=2)
"
        else
            # Create new config
            python3 -c "
import json
config = {'anthropic': {'apiKey': '$API_KEY'}}
with open('.ralph/config.json', 'w') as f:
    json.dump(config, f, indent=2)
"
        fi
        echo "✅ Added to .ralph/config.json"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Setup complete! You can now run Ralph."

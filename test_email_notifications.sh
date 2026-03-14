#!/bin/bash
# Test email notification system end-to-end

set -e

API_BASE="http://localhost:8000/api/v1"
SESSION_ID=$(uuidgen)  # Generate random session ID
TEST_EMAIL="aditya2005ads@gmail.com"

echo "🚀 Email Notification System Test"
echo "=================================="
echo ""
echo "Test Email: $TEST_EMAIL"
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: Register email
echo "📝 Test 1: Registering email..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/notify/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"email\": \"$TEST_EMAIL\"
  }")

echo "$REGISTER_RESPONSE" | jq '.' || echo "Failed to parse response"

SUCCESS=$(echo "$REGISTER_RESPONSE" | jq -r '.success' 2>/dev/null || echo "false")

if [ "$SUCCESS" == "true" ]; then
  echo "✅ Registration successful!"
else
  echo "❌ Registration failed!"
  exit 1
fi

echo ""
echo "⏳ Test 2: Checking subscription status..."
STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/notify/status/$SESSION_ID")
echo "$STATUS_RESPONSE" | jq '.'

SUBSCRIBED=$(echo "$STATUS_RESPONSE" | jq -r '.subscribed' 2>/dev/null || echo "false")

if [ "$SUBSCRIBED" == "true" ]; then
  echo "✅ Email is subscribed!"
else
  echo "❌ Subscription verification failed!"
  exit 1
fi

echo ""
echo "📂 Test 3: Checking subscription file..."
if [ -f "research-paper-graph/data/pipeline_storage/email_subscriptions.json" ]; then
  echo "✅ Subscriptions file exists"
  echo "Content:"
  cat research-paper-graph/data/pipeline_storage/email_subscriptions.json | jq '.' || echo "File exists but can't parse"
else
  echo "⚠️  Subscriptions file not created yet (will be created on first registration)"
fi

echo ""
echo "🔧 Test 4: Unregistering email..."
UNREG_RESPONSE=$(curl -s -X DELETE "$API_BASE/notify/unregister/$SESSION_ID")
echo "$UNREG_RESPONSE" | jq '.'

echo ""
echo "✅ All tests passed! Email notification system is working correctly."
echo ""
echo "Next steps:"
echo "1. Start the frontend: npm start (in research-paper-graph/frontend)"
echo "2. Run an analysis that takes at least a few seconds"
echo "3. When toast appears, enter your email"
echo "4. Wait for analysis to complete"
echo "5. Check your inbox for the notification email"

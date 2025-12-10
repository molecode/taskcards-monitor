# TaskCards API Authentication Flow

## Overview

TaskCards uses a visitor-based authentication system with GraphQL API for data access and REST API for permissions.

## Complete Authentication Flow

### For Private Boards with View Token

```
1. Create Visitor (GraphQL Mutation)
   POST https://www.taskcards.de/graphql
   Headers: Content-Type: application/json
   Body: {"query": "mutation { createVisitor { id } }"}
   Response: {"data": {"createVisitor": {"id": "VISITOR_ID"}}}

2. Grant Access (REST API)
   POST https://www.taskcards.de/api/boards/{BOARD_ID}/permissions/{VIEW_TOKEN}/accesses
   Headers:
     - Content-Type: application/json
     - x-token: VISITOR_ID
   Body: {"password":""}
   Response: 201 Created

   Note: The password field is required (empty string for boards without password protection)

3. Fetch Board Data (GraphQL Query)
   POST https://www.taskcards.de/graphql
   Headers:
     - Content-Type: application/json
     - x-token: VISITOR_ID
   Body: {"variables": {"id": "BOARD_ID"}, "query": "query($id:String!){board(id:$id){...}}"}
   Response: Full board data with lists and cards
```

### For Public Boards

```
1. Create Visitor (same as above)
2. Skip the permissions/accesses call (not needed for public boards)
3. Fetch Board Data (same as above)
```

## Key Insights

- **x-token**: The visitor ID returned from `createVisitor` is used as the authentication token
- **View Token**: The token in the URL (`?token=...`) must be used in the REST API call to grant access
- **Board ID**: Available in the URL path (`/board/{BOARD_ID}/view`)
- **Stateless**: Each visitor session is independent; tokens can be reused for the session duration

## Testing with curl

```bash
# Step 1: Create visitor
VISITOR_ID=$(curl -s 'https://www.taskcards.de/graphql' \
  -H 'Content-Type: application/json' \
  --data '{"query":"mutation { createVisitor { id } }"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['data']['createVisitor']['id'])")

echo "Visitor ID: $VISITOR_ID"

# Step 2: Grant access (for private boards)
curl -s 'https://www.taskcards.de/api/boards/BOARD_ID/permissions/VIEW_TOKEN/accesses' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "x-token: $VISITOR_ID"

# Step 3: Fetch board data
curl -s 'https://www.taskcards.de/graphql' \
  -H 'Content-Type: application/json' \
  -H "x-token: $VISITOR_ID" \
  --data '{"variables":{"id":"BOARD_ID"},"query":"query($id:String!){board(id:$id){id name lists{id name}cards{id title}}}"}' | \
  python3 -m json.tool
```

## Implementation Notes

1. **No Browser Automation Needed**: The entire flow can be implemented with HTTP requests
2. **Session Duration**: Visitor tokens appear to have a limited lifetime (session-based)
3. **Error Handling**:
   - If access is denied, the board query will return `BOARD_ERROR`
   - Invalid visitor IDs will fail authentication
4. **Rate Limiting**: Unknown; should implement reasonable delays between requests

## Benefits of Direct API Access

- ✅ Much faster than browser automation (no browser startup, rendering, etc.)
- ✅ Lower resource usage (no Chromium process)
- ✅ Simpler dependencies (just HTTP client, no Playwright)
- ✅ More reliable (no DOM selectors that might break)
- ✅ Structured data (JSON responses instead of DOM scraping)
- ✅ Works with both public and private boards

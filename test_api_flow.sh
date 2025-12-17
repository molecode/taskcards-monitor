#!/bin/bash

# Test GraphQL introspection to find Card type fields
curl -s -X POST https://www.taskcards.de/graphql \
  -H "Content-Type: application/json" \
  --data-binary @- <<'EOF' | python3 -m json.tool
{
  "query": "query { __type(name: \"Card\") { fields { name type { name kind ofType { name } } } } }"
}
EOF

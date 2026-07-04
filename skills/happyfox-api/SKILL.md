# HappyFox API Skill

Guide for interacting with HappyFox Help Desk APIs.

## Authentication

HappyFox uses **Basic HTTP Authentication** with API Key and Auth Code.

### Environment Variables
```bash
HFOX_API_KEY=<your_api_key>
HFOX_AUTH_CODE=<your_auth_code>
```

Source from `~/.zshrc` if needed (grep for values, don't source directly as it has zsh-specific syntax).

### Making Requests
```bash
curl -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" "https://support.openhands.dev/api/1.1/json/<endpoint>/"
```

## Production Instance

- **URL**: `https://support.openhands.dev`
- **API Base**: `https://support.openhands.dev/api/1.1/json/`

## Available Endpoints

### Contacts/Users

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/` | GET | List all contacts (paginated) |
| `/users/?q=<search>` | GET | Search contacts by name/email/phone |
| `/users/` | POST | Create a new contact |
| `/user/<id>/` | GET | Get single contact by ID |
| `/user/<id>/` | POST | Update existing contact |
| `/contact_groups/` | GET | List all contact groups |

**Create Single Contact Payload:**
```json
{
  "name": "Contact Name",
  "email": "email@example.com",
  "phones": [{"type": "mo", "number": "555-1234"}],
  "is_login_enabled": true
}
```

**Bulk Create/Update Contacts (up to 100):**
```json
[
  {"name": "Contact 1", "email": "contact1@example.com", "is_login_enabled": true},
  {"name": "Contact 2", "email": "contact2@example.com", "is_login_enabled": true}
]
```

**Bulk Response:**
```json
[
  {"email": "contact1@example.com", "success": true, "id": 12},
  {"email": "contact2@example.com", "success": true, "id": 13}
]
```

**Upsert Behavior:** If a contact with the same email exists, the API updates it rather than creating a duplicate.

**Phone Type Codes:** `mo` (mobile), `w` (work), `m` (main), `h` (home), `o` (other/default)

**Contact Response Fields:**
- `id` - Contact ID
- `name` - Contact name
- `email` - Email address
- `phones` - Array of phone objects (see phone type codes above)
- `primary_phone` - Primary phone object
- `contact_groups` - Array of groups
- `tickets_count` - Total ticket count
- `pending_tickets_count` - Open tickets
- `is_login_enabled` - Whether portal login is enabled
- `custom_fields` - Array of custom field values
- `created_at`, `updated_at` - Timestamps (UTC)

### Tickets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tickets/` | GET | List all tickets (paginated) |
| `/tickets/?size=<n>&page=<p>` | GET | Paginated ticket list |
| `/ticket/<id>/` | GET | Get single ticket by ID |
| `/tickets/` | POST | Create a new ticket |

### System Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/categories/` | GET | List ticket categories |
| `/statuses/` | GET | List ticket statuses |
| `/priorities/` | GET | List ticket priorities |
| `/staff/` | GET | List staff/agents |

### Knowledge Base

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/kb/articles/` | GET | List all KB articles |
| `/kb/articles/?size=<n>&page=<p>` | GET | Paginated article list |
| `/kb/article/<id>/` | GET | Get single article by ID |
| `/kb/sections/` | GET | List all KB sections |

**Article Response Fields:**
- `id` - Article ID
- `title` - Article title
- `contents` - HTML content
- `views` - View count
- `section_id`, `section_name` - Parent section
- `tags` - Array of tags
- `last_updated_at` - Timestamp (UTC)
- `full_url` - Public URL
- `attachments` - Array of attachments

## Example Usage

### List Contacts (paginated)
```bash
curl -s -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  "https://support.openhands.dev/api/1.1/json/users/?size=10&page=1" \
  | python3 -m json.tool
```

### Create a Contact
```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  "https://support.openhands.dev/api/1.1/json/users/" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}' \
  | python3 -m json.tool
```

### Search Contacts
```bash
curl -s -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  "https://support.openhands.dev/api/1.1/json/users/?q=john@example.com" \
  | python3 -m json.tool
```

### List Tickets
```bash
curl -s -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  "https://support.openhands.dev/api/1.1/json/tickets/?size=10&page=1" \
  | python3 -m json.tool
```

### List KB Articles (paginated)
```bash
curl -s -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  "https://support.openhands.dev/api/1.1/json/kb/articles/?size=10&page=1" \
  | python3 -m json.tool
```

## API Notes

1. **All timestamps are in UTC**
2. **Pagination**: Use `size` (max 50) and `page` query params
3. **Rate Limiting**: API has rate limits - be mindful of request frequency
4. **Content-Type**: Use `application/json` for POST requests
5. **No welcome email trigger**: The API does not send welcome/password emails when creating contacts. New users must set their password via the forgot password flow.

## Support Portal Password Reset

New contacts must set their password before logging in:

**Password Reset URL:** `https://support.openhands.dev/forgotpassword/`

**Workflow for new users:**
1. Create contact via API with `is_login_enabled: true`
2. Direct user to the password reset URL
3. User enters their email and receives a reset link
4. User sets their password and can then log in

## Documentation Links

- [Main API Docs](https://support.happyfox.com/kb/article/360-api-for-happyfox/)
- [Tickets Endpoint](https://support.happyfox.com/kb/article/1039-tickets-endpoint/)
- [Contacts API](https://support.happyfox.com/kb/article/1092-contacts-and-contact-groups-api-endpoints/)
- [Reports API](https://support.happyfox.com/kb/article/1088-get-reports-via-api/)
- [Create API Key](https://support.happyfox.com/kb/article/476-create-api-key-auth-code-happyfox/)
- [Rate Limiting](https://support.happyfox.com/kb/article/1148-rate-limiting/)

## Troubleshooting

### "Authorization Required" Response
- Verify API key is enabled in HappyFox admin (Apps → Goodies → API)
- Check if the API key has been deactivated
- Ensure you're using the correct instance URL (support.openhands.dev)

### JSON Error Response vs HTML
- JSON `{"error": "..."}` = Authenticated but endpoint issue
- Plain "Authorization Required" text = Authentication or permission failure

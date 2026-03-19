# Access Control Setup Guide

Your website is now configured to support private access control. Here's how to set it up:

## Current Status

**By default, your site is PUBLIC** (for backward compatibility). To make it private, you need to set the `ALLOWED_USERS` environment variable.

## How to Make Your Site Private

### Step 1: Add Environment Variable on Render

1. Go to your Render dashboard
2. Select your web service
3. Go to the **Environment** tab
4. Click **Add Environment Variable**
5. Add the following:

   **Key:** `ALLOWED_USERS`
   
   **Value:** Your email and your collaborators' emails, separated by commas (no spaces)
   
   Example:
   ```
   your-email@example.com,collaborator1@example.com,collaborator2@example.com
   ```

6. Click **Save Changes**
7. Render will automatically redeploy your service

### Step 2: Verify It Works

1. Try accessing your site without logging in - you should be redirected to login
2. Try signing up with an unauthorized email - you should see an error message
3. Log in with an authorized email - you should have full access

## How It Works

- **When `ALLOWED_USERS` is NOT set:** Site is public (anyone can sign up and access)
- **When `ALLOWED_USERS` IS set:** Only the listed emails can:
  - Sign up for new accounts
  - Log in to existing accounts
  - Access any page on the site

## Protected Routes

All routes are now protected except:
- `/login` - Login page (but login will check authorization)
- `/signup` - Signup page (but signup will check authorization)
- `/forgot-password` - Password recovery
- `/reset-password/<token>` - Password reset

## Adding New Collaborators

To add a new collaborator:
1. Go to Render dashboard → Your service → Environment tab
2. Edit the `ALLOWED_USERS` variable
3. Add the new email (comma-separated)
4. Save and redeploy

## Removing Access

To remove someone's access:
1. Edit `ALLOWED_USERS` in Render
2. Remove their email from the list
3. Save and redeploy
4. They will be logged out on their next request and won't be able to log back in

## Local Development

For local development, add to your `.env` file:
```
ALLOWED_USERS=your-email@example.com,collaborator@example.com
```

## Security Notes

- Email addresses are case-insensitive (automatically converted to lowercase)
- The check happens on every request
- Users who are logged in but not authorized will be logged out automatically
- The authorization check happens after login, so unauthorized users can't bypass it

